"""Turn-by-turn diff of two teams' ACTUAL action streams, keyed by shop pair.

Question this answers
---------------------
"For a shop pair both we and the rival have played, at which exact step does the
rival's action stream diverge from ours, and what does the divergence imply?"

Why not diff our *route tables* against the rival's tape
--------------------------------------------------------
Our agent is a tape agent, but its emitted action is NOT the raw tape entry: the
`Chassis` layers (`_apply_suppression`, `_sell_lead`, `_budget_guard`,
`_clamp_sells`, `_terminal_liquidation`, `_hand_align`, `_weed_repair`) rewrite
it every step. Comparing a rival's real stream against our raw tape would show a
difference on nearly every step and mean nothing (we measured: 4 identical steps
out of 575 for YARN_STORE|YARN_STORE). So both sides here are *emitted* actions
from real episodes.

Shop-pair key = `tuple(unlocked_shops[:2])` read at step 144 -- exactly the key
our `_router` uses, so "same pair" means "our router would have picked the same
route".

Usage:
    .venv/Scripts/python scripts/dsm_diff.py \
        --a reverse/replays --a-team DSM \
        --b replays_v28 replays_v25 --b-team ReD_MooN_rise \
        --pairs "YARN_STORE|YARN_STORE" --days
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROUTE_STEP = 144
DAYS = (12, 16, 20, 29)


def load(paths, team):
    """[(file, data, seat)] for every seat of `team` in the given dirs."""
    files = []
    for p in paths:
        q = p if os.path.isabs(p) else os.path.join(ROOT, p)
        files += sorted(glob.glob(os.path.join(q, "episode-*-replay.json")))
    out = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        if "info" not in d or len(d.get("steps", [])) < 720:
            continue
        names = d["info"].get("TeamNames") or []
        for s in (0, 1):
            if s < len(names) and names[s] == team:
                out.append((os.path.basename(f), d, s))
    return out


def pair_key(d, s):
    o = d["steps"][ROUTE_STEP][s]["observation"]
    return tuple((o.get("town", {}).get("unlocked_shops") or [])[:2])


def ops(o):
    return o[0] if isinstance(o, (list, tuple)) and o else o


def act_summary(d, s, lo, hi):
    """Counters over emitted actions in [lo,hi)."""
    far, hands, mkt, sells = (collections.Counter(), collections.Counter(),
                              collections.Counter(), collections.Counter())
    for t in range(lo, min(hi, len(d["steps"]))):
        a = d["steps"][t][s].get("action") or {}
        far[ops(a.get("farmer"))] += 1
        for h in (a.get("hands") or []):
            hands[ops(h)] += 1
        for o in (a.get("market") or []):
            k = ops(o)
            if k == "SELL" and len(o) >= 3:
                sells[o[1]] += o[2]
                mkt["SELL"] += o[2]
            else:
                mkt[str(k)] += 1
    return far, hands, mkt, sells


def farm_snap(d, s, day):
    t = day * 24
    if t >= len(d["steps"]):
        return None
    f = d["steps"][t][s]["observation"]["farms"][s]
    herd, crops, empty, lock = collections.Counter(), collections.Counter(), 0, 0
    for row in f["tiles"]:
        for tile in row:
            if tile == "LOCKED":
                lock += 1
            elif not isinstance(tile, dict):
                empty += 1
            elif "animal" in tile:
                herd[tile["animal"]] += 1
            elif tile.get("kind") == "PLANT":
                crops[tile["crop"]] += 1
    mx = 0
    for h in range(24):
        tt = day * 24 + h
        if tt < len(d["steps"]):
            mx = max(mx, len(d["steps"][tt][s]["observation"]["farms"][s].get("hands") or []))
    return {"herd": herd, "crops": crops, "empty": empty, "locked": lock,
            "money": f["money"], "hands": mx}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", nargs="+", required=True, help="replay dirs for team A")
    ap.add_argument("--a-team", required=True, help="team A name (e.g. DSM)")
    ap.add_argument("--b", nargs="+", required=True, help="replay dirs for team B")
    ap.add_argument("--b-team", required=True, help="team B name (e.g. ReD_MooN_rise)")
    ap.add_argument("--pairs", default="", help="comma-separated SHOP|SHOP; default all shared")
    ap.add_argument("--days", action="store_true", help="per-day side-by-side op profile")
    ap.add_argument("--profile", action="store_true", help="farm snapshots d12/16/20/29 for both")
    ap.add_argument("--sample", type=int, default=0, help="print N divergent steps verbatim")
    args = ap.parse_args()

    A = load(args.a, args.a_team)
    B = load(args.b, args.b_team)
    print(f"# A = {args.a_team}: {len(A)} seats in {'+'.join(args.a)}")
    print(f"# B = {args.b_team}: {len(B)} seats in {'+'.join(args.b)}\n")

    if args.profile:
        for lbl, rows in ((args.a_team, A), (args.b_team, B)):
            print(f"## farm snapshots: {lbl} (n={len(rows)})")
            for day in DAYS:
                snaps = [s for s in (farm_snap(d, s, day) for _, d, s in rows) if s]
                if not snaps:
                    continue
                print(f"  d{day:<3d} n={len(snaps)} money mean {statistics.mean(s['money'] for s in snaps):>10,.0f}"
                      f"  hands {statistics.mean(s['hands'] for s in snaps):>5.1f}"
                      f"  empty {statistics.mean(s['empty'] for s in snaps):>5.1f}"
                      f"  locked {statistics.mean(s['locked'] for s in snaps):>5.1f}")
                for key in ("herd", "crops"):
                    ks = sorted({k for s in snaps for k in s[key]})
                    print(f"        {key:<6}" + "".join(
                        f" {k[:4]} {statistics.mean(s[key].get(k, 0) for s in snaps):5.1f}"
                        f"[{min(s[key].get(k,0) for s in snaps)}-{max(s[key].get(k,0) for s in snaps)}]"
                        for k in ks))
            print()

    pa = collections.defaultdict(list)
    for r in A:
        pa[pair_key(r[1], r[2])].append(r)
    pb = collections.defaultdict(list)
    for r in B:
        pb[pair_key(r[1], r[2])].append(r)
    shared = sorted(set(pa) & set(pb))
    print(f"# shared shop pairs: {len(shared)}/{len(pb)} of {args.b_team}'s pairs\n")
    if args.pairs:
        want = [tuple(p.strip().split("|")) for p in args.pairs.split(",")]
    else:
        want = shared

    for key in want:
        if key not in pa or key not in pb:
            print(f"## {'|'.join(key)}: not shared (A n={len(pa.get(key,[]))}, B n={len(pb.get(key,[]))})\n")
            continue
        print(f"## {'|'.join(key)}   A n={len(pa[key])}  B n={len(pb[key])}")
        # use the longest A instance as the reference stream
        _, da, sa = max(pa[key], key=lambda r: len(r[1]["steps"]))
        _, db, sb = max(pb[key], key=lambda r: len(r[1]["steps"]))
        for lbl, d, s in ((args.a_team, da, sa), (args.b_team, db, sb)):
            far, hands, mkt, sells = act_summary(d, s, 0, 720)
            print(f"  {lbl:<16} np={d['info'].get('seed')} money_end "
                  f"{d['rewards'][s]:>10,.0f}")
            print(f"    farmer {dict(far.most_common(7))}")
            print(f"    hands  {dict(hands.most_common(7))}")
            print(f"    market {dict(mkt.most_common(7))}")
            print(f"    sells  " + "; ".join(f"{k} {v}u" for k, v in sells.most_common()))
        print()

        if args.days:
            print("  per-day (top 5 ops per actor; market numbers are UNITS sold / op counts)")
            for lbl, d, s in ((args.a_team, da, sa), (args.b_team, db, sb)):
                print(f"    === {lbl}")
                for day in range(0, 30):
                    lo, hi = day * 24, (day + 1) * 24
                    far, hands, mkt, sells = act_summary(d, s, lo, hi)
                    if not (sum(far.values()) or sum(hands.values())):
                        continue
                    print(f"      d{day:<3d} far[{' '.join(f'{k}={v}' for k,v in far.most_common(5))}]")
                    print(f"           hnd[{' '.join(f'{k}={v}' for k,v in hands.most_common(6))}]")
                    print(f"           mkt[{' '.join(f'{k}={v}' for k,v in mkt.most_common(6))}]")
            print()

        if args.sample:
            n = min(len(da["steps"]), len(db["steps"]))
            shown = 0
            for t in range(n):
                aa = da["steps"][t][sa].get("action") or {}
                bb = db["steps"][t][sb].get("action") or {}
                if aa == bb:
                    continue
                print(f"    t{t:<4d}(d{t//24:>2d}h{t%24:02d}) A {json.dumps(aa, separators=(',', ':'))[:150]}")
                print(f"                  B {json.dumps(bb, separators=(',', ':'))[:150]}")
                shown += 1
                if shown >= args.sample:
                    break
            print()


if __name__ == "__main__":
    main()
