"""Measure boatlee V14's `_clone_distance` gate against our whole opponent panel.

boatlee's gate is the only clone detector in the repo that is *not* built on the
tape/first-turn-cash idea that v31 showed to be blind inside our own family:

    _public_signature(farm) = (hands, unlocked_quadrants, tile-kind counts)
    _clone_distance(obs)    = |dh| + 3*|dq| + sum|dtile|
    gate open               <= _PREEMPT_MAX_CLONE_DISTANCE (6)

It is symmetric, seat-independent, and uses ONLY public farm state.  Step 1 of
this task is to find out whether it separates clones from non-clones at all
before anything is built on top of it.

Observation wrapper: we re-load the reference module (experiments/boatlee_v14.py)
and call ITS `_public_signature` / `_clone_distance` verbatim, while the observed
player is `main.py`.  The observer never changes its own action.

Usage:
  .venv/Scripts/python scripts/clone_distance_probe.py --seeds 2000-2004
  .venv/Scripts/python scripts/clone_distance_probe.py --opponents main v55 --seeds 2000-2009
"""
import argparse
import importlib.util
import json
import multiprocessing as mp
import os
import statistics
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402

REF = os.path.join(ROOT, "experiments", "boatlee_v14.py")
CAND = os.path.join(ROOT, "main.py")

OPPONENTS = {
    "main": os.path.join(ROOT, "main.py"),
    "v23c7": os.path.join(ROOT, "experiments", "v23c7_baseline.py"),
    "v25": os.path.join(ROOT, "experiments", "v25", "baseline_v25.py"),
    "v26": os.path.join(ROOT, "experiments", "v26", "v26_baseline.py"),
    "v27": os.path.join(ROOT, "experiments", "v28", "v27_baseline.py"),
    "v55": os.path.join(ROOT, "opponents", "v55", "main.py"),
    "prvsiyan": os.path.join(ROOT, "opponents", "prvsiyan", "main.py"),
    "guru": os.path.join(ROOT, "opponents", "guru", "main.py"),
    "beatv48": os.path.join(ROOT, "opponents", "beatv48", "main.py"),
    "boatlee": os.path.join(ROOT, "experiments", "boatlee_v14.py"),
    # wider panel: other public agents, to see what the gate actually detects
    "tetsutani": os.path.join(ROOT, "opponents", "tetsutani", "main.py"),
    "pilkwang": os.path.join(ROOT, "opponents", "pilkwang", "main.py"),
    "salem2900": os.path.join(ROOT, "opponents", "salem2900", "main.py"),
    "haideptry": os.path.join(ROOT, "opponents", "haideptry", "main.py"),
    "rule_v15": os.path.join(ROOT, "opponents", "rule_v15", "main.py"),
    "tetsutani": os.path.join(ROOT, "opponents", "tetsutani", "main.py"),
}

# boatlee V14 constants (mirrored so the probe reports the gate as they defined it)
PREEMPT_START = 120
PREEMPT_STOP = 680
MAX_CLONE_DISTANCE = 6


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
    ref_mod, _ = load(REF, "ref_%s_%d" % (opp_name, seed))
    obs_mod, obs_agent = load(CAND, "obs_%s_%d" % (opp_name, seed))
    _, opp_agent = load(opp_path, "opp_%s_%d" % (opp_name, seed))

    rows = []

    def wrapped(observation, configuration=None):
        try:
            farms = list(observation.get("farms") or [])
            if len(farms) >= 2:
                a = ref_mod._public_signature(farms[0])
                b = ref_mod._public_signature(farms[1])
                step = int(observation.get("step", 0) or 0)
                rows.append((step,
                             abs(a[0] - b[0]),
                             abs(a[1] - b[1]),
                             sum(abs(x - y) for x, y in zip(a[2], b[2])),
                             ref_mod._clone_distance(observation)))
        except Exception:
            pass
        return obs_agent(observation, configuration)

    agents = [wrapped, opp_agent] if seat == 0 else [opp_agent, wrapped]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(agents)
    fin = env.steps[-1]
    win = [r for r in rows if PREEMPT_START <= r[0] < PREEMPT_STOP]
    opn = [r for r in rows if r[0] < PREEMPT_START]
    return {
        "opponent": opp_name, "seed": seed, "seat": seat,
        "margin": fin[seat].reward - fin[1 - seat].reward,
        "n_steps": len(rows),
        "n_window": len(win),
        # gate open turns inside boatlee's own preempt window
        "gate_open_window": sum(1 for r in win if r[4] <= MAX_CLONE_DISTANCE),
        "gate_open_full": sum(1 for r in rows if r[4] <= MAX_CLONE_DISTANCE),
        # first turn the gate ever opens (or -1)
        "first_open": next((r[0] for r in rows if r[4] <= MAX_CLONE_DISTANCE), -1),
        "dist_window": [r[4] for r in win],
        "dist_open": [r[4] for r in opn],
        "dist_all": [r[4] for r in rows],
        "hands_diff": [r[1] for r in win],
        "quad_diff": [r[2] for r in win],
        "tile_diff": [r[3] for r in win],
    }


