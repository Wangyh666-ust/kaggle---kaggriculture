"""What decides the near-mirror (clone-class) ladder games?

Reads the cache built by scripts/clone_dataset.py and reports, with sample sizes
and uncertainty on every number:

  1. corpus overview, self-play (VALIDATION) episodes reported separately
  2. clone vs other: W-L, win rate + 95% Wilson interval, margin moments
  3. clone-class margin distribution and how much of it is decided by < $1000
  4. seat effect
  5. how far apart the two action tapes are (n_diff_steps, first_diff)
  6. shop-pair worlds
  7. day-3 early signal vs final margin

Usage:
  .venv/Scripts/python scripts/clone_analysis.py
"""
import collections
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE = os.path.join(ROOT, "reverse", "clone_games.jsonl")


def load():
    recs = []
    with open(CACHE, encoding="utf-8") as fh:
        for line in fh:
            recs.append(json.loads(line))
    return recs


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def boot_ci(xs, fn=st.mean, n=4000, seed=7):
    import random
    rng = random.Random(seed)
    xs = list(xs)
    if len(xs) < 3:
        return (float("nan"), float("nan"))
    out = []
    for _ in range(n):
        out.append(fn([xs[rng.randrange(len(xs))] for _ in xs]))
    out.sort()
    return out[int(0.025 * n)], out[int(0.975 * n)]


def binom_p(k, n):
    """Two-sided exact-ish binomial p against 0.5 (normal approx, fine for n>20)."""
    if n == 0:
        return float("nan")
    z = (k - n / 2) / math.sqrt(n * 0.25)
    return math.erfc(abs(z) / math.sqrt(2))


