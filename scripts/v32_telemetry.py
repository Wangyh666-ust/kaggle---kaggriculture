"""Per-layer telemetry for the v32 preempt-with-repay candidate.

Answers, per opponent x seed: did the gate open, did preemption actually fire,
did the repayment actually match a SELL on the next turn, and how much of the
shifted quantity was repaid (the contract boatlee's design depends on).

Usage: .venv/Scripts/python scripts/v32_telemetry.py [--cand experiments/v32/preempt_repay.py]
"""
import argparse
import collections
import importlib.util
import multiprocessing as mp
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from kaggle_environments import make  # noqa: E402
from adv_gate_probe import resolve  # noqa: E402

DEFAULT_CAND = os.path.join(ROOT, "experiments", "v32", "preempt_repay.py")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "agent", None)
    if not callable(fn):
        c = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
        fn = c[-1][1] if c else None
    return mod, fn


def one(task):
    cand_path, name, seed = task
    p, n = resolve(name)
    cm, ca = load(cand_path, "c%s%d" % (n, seed))
    _, oa = load(p, "o%s%d" % (n, seed))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([ca, oa])
    f = env.steps[-1]
    return (n, seed, f[0].reward - f[1].reward, dict(getattr(cm, "_PREEMPT_REPORT", {})))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default=DEFAULT_CAND)
    ap.add_argument("--seeds", default="2000-2004")
    ap.add_argument("--opponents", nargs="+",
                    default=["main", "v23c7", "v25", "v26", "v27", "v55", "prvsiyan", "guru"])
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    def parse_seeds(s):
        if "-" in s:
            a, b = s.split("-")
            return list(range(int(a), int(b) + 1))
        return [int(x) for x in s.split(",")]

    cand = args.cand if os.path.isabs(args.cand) else os.path.join(ROOT, args.cand)
    seeds = parse_seeds(args.seeds)
    tasks = [(cand, n, s) for n in args.opponents for s in seeds]
    with mp.Pool(args.workers) as pool:
        res = pool.map(one, tasks)
    by = collections.defaultdict(list)
    for r in res:
        by[r[0]].append(r)

    keys = ["turns", "gate_calls", "gate_open_turns", "future_nonempty", "future_units",
            "preempt_turns", "preempt_units", "repay_turns", "repay_offered",
            "repaid_units", "repay_unmatched", "preempt_skipped_slots", "errors"]
    print("candidate:", os.path.relpath(cand, ROOT))
    print("%-10s %3s %5s | %s" % ("opponent", "n", "W", "  ".join("%s" % k for k in keys)))
    for n in args.opponents:
        rs = by[n]
        k = len(rs)
        vals = []
        for key in keys:
            vals.append(sum(r[3].get(key, 0) for r in rs) / k)
        fired = sum(1 for r in rs if r[3].get("preempt_turns", 0) > 0)
        full = sum(1 for r in rs if r[3].get("gate_open_turns", 0) == 560)
        print("%-10s %3d %5d | %s   [preempt>=1 turn: %d/%d; gate open all 560: %d/%d]" % (
            n, k, sum(1 for r in rs if r[2] > 0),
            "  ".join("%.1f" % v for v in vals), fired, k, full, k))
    print("\npreempt: units sold early / game. repay: of those, units actually cancelled")
    print("on the next turn (boatlee's contract = repaid_units == preempt_units).")


if __name__ == "__main__":
    main()
