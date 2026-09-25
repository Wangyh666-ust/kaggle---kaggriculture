"""Render one game as a self-contained HTML "field ledger".

What it is for. Reading a loss from a bare score is useless -- you cannot tell a
starved herd from an idle crew from a shop drought. This runs a single game (or
reads a saved replay) and lays every economic layer of it out side by side, in
the spirit of leoprovorov's Field Ledger: projected score, cash flow, market
execution, idle labour, tile mix, and the closing book.

No dependencies. This venv has no numpy/matplotlib/pandas, so the charts are
hand-written inline SVG in a single HTML file. That also makes the output a
thing you can open, screenshot and hand to someone, which a PNG in a tmp dir is
not.

Usage:
  .venv/Scripts/python scripts/field_ledger.py --b opponents/v53/main.py --seed 4242 \
      --out results/ledger/seed4242.html
  .venv/Scripts/python scripts/field_ledger.py --b opponents/tetsutani_cha22/main.py \
      --seeds 1000,1001,1002 --out results/ledger/tetsu.html
"""
import argparse
import collections
import html
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402

CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
MKT = ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL", "BUY_LAND", "HIRE")
COLORS = {"WHEAT": "#d9a441", "CARROT": "#e07b39", "TOMATO": "#c0392b",
          "STRAWBERRY": "#d94f8a", "MELON": "#4aa96c", "PASTURE": "#7d6b5d",
          "WEED": "#5b6b52", "EMPTY": "#cfd8d3", "LOCKED": "#8d9a93",
          "A": "#1d7b4a", "B": "#8357a8"}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cbs = [v for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
    return cbs[-1] if cbs else None


def tile_kind(tile):
    if tile is None:
        return "EMPTY"
    if tile == "LOCKED":
        return "LOCKED"
    if isinstance(tile, dict):
        k = tile.get("kind")
        if k == "CROP":
            return tile.get("crop") or "CROP"
        if k == "PASTURE":
            return "PASTURE"
        if k == "WEED":
            return "WEED"
        return str(k)
    return str(tile)


def collect(env_steps, seats=2):
    """Per-step series for every player, anchored on the observation itself.

    Takes the raw `steps` list, not an env. A fetched replay from
    `kaggle competitions replay` has exactly this shape (720 entries of two
    {action, observation, reward, status} dicts with identical observation
    keys), so the same code renders a ladder game and a local one.
    """
    steps = []
    for t in range(len(env_steps)):
        row = {"t": t}
        for seat in range(seats):
            st = env_steps[t][seat]
            obs = st.get("observation") or {}
            if not obs.get("farms"):
                row[seat] = None
                continue
            p = int(obs.get("player", seat))
            farm = obs["farms"][p]
            act = st.get("action") or {}
            hands = act.get("hands") or []
            idle = sum(1 for a in hands
                       if (isinstance(a, list) and a and a[0] == "PASS")
                       or (isinstance(a, str) and a == "PASS"))
            farmer = act.get("farmer")
            if isinstance(farmer, list) and farmer and farmer[0] == "PASS":
                idle += 1
            orders = [list(o) for o in (act.get("market") or []) if o]
            counts = collections.Counter(o[0] for o in orders if o)
            tiles = collections.Counter(tile_kind(x) for x in (farm.get("tiles") or []))
            row[seat] = {
                "step": obs.get("step", t), "day": int(obs.get("day", t // 24)),
                "hour": int(obs.get("hour", t % 24)),
                "money": float(farm.get("money", 0)),
                "hands": len(farm.get("hands") or []),
                "idle": idle, "orders": counts, "tiles": tiles,
                "shops": list((obs.get("town") or {}).get("unlocked_shops") or []),
                "shed": dict((obs.get("private") or {}).get("shed") or {}),
                "prices": dict((obs.get("market") or {}).get("prices") or {}),
            }
        steps.append(row)
    return steps


# ---------------------------------------------------------------- svg helpers
def _scale(vals, lo, hi, a, b):
    if hi <= lo:
        return (a + b) / 2
    return a + (b - a) * (vals - lo) / (hi - lo)


def line_chart(series, title, ylabel, width=980, height=210, ymin=None, ymax=None,
               markers=()):
    """series: list of (label, color, [(x, y), ...]). markers: [(x, label)]."""
    allv = [y for _, _, pts in series for _, y in pts]
    if not allv:
        return ""
    lo = min(allv) if ymin is None else ymin
    hi = max(allv) if ymax is None else ymax
    if hi == lo:
        hi = lo + 1
    ml, mr, mt, mb = 74, 12, 26, 26
    px0, px1 = ml, width - mr
    py0, py1 = mt, height - mb
    xs = [x for _, _, pts in series for x, _ in pts]
    xlo, xhi = min(xs), max(xs)
    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">',
           f'<text x="{ml}" y="15" class="ttl">{html.escape(title)}</text>']
    for i in range(5):
        yv = lo + (hi - lo) * i / 4
        yy = _scale(yv, lo, hi, py1, py0)
        out.append(f'<line x1="{px0}" y1="{yy:.1f}" x2="{px1}" y2="{yy:.1f}" class="grid"/>')
        out.append(f'<text x="{px0-6}" y="{yy+3.5:.1f}" class="ax" text-anchor="end">'
                   f'{yv:,.0f}</text>')
    for xv in (xlo, (xlo + xhi) / 2, xhi):
        xx = _scale(xv, xlo, xhi, px0, px1)
        out.append(f'<text x="{xx:.1f}" y="{py1+16}" class="ax" text-anchor="middle">'
                   f'{xv:,.0f}</text>')
    out.append(f'<text x="14" y="{(py0+py1)/2:.0f}" class="ax" transform="rotate(-90 14 '
               f'{(py0+py1)/2:.0f})" text-anchor="middle">{html.escape(ylabel)}</text>')
    for label, color, pts in series:
        d = " ".join(f"{_scale(x, xlo, xhi, px0, px1):.1f},"
                     f"{_scale(y, lo, hi, py1, py0):.1f}" for x, y in pts)
        out.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="1.7"/>')
    for mx, mlabel in markers:
        mxx = _scale(mx, xlo, xhi, px0, px1)
        out.append(f'<line x1="{mxx:.1f}" y1="{py0}" x2="{mxx:.1f}" y2="{py1}" '
                   f'class="mark"/>')
        out.append(f'<text x="{mxx+3:.1f}" y="{py0+10}" class="mk">{html.escape(mlabel)}</text>')
    lx = px0 + 8
    for label, color, _ in series:
        out.append(f'<rect x="{lx}" y="{mt-8}" width="16" height="3" fill="{color}"/>')
        out.append(f'<text x="{lx+21}" y="{mt-5}" class="lg">{html.escape(label)}</text>')
        lx += 34 + 7 * len(label)
    out.append("</svg>")
    return "\n".join(out)


def stacked_days(per_day, keys, title, width=980, height=230):
    """per_day: {day: Counter}. Stacked bars, one bar per day."""
    days = sorted(per_day)
    if not days:
        return ""
    totals = [sum(per_day[d].values()) for d in days]
    hi = max(totals) or 1
    ml, mr, mt, mb = 74, 12, 26, 34
    px0, px1 = ml, width - mr
    py0, py1 = mt, height - mb
    bw = max(2.0, (px1 - px0) / max(1, len(days)) - 2)
    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">',
           f'<text x="{ml}" y="15" class="ttl">{html.escape(title)}</text>']
    for i in range(5):
        yv = hi * i / 4
        yy = _scale(yv, 0, hi, py1, py0)
        out.append(f'<line x1="{px0}" y1="{yy:.1f}" x2="{px1}" y2="{yy:.1f}" class="grid"/>')
        out.append(f'<text x="{px0-6}" y="{yy+3.5:.1f}" class="ax" text-anchor="end">'
                   f'{yv:,.0f}</text>')
    for d in days:
        x = px0 + (px1 - px0) * (d + 0.5) / len(days) - bw / 2
        acc = 0.0
        for k in keys:
            v = per_day[d].get(k, 0)
            if not v:
                continue
            y0 = _scale(acc, 0, hi, py1, py0)
            y1 = _scale(acc + v, 0, hi, py1, py0)
            out.append(f'<rect x="{x:.1f}" y="{y1:.1f}" width="{bw:.1f}" '
                       f'height="{max(0.6, y0-y1):.1f}" fill="{COLORS.get(k, "#999")}">'
                       f'<title>day {d} {k}: {v}</title></rect>')
            acc += v
        if d % 3 == 0:
            out.append(f'<text x="{x+bw/2:.1f}" y="{py1+15}" class="ax" '
                       f'text-anchor="middle">{d}</text>')
    lx = px0 + 8
    for k in keys:
        out.append(f'<rect x="{lx}" y="{mt-8}" width="10" height="10" fill="{COLORS.get(k,"#999")}"/>')
        out.append(f'<text x="{lx+14}" y="{mt+1}" class="lg">{k}</text>')
        lx += 26 + 6 * len(k)
    out.append("</svg>")
    return "\n".join(out)


def bar_days(per_day, title, width=980, height=200, color="#1d7b4a", ylabel=""):
    days = sorted(per_day)
    if not days:
        return ""
    vals = [per_day[d] for d in days]
    lo, hi = min(min(vals), 0), max(max(vals), 1)
    ml, mr, mt, mb = 74, 12, 26, 30
    px0, px1 = ml, width - mr
    py0, py1 = mt, height - mb
    bw = max(2.0, (px1 - px0) / max(1, len(days)) - 2)
    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">',
           f'<text x="{ml}" y="15" class="ttl">{html.escape(title)}</text>']
    for i in range(5):
        yv = lo + (hi - lo) * i / 4
        yy = _scale(yv, lo, hi, py1, py0)
        out.append(f'<line x1="{px0}" y1="{yy:.1f}" x2="{px1}" y2="{yy:.1f}" class="grid"/>')
        out.append(f'<text x="{px0-6}" y="{yy+3.5:.1f}" class="ax" text-anchor="end">'
                   f'{yv:,.0f}</text>')
    zero = _scale(0, lo, hi, py1, py0)
    if lo < 0:
        out.append(f'<line x1="{px0}" y1="{zero:.1f}" x2="{px1}" y2="{zero:.1f}" '
                   f'class="axis"/>')
    for d in days:
        v = per_day[d]
        x = px0 + (px1 - px0) * (d + 0.5) / len(days) - bw / 2
        y = _scale(v, lo, hi, py1, py0)
        out.append(f'<rect x="{x:.1f}" y="{min(y,zero):.1f}" width="{bw:.1f}" '
                   f'height="{max(0.6, abs(y-zero)):.1f}" fill="{color}">'
                   f'<title>day {d}: {v:,.0f}</title></rect>')
        if d % 3 == 0:
            out.append(f'<text x="{x+bw/2:.1f}" y="{py1+15}" class="ax" '
                       f'text-anchor="middle">{d}</text>')
    out.append("</svg>")
    return "\n".join(out)


