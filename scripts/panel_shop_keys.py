"""Which route keys does the evaluation panel actually exercise?

`_router` picks the route at step 144 from `tuple(unlocked_shops[:2])`, so a
route swap only changes behaviour on worlds whose first two shops match the
swapped pair — and the shop draw itself depends on both players' farm states,
so the pair differs per (seed, opponent) matchup.

Run this before planning a route swap: it reports the pair distribution over
the seeds the panel uses, i.e. how much of the panel any given swap can touch.

Usage:
  .venv/Scripts/python scripts/panel_shop_keys.py --seeds 2000-2019 --opp opponents/v55/main.py
"""
import argparse
import collections
import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402

ROUTE_STEP = 144


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "agent", None)):
        c = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
        if c:
            return c[-1][1]
    return mod.agent


def parse_seeds(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default="main.py")
    ap.add_argument("--opp", default="opponents/v55/main.py")
    ap.add_argument("--seeds", default="2000-2019")
    ap.add_argument("--seat", type=int, default=0)
    args = ap.parse_args()

    cand = load_agent(os.path.join(ROOT, args.cand), "cand")
    opp = load_agent(os.path.join(ROOT, args.opp), "opp")
    agents = [cand, opp] if args.seat == 0 else [opp, cand]

    dist = collections.Counter()
    for seed in parse_seeds(args.seeds):
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run(agents)
        o = env.steps[ROUTE_STEP][args.seat]["observation"]
        key = tuple((o.get("town", {}).get("unlocked_shops") or [])[:2])
        dist[key] += 1
        print(f"  seed {seed}  {key}")

    print(f"\n{len(dist)} distinct pairs over {sum(dist.values())} games "
          f"(vs {os.path.basename(os.path.dirname(args.opp))})")
    for key, n in dist.most_common():
        yarn = "YARN" if "YARN_STORE" in key else "new "
        print(f"  {n:2d}x  {yarn}  {key}")


if __name__ == "__main__":
    main()
