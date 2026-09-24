"""Print every extracted opponent's opening market orders (first 3 steps).

Question it answers: is the top-of-ladder family (the shared signature
`SELL WHEAT 1, HIRE x4, COW 1, SHEEP 3` at step 2) simply a public agent we
already have on disk? If so, adopting it is a copy, not a research project.

Run against a fixed seed so all opponents see the same world.

Usage:
  .venv/Scripts/python scripts/opponent_openings.py --seeds 900,901
"""
import argparse
import glob
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402

FAMILY2 = ('[["SELL","WHEAT",1],["HIRE"],["HIRE"],["HIRE"],["HIRE"],'
           '["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",3]]')


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "agent", None)):
        c = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
        if c:
            return c[-1][1]
    return mod.agent


def sig(act):
    mk = act.get("market") if isinstance(act, dict) else None
    return json.dumps(mk, separators=(",", ":")) if mk is not None else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default="main.py")
    ap.add_argument("--seeds", default="900")
    args = ap.parse_args()

    cand = load_agent(os.path.join(ROOT, args.cand), "cand")
    opps = sorted(glob.glob(os.path.join(ROOT, "opponents", "*", "main.py")))
    seed = int(args.seeds.split(",")[0])

    print(f"{'opponent':16s} {'step1 market':52s} {'step2 matches family2?'}")
    print("-" * 100)
    for path in opps:
        name = os.path.basename(os.path.dirname(path))
        try:
            opp = load_agent(path, f"opp_{name}")
        except Exception as exc:  # noqa: BLE001
            print(f"{name:16s} load failed: {exc}")
            continue
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run([cand, opp])
        s1 = sig(env.steps[1][1].get("action"))
        s2 = sig(env.steps[2][1].get("action"))
        mark = "  <== FAMILY-2 SIGNATURE" if s2 == FAMILY2 else ""
        print(f"{name:16s} {s1[:50]:52s} {mark}")

    # and our own candidate, seat 1
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([cand, cand])
    print(f"{'(ours)':16s} {sig(env.steps[1][1].get('action'))[:50]:52s}")


if __name__ == "__main__":
    main()