CSS = """
:root{--ink:#173322;--mut:#607468;--line:#d4e3da;--green:#1d7b4a;--violet:#8357a8;
--paper:#fcfefc;--bg:#eef4f0}
*{box-sizing:border-box}
body{margin:0;padding:22px;background:var(--bg);color:var(--ink);
font:13px/1.5 ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif}
h1{font-size:19px;margin:0 0 4px}
h2{font-size:14px;margin:22px 0 8px;padding:7px 12px;background:#fff;border:1px solid var(--line);
border-left:5px solid var(--green);border-radius:9px}
.sub{color:var(--mut);margin:0 0 14px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px;
margin-bottom:12px;box-shadow:0 4px 14px rgba(20,60,38,.05)}
.chart{width:100%;height:auto;display:block}
.grid{stroke:#e7efea;stroke-width:1}
.axis{stroke:#a9bcb2;stroke-width:1}
.mark{stroke:#c9d8d0;stroke-width:1;stroke-dasharray:3 3}
.mk{fill:#8fa49a;font-size:9px}
.ax{fill:var(--mut);font-size:10px}
.ttl{fill:var(--ink);font-size:12px;font-weight:600}
.lg{fill:var(--mut);font-size:10px}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600;background:#f7fbf8}
.win{color:var(--green);font-weight:700}.lose{color:#b85348;font-weight:700}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.kpi div{background:#fff;border:1px solid var(--line);border-radius:10px;padding:8px 13px}
.kpi b{display:block;font-size:17px}
.kpi span{color:var(--mut);font-size:11px}
.note{color:var(--mut);font-size:11px;margin:8px 2px 2px}
"""


