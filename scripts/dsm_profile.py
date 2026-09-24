"""Profile one ladder team (default: DSM / teamId 16732748) out of a replay corpus.

Question this answers
---------------------
"Given the replays in reverse/replays/, what exactly does team X do -- its
opening signature, its farm plan at d12/16/20/29, its market cadence, and where
its action stream diverges from ours turn by turn?"

It is deliberately self-contained (no import of ladder_meta_report) so the
numbers quoted in a profile can be re-derived with one command:

    .venv/Scripts/python scripts/dsm_profile.py --team DSM \
        --replays reverse/replays [--diff-shops HOUR] [--json out.json]

Sections:
  1 signatures    opening market signature (first 3 steps) + who else shares it
  2 farm snapshots  herd/crop/empty/hands/money at d12/16/20/29
  3 land           land quadrant unlocks (board_size growth) per day
  4 market         per-item sell volume + first/last sell day, order-slot layout
  5 purchases      seed and animal buys by day
  6 prices         per-day price trajectory of the goods it trades
  7 diff          (--diff) same-shop-pair turn-by-turn diff against our tape
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DAYS = (12, 16, 20, 29)
TAPE_LEN = 720


def load_corpus(*dirs):
    files = []
    for d in dirs:
        p = d if os.path.isabs(d) else os.path.join(ROOT, d)
        files += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))
    out = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        if "info" not in d or "steps" not in d or len(d["steps"]) < TAPE_LEN:
            continue
        out.append((f, d))
    return out


def tile_mix(farm):
    herd, crops, empty, structures = collections.Counter(), collections.Counter(), 0, 0
    for row in farm["tiles"]:
        for t in row:
            if not isinstance(t, dict):
                empty += 1
            elif "animal" in t:
                herd[t["animal"]] += 1
            elif t.get("kind") == "PLANT":
                crops[t["crop"]] += 1
            else:
                structures += 1
    return herd, crops, empty, structures


def snap(steps, seat, day):
    t = day * 24
    if t >= len(steps):
        return None
    o = steps[t][seat]["observation"]
    farm = o["farms"][seat]
    return o, farm


def day_stats(steps, seat, day):
    """Peak hands/hires seen at any hour of `day` (hour-0 snapshots read 0)."""
    mx = hires = 0
    for h in range(24):
        t = day * 24 + h
        if t >= len(steps):
            break
        f = steps[t][seat]["observation"]["farms"][seat]
        mx = max(mx, len(f.get("hands") or []))
        hires = max(hires, f.get("hires_today") or 0)
    return mx, hires


def unlocked_quadrants(farm, board_size):
    """How many of the 4 land quadrants are bought (NW always there)."""
    q = set()
    for y in range(board_size):
        for x in range(board_size):
            if farm["tiles"][y][x] != "LOCKED":
                q.add(("N" if y < board_size // 2 else "S")
                      + ("W" if x < board_size // 2 else "E"))
    return q


def fmt_counter(c):
    return "+".join(f"{k[:4]}{v}" for k, v in sorted(c.items()) if v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="DSM")
    ap.add_argument("--replays", nargs="+", default=["reverse/replays"])
    ap.add_argument("--ours-replays", nargs="+", default=[],
                    help="dirs of OUR replays, for the turn-by-turn diff")
    ap.add_argument("--ours-team", default="ReD_MooN_rise")
    ap.add_argument("--diff", action="store_true", help="emit the turn-by-turn diff")
    ap.add_argument("--json", default="", help="dump the collected rows as json")
    args = ap.parse_args()

    corpus = load_corpus(*args.replays)
    if not corpus:
        print("no usable replays in", args.replays)
        return

    # ---- seat rows for the target team -------------------------------------
    rows = []
    for path, d in corpus:
        names = d["info"].get("TeamNames") or []
        steps = d["steps"]
        for seat in (0, 1):
            if seat >= len(names) or names[seat] != args.team:
                continue
            rows.append({"file": os.path.basename(path), "episode": d["info"].get("EpisodeId"),
                         "seed": d["info"].get("seed"), "seat": seat,
                         "opp": names[1 - seat], "reward": d["rewards"][seat],
                         "opp_reward": d["rewards"][1 - seat],
                         "steps": steps, "n": len(steps)})

    if not rows:
        print(f"team {args.team!r} not in corpus")
        return

    print(f"# {args.team}: {len(rows)} seats over {len({r['episode'] for r in rows})} episodes")
    print(f"# corpus: {len(corpus)} replay files from {args.replays}\n")

    # ---- 1. opening signature ---------------------------------------------
    print("## 1. opening signatures (market orders, first 3 steps)\n")
    sigs = collections.Counter()
    for r in rows:
        parts = []
        for st in r["steps"][:3]:
            mk = st[r["seat"]].get("action", {}).get("market") or []
            parts.append(json.dumps(mk, separators=(",", ":")))
        sigs["|".join(parts)] += 1
    for s, n in sigs.most_common():
        print(f"  n={n:2d}  {s}")
    print()
    # same-signature teams across the whole corpus
    allsig = collections.defaultdict(set)
    for path, d in corpus:
        names = d["info"].get("TeamNames") or []
        for seat in (0, 1):
            if seat >= len(names):
                continue
            parts = []
            for st in d["steps"][:3]:
                mk = st[seat].get("action", {}).get("market") or []
                parts.append(json.dumps(mk, separators=(",", ":")))
            allsig["|".join(parts)].add(names[seat])
    print("  shared with (whole corpus):")
    for s, n in sigs.most_common(3):
        print(f"    {s[:70]}... -> {sorted(allsig[s])}\n")

    # ---- 2/3. farm snapshots ----------------------------------------------
    print("## 2. farm snapshots\n")
    for day in DAYS:
        agg = []
        for r in rows:
            s = snap(r["steps"], r["seat"], day)
            if not s:
                continue
            o, farm = s
            herd, crops, empty, struct = tile_mix(farm)
            hands, hires = day_stats(r["steps"], r["seat"], day)
            bs = len(farm["tiles"])
            agg.append({"herd": herd, "crops": crops, "empty": empty, "struct": struct,
                        "money": farm["money"], "hands": hands, "hires": hires,
                        "quad": len(unlocked_quadrants(farm, bs)),
                        "bs": bs, "day": o["day"]})
        if not agg:
            continue
        print(f"  d{day}: n={len(agg)}")
        print(f"    money  mean {statistics.mean(a['money'] for a in agg):>10,.0f}"
              f"  range {min(a['money'] for a in agg):>9,.0f} .. {max(a['money'] for a in agg):>9,.0f}")
        print(f"    hands  mean {statistics.mean(a['hands'] for a in agg):>6.1f}"
              f"  range {min(a['hands'] for a in agg)} .. {max(a['hands'] for a in agg)}")
        print(f"    empty  mean {statistics.mean(a['empty'] for a in agg):>6.1f}"
              f"  range {min(a['empty'] for a in agg)} .. {max(a['empty'] for a in agg)}")
        print(f"    quad   mean {statistics.mean(a['quad'] for a in agg):>6.2f}"
              f"  range {min(a['quad'] for a in agg)} .. {max(a['quad'] for a in agg)}"
              f"   (tiles {agg[0]['bs']}x{agg[0]['bs']})")
        for lbl, key in (("herd", "herd"), ("crop", "crops")):
            keys = sorted({k for a in agg for k in a[key]})
            line = "    " + lbl.ljust(5)
            for k in keys:
                vals = [a[key].get(k, 0) for a in agg]
                line += (f" {k[:4]} {statistics.mean(vals):5.1f}"
                         f"[{min(vals)}-{max(vals)}]")
            print(line)
        # exact per-game herd string
        print("    per-game herd:", " | ".join(fmt_counter(a["herd"]) for a in agg))
        print()

    print("## 3. land quadrants bought, by day (1=NW only, 4=full board)\n")
    for day in (1, 3, 5, 6, 7, 9, 11, 12, 16, 20, 29):
        vals = []
        for r in rows:
            s = snap(r["steps"], r["seat"], day)
            if s:
                vals.append((len(unlocked_quadrants(s[1], len(s[1]["tiles"]))))
            )
        if vals:
            c = collections.Counter(vals)
            print(f"  d{day:<3d} " + "  ".join(f"{k}q x{v}" for k, v in sorted(c.items())))
    buys = collections.Counter()
    for r in rows:
        for t in range(r["n"]):
            mk = (r["steps"][t][r["seat"]].get("action") or {}).get("market") or []
            for o in mk:
                if isinstance(o, (list, tuple)) and o and o[0] == "BUY_LAND":
                    buys[t // 24] += 1
    print("  BUY_LAND orders by day:",
          " ".join(f"d{k}:{v}" for k, v in sorted(buys.items())))

    # ---- 4. market cadence -------------------------------------------------
    print("\n## 4. market cadence (orders this team issued)\n")
    sell_vol = collections.Counter()
    sell_days = collections.defaultdict(list)
    order_kinds = collections.Counter()
    slot_pos = collections.defaultdict(collections.Counter)
    all_orders = collections.Counter()
    for r in rows:
        for t in range(r["n"]):
            act = r["steps"][t][r["seat"]].get("action") or {}
            mk = act.get("market") or []
            for i, o in enumerate(mk):
                if not isinstance(o, (list, tuple)) or not o:
                    continue
                all_orders[o[0]] += 1
                slot_pos[o[0]][(i, len(mk))] += 1
                if len(o) >= 3 and o[0] in ("SELL", "SELL_ANIMAL", "SELL_PRODUCT"):
                    sell_vol[o[1]] += o[2]
                    sell_days[o[1]].append(t // 24)
    print("  order-op counts:", dict(all_orders.most_common()))
    print(f"\n  {'item':<14}{'units':>8}{'first_day':>10}{'last_day':>9}   day histogram")
    for item, v in sell_vol.most_common():
        dd = sell_days[item]
        h = collections.Counter(dd)
        print(f"  {item:<14}{v:>8}{min(dd):>10}{max(dd):>9}   "
              + " ".join(f"{k}:{h[k]}" for k in sorted(h)))
    print("\n  order slots (op -> (position,total_len):count)")
    for op, c in order_kinds.items():
        pass
    for op in ("SELL", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "HIRE"):
        if slot_pos[op]:
            top = ", ".join(f"{p}:{n}" for p, n in slot_pos[op].most_common(5))
            print(f"    {op:<12} {top}")

    # ---- 5. purchases ------------------------------------------------------
    print("\n## 5. purchases by day\n")
    seeds = collections.defaultdict(collections.Counter)
    animals = collections.defaultdict(collections.Counter)
    for r in rows:
        for t in range(r["n"]):
            mk = (r["steps"][t][r["seat"]].get("action") or {}).get("market") or []
            for o in mk:
                if not isinstance(o, (list, tuple)) or len(o) < 3:
                    continue
                if o[0] == "BUY_SEED":
                    seeds[o[1]][t // 24] += o[2]
                elif o[0] == "BUY_ANIMAL":
                    animals[o[1]][t // 24] += o[2]
    for lbl, data in (("SEED", seeds), ("ANIMAL", animals)):
        for item, c in sorted(data.items()):
            tot = sum(c.values())
            print(f"  {lbl:<7}{item:<12} total {tot:>5}   "
                  + " ".join(f"d{k}:{v}" for k, v in sorted(c.items()) if v))

    # ---- 6. prices ---------------------------------------------------------
    print("\n## 6. price trajectory (mean over games)\n")
    pd_ = collections.defaultdict(dict)
    for r in rows:
        for t in range(r["n"]):
            o = r["steps"][t][r["seat"]]["observation"]
            if o["hour"] != 0:
                continue
            for item, p in (o.get("market", {}).get("prices") or {}).items():
                pd_[item].setdefault(o["day"], []).append(p)
    items = sorted(pd_)
    days = [8, 12, 16, 20, 24, 26, 29]
    hdr = "  " + "item".ljust(13) + "".join(f"d{d:<7}" for d in days)
    print(hdr)
    for item in items:
        line = "  " + item[:12].ljust(13)
        for d in days:
            v = pd_[item].get(d)
            line += f"{statistics.mean(v):<8.1f}" if v else "-       "
        print(line)

    if args.json:
        out = os.path.join(ROOT, args.json)
        json.dump([{k: v for k, v in r.items() if k != "steps"} for r in rows],
                  open(out, "w", encoding="utf-8"), indent=1)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
