"""Side-by-side comparison of two paired tournament runs.

Both runs must cover the same (opponent, seed, seat) triples — the panel is
seeded, so the same seed block on the baseline and the candidate is a paired
comparison and the per-game margin differences are meaningful.

Usage:
  .venv/Scripts/python scripts/compare_tournaments.py BASE.json CAND.json [--labels main.py v25]
"""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {(r["opponent"], r["seed"], r["our_seat"]): r for r in data["results"]}, data


def summarize(rows):
    wins = sum(1 for r in rows if r["margin"] > 0)
    losses = sum(1 for r in rows if r["margin"] < 0)
    margins = [r["margin"] for r in rows]
    return dict(games=len(rows), w=wins, l=losses, t=len(rows) - wins - losses,
                mean=sum(margins) / len(margins), worst=min(margins),
                non_done=sum(1 for r in rows if r["status"] != "DONE"))


def wlt(s):
    return f"{s['w']}W-{s['l']}L-{s['t']}T"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("cand")
    ap.add_argument("--labels", nargs=2, default=None)
    args = ap.parse_args()

    base, bdoc = load(args.base if os.path.isabs(args.base) else os.path.join(ROOT, args.base))
    cand, cdoc = load(args.cand if os.path.isabs(args.cand) else os.path.join(ROOT, args.cand))
    lb, lc = args.labels or (bdoc["candidate"], cdoc["candidate"])

    missing = set(base) ^ set(cand)
    if missing:
        print(f"!! {len(missing)} games not shared, e.g. {sorted(missing)[:3]}")

    opps = sorted({k[0] for k in base})
    print(f"baseline  {lb}")
    print(f"candidate {lc}")
    print(f"seeds {bdoc['seeds']}  ({sum(1 for k in base if k[0]==opps[0])} games per opponent)")
    print()
    header = (f"| {'opponent':<12} | {'baseline':>12} | {'v25':>12} | {'base mean':>10} | "
              f"{'v25 mean':>10} | {'Δmean':>9} | {'base worst':>11} | {'v25 worst':>11} | "
              f"{'Δworst':>9} |")
    print(header)
    print("|" + "|".join(["-" * 14] * 3 + ["-" * 12] * 2 + ["-" * 11] + ["-" * 13] * 2 + ["-" * 11]) + "|")
    all_b, all_c = [], []
    for opp in opps:
        rows_b = [v for k, v in base.items() if k[0] == opp]
        rows_c = [v for k, v in cand.items() if k[0] == opp]
        if not rows_b or not rows_c:
            print(f"| {opp:<12} | not run | not run |")
            continue
        sb, sc = summarize(rows_b), summarize(rows_c)
        all_b += rows_b
        all_c += rows_c
        print(f"| {opp:<12} | {wlt(sb):>12} | {wlt(sc):>12} | {sb['mean']:>+10.0f} | "
              f"{sc['mean']:>+10.0f} | {sc['mean'] - sb['mean']:>+9.0f} | {sb['worst']:>+11.0f} | "
              f"{sc['worst']:>+11.0f} | {sc['worst'] - sb['worst']:>+9.0f} |")
    sb, sc = summarize(all_b), summarize(all_c)
    print(f"| {'TOTAL':<12} | {wlt(sb):>12} | {wlt(sc):>12} | {sb['mean']:>+10.0f} | "
          f"{sc['mean']:>+10.0f} | {sc['mean'] - sb['mean']:>+9.0f} | {sb['worst']:>+11.0f} | "
          f"{sc['worst']:>+11.0f} | {sc['worst'] - sb['worst']:>+9.0f} |")
    print()
    flips = sum(1 for k in base if k in cand
                and (base[k]["margin"] > 0) != (cand[k]["margin"] > 0))
    wins_gained = sum(1 for k in base if k in cand
                      and cand[k]["margin"] > 0 >= base[k]["margin"])
    wins_lost = sum(1 for k in base if k in cand
                    and base[k]["margin"] > 0 >= cand[k]["margin"])
    same = sum(1 for k in base if k in cand and base[k]["our"] == cand[k]["our"]
               and base[k]["theirs"] == cand[k]["theirs"])
    print(f"games identical (bit-for-bit reward): {same}/{len(base)}")
    print(f"win/loss flips: {flips}  (gained {wins_gained}, lost {wins_lost})")
    if sb["non_done"] or sc["non_done"]:
        print(f"non-DONE games: baseline {sb['non_done']}, candidate {sc['non_done']}")


if __name__ == "__main__":
    main()
