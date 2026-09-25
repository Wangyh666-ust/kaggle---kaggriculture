"""Win rate per shop world, not one global number.

Why. Our methodology note L4 says the local panel has a structural hole: the
band of opponents that actually hurts us on the ladder is not represented
locally, so a global local win rate hides where we lose. leoprovorov's agent-map
framing gives the fix -- "the useful unit of analysis is a route inside a world,
not one global win rate" -- because the shop draw decides which route the tape
commits to, and therefore which economics we play.

This runs a candidate against a panel, records the world (the first two unlocked
shops, which is exactly what the router reads at step 144) plus coarse world
features, and reports the win rate per cell. The point is to find cells where we
lose systematically, not to raise the global average.

Usage:
  .venv/Scripts/python scripts/world_split.py --candidate experiments/v41/cxd.py \
      --opponents opponents/v53/main.py opponents/v55/main.py --seeds 1000-1049
"""
import argparse
import collections
import importlib.util
import json
import multiprocessing as mp
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from kaggle_environments import make  # noqa: E402

MILK_SHOPS = ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP")
EGG_SHOPS = ("BAKERY", "BRUNCH_SPOT")
TOM_SHOPS = ("PIZZA_SHOP", "FARMERS_MARKET")


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cbs = [v for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
    return cbs[-1] if cbs else None


def run_one(task):
    cand_path, opp_path, opp_name, seed, our_seat = task
    cand = load_agent(cand_path, f"c{opp_name}{seed}{our_seat}")
    opp = load_agent(opp_path, f"o{opp_name}{seed}{our_seat}")
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([cand, opp] if our_seat == 0 else [opp, cand])

    # The world is fixed the moment the second shop unlocks; read it at the
    # last step before the router commits (step 144 / day 6).
    obs = env.steps[144][our_seat]["observation"]
    shops = list(obs["town"]["unlocked_shops"])
    p = int(obs.get("player", our_seat))
    quads = len(obs["farms"][p].get("unlocked_quadrants") or [])

    final = env.steps[-1]
    our, theirs = float(final[our_seat].reward), float(final[1 - our_seat].reward)
    return {
        "opponent": opp_name, "seed": seed, "seat": our_seat,
        "world": tuple(sorted(shops[:2])), "order": tuple(shops[:2]),
        "n_shops": len(shops), "quads": quads,
        "our": our, "theirs": theirs, "margin": our - theirs,
        "win": our > theirs, "tie": our == theirs,
    }


def parse_seeds(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def rates(rows, key):
    """key: callable row -> cell label. Returns [(cell, n, win_rate, mean_margin)]."""
    agg = collections.defaultdict(lambda: [0, 0, 0.0])
    for r in rows:
        c = key(r)
        if c is None:
            continue
        agg[c][0] += 1
        agg[c][1] += 1 if r["win"] else 0
        agg[c][2] += r["margin"]
    out = []
    for c, (n, w, m) in agg.items():
        out.append((c, n, w / n, m / n))
    return sorted(out, key=lambda x: x[2])


def show(title, items, min_n=1):
    print(f"\n=== {title} ===")
    print(f"  {'cell':44s} {'n':>4} {'win%':>7} {'mean margin':>13}")
    for c, n, wr, mm in items:
        if n < min_n:
            continue
        label = c if isinstance(c, str) else str(c)
        print(f"  {label[:44]:44s} {n:>4} {100*wr:>6.1f}% {mm:>+13,.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="main.py")
    ap.add_argument("--opponents", nargs="*", required=True)
    ap.add_argument("--seeds", default="1000-1049")
    ap.add_argument("--seats", default="01")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    cand = args.candidate if os.path.isabs(args.candidate) else os.path.join(ROOT, args.candidate)
    seeds = parse_seeds(args.seeds)
    workers = args.workers or max(1, min(16, (os.cpu_count() or 4) - 4))

    tasks = []
    for opp in args.opponents:
        p = opp if os.path.isabs(opp) else os.path.join(ROOT, opp)
        stem = os.path.splitext(os.path.basename(p))[0]
        name = os.path.basename(os.path.dirname(p)) if stem == "main" else stem
        for seed in seeds:
            for seat in [int(c) for c in args.seats]:
                tasks.append((cand, p, name, seed, seat))

    print(f"candidate: {os.path.relpath(cand, ROOT)}")
    print(f"{len(args.opponents)} opponents x {len(seeds)} seeds x {len(args.seats)} seat(s) "
          f"= {len(tasks)} games, {workers} workers")
    rows = []
    with mp.Pool(workers) as pool:
        for i, r in enumerate(pool.imap_unordered(run_one, tasks), 1):
            rows.append(r)
            if i % 50 == 0:
                print(f"    {i}/{len(tasks)} games", flush=True)

    wins = sum(1 for r in rows if r["win"])
    print(f"\n  TOTAL {wins}/{len(rows)} = {100*wins/len(rows):.1f}%   "
          f"mean ${sum(r['margin'] for r in rows)/len(rows):+,.0f}")

    show("by shop world (exact pair, sorted)",
         rates(rows, lambda r: " + ".join(r["world"]) or "(none)"), min_n=3)
    show("by shop world (unlock order preserved)",
         rates(rows, lambda r: " -> ".join(r["order"]) or "(none)"), min_n=3)
    show("by milk-shop count in the first two",
         rates(rows, lambda r: f"{sum(s in MILK_SHOPS for s in r['world'])} milk shops"), min_n=3)
    show("by egg-shop count",
         rates(rows, lambda r: f"{sum(s in EGG_SHOPS for s in r['world'])} egg shops"), min_n=3)
    show("by tomato-shop count",
         rates(rows, lambda r: f"{sum(s in TOM_SHOPS for s in r['world'])} tomato shops"), min_n=3)
    show("by quadrant count at step 144",
         rates(rows, lambda r: f"{r['quads']} quadrants"), min_n=3)
    show("by opponent", rates(rows, lambda r: r["opponent"]), min_n=3)
    show("by seat", rates(rows, lambda r: f"seat {r['seat']}"), min_n=3)

    if args.out:
        out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump([{**r, "world": list(r["world"]), "order": list(r["order"])} for r in rows],
                  open(out, "w", encoding="utf-8"), indent=1)
        print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
