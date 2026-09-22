"""How often does the v9/2 PREDICT hook actually fire, old library vs new?

Loads an agent file, plays seeded games against a chosen opponent, then reads
the module-level `_V92_P_REPORT` telemetry that the hook updates
(pred_fires / pred_units / pred_errors).  Same seeds on both candidates, so the
opening turns are identical and only the library differs.

Usage:
  .venv/Scripts/python scripts/v92_fire_probe.py --seeds 2000-2003 \
      --candidates main.py versions/main_v25_ownlib.py --opponent opponents/guru/main.py
"""
import argparse
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_seeds(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", nargs="+",
                    default=["main.py", "versions/main_v25_ownlib.py"])
    ap.add_argument("--opponent", default="opponents/guru/main.py")
    ap.add_argument("--seeds", default="2000-2003")
    ap.add_argument("--seat", type=int, default=0)
    args = ap.parse_args()

    opp_path = os.path.join(ROOT, args.opponent)
    for cand in args.candidates:
        tot = dict(games=0, pred_fires=0, pred_units=0, pred_errors=0, wins=0, margin=0.0)
        for seed in parse_seeds(args.seeds):
            for seat in (0, 1):
                mod = load_agent(os.path.join(ROOT, cand), f"probe_{seed}_{seat}")
                opp = load_agent(opp_path, f"probe_opp_{seed}_{seat}")
                agents = [mod.agent, opp.agent] if seat == 0 else [opp.agent, mod.agent]
                env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                env.run(agents)
                final = env.steps[-1]
                rep = getattr(mod, "_V92_P_REPORT", {})
                tot["games"] += 1
                tot["pred_fires"] += rep.get("pred_fires", 0)
                tot["pred_units"] += rep.get("pred_units", 0)
                tot["pred_errors"] += rep.get("pred_errors", 0)
                tot["wins"] += 1 if final[seat].reward > final[1 - seat].reward else 0
                tot["margin"] += final[seat].reward - final[1 - seat].reward
        print(f"{cand:38s} games {tot['games']:3d}  fires {tot['pred_fires']:5d}  "
              f"units {tot['pred_units']:6d}  errors {tot['pred_errors']:3d}  "
              f"wins {tot['wins']:3d}  mean margin {tot['margin'] / tot['games']:+8.0f}")


if __name__ == "__main__":
    main()
