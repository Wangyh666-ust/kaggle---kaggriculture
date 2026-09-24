"""Harvest a ladder corpus into candidate route tables.

Background
----------
Our agent is a tape agent: `Chassis` replays `routes[router(obs)]`, where
`_router` picks the route at **step 144 (day 6)** from the **first two unlocked
shops** (`tuple(unlocked_shops[:2])`). `_R108_SHOP_ROUTES` already maps all 64
ordered pairs onto 41 recorded tapes — those tapes were themselves harvested
from recorded games (yhay81's "Shop Router", thomastschinkel's Farm).

A public ladder replay stores exactly the same object our routes are made of:
`steps[t][seat]["action"]` is a `{"farmer": …, "hands": …, "market": …}` dict —
the agent's full 720-step control stream. So the top families' tapes can be
harvested with no decoding at all, and swapped in per shop pair the same way
`_R108_DATA` / `_V92_P_BLOB` were.

This script does the extraction and, importantly, tells you **how much of the
panel the harvested routes would actually fire on** — a swap that fires on 0 of
the panel's 20 seeds cannot be A/B-tested.

Usage:
  .venv/Scripts/python scripts/harvest_routes.py --replays replays_top replays_ladder_ops \
      --out experiments/harvested/routes_top.json
  .venv/Scripts/python scripts/harvest_routes.py --replays replays_top --coverage-only
"""
import argparse
import collections
import glob
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROUTE_STEP = 144          # the router decides at day 6
TAPE_LEN = 719


def load_agent_module():
    spec = importlib.util.spec_from_file_location("_agent_for_harvest", os.path.join(ROOT, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def route_key(steps, seat):
    """The (shop, shop) tuple our router would key on, read at the decision step."""
    o = steps[ROUTE_STEP][seat]["observation"]
    return tuple((o.get("town", {}).get("unlocked_shops") or [])[:2])


def extract(steps, seat):
    """The seat's action stream in our tape format, or None if too short."""
    tape = []
    for st in steps[:TAPE_LEN]:
        act = st[seat].get("action")
        if not isinstance(act, dict):
            return None
        tape.append({"farmer": act.get("farmer"), "hands": act.get("hands", []),
                     "market": act.get("market", [])})
    return tape if len(tape) >= TAPE_LEN else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", nargs="+", default=["replays_top"])
    ap.add_argument("--out", default="experiments/harvested/routes_top.json")
    ap.add_argument("--coverage-only", action="store_true")
    ap.add_argument("--prefer", default="",
                    help="comma-separated team names to prefer when a shop pair has "
                         "several candidate tapes")
    args = ap.parse_args()

    files = []
    for a in args.replays:
        p = a if os.path.isabs(a) else os.path.join(ROOT, a)
        files += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))

    agent = load_agent_module()
    ours_new = getattr(agent, "_R108_SHOP_ROUTES", {})
    ours_old = getattr(agent, "_R110_OLD_SHOPS", {})

    harvest = {}
    per_key = collections.defaultdict(list)
    for path in files:
        d = json.load(open(path, encoding="utf-8"))
        names = d["info"]["TeamNames"]
        steps = d["steps"]
        for seat in (0, 1):
            try:
                key = route_key(steps, seat)
            except Exception:  # noqa: BLE001
                continue
            tape = extract(steps, seat)
            if not tape or len(key) < 2:
                continue
            per_key[key].append({"team": names[seat], "file": os.path.basename(path),
                                 "seed": d["info"].get("seed"),
                                 "reward": d["rewards"][seat], "tape": tape})

    # One tape per shop pair. With --prefer, a candidate from a preferred team
    # wins; otherwise the highest-scoring seat at that pair wins.
    prefer = [t.strip() for t in args.prefer.split(",") if t.strip()]
    for key, cands in per_key.items():
        if prefer:
            ranked = sorted(cands, key=lambda c: (c["team"] not in prefer, -c["reward"]))
        else:
            ranked = sorted(cands, key=lambda c: -c["reward"])
        best = ranked[0]
        harvest["|".join(key)] = {"shops": list(key), "tape": best["tape"],
                                  "source": best["team"], "episode": best["file"],
                                  "reward": best["reward"]}

    print(f"{len(files)} replays -> {len(per_key)} distinct shop pairs, "
          f"{len(harvest)} tapes harvested\n")

    print("coverage against our route tables")
    covered, missing = 0, []
    for key in sorted(per_key):
        have = key in ours_new or key in ours_old
        n = len(per_key[key])
        # how many distinct teams played this pair in the corpus
        teams = sorted({h["team"] for h in per_key[key]})
        mark = "have" if have else "NEW "
        if have:
            covered += 1
        else:
            missing.append(key)
        print(f"  {mark} {key[0]:<16s} {key[1]:<16s}  n={n}  {'/'.join(t[:16] for t in teams[:3])}")
    print(f"\n  {covered}/{len(per_key)} pairs already in our tables; "
          f"{len(missing)} are new")

    if args.coverage_only:
        return

    out = os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"harvestedAt": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
                   "replays": len(files), "pairs": harvest}, fh)
    print(f"\nwrote {args.out} ({len(harvest)} tapes x {TAPE_LEN} steps)")


if __name__ == "__main__":
    main()
