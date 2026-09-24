"""What does a random weed actually cost, on the real ladder?

For each game, and each side, walk the day rollovers and record every RANDOM
weed event: a tile that was empty just before the rollover becomes WEED. (The
other weed source is deterministic plant decay, which hits both sides equally
when they run the same plan, so it is excluded.)

For each weed event we record whether that tile ever held a plant/animal again,
and after how many days. A weed that is never replanted costs the tile's whole
remaining production.

Outputs:
  * weed events per side per game
  * "never replanted" rate
  * the correlation between (our_unrecovered - their_unrecovered) and the margin
  * the same, restricted to the clone class

Usage:
  .venv/Scripts/python scripts/weed_cost.py --limit 120
  .venv/Scripts/python scripts/weed_cost.py --all
"""
import argparse
import collections
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def is_weed(t):
    return isinstance(t, dict) and t.get("kind") == "WEED"


def is_empty(t):
    return t is None or t == "LOCKED"


def is_prod(t):
    return isinstance(t, dict) and t.get("kind") in ("PLANT", "COOP", "PASTURE", "ANIMAL") \
        or (isinstance(t, dict) and ("animal" in t or "crop" in t))


def analyse(path, us):
    d = json.load(open(os.path.join(ROOT, path), encoding="utf-8"))
    opp = 1 - us
    steps = d["steps"]
    events = {0: [], 1: []}   # seat -> list of (day, y, x)
    prev = [None, None]
    prev_day = -1
    for s in steps:
        o = s[us]["observation"]
        day = o["day"]
        farms = o["farms"]
        if day != prev_day and prev[0] is not None:
            for seat, idx in ((0, us), (1, opp)):
                cur, old = farms[idx], prev[seat]
                for y in range(len(cur["tiles"])):
                    for x in range(len(cur["tiles"][y])):
                        now, was = cur["tiles"][y][x], old["tiles"][y][x]
                        if is_weed(now) and is_empty(was):
                            events[seat].append((day, y, x))
        prev = [farms[us], farms[opp]]
        prev_day = day

    # did the tile come back?
    final = steps[-1][us]["observation"]["farms"]
    out = {}
    for seat, idx in ((0, us), (1, opp)):
        n_ev = len(events[seat])
        never = 0
        for day, y, x in events[seat]:
            came_back = False
            for s in steps:
                o = s[us]["observation"]
                if o["day"] <= day:
                    continue
                t = o["farms"][idx]["tiles"][y][x]
                if is_prod(t):
                    came_back = True
                    break
            if not came_back:
                never += 1
        out[seat] = (n_ev, never)
    return {"file": path, "opp": d["info"]["TeamNames"][opp], "our_seat": us,
            "margin": d["rewards"][us] - d["rewards"][opp],
            "our_weeds": out[0][0], "our_never": out[0][1],
            "their_weeds": out[1][0], "their_never": out[1][1]}


def cov(xs, ys):
    if len(xs) < 3:
        return float("nan")
    mx, my = st.mean(xs), st.mean(ys)
    sx, sy = st.pstdev(xs), st.pstdev(ys)
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / len(xs) / (sx * sy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    cache = os.path.join(ROOT, "reverse", "clone_games.jsonl")
    recs = [json.loads(l) for l in open(cache, encoding="utf-8")]
    ladder = [r for r in recs if not r["selfplay"]]
    sig = collections.Counter(r["our_open"] for r in ladder).most_common(1)[0][0]
    sel = ladder if args.all else [r for r in ladder if r["opp_open"] == sig]
    if args.limit:
        sel = sel[:args.limit]
    print(f"analysing {len(sel)} games (clone class only = "
          f"{'no' if args.all else 'yes'}, limit={args.limit or 'none'})")
    rows = []
    out = os.path.join(ROOT, "reverse", f"weed_cost{args.tag}.jsonl")
    with open(out, "w", encoding="utf-8") as fh:
        for i, r in enumerate(sel, 1):
            try:
                t = analyse(r["file"], r["our_seat"])
            except Exception as exc:  # noqa: BLE001
                print("  fail", r["file"], exc)
                continue
            rows.append(t)
            fh.write(json.dumps(t) + "\n")
            if i % 40 == 0:
                print(f"  {i}/{len(sel)}", flush=True)

    n = len(rows)
    print(f"\nn={n}")
    print(f"  random weeds per game: ours mean {st.mean(r['our_weeds'] for r in rows):.2f}  "
          f"theirs mean {st.mean(r['their_weeds'] for r in rows):.2f}")
    print(f"  never replanted:       ours {sum(r['our_never'] for r in rows)}/"
          f"{sum(r['our_weeds'] for r in rows)}  "
          f"theirs {sum(r['their_never'] for r in rows)}/{sum(r['their_weeds'] for r in rows)}")
    d = [r["our_never"] - r["their_never"] for r in rows]
    m = [r["margin"] for r in rows]
    print(f"  corr(our_never - their_never, margin) = {cov(d, m):+.2f}")
    d2 = [r["our_weeds"] - r["their_weeds"] for r in rows]
    print(f"  corr(our_weeds - their_weeds, margin) = {cov(d2, m):+.2f}")
    same = [r for r in rows if r["our_weeds"] == r["their_weeds"]]
    print(f"  games with equal weed counts: n={len(same)} "
          f"mean margin ${st.mean([r['margin'] for r in same]):+,.0f} "
          f"win%={sum(1 for r in same if r['margin']>0)/max(1,len(same)):.1%}")
    for dlt in (-2, -1, 0, 1, 2):
        g = [r["margin"] for r in rows if r["our_never"] - r["their_never"] == dlt]
        if len(g) >= 3:
            print(f"    never-diff {dlt:+d}: n={len(g):3d} mean ${st.mean(g):+9,.0f} "
                  f"win%={sum(1 for x in g if x>0)/len(g):5.1%}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
