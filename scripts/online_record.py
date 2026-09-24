"""Online record of one or more submissions, joined against the leaderboard.

Prints, per replay directory: win/loss, win rate, and the mean leaderboard score
of the opponents actually faced. The last column is the point — it shows that a
converged ladder score tracks the strength of the opponent draw far more than it
tracks our own results (see results/score_is_opponent_draw.md).

Usage:
  .venv/Scripts/python scripts/online_record.py replays_v23 replays_v23r replays_v25 replays_v27
  .venv/Scripts/python scripts/online_record.py replays_v27 --ratings 2452.2,1776.9,2263.6,2241.4
"""
import argparse
import glob
import json
import math
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"


def load_board():
    p = os.path.join(ROOT, "replays_ladder", "leaderboard.json")
    if not os.path.exists(p):
        return {}
    return {r["teamName"]: r["score"] for r in json.load(open(p, encoding="utf-8"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--ratings", default="", help="converged score per dir, comma separated")
    ap.add_argument("--team", default=OURS)
    args = ap.parse_args()

    board = load_board()
    ratings = [x.strip() for x in args.ratings.split(",") if x.strip()]

    print(f"{'dir':14s} {'converged':>9s} {'W-L':>8s} {'win%':>7s} "
          f"{'opp mean':>9s} {'opp med':>8s} {'opp range':>14s}")
    for i, d in enumerate(args.dirs):
        p = d if os.path.isabs(d) else os.path.join(ROOT, d)
        files = sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))
        w = l = t = 0
        opp_r, unknown, bad = [], 0, 0
        for f in files:
            try:
                dd = json.load(open(f, encoding="utf-8"))
                names = list(dd["info"]["TeamNames"])
                rewards = list(dd["rewards"])
                us = names.index(args.team)
                opp = names[1 - us]
                m = rewards[us] - rewards[1 - us]
            except Exception:  # noqa: BLE001
                bad += 1
                continue
            w += m > 0
            l += m < 0
            t += m == 0
            if opp in board:
                opp_r.append(board[opp])
            else:
                unknown += 1
        n = w + l + t
        if not n:
            print(f"{os.path.basename(p):14s} (no replays: {bad} unreadable)")
            continue
        rate = f"{w/(w+l):.1%}" if w + l else "-"
        conv = ratings[i] if i < len(ratings) else "-"
        if opp_r:
            rng = f"{min(opp_r):.0f}-{max(opp_r):.0f}"
            print(f"{os.path.basename(p):14s} {conv:>9s} {f'{w}-{l}':>8s} {rate:>7s} "
                  f"{statistics.mean(opp_r):9.1f} {statistics.median(opp_r):8.1f} {rng:>14s}")
        else:
            print(f"{os.path.basename(p):14s} {conv:>9s} {f'{w}-{l}':>8s} {rate:>7s}  (no ratings joined)")
        if unknown or bad:
            print(f"{'':14s}   note: {unknown} opponents not on the board snapshot, {bad} unreadable files")


if __name__ == "__main__":
    main()
