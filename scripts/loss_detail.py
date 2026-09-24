"""List a replay corpus's losses with the signatures that explain them.

Prints, per loss: margin, opponent, day-3 herd (the early-death signature the
v25 fix targeted: a healthy start is 5 animals, an early death shows as <=3),
final herd/crops, and whether the status was not DONE.

Also prints the first-N-games record so a fresh submission can be compared
against an older one at the SAME episode age (a score alone is not comparable
early, because the opponent draw sets how fast it climbs).

Usage:
  .venv/Scripts/python scripts/loss_detail.py replays_v28
  .venv/Scripts/python scripts/loss_detail.py replays_v28 replays_v27 --first 25
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"


def counters(farm):
    herd = collections.Counter()
    crops = collections.Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if "animal" in t:
                    herd[t["animal"]] += 1
                elif t.get("kind") == "PLANT":
                    crops[t["crop"]] += 1
    return herd, crops


def read(f, team):
    d = json.load(open(f, encoding="utf-8"))
    names = list(d["info"]["TeamNames"])
    if team not in names:
        return None
    # Kaggle's submission-validation episode pairs the agent with itself. It is
    # not a ladder game and must not be counted as one — and it is not always a
    # $0 mirror (seed-dependent seat asymmetry), so it produces fake "losses".
    if names[0] == names[1]:
        return None
    us = names.index(team)
    opp = 1 - us
    rec = {"file": os.path.basename(f), "seed": d["info"].get("seed"),
           "opp": names[opp], "created": str(d["info"].get("EpisodeId")),
           "margin": d["rewards"][us] - d["rewards"][opp],
           "our": d["rewards"][us], "theirs": d["rewards"][opp],
           "status": d["statuses"][us]}
    for st in d["steps"]:
        o = st[us]["observation"]
        if o["day"] == 3 and o["hour"] == 23:
            herd, crops = counters(o["farms"][us])
            rec["d3_herd"] = sum(herd.values())
            rec["d3_money"] = o["farms"][us]["money"]
            break
    last = d["steps"][-1][us]["observation"]
    herd, crops = counters(last["farms"][us])
    rec["end_herd"] = dict(herd)
    rec["end_crops"] = dict(crops)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--team", default=OURS)
    ap.add_argument("--first", type=int, default=0,
                    help="only the first N games by episode id (same-age comparison)")
    args = ap.parse_args()

    board = {}
    p = os.path.join(ROOT, "replays_ladder", "leaderboard.json")
    if os.path.exists(p):
        board = {r["teamName"]: r["score"] for r in json.load(open(p, encoding="utf-8"))}

    for d in args.dirs:
        path = d if os.path.isabs(d) else os.path.join(ROOT, d)
        files = sorted(glob.glob(os.path.join(path, "episode-*-replay.json")),
                       key=lambda f: int(f.split("episode-")[1].split("-")[0]))
        if args.first:
            files = files[:args.first]
        recs = []
        for f in files:
            try:
                r = read(f, args.team)
            except Exception:  # noqa: BLE001
                continue
            if r:
                recs.append(r)
        if not recs:
            print(f"{d}: no matching replays")
            continue
        w = sum(1 for r in recs if r["margin"] > 0)
        l = sum(1 for r in recs if r["margin"] < 0)
        t = len(recs) - w - l
        opp_r = [board[r["opp"]] for r in recs if r["opp"] in board]
        print(f"\n=== {os.path.basename(path)}  n={len(recs)}  W{w} L{l} T{t} = "
              f"{w/len(recs):.1%}  opp mean "
              f"{statistics.mean(opp_r):.0f}" if opp_r else "")
        if opp_r:
            print(f"    opp mean {statistics.mean(opp_r):.0f}  median {statistics.median(opp_r):.0f}")
        losses = sorted((r for r in recs if r["margin"] < 0), key=lambda r: r["margin"])
        print(f"    losses ({len(losses)}):")
        for r in losses:
            print(f"      {r['margin']:+9,.0f}  d3_herd={r.get('d3_herd')} "
                  f"d3_money=${r.get('d3_money', 0):,.0f}  status={r['status']}  "
                  f"vs {r['opp'][:22]:22s} (lr {board.get(r['opp'], float('nan')):.0f})")
            print(f"                 end herd={r['end_herd']} crops={r['end_crops']}")


if __name__ == "__main__":
    main()