def main():
    recs = load()
    ladder = [r for r in recs if not r["selfplay"]]
    selfplay = [r for r in recs if r["selfplay"]]
    print(f"corpus: {len(recs)} episode records, "
          f"{len(ladder)} ladder games, {len(selfplay)} self-play (VALIDATION)")

    if selfplay:
        m = [r["margin"] for r in selfplay]
        nz = [x for x in m if x != 0]
        print(f"  VALIDATION self-play: n={len(m)} non-zero={len(nz)} "
              f"min={min(m):+,.0f} max={max(m):+,.0f} mean={st.mean(m):+,.0f}")
        by_ver = collections.defaultdict(list)
        for r in selfplay:
            by_ver[r["file"].split("/")[0]].append(r["margin"])
        for k, v in sorted(by_ver.items()):
            print(f"     {k:20s} n={len(v):3d} nonzero={sum(1 for x in v if x):3d} "
                  f"mean={st.mean(v):+9,.0f} min={min(v):+9,.0f}")

    # ---- our opening signature, from our own seats
    sigs = collections.Counter(r["our_open"] for r in ladder if r["our_open"])
    our_sig = sigs.most_common(1)[0][0]
    print(f"\nour modal opening (step 3 market): {our_sig[:70]}  ({sigs.most_common(1)[0][1]}/{sum(sigs.values())})")
    if len(sigs) > 1:
        print("  other openings we produced:")
        for s, k in sigs.most_common()[1:6]:
            print(f"    {k:3d}x {s[:80]}")

    for r in ladder:
        r["clone"] = r["opp_open"] == our_sig

    print("\n=== clone vs other ===")
    for cls in (True, False):
        rs = [r for r in ladder if r["clone"] == cls]
        w = sum(1 for r in rs if r["margin"] > 0)
        l = sum(1 for r in rs if r["margin"] < 0)
        t = len(rs) - w - l
        m = [r["margin"] for r in rs]
        lo, hi = wilson(w, w + l)
        print(f"{'clone' if cls else 'other':6s} n={len(rs):4d} W{w:3d} L{l:3d} T{t:2d}  "
              f"win%={w/(w+l):6.1%} [{lo:.1%},{hi:.1%}] p={binom_p(w, w+l):.2g}  "
              f"mean=${st.mean(m):+9,.0f}  sd=${st.pstdev(m):9,.0f}  median=${st.median(m):+9,.0f}")

    # ---- clone margin distribution
    cl = [r for r in ladder if r["clone"]]
    m = sorted(r["margin"] for r in cl)
    n = len(m)
    print(f"\n=== clone-class margin distribution (n={n}) ===")
    qs = [0, 5, 10, 25, 50, 75, 90, 95, 100]
    print("  " + "  ".join(f"p{q}=${m[min(n-1, int(q/100*n))]:+,.0f}" for q in qs))
    for thr in (100, 500, 1000, 2000, 5000, 10000):
        k = sum(1 for x in m if abs(x) <= thr)
        print(f"  |margin| <= ${thr:>6,d}: {k:4d}/{n} = {k/n:5.1%}   "
              f"95%CI [{wilson(k,n)[0]:.1%},{wilson(k,n)[1]:.1%}]")
    lo, hi = boot_ci(m)
    print(f"  mean ${st.mean(m):+,.0f}  bootstrap 95% CI [${lo:+,.0f}, ${hi:+,.0f}]  "
          f"(0 inside => no systematic edge, pure coin-flip class)")

    print("\n=== seat effect within clone class ===")
    for seat in (0, 1):
        rs = [r for r in cl if r["our_seat"] == seat]
        w = sum(1 for r in rs if r["margin"] > 0)
        l = sum(1 for r in rs if r["margin"] < 0)
        t = len(rs) - w - l
        mm = [r["margin"] for r in rs]
        if w + l:
            lo, hi = wilson(w, w + l)
            print(f"  seat {seat}: n={len(rs):3d} W{w:3d} L{l:3d} T{t:2d} "
                  f"win%={w/(w+l):6.1%} [{lo:.1%},{hi:.1%}]  mean=${st.mean(mm):+9,.0f}  "
                  f"sgnp={binom_p(w, w+l):.2g}")
    # same for other
    ot = [r for r in ladder if not r["clone"]]
    for seat in (0, 1):
        rs = [r for r in ot if r["our_seat"] == seat]
        w = sum(1 for r in rs if r["margin"] > 0)
        l = sum(1 for r in rs if r["margin"] < 0)
        if w + l:
            print(f"  [other] seat {seat}: n={len(rs):3d} win%={w/(w+l):6.1%} "
                  f"mean=${st.mean([r['margin'] for r in rs]):+9,.0f}")

    print("\n=== how different are the two tapes in clone games? ===")
    nd = [(r["n_diff_steps"], r["margin"]) for r in cl if r.get("n_diff_steps") is not None]
    nd.sort()
    if nd:
        vals = [x for x, _ in nd]
        print(f"  n_diff_steps (of 720): median={st.median(vals):.0f} "
              f"p10={vals[len(vals)//10]} p90={vals[9*len(vals)//10]} min={min(vals)} max={max(vals)}")
        # split by whether the tapes are nearly identical
        for thr in (1, 5, 20, 100, 400):
            a = [mm for x, mm in nd if x <= thr]
            b = [mm for x, mm in nd if x > thr]
            if len(a) >= 5 and len(b) >= 5:
                wa = sum(1 for x in a if x > 0) / len(a)
                wb = sum(1 for x in b if x > 0) / len(b)
                print(f"  n_diff<={thr:3d}: n={len(a):3d} win%={wa:6.1%} mean=${st.mean(a):+9,.0f} | "
                      f"n_diff>{thr:3d}: n={len(b):3d} win%={wb:6.1%} mean=${st.mean(b):+9,.0f}")
    fd = [r["first_diff"] for r in cl if r.get("first_diff") is not None]
    if fd:
        fd.sort()
        print(f"  first differing step: median={st.median(fd):.0f} min={min(fd)} max={max(fd)}")
        print(f"    within first 5 steps: {sum(1 for x in fd if x < 5)}/{len(fd)}"
              f"   within first 60: {sum(1 for x in fd if x < 60)}/{len(fd)}")

    print("\n=== shop-pair worlds (town unlock timeline) in clone games ===")
    pairs = collections.Counter()
    for r in cl:
        tl = r.get("shops_tl") or {}
        # the first key with 2 shops is the pair the router keys on
        k2 = None
        for k, step in sorted(tl.items(), key=lambda kv: kv[1]):
            if k.count("'") >= 4:
                k2 = (k, step)
                break
        pairs[k2[0] if k2 else "-"] += 1
    for k, v in pairs.most_common(8):
        rs = [r for r in cl if str(r.get("shops_tl", {})).find(k) >= 0] if k != "-" else []
    # simpler: group by final shop tuple
    grp = collections.defaultdict(list)
    for r in cl:
        sh = r["snap"][-1]["shops"] if r["snap"][-1] else []
        grp[tuple(sh)].append(r["margin"])
    print("  by FINAL unlocked shops:")
    for k, v in sorted(grp.items(), key=lambda kv: -len(kv[1])):
        w = sum(1 for x in v if x > 0)
        l = sum(1 for x in v if x < 0)
        print(f"    {str(k):48s} n={len(v):3d} W{w:3d}L{l:3d} mean=${st.mean(v):+9,.0f}")

    print("\n=== day-3 signal in clone games ===")
    dd = [(r.get("d3_herd"), r["margin"]) for r in cl if r.get("d3_herd")]
    if dd:
        print(f"  our d3 herd counter: {dict(collections.Counter(x for x, _ in dd))}")
        for h in sorted(set(x for x, _ in dd)):
            v = [mm for x, mm in dd if x == h]
            print(f"    d3_herd={h}: n={len(v):3d} mean=${st.mean(v):+9,.0f} "
                  f"win%={sum(1 for x in v if x>0)/len(v):6.1%}")
    dm = [(r["snap"][0]["money"], r["margin"]) for r in cl if r["snap"][0]]
    if dm:
        dm.sort()
        h = len(dm) // 2
        for lbl, part in (("low step-2 money", dm[:h]), ("high step-2 money", dm[h:])):
            print(f"  {lbl:20s} n={len(part)} mean margin=${st.mean(x for _, x in part):+9,.0f} "
                  f"win%={sum(1 for _, x in part if x>0)/len(part):6.1%}")

    print("\n=== deterministic repeat check (same opp + same seed) ===")
    key = collections.defaultdict(list)
    for r in ladder:
        key[(r["opp"], r["seed"])].append(r["margin"])
    dup = {k: v for k, v in key.items() if len(v) > 1}
    same = sum(1 for v in dup.values() if len(set(v)) == 1)
    print(f"  {len(dup)} (opponent,seed) keys repeated; {same} reproduce the same margin exactly")
    if dup:
        for k, v in list(dup.items())[:5]:
            print(f"    {k[0][:20]:20s} seed={k[1]} -> {v}")


if __name__ == "__main__":
    main()
