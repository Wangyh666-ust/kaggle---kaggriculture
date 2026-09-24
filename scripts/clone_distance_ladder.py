"""Measure boatlee V14's `_clone_distance` gate on the REAL ladder corpus.

The local panels cannot answer whether the gate discriminates, because every
opponent on them belongs to the same route family (Step 1 of the task measured
the distance to be identically <= 1 against all eight of them).  The ladder
corpus contains agents from OUTSIDE the family, so it is the only place where
the gate's separation can be measured against real opponents.

For every replay that has `ReD_MooN_rise` in it we recompute, at every 4th step
inside boatlee's own preempt window [120, 680), the clone distance between the
two PUBLIC farm signatures -- i.e. exactly the quantity `_clone_distance`
returns, from data both agents can see.

Reported per domain:
  * fire rate = fraction of games whose median window distance is <= 6
  * win rate / mean margin in the fired vs silent domain
  * the cross-tab against mirror_share's clone class (turn-1 market signature
    equality with ours), which is how this repo defines "clone" on the ladder.

Usage: .venv/Scripts/python scripts/clone_distance_ladder.py
"""
import collections
import glob
import json
import multiprocessing as mp
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"
DIRS = ["replays_v21", "replays_v23", "replays_v23r", "replays_v24", "replays_v24r",
        "replays_v25", "replays_v27", "replays_v28", "replays_ladder",
        "replays_ladder_ops", "replays_all", "replays_top"]
WINDOW = list(range(120, 680, 4))
MAX_CLONE_DISTANCE = 6
KEYS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "COW", "SHEEP", "GOOSE", "PASTURE", "COOP", "WEED")


def _public_signature(farm):
    counts = {key: 0 for key in KEYS}
    for row in (farm.get("tiles") or []):
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            for field in ("crop", "animal", "kind"):
                value = str(tile.get(field, "")).upper()
                if value in counts:
                    counts[value] += 1
                    break
    return (
        len(farm.get("hands") or []),
        len(farm.get("unlocked_quadrants") or []),
        tuple(counts[key] for key in sorted(counts)),
    )


def sig(mk):
    return json.dumps([list(o) for o in (mk or [])], separators=(",", ":"))


def one(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        names = list(d["info"]["TeamNames"])
        if OURS not in names or names[0] == names[1]:
            return None
        us = names.index(OURS)
        opp = 1 - us
        st = d["steps"]
        dists = []
        for t in WINDOW:
            if t >= len(st):
                continue
            obs = st[t][0].get("observation") or {}
            farms = obs.get("farms") or []
            if len(farms) < 2:
                continue
            a, b = _public_signature(farms[0]), _public_signature(farms[1])
            dists.append(abs(a[0] - b[0]) + 3 * abs(a[1] - b[1])
                         + sum(abs(x - y) for x, y in zip(a[2], b[2])))
        if not dists:
            return None
        clone = sig((st[2][us].get("action") or {}).get("market")) == \
            sig((st[2][opp].get("action") or {}).get("market"))
        return {"file": os.path.relpath(path, ROOT), "opp": names[opp],
                "med": statistics.median(dists), "min": min(dists), "max": max(dists),
                "frac_open": sum(1 for x in dists if x <= MAX_CLONE_DISTANCE) / len(dists),
                "clone": clone,
                "margin": d["rewards"][us] - d["rewards"][opp]}
    except Exception as e:  # noqa: BLE001
        return {"err": repr(e)}


def show(name, sub):
    n = len(sub)
    if not n:
        print("%-40s n=0" % name)
        return
    w = sum(1 for r in sub if r["margin"] > 0)
    m = [r["margin"] for r in sub]
    print("%-40s n=%4d %4dW-%4dL  win %6.1f%%  mean $%+8.0f  median $%+8.0f" % (
        name, n, w, n - w, 100.0 * w / n, sum(m) / n, sorted(m)[n // 2]))


def main():
    files = []
    for dd in DIRS:
        p = os.path.join(ROOT, dd)
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))
    files = sorted(set(files))
    print("%d replay files" % len(files))
    with mp.Pool(max(1, min(10, (os.cpu_count() or 4) - 4))) as pool:
        recs = [r for r in pool.imap_unordered(one, files, chunksize=2) if r]
    bad = [r for r in recs if "err" in r]
    recs = [r for r in recs if "err" not in r]
    print("%d usable ladder games (%d unparsed)\n" % (len(recs), len(bad)))

    meds = sorted(r["med"] for r in recs)
    if meds:
        print("median window distance percentiles: "
              + "  ".join("p%d=%d" % (p, meds[min(len(meds) - 1, int(len(meds) * p / 100))])
                          for p in (5, 10, 25, 50, 75, 90, 95)))
    print("games with median distance <= 6: %d/%d (%.1f%%)" % (
        sum(1 for r in recs if r["med"] <= MAX_CLONE_DISTANCE), len(recs),
        100.0 * sum(1 for r in recs if r["med"] <= MAX_CLONE_DISTANCE) / max(1, len(recs))))

    print("\n--- gate = median window distance <= 6 (boatlee's threshold) ---")
    show("ALL", recs)
    fired = [r for r in recs if r["med"] <= MAX_CLONE_DISTANCE]
    silent = [r for r in recs if r["med"] > MAX_CLONE_DISTANCE]
    show("gate OPEN", fired)
    show("gate CLOSED", silent)
    print("\n--- cross-tab with mirror_share's ladder clone class ---")
    show("clone class (turn-1 sig)", [r for r in recs if r["clone"]])
    show("  clone AND gate OPEN", [r for r in recs if r["clone"] and r["med"] <= 6])
    show("  clone AND gate CLOSED", [r for r in recs if r["clone"] and r["med"] > 6])
    show("  non-clone AND gate OPEN", [r for r in recs if not r["clone"] and r["med"] <= 6])
    show("  non-clone AND gate CLOSED", [r for r in recs if not r["clone"] and r["med"] > 6])
    print("\nprecision of the gate for the clone class = %.0f%%" % (
        100.0 * sum(1 for r in recs if r["clone"] and r["med"] <= 6) / max(1, len(fired))))
    print("fire rate = %.1f%% (%d/%d)" % (
        100.0 * len(fired) / max(1, len(recs)), len(fired), len(recs)))

    print("\n--- how hard is the domain the gate selects?  (by median distance bucket) ---")
    buckets = [(0, 0), (1, 2), (3, 6), (7, 14), (15, 29), (30, 10 ** 9)]
    for lo, hi in buckets:
        grp = [r for r in recs if lo <= r["med"] <= hi]
        if grp:
            show("median distance %s-%s" % (lo, "" if hi > 10 ** 8 else hi), grp)

    out = os.path.join(ROOT, "reverse", "clone_distance_ladder.json")
    json.dump(recs, open(out, "w", encoding="utf-8"), indent=1)
    print("\nsaved ->", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    sys.exit(main())
