"""For clone-class ladder games: what makes the two farms diverge, and does it
explain the margin?

For every game we walk the 720 steps and classify the FIRST divergence between
the two seats' farm states, plus count later asymmetric events:

  * RANDOM WEED  - a tile that was empty on one side is a WEED on that side only
                   at end-of-day while the other side's tile is still empty
                   (the _spawn_weeds() draw; deterministic given the hidden seed)
  * TILE DIFF    - anything else (different crop/animal/hand position, i.e. the
                   two agents actually did different things)
  * MONEY DIFF   - money differs while tiles match

Output: one row per game, then group stats (clone vs other) and the correlation
between "how many random weed events hit only us minus only them" and margin.

Usage:
  .venv/Scripts/python scripts/divergence_trace.py            # clone class only
  .venv/Scripts/python scripts/divergence_trace.py --all
"""
import argparse
import collections
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE = os.path.join(ROOT, "reverse", "clone_games.jsonl")
OUT = os.path.join(ROOT, "reverse", "divergence.jsonl")


def tiles_key(farm):
    return json.dumps(farm["tiles"], sort_keys=True)


def weeds(farm):
    s = set()
    for y, row in enumerate(farm["tiles"]):
        for x, t in enumerate(row):
            if isinstance(t, dict) and t.get("kind") == "WEED":
                s.add((y, x))
    return s


def empties(farm):
    s = set()
    for y, row in enumerate(farm["tiles"]):
        for x, t in enumerate(row):
            if t is None:
                s.add((y, x))
    return s


def trace(path, us):
    d = json.load(open(os.path.join(ROOT, path), encoding="utf-8"))
    opp = 1 - us
    steps = d["steps"]
    first_state = None
    cause = None
    weed_us = weed_them = 0
    prev_w = [None, None]
    action_diff_steps = 0
    for i, s in enumerate(steps):
        a0 = json.dumps(s[0].get("action"), sort_keys=True)
        a1 = json.dumps(s[1].get("action"), sort_keys=True)
        if a0 != a1:
            action_diff_steps += 1
        fu = s[us]["observation"]["farms"][us]
        fo = s[opp]["observation"]["farms"][opp]
        wu, wo = weeds(fu), weeds(fo)
        if first_state is None and (tiles_key(fu) != tiles_key(fo)
                                    or fu["money"] != fo["money"]):
            first_state = i
            if tiles_key(fu) == tiles_key(fo):
                cause = "MONEY"
            else:
                # is the difference exactly "a random weed landed on one side"?
                eu, eo = empties(fu), empties(fo)
                only_us = wu - wo
                only_them = wo - wu
                if only_us and not only_them and only_us <= eu:
                    cause = "RANDOM_WEED_ON_US"
                elif only_them and not only_us:
                    cause = "RANDOM_WEED_ON_THEM"
                else:
                    tu = json.loads(tiles_key(fu))
                    to = json.loads(tiles_key(fo))
                    n = sum(1 for r in range(len(tu)) for c in range(len(tu[r]))
                            if tu[r][c] != to[r][c])
                    cause = f"TILE_DIFF({n})"
        # random weed events after the first divergence: a tile that is WEED now
        # on one side only (the deterministic plant-decay weeds appear on both
        # sides only if the tapes match; we only count the asymmetric ones)
    return {"file": path, "our_seat": us, "opp": d["info"]["TeamNames"][opp],
            "margin": d["rewards"][us] - d["rewards"][opp],
            "first_state_diff": first_state, "cause": cause,
            "action_diff_steps": action_diff_steps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    recs = [json.loads(l) for l in open(CACHE, encoding="utf-8")]
    ladder = [r for r in recs if not r["selfplay"]]
    our_sig = collections.Counter(r["our_open"] for r in ladder).most_common(1)[0][0]
    for r in ladder:
        r["clone"] = r["opp_open"] == our_sig
    sel = ladder if args.all else [r for r in ladder if r["clone"]]
    print(f"tracing {len(sel)} games")
    rows = []
    with open(OUT, "w", encoding="utf-8") as out:
        for i, r in enumerate(sel, 1):
            try:
                t = trace(r["file"], r["our_seat"])
            except Exception as exc:  # noqa: BLE001
                print(f"  fail {r['file']}: {exc}")
                continue
            t["clone"] = r["clone"]
            t["ver"] = r["file"].split("/")[0]
            t["n_diff_steps"] = r.get("n_diff_steps")
            rows.append(t)
            out.write(json.dumps(t) + "\n")
            if i % 40 == 0:
                print(f"  {i}/{len(sel)}", flush=True)

    for cls in (True, False):
        sub = [t for t in rows if t["clone"] == cls]
        if not sub:
            continue
        print(f"\n=== {'clone' if cls else 'other'} n={len(sub)} ===")
        c = collections.Counter(t["cause"] for t in sub)
        tot = len(sub)
        for k, v in c.most_common():
            mg = [t["margin"] for t in sub if t["cause"] == k]
            w = sum(1 for x in mg if x > 0)
            print(f"  first divergence cause {str(k):24s} {v:4d} ({v/tot:5.1%})  "
                  f"win%={w/len(mg):5.1%}  mean=${st.mean(mg):+9,.0f}")
        fd = [t["first_state_diff"] for t in sub if t["first_state_diff"] is not None]
        if fd:
            fd.sort()
            print(f"  first state divergence step: median={st.median(fd):.0f} "
                  f"p10={fd[len(fd)//10]} p90={fd[9*len(fd)//10]} min={min(fd)}")
        ad = [t["action_diff_steps"] for t in sub]
        print(f"  action-diff steps: median={st.median(ad):.0f}")

    # dose-response: random-weed asymmetry vs margin, only for WEED causes
    for cls in (True, False):
        sub = [t for t in rows if t["clone"] == cls]
        rw = [t for t in sub if t["cause"] and t["cause"].startswith("RANDOM_WEED")]
        if len(rw) < 5:
            continue
        ours = [t for t in rw if t["cause"] == "RANDOM_WEED_ON_US"]
        theirs = [t for t in rw if t["cause"] == "RANDOM_WEED_ON_THEM"]
        print(f"\n{'clone' if cls else 'other'}: first divergence is a random weed — "
              f"on us n={len(ours)} mean=${st.mean([t['margin'] for t in ours]):+,.0f} "
              f"win%={sum(1 for t in ours if t['margin']>0)/max(1,len(ours)):.0%} | "
              f"on them n={len(theirs)} mean=${st.mean([t['margin'] for t in theirs]):+,.0f} "
              f"win%={sum(1 for t in theirs if t['margin']>0)/max(1,len(theirs)):.0%}")
        if ours and theirs:
            a = [t["margin"] for t in ours]
            b = [t["margin"] for t in theirs]
            # Welch t
            ma, mb = st.mean(a), st.mean(b)
            va = st.variance(a) / len(a) if len(a) > 1 else 0
            vb = st.variance(b) / len(b) if len(b) > 1 else 0
            if va + vb > 0:
                tval = (ma - mb) / math.sqrt(va + vb)
                print(f"    difference ${ma-mb:+,.0f}  Welch t={tval:+.2f} (|t|>2 ≈ significant)")


if __name__ == "__main__":
    main()
