"""Controlled mirror experiments: where does a mirror game's margin come from?

The environment's only hidden randomness is _spawn_weeds(), one shared
`random.Random((seed*1_000_003) ^ day)` per day, iterating farm 0's 100 tiles
then farm 1's 100 tiles. So:
  * with weedSpawnChance=0 the game is exactly seat-symmetric, and
  * with the default 0.005 the asymmetry is a weed lottery whose exact outcome
    is a deterministic function of the (hidden) episode seed.

This script measures:
  A) self-play margin with weeds off  -> must be exactly 0 (proves the claim)
  B) self-play margin with weeds on   -> the mirror lottery's distribution
  C) us vs each local "clone-family" opponent, weeds on
  D) the weed count per side and its correlation with the margin

Usage:
  .venv/Scripts/python scripts/mirror_probe.py --mode selfplay --seeds 0-39
  .venv/Scripts/python scripts/mirror_probe.py --mode opp --opponents ourv21 v55 \
      --seeds 0-39
  .venv/Scripts/python scripts/mirror_probe.py --mode noweed --seeds 0-39
"""
import argparse
import importlib.util
import json
import multiprocessing as mp
import os
import statistics as st
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "agent", None)):
        c = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
        if c:
            return c[-1][1]
    return mod.agent


def count_weeds(farm):
    n = 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "WEED":
                n += 1
    return n


def run_one(task):
    kind, a_path, b_path, seed, weed, swap = task
    cfg = {"seed": seed}
    if weed is not None:
        cfg["weedSpawnChance"] = weed
    A = load_agent(a_path, f"A_{seed}_{swap}")
    B = load_agent(b_path, f"B_{seed}_{swap}")
    agents = [A, B] if not swap else [B, A]
    env = make("kaggriculture", configuration=cfg, debug=False)
    env.run(agents)
    st_last = env.steps[-1]
    # weeds are only visible when they are on the board; sample every day
    w0 = w1 = 0
    seen0, seen1 = set(), set()
    for s in env.steps:
        for seat in (0, 1):
            f = s[seat].observation.farms[seat]
            for y, row in enumerate(f["tiles"]):
                for x, t in enumerate(row):
                    if isinstance(t, dict) and t.get("kind") == "WEED":
                        (seen0 if seat == 0 else seen1).add((s[seat].observation.day, y, x))
    w0, w1 = len(seen0), len(seen1)
    # "our" side is the one holding A
    our = 0 if not swap else 1
    return {"group": kind, "seed": seed, "swap": swap,
            "ours": st_last[our].reward, "theirs": st_last[1 - our].reward,
            "margin": st_last[our].reward - st_last[1 - our].reward,
            "our_weeds": w0 if our == 0 else w1,
            "their_weeds": w1 if our == 0 else w0,
            "our_status": st_last[our].status}


def parse_seeds(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="selfplay",
                    choices=["selfplay", "opp", "noweed"])
    ap.add_argument("--candidate", default="main.py")
    ap.add_argument("--opponents", nargs="*", default=["ourv21"])
    ap.add_argument("--seeds", default="0-39")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--weed", default=None, type=float,
                    help="override weedSpawnChance (0.0 = prove symmetry)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    cand = os.path.join(ROOT, args.candidate)
    seeds = parse_seeds(args.seeds)
    tasks = []
    if args.mode == "selfplay":
        combos = [("selfplay", cand, cand, None)]
    elif args.mode == "noweed":
        combos = [("noweed", cand, cand, 0.0)]
    else:
        combos = [(n, cand, os.path.join(ROOT, "opponents", n, "main.py"), args.weed)
                  for n in args.opponents]
    for name, a, b, weed in combos:
        for seed in seeds:
            for swap in (0, 1):
                tasks.append((name, a, b, seed, weed, swap))

    workers = args.workers or max(1, min(20, (os.cpu_count() or 4) - 2))
    print(f"{len(tasks)} games, {workers} workers")
    with mp.Pool(processes=workers) as pool:
        recs = list(pool.imap_unordered(run_one, tasks))

    print(f"\n{'group':12s} {'n':>4s} {'W':>3s} {'L':>3s} {'T':>3s} {'win%':>6s} "
          f"{'mean':>9s} {'sd':>8s} {'min':>9s} {'max':>9s}")
    for name in sorted(set(r["group"] for r in recs)):
        rs = [r for r in recs if r["group"] == name]
        mg = [r["margin"] for r in rs]
        w = sum(1 for x in mg if x > 0)
        l = sum(1 for x in mg if x < 0)
        t = len(mg) - w - l
        sd = st.pstdev(mg) if len(mg) > 1 else 0.0
        print(f"{name:12s} {len(rs):4d} {w:3d} {l:3d} {t:3d} "
              f"{(w/(w+l) if w+l else 0):6.1%} {st.mean(mg):+9,.0f} {sd:8,.0f} "
              f"{min(mg):+9,.0f} {max(mg):+9,.0f}")

    # weed-count vs margin
    print("\nweed count vs margin")
    rows = [(r["our_weeds"], r["their_weeds"], r["margin"]) for r in recs]
    dw = [a - b for a, b, _ in rows]
    print(f"  our weeds/game: mean {st.mean(r[0] for r in rows):.1f}  "
          f"their weeds/game: mean {st.mean(r[1] for r in rows):.1f}")
    for name in sorted(set(r["group"] for r in recs)):
        sub = [(r["our_weeds"], r["their_weeds"], r["margin"])
               for r in recs if r["group"] == name]
        if len(sub) < 5:
            continue
        d = [a - b for a, b, _ in sub]
        mm = [m for _, _, m in sub]
        md, sd = st.mean(d), st.pstdev(d)
        if sd > 0:
            cov = sum((x - md) * (y - st.mean(mm)) for x, y in zip(d, mm)) / len(d)
            print(f"  {name:12s} corr(weed_diff, margin) = {cov/(sd*st.pstdev(mm)):+.2f}  "
                  f"(mean weed_diff {md:+.2f})")
    out = os.path.join(ROOT, "tournament_results",
                       f"mirror_{args.tag or args.mode}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(recs, fh)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