def parse_seeds(s):
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponents", nargs="+", default=list(OPPONENTS))
    ap.add_argument("--seeds", default="2000-2004")
    ap.add_argument("--seats", default="0")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--dump", default="")
    args = ap.parse_args()

    seeds = parse_seeds(args.seeds)
    seats = [int(c) for c in args.seats]
    tasks = []
    for name in args.opponents:
        p = OPPONENTS.get(name, name if os.path.isabs(name) else os.path.join(ROOT, name))
        for s in seeds:
            for st in seats:
                tasks.append((p, name, s, st))
    workers = args.workers or max(1, min(16, (os.cpu_count() or 4) - 4))
    print("%d games, %d workers" % (len(tasks), workers))
    t0 = time.time()
    with mp.Pool(workers) as pool:
        recs = list(pool.imap_unordered(one, tasks))
    print("wall %.0fs\n" % (time.time() - t0))

    by = {}
    for r in recs:
        by.setdefault(r["opponent"], []).append(r)

    def stats(vals):
        if not vals:
            return (float("nan"), float("nan"), float("nan"), -1, -1)
        s = sorted(vals)
        return (statistics.median(s), s[0], s[-1], s[int(len(s) * .10)], s[int(len(s) * .90)])

    print("%-10s %3s | %-34s | %-34s | %s" % (
        "opponent", "n", "window 120-680: med/min/max", "full game 0-719: med/min/max",
        "gate<=6 turns/game (window | full)"))
    print("-" * 128)
    rows_out = {}
    for k in sorted(by):
        rs = by[k]
        n = len(rs)
        alld = [d for r in rs for d in r["dist_window"]]
        full = [d for r in rs for d in r["dist_all"]]
        opens = [r["gate_open_window"] for r in rs]
        opens_full = [r["gate_open_full"] for r in rs]
        wins = [r["n_window"] for r in rs]
        med, mn, mx, p10, p90 = stats(alld)
        fmed, fmn, fmx, _, _ = stats(full)
        firsts = [r["first_open"] for r in rs]
        fo = statistics.median([f for f in firsts if f >= 0]) if any(f >= 0 for f in firsts) else -1
        rows_out[k] = {
            "median": med, "p10": p10, "p90": p90, "max": mx, "min": mn,
            "full_median": fmed, "full_min": fmn, "full_max": fmx,
            "gate_open_turns_per_game": sum(opens) / n,
            "gate_open_turns_full_per_game": sum(opens_full) / n,
            "window_turns_per_game": sum(wins) / n,
            "frac_window_gate_open": sum(opens) / max(1, sum(wins)),
            "frac_full_gate_open": sum(opens_full) / max(1, sum(r["n_steps"] for r in rs)),
            "games_with_gate_open": sum(1 for o in opens if o > 0),
            "games_fully_open": sum(1 for r, o in zip(rs, opens) if o == r["n_window"]),
            "first_open_median": fo,
            "wins": sum(1 for r in rs if r["margin"] > 0),
            "n": n,
        }
        print("%-10s %3d | med %6.1f  min %5d  max %5d        | med %6.1f  min %5d  max %5d        | "
              "%6.1f / %5.1f  (%.0f%% | %.0f%%)" % (
                  k, n, med, mn, mx, fmed, fmn, fmx,
                  sum(opens) / n, sum(opens_full) / n,
                  100.0 * sum(opens) / max(1, sum(wins)),
                  100.0 * sum(opens_full) / max(1, sum(r["n_steps"] for r in rs))))

    print("\nper-component means inside window (hands x1, quadrants x3, tiles x1):")
    for k in sorted(by):
        rs = by[k]
        h = statistics.mean([x for r in rs for x in r["hands_diff"]]) if rs[0]["hands_diff"] else float("nan")
        q = statistics.mean([x for r in rs for x in r["quad_diff"]]) if rs[0]["quad_diff"] else float("nan")
        t = statistics.mean([x for r in rs for x in r["tile_diff"]]) if rs[0]["tile_diff"] else float("nan")
        print("  %-10s hands %.2f   quadrants %.2f   tiles %.1f" % (k, h, q, t))

    if args.dump:
        slim = [{kk: vv for kk, vv in r.items() if not kk.startswith("dist_")} for r in recs]
        with open(args.dump, "w", encoding="utf-8") as f:
            json.dump({"summary": rows_out, "recs": slim}, f, indent=1)
        print("\nsaved ->", args.dump)


if __name__ == "__main__":
    main()
