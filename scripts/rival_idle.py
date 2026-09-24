"""Unit-turn accounting: how many PASS (idle) turns each team's units emit.

Question this answers
---------------------
"Does the rival convert more of its 720xN unit-turns into productive actions
than we do?"  Counts every action slot (farmer + each hand) per step and splits
it into productive op vs PASS (and vs 'no action emitted at all'), for two teams
across two replay corpora, and reports the market-order layout (which op goes in
which slot) for each.

Usage:
  .venv/Scripts/python scripts/rival_idle.py \
      --a reverse/replays --a-team DSM \
      --b replays_v28 replays_v25 --b-team ReD_MooN_rise
"""
import argparse, collections, glob, json, os, statistics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LISTOPS = ("SELL", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "HIRE", "BUY_LAND")


def load(paths, team):
    out = []
    for p in paths:
        q = p if os.path.isabs(p) else os.path.join(ROOT, p)
        for f in sorted(glob.glob(os.path.join(q, "episode-*-replay.json"))):
            try:
                d = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            if "info" not in d or len(d.get("steps", [])) < 720:
                continue
            nm = d["info"].get("TeamNames") or []
            for s in (0, 1):
                if s < len(nm) and nm[s] == team:
                    out.append((os.path.basename(f), d, s))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", nargs="+", required=True); ap.add_argument("--a-team", required=True)
    ap.add_argument("--b", nargs="+", required=True); ap.add_argument("--b-team", required=True)
    ap.add_argument("--from", dest="lo", type=int, default=0)
    a = ap.parse_args()

    for lbl, rows in ((a.a_team, load(a.a, a.a_team)), (a.b_team, load(a.b, a.b_team))):
        if not rows:
            print(f"{lbl}: no seats"); continue
        per = []
        slots = collections.defaultdict(collections.Counter)
        mklen = collections.Counter()
        for f, d, s in rows:
            units = prod = idle = none = 0
            for t in range(a.lo, 720):
                act = d["steps"][t][s].get("action") or {}
                mk = act.get("market") or []
                mklen[len(mk)] += 1
                for i, o in enumerate(mk):
                    if isinstance(o, (list, tuple)) and o and o[0] in LISTOPS:
                        slots[o[0]][(i, len(mk))] += 1
                ul = [act.get("farmer")] + list(act.get("hands") or [])
                for u in ul:
                    units += 1
                    op = u[0] if isinstance(u, (list, tuple)) and u else u
                    if op is None:
                        none += 1
                    elif op == "PASS":
                        idle += 1
                    else:
                        prod += 1
            per.append((units, prod, idle, none))
        tu = sum(p[0] for p in per)
        tp = sum(p[1] for p in per)
        ti = sum(p[2] for p in per)
        tn = sum(p[3] for p in per)
        print(f"## {lbl}  (n={len(rows)} seats, steps {a.lo}..720, {tu:,} unit-turns)")
        print(f"   productive {tp:,} ({100*tp/tu:.1f}%)   PASS {ti:,} ({100*ti/tu:.1f}%)   "
              f"no-op/missing {tn:,} ({100*tn/tu:.1f}%)")
        print(f"   per game: prod {statistics.mean(p[1] for p in per):,.0f} "
              f"idle {statistics.mean(p[2] for p in per):,.0f}")
        print(f"   market list length histogram (top): "
              + ", ".join(f"{k}:{v}" for k, v in mklen.most_common(8)))
        print(f"   market slot layout:")
        for op in LISTOPS:
            if slots[op]:
                tot = sum(slots[op].values())
                top = ", ".join(f"@{i}/{n}:{c}" for (i, n), c in slots[op].most_common(4))
                print(f"     {op:<12} n={tot:<6} {top}")
        print()


if __name__ == "__main__":
    main()
