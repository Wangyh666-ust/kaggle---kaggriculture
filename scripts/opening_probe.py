"""Dump the first turns of a game for two agents, side by side.

Question it answers: what does each agent actually *do* at steps 0..N, and
what does it cost? Needed because the market orders an agent emits are only
half the story -- an order can be emitted and then fail for lack of cash.

Run on a fixed seed so both seats see the same world.

Usage:
  .venv/Scripts/python scripts/opening_probe.py --a main.py --b opponents/v53/main.py \
      --seed 4242 --steps 6
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


def brief(act):
    parts = []
    for o in act.get("market") or []:
        parts.append(" ".join(str(x) for x in o))
    farm = act.get("farmer") or []
    hands = act.get("hands") or []
    return parts, farm, hands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="main.py")
    ap.add_argument("--b", required=True)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--steps", type=int, default=6)
    args = ap.parse_args()

    agents = [load(os.path.join(ROOT, args.a), "A"), load(os.path.join(ROOT, args.b), "B")]
    env = make("kaggriculture", configuration={"seed": args.seed}, debug=True)
    env.run(agents)

    names = [os.path.basename(os.path.dirname(os.path.join(ROOT, p)))
             for p in (args.a, args.b)]

    for seat in (0, 1):
        st = env.steps[0][seat]
        obs = st["observation"]
        farm = obs["farms"][seat]
        print(f"\n=== seat {seat}  ({names[seat]})  initial state ===")
        print(f"  money {farm['money']}  shed {json.dumps(farm.get('shed'))}")
        print(f"  tiles {len(farm['tiles'])}  unlocked {farm['unlocked_quadrants']}")
        print(f"  seeds {json.dumps(farm.get('seeds'))}  hands {farm.get('hands')}")
        print(f"  market inv {json.dumps(obs['market'].get('inventory'))}")
        print(f"  shops {obs['town']['unlocked_shops']}")

    for t in range(args.steps):
        print(f"\n=== step {t} ===")
        for seat in (0, 1):
            st = env.steps[t][seat]
            act = st["action"] or {}
            mkt, farm_a, hands = brief(act)
            nt = env.steps[t + 1][seat]["observation"] if t + 1 < len(env.steps) else None
            nf = nt["farms"][seat] if nt else {}
            print(f"  seat {seat} {names[seat]:14s} money {st['observation']['farms'][seat]['money']:>7}"
                  f" -> {nf.get('money')}")
            print(f"      market: {mkt}")
            print(f"      farmer: {farm_a}   hands[{len(hands)}]: {hands}")


if __name__ == "__main__":
    main()
