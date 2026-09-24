"""Measure the ADV clone-gate candidates in main.py, per game, per opponent.

The gate has to answer one question: "is the rival running a near-copy of our
tape?"  main.py already computes three candidate signals inside the RACE layer:

  M  race_mirror        step-1 money equality (<$0.5) -> same first-turn round trip
  C  race_clone_turns   steps where _race_clone() held: 4/6 recent turns with
                        identical hands+farmer, AND _r37_similarity >= 0.95
  H  race_horizon_turns steps where the gate was live (horizon > 0), i.e. C
  E  race_escalations   steps where _race_lost() fired (rival pre-empted our sale)

This script runs candidate-vs-opponent games and dumps `_RACE_REPORT` from the
candidate's own module after each episode.  Fire rate + precision follow directly.

Usage:
  .venv/Scripts/python scripts/adv_gate_probe.py --opponents main.py v55 prvsiyan guru
  .venv/Scripts/python scripts/adv_gate_probe.py --opponents experiments/v25/baseline_v25.py
"""
import argparse
import importlib.util
import json
import multiprocessing as mp
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402

CANDS = {
    "main": os.path.join(ROOT, "main.py"),
    "v23c7": os.path.join(ROOT, "experiments", "v23c7_baseline.py"),
    "v25": os.path.join(ROOT, "experiments", "v25", "baseline_v25.py"),
    "v26": os.path.join(ROOT, "experiments", "v26", "v26_baseline.py"),
    "v27": os.path.join(ROOT, "experiments", "v28", "v27_baseline.py"),
    "v55": os.path.join(ROOT, "opponents", "v55", "main.py"),
    "prvsiyan": os.path.join(ROOT, "opponents", "prvsiyan", "main.py"),
    "guru": os.path.join(ROOT, "opponents", "guru", "main.py"),
}


def resolve(name):
    if name in CANDS:
        return CANDS[name], name
    p = name if os.path.isabs(name) else os.path.join(ROOT, name)
    return p, os.path.basename(os.path.dirname(p)) or os.path.basename(p)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "agent", None)
    if not callable(fn):
        c = [(k, v) for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
        fn = c[-1][1] if c else None
    return mod, fn


def one(task):
    opp_path, opp_name, seed, seat = task
    probe_mod, probe = load(os.path.join(ROOT, "main.py"), f"probe_{opp_name}_{seed}")
    opp_mod, opp = load(opp_path, f"opp_{opp_name}_{seed}")
    agents = [probe, opp] if seat == 0 else [opp, probe]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(agents)
    fin = env.steps[-1]
    rep = dict(getattr(probe_mod, "_RACE_REPORT", {}))
    return {"opponent": opp_name, "seed": seed, "our_seat": seat,
            "margin": fin[seat].reward - fin[1 - seat].reward,
            "status": fin[seat].status,
            "race_mirror": rep.get("race_mirror", -1),
            "clone_turns": rep.get("race_clone_turns", -1),
            "horizon_turns": rep.get("race_horizon_turns", -1),
            "escalations": rep.get("race_escalations", -1),
            "errors": rep.get("race_errors", -1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponents", nargs="+", default=["main", "v23c7", "v25", "v26", "v27",
                                                       "v55", "prvsiyan", "guru"])
    ap.add_argument("--seeds", default="2000-2009")
    ap.add_argument("--seats", default="0")
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()

    def parse_seeds(s):
        if "-" in s:
            a, b = s.split("-")
            return list(range(int(a), int(b) + 1))
        return [int(x) for x in s.split(",")]

    seeds = parse_seeds(args.seeds)
    seats = [int(c) for c in args.seats]
    tasks = []
    for name in args.opponents:
        p, n = resolve(name)
        for s in seeds:
            for st in seats:
                tasks.append((p, n, s, st))
    workers = args.workers or max(1, min(16, (os.cpu_count() or 4) - 4))
    print(f"{len(tasks)} games, {workers} workers")
    t0 = time.time()
    with mp.Pool(workers) as pool:
        recs = list(pool.imap_unordered(one, tasks))
    print(f"wall {time.time()-t0:.0f}s\n")

    by = {}
    for r in recs:
        by.setdefault(r["opponent"], []).append(r)
    print(f"{'opponent':12s} {'n':>3s} {'W':>3s} {'mirrorR':>8s} {'cloneFire':>10s} "
          f"{'cloneTurns':>11s} {'escal':>6s} {'horizonFire':>12s}")
    for k in sorted(by):
        rs = by[k]
        n = len(rs)
        w = sum(1 for r in rs if r["margin"] > 0)
        m = sum(1 for r in rs if r["race_mirror"] == 1)
        cf = sum(1 for r in rs if r["clone_turns"] > 0)
        ct = [r["clone_turns"] for r in rs]
        es = [r["escalations"] for r in rs]
        print(f"{k:12s} {n:3d} {w:3d} {m:3d}/{n:<4d} {cf:5d}/{n:<4d} "
              f"{sum(ct)/n:11.1f} {sum(es)/n:6.1f} "
              f"{sum(1 for r in rs if r['horizon_turns'] > 0):5d}/{n:<4d}")
    out = os.path.join(ROOT, "tournament_results", f"advgate-{time.strftime('%Y%m%d-%H%M%S')}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(recs, f, indent=1)
    print("\nsaved ->", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
