"""Count turns where the engine's atomic-PLANT rule silently deletes our planting.

The engine (kaggriculture.py, `interpreter`) validates PLANT requests as a
block: for each crop, if the number of PLANT requests this turn exceeds the
seeds we hold, EVERY PLANT request for that crop is replaced by PASS. So one
request too many does not cost one plant -- it costs all of them.

This probe wraps a candidate agent, recomputes the same block test from the
public action + private seeds, and reports how often it fires and how many
unit-actions are lost. It changes nothing about the agent's behaviour.

Usage:
  .venv/Scripts/python scripts/atomic_plant_probe.py --candidate main.py \
      --opponents opponents/v53/main.py --seeds 1000-1009
"""
import argparse
import collections
import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cbs = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
    return cbs[-1][1] if cbs else None


REPORT = collections.Counter()
EVENTS = []


def wrap(fn, tag):
    def probe(observation, configuration=None):
        action = fn(observation, configuration)
        try:
            units = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
            demand = collections.Counter()
            for a in units:
                if isinstance(a, list) and len(a) >= 2 and a[0] == "PLANT":
                    demand[a[1]] += 1
            seeds = (observation.get("private") or {}).get("seeds") or {}
            blocked = {c: n for c, n in demand.items() if n > int(seeds.get(c, 0) or 0)}
            if blocked:
                lost = sum(min(n, len(units)) for n in blocked.values())
                REPORT["blocked_turns"] += 1
                REPORT["lost_plants"] += lost
                REPORT[f"crop:{','.join(sorted(blocked))}"] += 1
                EVENTS.append({"tag": tag, "step": int(observation.get("step", -1)),
                               "day": int(observation.get("day", -1)),
                               "blocked": [f"{c} want{n} have{int(seeds.get(c, 0) or 0)}"
                                           for c, n in sorted(blocked.items())],
                               "demand": dict(demand),
                               "seeds": {k: int(v) for k, v in seeds.items()}})
            REPORT["turns"] += 1
        except Exception as exc:  # noqa: BLE001
            REPORT[f"probe_error:{type(exc).__name__}"] += 1
        return action
    return probe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="main.py")
    ap.add_argument("--opponents", nargs="*", required=True)
    ap.add_argument("--seeds", default="1000-1004")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    seeds = (list(range(int(args.seeds.split("-")[0]), int(args.seeds.split("-")[1]) + 1))
             if "-" in args.seeds else [int(x) for x in args.seeds.split(",")])

    for opp in args.opponents:
        for seed in seeds:
            for seat in (0, 1):
                cand = wrap(load(os.path.join(ROOT, args.candidate), f"c{seed}{seat}"), "cand")
                o = load(os.path.join(ROOT, opp), f"o{seed}{seat}")
                env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                env.run([cand, o] if seat == 0 else [o, cand])

    print(f"candidate: {args.candidate}")
    for k in sorted(REPORT):
        print(f"  {k:34s} {REPORT[k]}")
    if REPORT["turns"]:
        print(f"\n  blocked rate: {REPORT['blocked_turns']}/{REPORT['turns']} turns "
              f"= {100.0 * REPORT['blocked_turns'] / REPORT['turns']:.2f}%")
    if args.verbose:
        for e in EVENTS[:60]:
            print(f"    step {e['step']:>3} day {e['day']:>2} {e['blocked']} demand={e['demand']}")


if __name__ == "__main__":
    main()
