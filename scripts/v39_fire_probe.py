"""V39: does loosening a V219 gate actually make the tomato layer fire more?

Two things are recorded per game, both from inside the real agent:
  * the layer's own latch -- `_V219_STATES[seat]['eligible']` at step PLANT_DAY*24
    and `_V219_REPORT['commitments']` at the end (the layer's own counters), and
  * the phase profile the fleet harness would see -- money / empty tiles / tomato
    tiles at the end of days 11, 17 and 23 (steps 287, 431, 575).

The per-gate decomposition is re-derived from the captured observation (money,
TOMATO price, shop count, SE quadrant untouched) so a variant that does not fire
tells us *which* gate was binding rather than just "no".

Usage:
  .venv/Scripts/python scripts/v39_fire_probe.py --variants main.py experiments/v39/gate_a_money8000.py \
      --seeds 3000-3023 --workers 16
"""
import argparse
import collections
import importlib.util
import json
import multiprocessing as mp
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PANEL = ["experiments/v23c7_baseline.py", "experiments/v25/baseline_v25.py",
         "experiments/v26/v26_baseline.py", "experiments/v28/v27_baseline.py",
         "experiments/v28/v57_layers.py", "experiments/v35/v34_base.py",
         "experiments/v35/consts.py", "experiments/v36/race44.py",
         "experiments/herdsafe_main.py", "experiments/shepherd.py",
         "experiments/v16rc5.py", "experiments/boatlee_v14.py"]
SNAP_DAYS = (11, 17, 23)
SE = [(x, y) for y in (5, 6) for x in range(5, 10)]


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snap(farm):
    empty = sum(1 for row in farm["tiles"] for t in row if not isinstance(t, dict))
    crops = collections.Counter()
    herd = collections.Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if "animal" in t:
                    herd[t["animal"]] += 1
                elif t.get("kind") == "PLANT":
                    crops[t["crop"]] += 1
    return {"money": farm["money"], "empty": empty, "hands": len(farm["hands"]),
            "tomato": crops.get("TOMATO", 0), "crops": dict(crops), "herd": dict(herd)}


def gates(obs):
    """The four state gates of _v219_qualifies, re-derived for diagnosis only."""
    farm = obs["farms"][obs["player"]]
    out = {"tiles10+quadrants": len(farm["tiles"]) == 10
           and set(farm["unlocked_quadrants"]) == {"NW", "NE", "SW"},
           "money>=12000": farm["money"] >= 12000,
           "money>=8000": farm["money"] >= 8000,
           "price>=70": obs["market"]["prices"]["TOMATO"] >= 70,
           "price>=55": obs["market"]["prices"]["TOMATO"] >= 55,
           "shops>=3": sum(s in ("PIZZA_SHOP", "FARMERS_MARKET")
                           for s in obs["town"]["unlocked_shops"]) >= 3,
           "shops>=2": sum(s in ("PIZZA_SHOP", "FARMERS_MARKET")
                           for s in obs["town"]["unlocked_shops"]) >= 2,
           "SE_untouched": all(farm["tiles"][y][x] == "LOCKED" for x, y in SE)}
    out["money"] = farm["money"]
    out["price"] = obs["market"]["prices"]["TOMATO"]
    out["shops"] = sum(s in ("PIZZA_SHOP", "FARMERS_MARKET")
                       for s in obs["town"]["unlocked_shops"])
    return out


