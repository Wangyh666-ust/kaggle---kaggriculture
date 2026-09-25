"""Paired-seat tournament: our candidate vs a panel of opponents — PARALLEL.

Protocol (following the top players' evaluation style):
  - every matchup plays a fixed seed block, each seed BOTH seats
  - report per-opponent win/loss/tie, mean margin AND worst margin
    (Elo only cares about W/L/T, but margins show whether a win is luck)

Episodes are independent, so they run in a process pool: with 24 logical cores
this is ~10x faster than the sequential version (the simulator is pure Python,
so GPU offers nothing here).

Usage:
  .venv/Scripts/python scripts/tournament.py --candidate main.py --seeds 1000-1009
  .venv/Scripts/python scripts/tournament.py --candidate main.py --workers 12
Results are written to tournament_results/<tag>-<timestamp>.json
"""
import argparse
import glob
import importlib.util
import json
import multiprocessing as mp
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS = os.path.join(ROOT, "tournament_results")


# "kaggle" = last callable (what Kaggle actually runs), "agent" = the name `agent`.
# Read from the environment, not from main(): the process pool uses spawn on
# Windows, so children re-import this module and would reset a plain global.
LOADER = os.environ.get("TOURNAMENT_LOADER", "kaggle")


def load_agent(path, name):
    # Kaggle's own loader appends the agent's directory to sys.path, because a
    # public release can ship a sibling module (fieldcraft ships mirror_plan.py,
    # 502KB of route data). Without this the import fails and the agent silently
    # plays nothing, which would read as a 40-0 win.
    d = os.path.dirname(os.path.abspath(path))
    if d not in sys.path:
        sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    callables = [(k, v) for k, v in vars(mod).items()
                 if callable(v) and not k.startswith("__")]
    if LOADER == "kaggle":
        # Kaggle resolves the entrypoint as the LAST callable in the namespace.
        # Several public agents (v50/v51/v52/v53/v55, prvsiyan, tetsutani,
        # kaito_v27, beatv48) define experimental layers AFTER def agent(), so
        # taking `agent` silently evaluates a shorter stack than the ladder does.
        if callables:
            return callables[-1][1]
        return mod.agent
    if callable(getattr(mod, "agent", None)):
        return mod.agent
    return callables[-1][1] if callables else None


def run_one(task):
    """One episode. Top-level so it is picklable for the process pool."""
    cand_path, opp_path, opp_name, seed, our_seat = task
    cand = load_agent(cand_path, f"cand_{opp_name}_{seed}_{our_seat}")
    opp = load_agent(opp_path, f"opp_{opp_name}_{seed}_{our_seat}")
    agents = [cand, opp] if our_seat == 0 else [opp, cand]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(agents)
    final = env.steps[-1]
    our = final[our_seat].reward
    theirs = final[1 - our_seat].reward
    return {"opponent": opp_name, "seed": seed, "our_seat": our_seat,
            "our": our, "theirs": theirs, "margin": our - theirs,
            "status": final[our_seat].status}


def parse_seeds(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="main.py")
    ap.add_argument("--seeds", default="1000-1005")
    ap.add_argument("--opponents", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=0, help="0 = auto (16 on a 24-core box)")
    ap.add_argument("--seats", default="01",
                    help="which seats to play per seed: '01' both (default), "
                         "'0' or '1' single. The environment is seat-symmetric, so "
                         "1 seat x 2x seeds gives the same wall time with twice the "
                         "independent samples.")
    ap.add_argument("--tag", default="")
    ap.add_argument("--loader", choices=("kaggle", "agent"), default="kaggle",
                    help="entrypoint rule: 'kaggle' = last callable (default, what the "
                         "ladder runs), 'agent' = the name `agent` (legacy behaviour)")
    args = ap.parse_args()
    global LOADER
    LOADER = args.loader
    os.environ["TOURNAMENT_LOADER"] = args.loader   # propagate into spawned workers

    cand_path = args.candidate if os.path.isabs(args.candidate) else os.path.join(ROOT, args.candidate)
    opp_paths = args.opponents or sorted(glob.glob(os.path.join(ROOT, "opponents", "*", "main.py")))
    seeds = parse_seeds(args.seeds)
    tag = args.tag or os.path.basename(os.path.dirname(cand_path)) or "candidate"
    workers = args.workers or max(1, min(16, (os.cpu_count() or 4) - 4))

    tasks = []
    for opp_path in opp_paths:
        # Name by the file stem when it is not the generic "main", else by its directory.
        # Using the directory alone silently merges every agent that shares a folder
        # (e.g. experiments/v35/{v34_base,consts}.py both became "v35"), which makes the
        # per-opponent breakdown useless.
        stem = os.path.splitext(os.path.basename(opp_path))[0]
        opp_name = os.path.basename(os.path.dirname(opp_path)) if stem == "main" else stem
        for seed in seeds:
            for our_seat in [int(c) for c in args.seats]:
                tasks.append((cand_path, opp_path, opp_name, seed, our_seat))

    print(f"candidate: {os.path.relpath(cand_path, ROOT)}")
    print(f"{len(opp_paths)} opponents x {len(seeds)} seeds x {len(args.seats)} seat(s) "
          f"= {len(tasks)} games, {workers} workers")
    t0 = time.time()
    with mp.Pool(processes=workers) as pool:
        recs = []
        for i, r in enumerate(pool.imap_unordered(run_one, tasks), 1):
            recs.append(r)
            if i % 20 == 0:
                print(f"    {i}/{len(tasks)} games  {time.time()-t0:.0f}s", flush=True)

    print()
    by_opp = {}
    for r in recs:
        by_opp.setdefault(r["opponent"], []).append(r)
    for opp_name in sorted(by_opp):
        rs = by_opp[opp_name]
        wins = sum(1 for r in rs if r["margin"] > 0)
        losses = sum(1 for r in rs if r["margin"] < 0)
        ties = len(rs) - wins - losses
        margins = [r["margin"] for r in rs]
        bad = [r for r in rs if r["status"] != "DONE"]
        flag = f"  [{len(bad)} non-DONE]" if bad else ""
        print(f"  {opp_name:12s} {wins:2d}W-{losses:2d}L-{ties:2d}T  "
              f"mean ${sum(margins)/len(margins):+8.0f}  worst ${min(margins):+9.0f}{flag}")
    tot_w = sum(1 for r in recs if r["margin"] > 0)
    margins = [r["margin"] for r in recs]
    print(f"  {'TOTAL':12s} {tot_w}/{len(recs)} wins ({tot_w/len(recs):.1%})  "
          f"mean ${sum(margins)/len(margins):+.0f}  worst ${min(margins):+.0f}")
    print(f"  wall {time.time()-t0:.0f}s")

    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, f"{tag}-{time.strftime('%Y%m%d-%H%M%S')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"candidate": os.path.relpath(cand_path, ROOT), "seeds": seeds,
                   "games": len(recs), "results": recs}, f, indent=1)
    print("saved ->", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
