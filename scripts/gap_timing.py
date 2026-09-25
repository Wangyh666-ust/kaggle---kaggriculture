"""When does the money gap open? Aggregate it over cached ladder games.

Why this matters more than the final margin. A $300 loss that was already $300
down at day 10 is a different problem from a $300 loss that opened on day 29:

  * gap born early   -> the ramp (planting, herd, land, hiring) is behind;
  * gap born mid     -> production/route economics differ;
  * gap born late    -> the close-out is the target (liquidation, last sales,
                        the day-25..29 decisions).

The daily cash ledger can tell these apart per game, but reading 40 of them by
hand is not analysis. This collapses them into one distribution.

Usage:
  .venv/Scripts/python scripts/gap_timing.py
  .venv/Scripts/python scripts/gap_timing.py --team ReD_MooN_rise --json results/gap_timing.json
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
CACHE = os.path.join(ROOT, "tmp_replays")


def load():
    import field_ledger as FL
    out = []
    for p in sorted(glob.glob(os.path.join(CACHE, "ep-*-summary.json"))):
        try:
            g = json.load(open(p, encoding="utf-8"))
            g["steps"] = FL.denormalise(g["steps"])
            out.append(g)
        except Exception:
            continue
    return out


def series(steps, seat, field):
    """{day: value at end of day} for one field."""
    out = {}
    for r in steps:
        d = r.get(seat)
        if d:
            out[int(d["day"])] = d[field]
    return out


def analyse(g, our, opp):
    mine = series(g["steps"], our, "money")
    theirs = series(g["steps"], opp, "money")
    days = sorted(set(mine) & set(theirs))
    if not days:
        return None
    gaps = {d: mine[d] - theirs[d] for d in days}
    final = gaps[days[-1]]
    sign = 1 if final >= 0 else -1
    signed = {d: gaps[d] * sign for d in days}
    # First day the eventual winner's lead reaches half the final margin.
    half = abs(final) / 2
    born = next((d for d in days if signed[d] >= half), days[-1])
    return {"episode": g["episode"], "final": final, "born": born,
            "gap_at": {d: gaps.get(d) for d in (5, 10, 15, 20, 25, 29) if d in gaps},
            "our_end": mine[days[-1]], "opp_end": theirs[days[-1]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="ReD_MooN_rise")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    games = load()
    if not games:
        sys.exit("缓存为空；先用 scripts/opponent_fingerprint.py --ref <ref> 抓一些")

    rows = []
    for g in games:
        seats = [i for i, t in enumerate(g["teams"]) if t == args.team]
        our = seats[0] if seats else 0
        r = analyse(g, our, 1 - our)
        if r:
            r["opp"] = g["teams"][1 - our]
            rows.append(r)

    wins = [r for r in rows if r["final"] > 0]
    losses = [r for r in rows if r["final"] < 0]
    print(f"共 {len(rows)} 局：我们 {len(wins)} 胜 / {len(losses)} 负"
          f"（胜率 {100.0*len(wins)/len(rows):.0f}%）\n")

    for label, sel in (("胜局", wins), ("负局", losses)):
        if not sel:
            continue
        m = sorted(abs(r["final"]) for r in sel)
        print(f"=== {label} n={len(sel)} ===")
        print(f"  差距 |margin|: 最小 ${m[0]:,.0f}  中位 ${statistics.median(m):,.0f}  "
              f"最大 ${m[-1]:,.0f}")
        print(f"  分位数: p25 ${m[len(m)//4]:,.0f}  p75 ${m[3*len(m)//4]:,.0f}")
        born = collections.Counter(r["born"] for r in sel)
        buckets = {"0-9天(开局)": 0, "10-19天(中盘)": 0, "20-24天": 0, "25-29天(终局)": 0}
        for r in sel:
            b = r["born"]
            k = ("0-9天(开局)" if b <= 9 else "10-19天(中盘)" if b <= 19 else
                 "20-24天" if b <= 24 else "25-29天(终局)")
            buckets[k] += 1
        print("  差距在哪段时间成型（差到终局差值一半的那天）:")
        for k, v in buckets.items():
            print(f"    {k:16s} {v:>3} 局  {100.0*v/len(sel):>5.0f}%")
        med = {d: statistics.median([r["gap_at"][d] for r in sel if d in r["gap_at"]])
               for d in (5, 10, 15, 20, 25, 29)}
        print("  各天中位差（正=我们领先）: "
              + "  ".join(f"d{d} {v:+,.0f}" for d, v in med.items()))
        print()

    print("=== 双方终局资金（中位）==="
          f"  我们 胜${statistics.median([r['our_end'] for r in wins]):,.0f} / "
          f"负${statistics.median([r['our_end'] for r in losses]):,.0f}")
    print(f"  对手 胜局里${statistics.median([r['opp_end'] for r in wins]):,.0f} / "
          f"负局里${statistics.median([r['opp_end'] for r in losses]):,.0f}")
    print("\n  读法：若我们负局的终局资金明显低于胜局，是我们自己打低了；"
          "若两者接近而对手更高，是对手打得更高。")

    if args.json:
        p = args.json if os.path.isabs(args.json) else os.path.join(ROOT, args.json)
        json.dump(rows, open(p, "w", encoding="utf-8"), indent=1, default=str)
        print(f"\nsaved -> {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main()
