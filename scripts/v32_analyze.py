"""Paired analysis of two tournament_results JSONs (baseline vs candidate).

Matches games on (opponent, seed, seat) and reports the per-opponent W/L/T
table, the mean/worst margin, and the paired flip counts with an exact
one-sided binomial p-value on the discordant pairs -- the statistic the v30/v31
reports used to decide that a win-rate regression was not noise.

Usage:
  .venv/Scripts/python scripts/v32_analyze.py <baseline.json> <candidate.json> [...]
"""
import collections
import glob
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resolve(spec):
    if os.path.isfile(spec):
        return os.path.abspath(spec)
    hits = sorted(glob.glob(os.path.join(ROOT, "tournament_results", spec + "-*.json")))
    if not hits:
        raise SystemExit("no result file matching " + spec)
    return hits[-1]


# tournament.py names an opponent after its PARENT DIRECTORY, which collapses
# experiments/v23c7_baseline.py and experiments/v28/v27_baseline.py onto
# "experiments" and "v28".  Map them back to the version they actually are.
ALIAS = {"experiments": "v23c7", "v28": "v27"}


def load(spec):
    path = resolve(spec)
    d = json.load(open(path, encoding="utf-8"))
    out = {}
    for r in d["results"]:
        out[(ALIAS.get(r["opponent"], r["opponent"]), r["seed"], r["our_seat"])] = r
    return os.path.basename(path), d, out


def binom_one_sided(k, n, p=0.5):
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) * p ** n for i in range(k, n + 1))


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    bname, bdoc, base = load(sys.argv[1])
    cname, cdoc, cand = load(sys.argv[2])
    print("baseline : %s (%d games)" % (bname, len(base)))
    print("candidate: %s (%d games)" % (cname, len(cand)))

    keys = sorted(set(base) & set(cand))
    print("matched pairs: %d\n" % len(keys))

    by = collections.defaultdict(list)
    for k in keys:
        by[k[0]].append(k)

    print("%-12s %-12s %-12s %10s %10s" % ("opponent", "base W/L/T", "cand W/L/T",
                                           "base mean", "cand mean"))
    print("-" * 66)
    tot_b = tot_c = tot_n = 0
    bm_all, cm_all = [], []
    for opp in sorted(by):
        ks = by[opp]
        bw = sum(1 for k in ks if base[k]["margin"] > 0)
        cw = sum(1 for k in ks if cand[k]["margin"] > 0)
        bl = sum(1 for k in ks if base[k]["margin"] < 0)
        cl = sum(1 for k in ks if cand[k]["margin"] < 0)
        n = len(ks)
        bm = [base[k]["margin"] for k in ks]
        cm = [cand[k]["margin"] for k in ks]
        bm_all += bm
        cm_all += cm
        tot_b += bw
        tot_c += cw
        tot_n += n
        print("%-12s %5d-%2d-%2d %5d-%2d-%2d %+10.0f %+10.0f   (n=%d)" % (
            opp, bw, bl, n - bw - bl, cw, cl, n - cw - cl,
            sum(bm) / n, sum(cm) / n, n))
    print("-" * 66)
    print("%-12s %5d/%d (%5.1f%%)  %5d/%d (%5.1f%%)  %+7.0f %+7.0f" % (
        "TOTAL", tot_b, tot_n, 100.0 * tot_b / tot_n,
        tot_c, tot_n, 100.0 * tot_c / tot_n,
        sum(bm_all) / tot_n, sum(cm_all) / tot_n))

    wl = sum(1 for k in keys if base[k]["margin"] > 0 and cand[k]["margin"] <= 0)
    lw = sum(1 for k in keys if base[k]["margin"] <= 0 and cand[k]["margin"] > 0)
    print("\npaired flips: W->not-W = %d, not-W->W = %d, discordant = %d" % (wl, lw, wl + lw))
    if wl + lw:
        p = binom_one_sided(max(wl, lw), wl + lw)
        side = "W->L" if wl > lw else "L->W"
        print("  dominant direction %s, one-sided binomial p = %.3g" % (side, p))
    print("  worst margin: base %+.0f  cand %+.0f" % (min(bm_all), min(cm_all)))
    print("  sum of margins: base %+.0f  cand %+.0f" % (sum(bm_all), sum(cm_all)))

    flips = [(k, base[k]["margin"], cand[k]["margin"]) for k in keys
             if (base[k]["margin"] > 0) != (cand[k]["margin"] > 0)]
    if flips:
        print("\nflipped games (opponent, seed, seat -> base margin, cand margin):")
        for k, b, c in sorted(flips):
            print("  %-10s seed %-6d seat %d  %+9.0f -> %+9.0f" % (k[0], k[1], k[2], b, c))
    big = sorted(((abs(cand[k]["margin"] - base[k]["margin"]), k,
                   base[k]["margin"], cand[k]["margin"]) for k in keys), reverse=True)[:5]
    print("\nlargest per-game margin swings:")
    for d, k, b, c in big:
        print("  %-10s seed %-6d seat %d  %+9.0f -> %+9.0f  (delta %+.0f)" % (
            k[0], k[1], k[2], b, c, c - b))


if __name__ == "__main__":
    main()
