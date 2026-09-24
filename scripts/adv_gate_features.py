"""Dump raw per-step clone features for a (candidate, opponent) pair.

Records, for the probe seat only:
  step, own money, rival money, |dMoney|,
  positions_equal (hands+farmer identical), sim=_r37_similarity,
  tile-signature equality at the crop level.

Used to decide which observable is a usable "the rival runs our tape" gate.

Usage:
  .venv/Scripts/python scripts/adv_gate_features.py --opponents main v55 --seeds 2000-2002
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402

from scripts.adv_gate_probe import resolve, load  # noqa: E402


def wrap(mod, fn, out):
    SIM = mod._r37_similarity

    def inner(observation, configuration=None):
        try:
            step = int(observation.get("step", 0))
        except Exception:
            step = -1
        if step >= 0:
            try:
                p = int(observation["player"])
                a, b = observation["farms"][p], observation["farms"][1 - p]
                rec = {
                    "step": step,
                    "dmoney": float(a["money"]) - float(b["money"]),
                    "hands_eq": bool(a["hands"]) and a["hands"] == b["hands"],
                    "farmer_eq": a["farmer"] == b["farmer"],
                    "sim": round(float(SIM(observation)), 4),
                    "quad_eq": a["unlocked_quadrants"] == b["unlocked_quadrants"],
                }
                sa = [(t.get("crop"), t.get("animal")) if isinstance(t, dict) else (None, None)
                      for row in a["tiles"] for t in row]
                sb = [(t.get("crop"), t.get("animal")) if isinstance(t, dict) else (None, None)
                      for row in b["tiles"] for t in row]
                rec["tile_match"] = (sum(1 for x, y in zip(sa, sb) if x == y),
                                     sum(1 for x, y in zip(sa, sb) if x != (None, None) or y != (None, None)))
                out.append(rec)
            except Exception as e:
                out.append({"step": step, "err": repr(e)})
        return fn(observation, configuration)
    return inner


def run(task):
    opp_path, opp_name, seed = task
    mod, _ = load(os.path.join(ROOT, "main.py"), f"feat_{opp_name}_{seed}")
    opp_mod, opp = load(opp_path, f"fopp_{opp_name}_{seed}")
    recs = []
    probe = wrap(mod, mod.agent, recs)
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([probe, opp])
    fin = env.steps[-1]
    return {"opponent": opp_name, "seed": seed,
            "margin": fin[0].reward - fin[1].reward, "recs": recs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponents", nargs="+", default=["main", "v55"])
    ap.add_argument("--seeds", default="2000-2002")
    ap.add_argument("--dump", default="")
    args = ap.parse_args()
    if "-" in args.seeds:
        a, b = args.seeds.split("-")
        seeds = list(range(int(a), int(b) + 1))
    else:
        seeds = [int(x) for x in args.seeds.split(",")]
    allrecs = []
    for name in args.opponents:
        p, n = resolve(name)
        for s in seeds:
            r = run((p, n, s))
            allrecs.append(r)
            # early-game money trace
            tr = [(x["step"], round(x.get("dmoney", 0), 2)) for x in r["recs"][:4]]
            sims = [x.get("sim") for x in r["recs"]]
            pe = sum(1 for x in r["recs"] if x.get("hands_eq") and x.get("farmer_eq"))
            fe = sum(1 for x in r["recs"] if x.get("farmer_eq"))
            he = sum(1 for x in r["recs"] if x.get("hands_eq"))
            step1 = next((x for x in r["recs"] if x["step"] == 1), {})
            print(f"{n:10s} seed {s}  margin {r['margin']:+7.0f}  "
                  f"dmoney@1 {step1.get('dmoney', float('nan')):+9.2f}  "
                  f"farmer_eq {fe:3d}  hands_eq {he:3d}  both {pe:3d}  "
                  f"sim>=.95 {sum(1 for v in sims if v and v >= .95):3d}/{len(sims)}")
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as f:
            json.dump(allrecs, f)


if __name__ == "__main__":
    main()
