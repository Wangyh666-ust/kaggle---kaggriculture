"""Per-callback wall time for an agent over a full 720-turn game.

Kaggle runs the agent in-process with a wall-clock budget, so a layer that adds
per-turn search (V57's counter-D evaluates up to `_CXD_BUDGET` orderings every
turn) can be a net loss even when it wins more games. Measure before adopting.

Reports mean / p50 / p95 / max over all callbacks, and the worst single turn.
The public authors quote their own figures this way (V55: ~45 ms peak callback),
so this keeps our numbers comparable.

Usage:
  .venv/Scripts/python scripts/callback_timing.py --cand main.py --games 2
  .venv/Scripts/python scripts/callback_timing.py --cand experiments/v28/cxd.py --opp main.py
"""
import argparse
import importlib.util
import os
import statistics
import sys
import time

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


def timed(fn, samples):
    def wrapper(observation, configuration=None):
        t0 = time.perf_counter()
        try:
            return fn(observation, configuration)
        finally:
            samples.append((time.perf_counter() - t0) * 1000.0)
    return wrapper


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default="main.py")
    ap.add_argument("--opp", default="")
    ap.add_argument("--seeds", default="2000,2001")
    ap.add_argument("--seat", type=int, default=0)
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    cand_path = os.path.join(ROOT, args.cand)
    opp_path = os.path.join(ROOT, args.opp) if args.opp else cand_path
    opp = load_agent(opp_path, "opp")

    all_samples = []
    per_game = []
    for seed in seeds:
        samples = []
        cand = timed(load_agent(cand_path, f"cand_{seed}"), samples)
        agents = [cand, opp] if args.seat == 0 else [opp, cand]
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run(agents)
        status = env.steps[-1][args.seat].status
        all_samples += samples
        per_game.append((seed, len(samples), statistics.mean(samples) if samples else 0,
                         max(samples) if samples else 0, status))

    if not all_samples:
        print("no samples")
        return
    s = sorted(all_samples)
    def pct(p):
        return s[min(len(s) - 1, int(len(s) * p))]
    print(f"candidate: {args.cand}   games: {len(seeds)}   callbacks: {len(s)}")
    print(f"  mean {statistics.mean(s):7.3f} ms   p50 {pct(.5):7.3f}   "
          f"p95 {pct(.95):7.3f}   p99 {pct(.99):7.3f}   max {max(s):8.3f} ms")
    print(f"  total agent time: {sum(s)/1000:.1f} s over {len(seeds)} game(s)")
    for seed, n, mean, mx, status in per_game:
        print(f"  seed {seed}: {n} callbacks, mean {mean:.3f} ms, max {mx:.3f} ms, status {status}")


if __name__ == "__main__":
    main()
