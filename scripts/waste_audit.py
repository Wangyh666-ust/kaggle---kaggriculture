"""Audit a replay corpus for value that was produced and then thrown away.

Every quantity here is mechanically lost value — it is independent of which
opponent was faced, so it is directly actionable rather than comparative:

  idle       unit-turns spent on PASS (labour that was paid for and not used)
  shed_full  steps where the shed sat at capacity (the night drop destroys overflow)
  end_stock  goods still in shed + worker inventories when the season ended
  weed_lost  tiles that were a PLANT at the end of day d and a WEED at d+1
  no_water   plants that died because consecutive_unwatered reached 2 (subset of weed_lost
             we cannot separate without engine internals, so weed_lost covers it)

All of it is readable from a public replay: each seat's own observation carries
its private shed / seeds / inventories, so the same audit runs on our agent and
on a top team's agent.

Usage:
  .venv/Scripts/python scripts/waste_audit.py replays_v25 --team ReD_MooN_rise
  .venv/Scripts/python scripts/waste_audit.py replays_top replays_ladder_ops
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

SHED_CAP = 100


def grid(farm):
    return [[t for t in row] for row in farm["tiles"]]


def is_plant(t):
    return isinstance(t, dict) and t.get("kind") == "PLANT"


def units_of(action, n_hands):
    """(farmer_action, [hand actions]) with missing slots treated as PASS."""
    if not isinstance(action, dict):
        return ["PASS"], [["PASS"]] * n_hands
    farmer = action.get("farmer") or ["PASS"]
    hands = action.get("hands") or []
    hands = [h if isinstance(h, list) and h else ["PASS"] for h in hands]
    return farmer, hands


def audit(path, team=None):
    d = json.load(open(path, encoding="utf-8"))
    names = d["info"]["TeamNames"]
    steps = d["steps"]
    out = {}
    for p in (0, 1):
        if team and names[p] != team:
            continue
        rec = {"name": names[p], "idle": 0, "unit_turns": 0, "shed_full": 0,
               "weed_lost": 0, "weed_lost_by_day": collections.Counter(),
               "hands_max": 0, "end_stock": 0}
        prev = None
        for i, st in enumerate(steps):
            o = st[p]["observation"]
            farm = o["farms"][p]
            n_hands = len(farm["hands"])
            rec["hands_max"] = max(rec["hands_max"], n_hands)
            farmer, hands = units_of(st[p].get("action"), n_hands)
            acts = [farmer] + hands
            rec["unit_turns"] += len(acts)
            rec["idle"] += sum(1 for a in acts if a and a[0] == "PASS")

            shed = o["private"].get("shed", {})
            if sum(shed.values()) >= SHED_CAP:
                rec["shed_full"] += 1

            if o["hour"] == 23:
                cur = grid(farm)
                if prev is not None:
                    for y in range(len(cur)):
                        for x in range(len(cur[y])):
                            if is_plant(prev[y][x]) and isinstance(cur[y][x], dict) \
                                    and cur[y][x].get("kind") == "WEED":
                                rec["weed_lost"] += 1
                                rec["weed_lost_by_day"][o["day"]] += 1
                prev = cur

        last = steps[-1][p]["observation"]
        end = sum(last["private"].get("shed", {}).values())
        for inv in last["private"].get("inventories", []):
            end += sum(v for v in inv.values() if isinstance(v, (int, float)))
        seeds = sum(last["private"].get("seeds", {}).values())
        rec["end_stock"] = end
        rec["end_seeds"] = seeds
        rec["final_money"] = last["farms"][p]["money"]
        out[p] = rec
    return {"file": os.path.basename(path), "names": names,
            "rewards": d["rewards"], "seats": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--team", default="", help="only audit seats whose name matches")
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args()

    files = []
    for a in args.dirs:
        files += sorted(glob.glob(os.path.join(a, "episode-*-replay.json"))) if os.path.isdir(a) else glob.glob(a)

    recs = []
    for p in files:
        try:
            recs.append(audit(p, args.team or None))
        except Exception as exc:  # noqa: BLE001
            print("skip", p, exc, file=sys.stderr)
    if not recs:
        print("no replays matched")
        return

    rows = [(r, s) for r in recs for s in r["seats"].values()]
    print(f"{len(rows)} seat-games from {len(recs)} replays\n")
    print(f"{'team':26s} {'idle%':>6s} {'unit-turns':>10s} {'shedfull':>8s} "
          f"{'weedlost':>8s} {'endstock':>8s} {'money':>10s}")
    for r, s in sorted(rows, key=lambda t: -(t[1]["money"] if "money" in t[1] else t[1]["final_money"])):
        money = s.get("final_money", 0)
        idle_pct = 100.0 * s["idle"] / max(1, s["unit_turns"])
        print(f"{s['name'][:26]:26s} {idle_pct:5.1f}% {s['unit_turns']:10d} "
              f"{s['shed_full']:8d} {s['weed_lost']:8d} {s['end_stock']:8d} {money:10,.0f}")

    print(f"\n-- aggregates ({len(rows)} seats) --")
    for key, fmt in (("idle", lambda v: f"{v:.0f}"), ("weed_lost", lambda v: f"{v:.1f}"),
                     ("end_stock", lambda v: f"{v:.1f}"), ("shed_full", lambda v: f"{v:.1f}")):
        vals = [s[key] for _, s in rows]
        print(f"  {key:12s} mean {statistics.mean(vals):8.1f}   median {statistics.median(vals):8.1f}   max {max(vals)}")

    if args.detail:
        print("\n-- weed losses by day --")
        for r, s in rows:
            if s["weed_lost"]:
                days = dict(sorted(s["weed_lost_by_day"].items()))
                print(f"  {s['name'][:24]:24s} total {s['weed_lost']:3d}  {days}")


if __name__ == "__main__":
    main()
