"""Trace money, prices and emitted actions turn-by-turn, anchored on obs['step'].

Question it answers: for a given agent, what exactly happens on the opening
turns -- what it orders, what executes, what it costs, and when cash crosses
the thresholds that gate hiring. The observation carries its own `step` field
so rows cannot silently shift by one (the mistake that makes cash deltas look
impossible).

Usage:
  .venv/Scripts/python scripts/opening_trace.py --a main.py --b opponents/v53/main.py \
      --seed 4242 --steps 5
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for key in ("agent", "ig_agent", "kaggle_agent"):
        fn = getattr(mod, key, None)
        if callable(fn):
            return fn
    cbs = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
    return cbs[-1][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="main.py")
    ap.add_argument("--b", required=True)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--steps", type=int, default=5)
    args = ap.parse_args()

    agents = [load(os.path.join(ROOT, args.a), "A"), load(os.path.join(ROOT, args.b), "B")]
    env = make("kaggriculture", configuration={"seed": args.seed}, debug=True)
    env.run(agents)
    labels = ["A:" + args.a, "B:" + args.b]

    # NOTE: env.steps[t][i]["observation"]["farms"][i]["money"] is the balance
    # AFTER agent i's action at step t has been applied. So the cash a turn
    # costs is money[t-1] - money[t], and money[t-1] is what the agent saw.
    n = min(args.steps + 1, len(env.steps))
    for t in range(n):
        print(f"\n--- step {t} ---")
        for seat in (0, 1):
            st = env.steps[t][seat]
            obs = st["observation"]
            farm = obs["farms"][obs["player"]]
            act = st.get("action") or {}
            mkt = [" ".join(str(x) for x in o) for o in (act.get("market") or [])]
            before = env.steps[t - 1][seat]["observation"]["farms"][obs["player"]]["money"] if t else farm["money"]
            print(f"  seat{seat} {labels[seat]:34s} obs.step={obs.get('step', t):>3}"
                  f" money {before:>9.1f} -> {farm['money']:>9.1f}"
                  f" (cost {before - farm['money']:>+8.1f})"
                  f" hands={len(farm.get('hands') or [])}"
                  f" wheat_px={obs['market']['prices']['WHEAT']:>5.1f}"
                  f" quads={','.join(farm.get('unlocked_quadrants') or [])}")
            print(f"        market: {mkt}")

    print("\n=== final ===")
    for seat in (0, 1):
        f = env.steps[-1][seat]["observation"]["farms"][seat]
        print(f"  seat{seat} {labels[seat]:34s} money={f['money']:>12,.1f} "
              f"(reward={env.steps[-1][seat]['reward']})")


if __name__ == "__main__":
    main()