def build_html(games, names):
    parts = [f"<!doctype html><meta charset='utf-8'><title>Field ledger</title>",
             f"<style>{CSS}</style><h1>Field ledger</h1>"]
    for g in games:
        steps, seed, final, result = g["steps"], g["seed"], g["final"], g["result"]
        parts.append(f"<p class='sub'>seed <b>{seed}</b> &middot; {html.escape(names[0])} "
                     f"(seat 0) vs {html.escape(names[1])} (seat 1) &middot; "
                     f"<span class='{'win' if result > 0 else 'lose'}'>"
                     f"{'WIN' if result > 0 else 'LOSS' if result < 0 else 'TIE'}"
                     f"</span> &middot; final ${final[0]:,.0f} : ${final[1]:,.0f}</p>")

        parts.append("<div class='kpi'>")
        for s in (0, 1):
            last = [r for r in steps if r.get(s)][-1][s]
            idle_total = sum(r[s]["idle"] for r in steps if r.get(s))
            parts.append(f"<div><b>${final[s]:,.0f}</b><span>seat {s} final bank</span></div>"
                         f"<div><b>{idle_total:,}</b><span>seat {s} idle unit-turns</span></div>"
                         f"<div><b>{len(last['shops'])}</b><span>seat {s} shops</span></div>")
        parts.append("</div>")

        # 1. bank over steps, annotated with the two structural events that
        #    dominate this architecture: the shop unlocks (which set the route)
        #    and step 144, where the router commits to a tape and stops adapting.
        ser = []
        for s in (0, 1):
            pts = [(r[s]["step"], r[s]["money"]) for r in steps if r.get(s)]
            ser.append((f"seat {s}", COLORS["A"] if s == 0 else COLORS["B"], pts))
        marks = [(144, "step144 route")]
        seen = 0
        for r in steps:
            if not r.get(0):
                continue
            n = len(r[0]["shops"])
            if n > seen:
                seen = n
                marks.append((r[0]["step"], f"+{r[0]['shops'][-1][:9]}"))
        parts.append("<div class='card'>" +
                     line_chart(ser, "Cash (every turn)", "$", markers=marks) + "</div>")

        # 2. idle labour
        ser = []
        for s in (0, 1):
            pts = [(r[s]["step"], r[s]["idle"]) for r in steps if r.get(s)]
            ser.append((f"seat {s}", COLORS["A"] if s == 0 else COLORS["B"], pts))
        parts.append("<div class='card'>" +
                     line_chart(ser, "Idle units per turn (farmer+hands issuing PASS)", "count",
                                height=170) +
                     "<p class='note'>Farm actions come from the shared route tape. Every "
                     "reflex layer in this architecture edits only the <b>market</b> list, so "
                     "idle labour is tape-determined and identical between two agents on the "
                     "same tape &mdash; differences here mean a different route or layout, "
                     "not a different market policy.</p></div>")

        # 3. tile ledger
        for s in (0, 1):
            per_day = collections.defaultdict(collections.Counter)
            for r in steps:
                if not r.get(s):
                    continue
                for k, v in r[s]["tiles"].items():
                    per_day[r[s]["day"]][k] += v
            n = len([d for d in per_day if per_day[d]])
            if not n:
                continue
            for d in per_day:
                per_day[d] = collections.Counter(
                    {k: round(v / n) for k, v in per_day[d].items()})
            keys = [k for k in (*CROPS, "PASTURE", "WEED", "EMPTY", "LOCKED")
                    if any(per_day[d].get(k) for d in per_day)]
            parts.append(f"<div class='card'>" +
                         stacked_days(per_day, keys,
                                      f"Tile ledger — seat {s} (mean over {n} samples/day)") + "</div>")

        # 4. daily cash flow
        for s in (0, 1):
            per_day = {}
            prev = None
            for r in steps:
                if not r.get(s):
                    continue
                if prev is not None and r[s]["day"] != prev[0]:
                    per_day[prev[0]] = prev[1]
                prev = (r[s]["day"], r[s]["money"])
            if prev:
                per_day[prev[0]] = prev[1]
            d0 = sorted(per_day)
            flow = {d: per_day[d] - (per_day[d - 1] if d - 1 in per_day else per_day[d])
                    for d in d0}
            parts.append(f"<div class='card'>" +
                         bar_days({d: flow[d] for d in sorted(flow)[1:]},
                                  f"Daily cash flow — seat {s} (Δbank, end of day)",
                                  color=COLORS["A"] if s == 0 else COLORS["B"]) + "</div>")

        # 5. market activity
        for s in (0, 1):
            per_day = collections.defaultdict(collections.Counter)
            for r in steps:
                if not r.get(s):
                    continue
                for k, v in r[s]["orders"].items():
                    per_day[r[s]["day"]][k] += v
            keys = [k for k in MKT if any(per_day[d].get(k) for d in per_day)]
            if not keys:
                continue
            parts.append(f"<div class='card'>" +
                         stacked_days(per_day, keys,
                                      f"Market orders per day — seat {s}") + "</div>")

        # 6. closing book
        for s in (0, 1):
            last = [r for r in steps if r.get(s)][-1][s]
            rows = "".join(
                f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>"
                for k, v in sorted(last["tiles"].items()))
            peak = collections.Counter()
            for r in steps:
                if not r.get(s):
                    continue
                for k, v in r[s]["shed"].items():
                    peak[k] = max(peak[k], int(v))
            shed = "".join(f"<tr><td>{html.escape(k)}</td><td>{peak[k]}</td>"
                           f"<td>{int(last['shed'].get(k, 0))}</td></tr>"
                           for k in sorted(peak) if peak[k])
            parts.append(f"<div class='card'><table><tr><th>seat {s} closing tiles</th>"
                         f"<th>n</th></tr>{rows}</table>"
                         f"<table style='margin-top:8px'><tr><th>shed</th><th>peak</th>"
                         f"<th>at end</th></tr>{shed or '<tr><td>-</td><td>0</td><td>0</td></tr>'}"
                         f"</table><p class='note'>Peak and end differ because a strong "
                         f"close-out sells the shed down before the final bell; a large "
                         f"end balance means stock was left unconverted.</p></div>")
        parts.append("<hr style='border:0;border-top:2px solid #d4e3da;margin:26px 0'>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="main.py")
    ap.add_argument("--b", default=None,
                    help="opponent; not needed with --replay")
    ap.add_argument("--seeds", default="4242")
    ap.add_argument("--out", default="results/ledger/ledger.html")
    ap.add_argument("--replay", default=None,
                    help="path to a fetched episode-*-replay.json (skips simulation)")
    args = ap.parse_args()

    a_path = args.a if os.path.isabs(args.a) else os.path.join(ROOT, args.a)
    b_path = None if not args.b else (
        args.b if os.path.isabs(args.b) else os.path.join(ROOT, args.b))
    names = [os.path.basename(os.path.dirname(p)) if os.path.basename(p) == "main.py"
             else os.path.splitext(os.path.basename(p))[0] for p in (a_path, b_path or a_path)]
    names[0] = "ours" if names[0] == os.path.basename(ROOT) else names[0]
    if not args.replay:
        A, B = load(a_path, "A"), load(b_path, "B")

    games = []
    if args.replay:
        rp = args.replay if os.path.isabs(args.replay) else os.path.join(ROOT, args.replay)
        d = json.load(open(rp, encoding="utf-8"))
        info = d.get("info") or {}
        teams = info.get("TeamNames") or ["seat0", "seat1"]
        names = [f"{teams[0]} (seat 0)", f"{teams[1]} (seat 1)"]
        final = [float(x) for x in d.get("rewards", [])]
        if len(final) < 2:
            final = [float(d["steps"][-1][s].get("reward") or 0) for s in (0, 1)]
        seed = info.get("seed", "?")
        print(f"replay {os.path.basename(rp)}: episode {info.get('EpisodeId')} "
              f"seed {seed}  {final[0]:,.0f} : {final[1]:,.0f}")
        games.append({"steps": collect(d["steps"]), "seed": seed, "final": final,
                      "result": final[0] - final[1]})
    for seed in ([] if args.replay else [int(x) for x in args.seeds.split(",")]):
        env = make("kaggriculture", configuration={"seed": seed}, debug=True)
        env.run([A, B])
        final = [float(env.steps[-1][s].reward) for s in (0, 1)]
        print(f"seed {seed}: {final[0]:,.0f} : {final[1]:,.0f}")
        games.append({"steps": collect(env.steps), "seed": seed, "final": final,
                      "result": final[0] - final[1]})

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(build_html(games, names))
    print(f"wrote {out}  ({os.path.getsize(out):,} bytes)")


if __name__ == "__main__":
    main()
