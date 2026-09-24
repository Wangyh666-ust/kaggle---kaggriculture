"""Trace ONE mirror episode step by step: what does a weed actually cost?

Runs A vs A (or A vs an opponent) at a fixed seed and prints, for every step
where the two farms first differ and every end-of-day, the tile-level deltas
plus the running money gap. Also classifies each new WEED as
  RANDOM (tile was empty just before the day rollover) or
  DECAY  (tile held a plant that ran out of water / lifespan).

Usage:
  .venv/Scripts/python scripts/weed_trace.py --seed 12
  .venv/Scripts/python scripts/weed_trace.py --seed 12 --opponents/v55
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "agent", None) or [
        v for k, v in vars(mod).items() if callable(v) and not k.startswith("__")][-1]


def grid(farm):
    return farm["tiles"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=12)
    ap.add_argument("--cand", default="main.py")
    ap.add_argument("--opp", default=None)
    args = ap.parse_args()
    A = load_agent(os.path.join(ROOT, args.cand), "A")
    B = A if not args.opp else load_agent(os.path.join(ROOT, args.opp), "B")
    env = make("kaggriculture", configuration={"seed": args.seed}, debug=False)
    env.run([A, B])

    prev = [None, None]
    prev_day = -1
    print(f"seed={args.seed}  A={os.path.basename(args.cand)}  B={args.opp or 'same'}")
    print(f"{'step':>4s} {'day':>3s} {'hr':>2s} | {'moneyA':>9s} {'moneyB':>9s} {'gap':>8s} | events")
    for i, s in enumerate(env.steps):
        o = s[0].observation
        d, h = o.day, o.hour
        fa, fb = o.farms[0], o.farms[1]
        events = []
        if d != prev_day and prev[0] is not None:
            for seat, cur, old in ((0, fa, prev[0]), (1, fb, prev[1])):
                ta, tb = grid(cur), grid(old)
                for y in range(len(ta)):
                    for x in range(len(ta[y])):
                        now, was = ta[y][x], tb[y][x]
                        if isinstance(now, dict) and now.get("kind") == "WEED" \
                                and not (isinstance(was, dict) and was.get("kind") == "WEED"):
                            kind = "RANDOM" if was is None else f"DECAY({was.get('crop')})"
                            events.append(f"seat{seat} {kind}@({y},{x})")
            prev_day = d
        if events or (d != prev_day):
            print(f"{i:4d} {d:3d} {h:2d} | {fa['money']:9,.0f} {fb['money']:9,.0f} "
                  f"{fa['money']-fb['money']:+8,.0f} | {'; '.join(events)}")
        prev = [fa, fb]
        prev_day = d

    o = env.steps[-1][0].observation
    print(f"\nfinal  A ${o.farms[0]['money']:,.0f}  B ${o.farms[1]['money']:,.0f}  "
          f"gap {o.farms[0]['money']-o.farms[1]['money']:+,.0f}")


if __name__ == "__main__":
    main()
