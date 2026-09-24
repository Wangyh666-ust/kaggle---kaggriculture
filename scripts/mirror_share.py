"""How much of the ladder is a copy of us, and how do we do against it?

The user's hypothesis: most ladder opponents run this same public agent (or a
slightly modified copy), so the win rate is set by near-mirror games. If true,
a change that specifically beats the mirror is worth far more than a general
strength gain, because it converts the modal matchup.

Classification is by the opponent's OWN opening market signature (the first
three steps of its action stream), read from the replay — not by name.

Usage:
  .venv/Scripts/python scripts/mirror_share.py replays_v25 replays_v27
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"


def sig(act):
    mk = act.get("market") if isinstance(act, dict) else None
    return json.dumps(mk, separators=(",", ":")) if mk is not None else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--team", default=OURS)
    args = ap.parse_args()

    files = []
    for a in args.dirs:
        p = a if os.path.isabs(a) else os.path.join(ROOT, a)
        files += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))

    # our own signature, taken from our own seats in the same corpus
    ours_sigs = collections.Counter()
    recs = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
            names = list(d["info"]["TeamNames"])
            us = names.index(args.team)
        except Exception:  # noqa: BLE001
            continue
        try:
            ours_sigs[sig(d["steps"][2][us].get("action"))] += 1
            recs.append((f, d, us))
        except Exception:  # noqa: BLE001
            continue
    if not ours_sigs:
        print("no replays matched")
        return
    our_sig = ours_sigs.most_common(1)[0][0]

    by_class = collections.defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "m": [],
                                                "names": collections.Counter()})
    for f, d, us in recs:
        opp = 1 - us
        try:
            osig = sig(d["steps"][2][opp].get("action"))
        except Exception:  # noqa: BLE001
            continue
        cls = "clone (same opening)" if osig == our_sig else "other"
        m = d["rewards"][us] - d["rewards"][opp]
        b = by_class[cls]
        b["w"] += m > 0
        b["l"] += m < 0
        b["t"] += m == 0
        b["m"].append(m)
        b["names"][d["info"]["TeamNames"][opp]] += 1

    n = sum(v["w"] + v["l"] + v["t"] for v in by_class.values())
    print(f"{len(files)} replays -> {n} classified games\n")
    print(f"{'class':24s} {'games':>6s} {'W-L':>8s} {'win%':>7s} {'mean margin':>12s} {'worst':>10s}")
    for cls, b in sorted(by_class.items(), key=lambda kv: -sum(kv[1][x] for x in "wlt")):
        tot = b["w"] + b["l"] + b["t"]
        rate = f"{b['w']/(b['w']+b['l']):.1%}" if b["w"] + b["l"] else "-"
        print(f"{cls:24s} {tot:6d} {f'{b[chr(119)]}-{b[chr(108)]}':>8s} {rate:>7s} "
              f"{statistics.mean(b['m']):12,.0f} {min(b['m']):10,.0f}")

    print("\nmost frequent opponents in the clone class:")
    for name, k in by_class.get("clone (same opening)", {"names": {}})["names"].most_common(6):
        print(f"   {k:3d}x  {name}")
    print("most frequent opponents in the other class:")
    for name, k in by_class.get("other", {"names": {}})["names"].most_common(6):
        print(f"   {k:3d}x  {name}")


if __name__ == "__main__":
    main()
