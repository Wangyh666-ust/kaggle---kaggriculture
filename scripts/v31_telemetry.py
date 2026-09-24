"""Per-layer telemetry for the v31 candidate over a fixed opponent x seed grid."""
import collections
import importlib.util
import multiprocessing as mp
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from kaggle_environments import make  # noqa: E402
from adv_gate_probe import resolve  # noqa: E402

CAND = os.path.join(ROOT, "experiments", "v31", "adv_gated.py")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.agent


def one(task):
    name, seed = task
    p, n = resolve(name)
    cm, ca = load(CAND, f"c{n}{seed}")
    _, oa = load(p, f"o{n}{seed}")
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([ca, oa])
    f = env.steps[-1]
    return (n, seed, f[0].reward - f[1].reward,
            dict(getattr(cm, "_ADVG_REPORT", {})),
            dict(getattr(cm, "_ADV_REPORT", {})),
            dict(getattr(cm, "_IG_REPORT", {})),
            dict(getattr(cm, "_RACE_REPORT", {})))


def main():
    seeds = list(range(2000, 2010))
    names = ["main", "v23c7", "v25", "v26", "v27", "v55", "prvsiyan", "guru"]
    tasks = [(n, s) for n in names for s in seeds]
    with mp.Pool(12) as pool:
        res = pool.map(one, tasks)
    by = collections.defaultdict(list)
    for r in res:
        by[r[0]].append(r)
    print(f"{'opp':10s} {'n':>3s} {'gateOpen':>9s} {'cloneTurns/g':>13s} "
          f"{'advTurns/g':>11s} {'advUnits/g':>11s} {'igQueue/g':>10s} {'igOpen':>7s} "
          f"{'raceCloneT/g':>13s}")
    for n in names:
        rs = by[n]
        k = len(rs)
        print(f"{n:10s} {k:3d} "
              f"{sum(1 for r in rs if r[3].get('gate_open') == 1):5d}/{k:<3d} "
              f"{sum(r[3].get('gate_clone_turns', 0) for r in rs)/k:13.1f} "
              f"{sum(r[4].get('adv_turns', 0) for r in rs)/k:11.1f} "
              f"{sum(r[4].get('adv_units', 0) for r in rs)/k:11.1f} "
              f"{sum(r[5].get('queue_changed_turns', 0) for r in rs)/k:10.1f} "
              f"{sum(r[5].get('opening_repairs', 0) for r in rs):7d} "
              f"{sum(r[6].get('race_clone_turns', 0) for r in rs)/k:13.1f}")


if __name__ == "__main__":
    main()
