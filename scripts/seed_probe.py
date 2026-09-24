"""Play our agent against a chosen opponent on a given seed; print the world.

Purpose: test whether a ladder seed reproduces the same shop-unlock sequence
locally. `_end_of_day` draws weeds from the same RNG it then draws the shop
from, and `_spawn_weeds` only calls rng.random() on EMPTY tiles — so the shop
sequence depends on both players' farm states. If two different agents produce
a different shop order on the same seed, cross-game money comparisons on that
seed are invalid and that must be known before any benchmark is built on it.

Usage:
  .venv/Scripts/python scripts/seed_probe.py --seed 8823651 --opp main.py
  .venv/Scripts/python scripts/seed_probe.py --seed 8823651 --opp opponents/v55/main.py
"""
import argparse
import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "agent", None)):
        callables = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
        if callables:
            return callables[-1][1]
    return mod.agent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--cand", default="main.py")
    ap.add_argument("--opp", default="main.py")
    ap.add_argument("--seat", type=int, default=0, help="candidate seat")
    args = ap.parse_args()

    cand = load_agent(os.path.join(ROOT, args.cand), "cand")
    opp = load_agent(os.path.join(ROOT, args.opp), "opp")
    agents = [cand, opp] if args.seat == 0 else [opp, cand]

    env = make("kaggriculture", configuration={"seed": args.seed}, debug=False)
    env.run(agents)
    steps = env.steps

    prev = None
    print(f"seed {args.seed}  {args.cand}(seat{args.seat}) vs {args.opp}(seat{1 - args.seat})")
    print("shop unlocks:")
    for st in steps:
        o = st[0]["observation"]
        s = tuple(sorted(o["town"]["unlocked_shops"]))
        if s != prev:
            print(f"   d{o['day']:2d} h{o['hour']:2d}  {list(s)}")
            prev = s
    final = steps[-1]
    print(f"final: ${final[args.seat].reward:,.0f} vs ${final[1 - args.seat].reward:,.0f}  "
          f"margin ${final[args.seat].reward - final[1 - args.seat].reward:+,.0f}")
    print(f"status: {final[args.seat].status} / {final[1 - args.seat].status}")


if __name__ == "__main__":
    main()
