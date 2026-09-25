"""Paired analysis of two tournament runs on the same (opponent, seed, seat).

The fleet harness scores W/L, which is a coarse instrument (we win 90.6% of these
games by a mean margin of $7.7k), so a candidate that changes our *reward* is nearly
invisible in the win column. The tournament JSON keeps `our` per game, and the two
runs replay the identical (opponent, seed, seat) triple, so the per-game reward
difference is a paired sample: games where the candidate behaves identically give
delta = 0 exactly, and the rest isolate the mechanism's effect.

Usage:
  .venv/Scripts/python scripts/v39_paired.py --base tournament_results/v39_baseline_main-*.json \
      --cand tournament_results/v39_gate_c_shops2-*.json
"""
import argparse
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load(pattern):
    paths = sorted(glob.glob(pattern if os.path.isabs(pattern) else os.path.join(ROOT, pattern)))
    assert paths, f"no file matches {pattern}"
    path = paths[-1]
    data = json.load(open(path, encoding="utf-8"))
    out = {}
    for r in data["results"]:
        out[(r["opponent"], r["seed"], r["our_seat"])] = r
    return path, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--cand", required=True)
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    bpath, base = load(args.base)
    cpath, cand = load(args.cand)
    keys = sorted(set(base) & set(cand))
    print(f"base {os.path.relpath(bpath, ROOT)}  ({len(base)} games)")
    print(f"cand {os.path.relpath(cpath, ROOT)}  ({len(cand)} games)")
    print(f"paired games: {len(keys)}  {args.label}\n")

    bw = sum(1 for k in keys if base[k]["margin"] > 0)
    cw = sum(1 for k in keys if cand[k]["margin"] > 0)
    bl = sum(1 for k in keys if base[k]["margin"] < 0)
    cl = sum(1 for k in keys if cand[k]["margin"] < 0)
    print(f"wins   base {bw}/{len(keys)}   cand {cw}/{len(keys)}")
    print(f"losses base {bl}/{len(keys)}   cand {cl}/{len(keys)}")
    flips_up = [k for k in keys if base[k]["margin"] <= 0 < cand[k]["margin"]]
    flips_dn = [k for k in keys if cand[k]["margin"] <= 0 < base[k]["margin"]]
    print(f"flips L/T->W {len(flips_up)}   W->L/T {len(flips_dn)}  (net {len(flips_up)-len(flips_dn):+d})")
    if flips_up:
        print("   gains:", ", ".join(f"{k[0]}/s{k[1]}/seat{k[2]}" for k in flips_up))
    if flips_dn:
        print("   losses:", ", ".join(f"{k[0]}/s{k[1]}/seat{k[2]}" for k in flips_dn))

    deltas = [cand[k]["our"] - base[k]["our"] for k in keys]
    nz = [d for d in deltas if d != 0]
    print(f"\nour-reward delta: identical games {len(deltas)-len(nz)}/{len(deltas)}"
          f"   changed {len(nz)}")
    if nz:
        mean = sum(nz) / len(nz)
        sd = statistics.pstdev(nz)
        se = sd / (len(nz) ** 0.5)
        print(f"  changed games: mean {mean:+,.0f}  median {statistics.median(nz):+,.0f}"
              f"  sd {sd:,.0f}  se {se:,.0f}  t {mean/se if se else 0:+.2f}"
              f"  min {min(nz):+,.0f}  max {max(nz):+,.0f}"
              f"  positive {sum(1 for d in nz if d > 0)}/{len(nz)}")
        print(f"  fleet-wide mean delta (all {len(deltas)} games): "
              f"{sum(deltas)/len(deltas):+,.0f}")
        # margins
        md = [cand[k]["margin"] - base[k]["margin"] for k in keys]
        print(f"  margin delta: mean {sum(md)/len(md):+,.0f}   worst "
              f"{min(cand[k]['margin'] for k in keys):+,.0f} (base worst "
              f"{min(base[k]['margin'] for k in keys):+,.0f})")
        worst = sorted(nz)[:6]
        print(f"  worst changed deltas: {', '.join(f'{d:+,.0f}' for d in worst)}")
    bad = [k for k in keys if cand[k]["status"] != "DONE"]
    if bad:
        print(f"  !! {len(bad)} non-DONE in candidate")

    # per-opponent W/L, the acceptance table
    print("\nper-opponent  base W-L  cand W-L   flips")
    opps = sorted(set(k[0] for k in keys))
    tot_b = tot_c = 0
    for opp in opps:
        ks = [k for k in keys if k[0] == opp]
        b = sum(1 for k in ks if base[k]["margin"] > 0)
        c = sum(1 for k in ks if cand[k]["margin"] > 0)
        tot_b += b
        tot_c += c
        f = len([k for k in ks if base[k]["margin"] <= 0 < cand[k]["margin"]]) - \
            len([k for k in ks if cand[k]["margin"] <= 0 < base[k]["margin"]])
        print(f"  {opp:16s} {b:2d}-{len(ks)-b:2d}   {c:2d}-{len(ks)-c:2d}    {f:+d}")
    print(f"  {'TOTAL':16s} {tot_b:2d}/{len(keys)}   {tot_c:2d}/{len(keys)}")


if __name__ == "__main__":
    main()
