"""Ground-truth tape dump: wrap BOTH agents and record their raw market orders.

For each turn we record our orders and the rival's orders (exact, by wrapping the
opponent module -- a measurement-only luxury), plus the public market inventory.
That lets us test, offline, how well a *reconstruction-only* gate (inventory
deltas + town consumption) recovers the rival's sale tape, and which gate
definition separates clone opponents from the public panel.

Usage:
  .venv/Scripts/python scripts/adv_tape_features.py --opponents main v55 --seeds 2000-2004
Output: reverse/adv_tape/<opp>-<seed>.json
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402

OUT = os.path.join(ROOT, "reverse", "adv_tape")
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


def make_wrap(fn, sink):
    def inner(obs, configuration=None):
        act = fn(obs, configuration)
        try:
            sink.append({"step": int(obs["step"]),
                         "market": [list(o) for o in (act.get("market") or [])],
                         "money": float(obs["farms"][int(obs["player"])]["money"]),
                         "inv": {k: int(v) for k, v in obs["market"]["inventory"].items()},
                         "shops": list(obs["town"].get("unlocked_shops", []))})
        except Exception:
            pass
        return act
    return inner


def run(task):
    opp_path, opp_name, seed = task
    _, ours = load(os.path.join(ROOT, "main.py"), f"tp_{opp_name}_{seed}")
    _, theirs = load(opp_path, f"to_{opp_name}_{seed}")
    a_rec, b_rec = [], []
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([make_wrap(ours, a_rec), make_wrap(theirs, b_rec)])
    fin = env.steps[-1]
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{opp_name}-{seed}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"opponent": opp_name, "seed": seed,
                   "margin": fin[0].reward - fin[1].reward,
                   "ours": a_rec, "theirs": b_rec}, f)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponents", nargs="+", default=list(CANDS))
    ap.add_argument("--seeds", default="2000-2004")
    args = ap.parse_args()
    if "-" in args.seeds:
        a, b = args.seeds.split("-")
        seeds = list(range(int(a), int(b) + 1))
    else:
        seeds = [int(x) for x in args.seeds.split(",")]
    for name in args.opponents:
        p, n = resolve(name)
        for s in seeds:
            out = run((p, n, s))
            print("wrote", os.path.relpath(out, ROOT), flush=True)


if __name__ == "__main__":
    main()