def run_one(task):
    variant, opp_path, seed, latch_step = task
    mod = load_agent(variant, f"v39_{os.path.basename(variant)}_{seed}")
    core = mod.agent
    captured = {}

    def probe(obs, config=None):
        step = int(obs["step"])
        if step == latch_step and "gates" not in captured:
            captured["gates"] = gates(obs)
        if step in [d * 24 + 23 for d in SNAP_DAYS]:
            captured[f"d{step // 24}"] = snap(obs["farms"][obs["player"]])
        return core(obs, config)

    probe.telemetry = getattr(core, "telemetry", None)
    opp = load_agent(os.path.join(ROOT, opp_path), f"opp_{os.path.basename(opp_path)}_{seed}")
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([probe, opp.agent])
    final = env.steps[-1]
    state = mod._V219_STATES.get(0, {})
    report = dict(mod._V219_REPORT)
    return {"variant": os.path.basename(variant), "opponent": os.path.basename(opp_path),
            "seed": seed, "our": final[0].reward, "theirs": final[1].reward,
            "status": final[0].status,
            "eligible": state.get("eligible"),
            "commitments": report.get("commitments", 0),
            "confirmed_plants": report.get("confirmed_plants", 0),
            "harvest_units": report.get("confirmed_harvest_units", 0),
            "sale_units": report.get("tomato_sale_requests", 0),
            "budget_declines": report.get("budget_declines", 0),
            "hire_shortfalls": report.get("hire_shortfalls", 0),
            "gates": captured.get("gates"),
            **{f"d{d}": captured.get(f"d{d}") for d in SNAP_DAYS}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="+", required=True)
    ap.add_argument("--seeds", default="3000-3023")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--latch", type=int, default=0, help="override the latch step (0=per-variant guess)")
    ap.add_argument("--tag", default="v39_fire")
    args = ap.parse_args()

    if "-" in args.seeds:
        a, b = args.seeds.split("-")
        seeds = list(range(int(a), int(b) + 1))
    else:
        seeds = [int(x) for x in args.seeds.split(",")]

    tasks = []
    for variant in args.variants:
        path = variant if os.path.isabs(variant) else os.path.join(ROOT, variant)
        text = open(path, encoding="utf-8").read()
        latch = args.latch or (int(text.split("_V219_PLANT_DAY = ")[1].split("\n")[0]) * 24
                               if "_V219_PLANT_DAY = " in text else 432)
        for index, seed in enumerate(seeds):
            tasks.append((path, PANEL[index % len(PANEL)], seed, latch))

    with mp.Pool(processes=args.workers) as pool:
        recs = list(pool.imap_unordered(run_one, tasks))

    outdir = os.path.join(ROOT, "tmp_v39")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{args.tag}.json")
    json.dump(recs, open(out, "w", encoding="utf-8"), indent=1)
    print("raw ->", os.path.relpath(out, ROOT))

    for variant in [os.path.basename(v) for v in args.variants]:
        rs = [r for r in recs if r["variant"] == variant]
        if not rs:
            continue
        n = len(rs)
        wins = sum(1 for r in rs if r["our"] > r["theirs"])
        elig = sum(1 for r in rs if r["eligible"] is True)
        commit = sum(1 for r in rs if r["commitments"] > 0)
        print(f"\n== {variant}  n={n} ==")
        print(f"  eligible@latch {elig}/{n} ({elig/n:.0%})   committed {commit}/{n} ({commit/n:.0%})"
              f"   budget_declines {sum(r['budget_declines'] for r in rs)}"
              f"   hire_shortfalls {sum(r['hire_shortfalls'] for r in rs)}")
        print(f"  plants {sum(r['confirmed_plants'] for r in rs)}"
              f"   harvest_units {sum(r['harvest_units'] for r in rs)}"
              f"   sale_units {sum(r['sale_units'] for r in rs)}"
              f"   wins {wins}/{n}")
        gs = [r["gates"] for r in rs if r["gates"]]
        if gs:
            for key in ("tiles10+quadrants", "money>=12000", "money>=8000", "price>=70",
                        "price>=55", "shops>=3", "shops>=2", "SE_untouched"):
                ok = sum(1 for g in gs if g[key])
                print(f"    gate {key:20s} pass {ok:2d}/{len(gs)}")
        rng = lambda k: [r[k] for r in rs if r.get(k)]  # noqa: E731
        for d in SNAP_DAYS:
            rows = rng(f"d{d}")
            if rows:
                print(f"    d{d:<2d} money ${statistics.median([r['money'] for r in rows]):7.0f}"
                      f"  empty {statistics.median([r['empty'] for r in rows]):3.0f}"
                      f"  tomato {statistics.median([r['tomato'] for r in rows]):3.0f}"
                      f"  hands {statistics.median([r['hands'] for r in rows]):3.0f}")
        bad = [r for r in rs if r["status"] != "DONE"]
        if bad:
            print(f"  !! {len(bad)} non-DONE")


if __name__ == "__main__":
    main()
