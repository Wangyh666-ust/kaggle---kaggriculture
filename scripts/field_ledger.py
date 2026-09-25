"""Render one game as a self-contained HTML "field ledger".

What it is for. Reading a loss from a bare score is useless -- you cannot tell a
starved herd from an idle crew from a shop drought. This runs a single game (or
reads a fetched replay) and lays the economic layers of it out in order, with a
plain-language takeaway at the top so the reader knows what they are looking at
before they see a single line.

No dependencies. This venv has no numpy/matplotlib/pandas, so the charts are
hand-written inline SVG in one HTML file. That also makes the output something
you can open, screenshot and send to someone, which a PNG in a tmp dir is not.

Rendering notes that are easy to get wrong (all three bit the first version):
  * every series must have an explicit colour -- a `.get(key, "#999")` fallback
    turned six market-order types into six identical grey stacks;
  * the SVG must not upscale past its viewBox width, or its 12px labels balloon
    out of proportion with the surrounding 13px page text;
  * panels comparing the two seats belong next to each other, not interleaved
    seat0-panel / seat1-panel / next-panel / seat1-panel.

Usage:
  .venv/Scripts/python scripts/field_ledger.py --b opponents/v53/main.py --seed 4242 \
      --out results/ledger/seed4242.html
  .venv/Scripts/python scripts/field_ledger.py --a experiments/v41/cxd.py \
      --b opponents/tetsutani_cha22/main.py --seeds 1000,1001 --out results/ledger/t.html
  .venv/Scripts/python scripts/field_ledger.py --replay replays/episode-112865123-replay.json \
      --out results/ledger/ladder.html
"""
import argparse
import collections
import html
import importlib.util
import math
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402

CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
TILE_ORDER = (*CROPS, "PASTURE", "WEED", "EMPTY", "LOCKED")
TILE_CN = {"WHEAT": "小麦", "CARROT": "胡萝卜", "TOMATO": "番茄", "STRAWBERRY": "草莓",
           "MELON": "瓜", "PASTURE": "牧场", "WEED": "杂草", "EMPTY": "空", "LOCKED": "锁"}
MKT_ORDER = ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL", "BUY_LAND", "HIRE")
MKT_CN = {"SELL": "卖出", "BUY_PRODUCT": "买货物", "BUY_SEED": "买种子",
          "BUY_ANIMAL": "买动物", "BUY_LAND": "买地", "HIRE": "雇工"}
SHOP_CN = {"BAKERY": "面包房", "BRUNCH_SPOT": "早午餐", "FARMERS_MARKET": "农夫市集",
           "ICE_CREAM_SHOP": "冰淇淋店", "PET_CAFE": "宠物咖啡", "PIZZA_SHOP": "披萨店",
           "SMOOTHIE_SHOP": "果汁店", "YARN_STORE": "毛线店"}

# Every series that can appear needs its own colour, and the six market-order
# types need colours that stay apart from each other.
COLOR = {
    "WHEAT": "#d9a441", "CARROT": "#e07b39", "TOMATO": "#c0392b",
    "STRAWBERRY": "#d94f8a", "MELON": "#4aa96c", "PASTURE": "#8d6e52",
    "WEED": "#4e5f45", "EMPTY": "#dde5e0", "LOCKED": "#98a49c",
    "SELL": "#c0392b", "BUY_PRODUCT": "#2471a3", "BUY_SEED": "#1e8449",
    "BUY_ANIMAL": "#7d3c98", "BUY_LAND": "#b9770e", "HIRE": "#5d6d7e",
    "s0": "#1d7b4a", "s1": "#8357a8",
}
SEAT_COLOR = ("#1d7b4a", "#8357a8")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cbs = [v for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
    return cbs[-1] if cbs else None


def iter_tiles(farm):
    """Yield every tile of a farm, flattening the board.

    `farm["tiles"]` is a 10x10 grid of ROWS, not a flat list. Passing a row to
    tile_kind() made isinstance(row, dict) false, so it returned str(row) -- the
    whole row as a crop name. Every key was then a unique string, the key filter
    matched nothing, and the tile panel rendered axes with no bars at all.
    """
    tiles = farm.get("tiles") or []
    if tiles and isinstance(tiles[0], (list, tuple)):
        for row in tiles:
            for t in row:
                yield t
    else:
        for t in tiles:
            yield t


def tile_kind(tile):
    """Map one tile to a ledger category.

    The engine's kinds are PLANT (not CROP) for crops, plus PASTURE and COOP for
    the animal structures; a None tile is bare soil.
    """
    if tile is None:
        return "EMPTY"
    if isinstance(tile, str):
        return tile
    get = getattr(tile, "get", None)
    if get is None:
        return "OTHER"
    k = get("kind")
    if k == "PLANT":
        return get("crop") or "OTHER"
    if k in ("PASTURE", "COOP"):
        return "PASTURE"
    if k == "WEED":
        return "WEED"
    if k in ("EMPTY", "LOCKED"):
        return k
    return str(k)


def collect(env_steps, seats=2):
    """Per-step series for every player.

    Takes the raw `steps` list, not an env: a fetched replay from
    `kaggle competitions replay` has exactly this shape.
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
            units = 1 + len(hands)
            orders = [list(o) for o in (act.get("market") or []) if o]
            row[seat] = {
                "step": obs.get("step", t), "day": int(obs.get("day", t // 24)),
                "hour": int(obs.get("hour", t % 24)),
                "money": float(farm.get("money", 0)),
                "hands": len(farm.get("hands") or []),
                "idle": idle, "units": units,
                "orders": collections.Counter(o[0] for o in orders if o),
                "tiles": collections.Counter(tile_kind(x) for x in iter_tiles(farm)),
                "shops": list((obs.get("town") or {}).get("unlocked_shops") or []),
                "shed": dict((obs.get("private") or {}).get("shed") or {}),
                "prices": dict((obs.get("market") or {}).get("prices") or {}),
                "order_list": orders,
            }
        steps.append(row)
    return steps


def fmt_money(v):
    a = abs(v)
    if a >= 1_000_000:
        return f"{v/1e6:.2f}M"
    if a >= 10_000:
        return f"{v/1000:.0f}k"
    if a >= 1000:
        return f"{v/1000:.1f}k"
    return f"{v:.0f}"


# ------------------------------------------------------------------ new charts
def _ax(out, px0, px1, py0, py1, lo, hi, n=5, money=True):
    for i in range(n + 1):
        yv = lo + (hi - lo) * i / n
        yy = _scale(yv, lo, hi, py1, py0)
        out.append(f'<line x1="{px0}" y1="{yy:.1f}" x2="{px1}" y2="{yy:.1f}" class="grid"/>')
        lab = f"${fmt_money(yv)}" if money else f"{yv:,.0f}"
        out.append(f'<text x="{px0-8}" y="{yy+4:.1f}" class="ax axy">{lab}</text>')


def _scale(v, lo, hi, a, b):
    if hi <= lo:
        return (a + b) / 2
    return a + (b - a) * (v - lo) / (hi - lo)


def line_panel(series, title, xlabel, ylabel, markers=(), width=980, height=250, money=True):
    """series: [(label, color, [(x, y), ...])] -- several seats on one axis.

    Layout choices that came out of reading the rendered page, not the code:
      * no rotated y-axis title -- it sat on top of the legend; the subtitle
        already names the unit;
      * the legend lives on its own row UNDER the plot, so it can never collide
        with axis labels;
      * marker labels are deduplicated and staggered over three rows, because
        eight shop unlocks in one game otherwise print on top of each other;
      * the first/last x tick anchors are clamped so they are not clipped.
    """
    pts_all = [p for _, _, ps in series for p in ps]
    if not pts_all:
        return ""
    xlo, xhi = min(p[0] for p in pts_all), max(p[0] for p in pts_all)
    ys = [p[1] for p in pts_all]
    lo, hi = 0, (max(ys) if max(ys) > 0 else 1)
    ml, mr, mt, mb = 66, 26, 52, 74
    px0, px1, py0, py1 = ml, width - mr, mt, height - mb
    o = [f'<svg viewBox="0 0 {width} {height}" class="chart">',
         f'<text x="{ml}" y="18" class="ttl">{html.escape(title)}</text>',
         f'<text x="{ml}" y="34" class="sub2">{html.escape(ylabel)}</text>']
    _ax(o, px0, px1, py0, py1, lo, hi, money=money)
    for i, xv in enumerate((xlo, (xlo + xhi) / 2, xhi)):
        xx = _scale(xv, xlo, xhi, px0, px1)
        anchor = ("start" if i == 0 else "end" if i == 2 else "middle")
        o.append(f'<text x="{xx:.1f}" y="{py1+18}" class="ax" text-anchor="{anchor}">'
                 f'{xv:,.0f}</text>')
    o.append(f'<text x="{(px0+px1)/2:.0f}" y="{py1+36}" class="ax mid">'
             f'{html.escape(xlabel)}</text>')
    for label, color, pts in series:
        d = " ".join(f"{_scale(x, xlo, xhi, px0, px1):.1f},{_scale(y, lo, hi, py1, py0):.1f}"
                     for x, y in pts)
        o.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="1.8"/>')
    # Markers: keep the tick, stagger the label over three rows, drop repeats.
    seen_lbl = set()
    row = 0
    for mx, mlabel in markers:
        mxx = _scale(mx, xlo, xhi, px0, px1)
        o.append(f'<line x1="{mxx:.1f}" y1="{py0}" x2="{mxx:.1f}" y2="{py1}" class="mark">'
                 f'<title>{html.escape(mlabel)}</title></line>')
        if mlabel in seen_lbl:
            continue
        seen_lbl.add(mlabel)
        ly = py0 + 11 + row * 11
        anchor = "end" if mxx > px1 - 60 else "start"
        o.append(f'<text x="{mxx + (-3 if anchor == "end" else 3):.1f}" y="{ly:.0f}" '
                 f'class="mk" text-anchor="{anchor}">{html.escape(mlabel)}</text>')
        row = (row + 1) % 3
    lx = ml
    for label, color, _ in series:
        o.append(f'<rect x="{lx}" y="{py1+48}" width="18" height="4" rx="2" fill="{color}"/>')
        o.append(f'<text x="{lx+23}" y="{py1+53}" class="lg">{html.escape(label)}</text>')
        lx += 34 + 13 * len(label)
    o.append("</svg>")
    return "\n".join(o)


def stacked_panel(per_day, keys, title, note="", width=980, height=250, label_cn=None):
    days = sorted(per_day)
    if not days:
        return ""
    hi = max(sum(per_day[d].values()) for d in days) or 1
    ml, mr, mt, mb = 82, 18, 54, 40
    px0, px1, py0, py1 = ml, width - mr, mt, height - mb
    bw = max(2.0, (px1 - px0) / max(1, len(days)) - 2)
    o = [f'<svg viewBox="0 0 {width} {height}" class="chart">',
         f'<text x="{ml}" y="18" class="ttl">{html.escape(title)}</text>']
    if note:
        o.append(f'<text x="{ml}" y="34" class="sub2">{html.escape(note)}</text>')
    _ax(o, px0, px1, py0, py1, 0, hi, money=False)
    for d in days:
        x = px0 + (px1 - px0) * (d + 0.5) / len(days) - bw / 2
        acc = 0.0
        for k in keys:
            v = per_day[d].get(k, 0)
            if not v:
                continue
            y0 = _scale(acc, 0, hi, py1, py0)
            y1 = _scale(acc + v, 0, hi, py1, py0)
            cn = (label_cn or {}).get(k, k)
            o.append(f'<rect x="{x:.1f}" y="{y1:.1f}" width="{bw:.1f}" '
                     f'height="{max(0.8, y0-y1):.1f}" fill="{COLOR.get(k, "#888")}">'
                     f'<title>第{d}天 {cn}: {v}</title></rect>')
            acc += v
        if d % 3 == 0:
            o.append(f'<text x="{x+bw/2:.1f}" y="{py1+18}" class="ax mid">{d}</text>')
    o.append(f'<text x="{(px0+px1)/2:.0f}" y="{height-4}" class="ax mid">第几天</text>')
    lx = ml
    for k in keys:
        cn = (label_cn or {}).get(k, k)
        o.append(f'<rect x="{lx}" y="{mt-18}" width="11" height="11" rx="2" '
                 f'fill="{COLOR.get(k, "#888")}"/>')
        o.append(f'<text x="{lx+15}" y="{mt-9}" class="lg">{html.escape(cn)}</text>')
        lx += 24 + 13 * len(cn)
    o.append("</svg>")
    return "\n".join(o)


def grouped_panel(by_seat, title, note="", width=980, height=250):
    """by_seat: {seat: {day: value}} -- two bars per day so they compare directly."""
    days = sorted(set().union(*[set(v) for v in by_seat.values()])) if by_seat else []
    if not days:
        return ""
    vals = [v for d in by_seat.values() for v in d.values()] or [0]
    lo, hi = min(min(vals), 0), max(max(vals), 1)
    ml, mr, mt, mb = 82, 18, 54, 40
    px0, px1, py0, py1 = ml, width - mr, mt, height - mb
    slot = (px1 - px0) / max(1, len(days))
    bw = max(2.0, slot / 2 - 1.5)
    o = [f'<svg viewBox="0 0 {width} {height}" class="chart">',
         f'<text x="{ml}" y="18" class="ttl">{html.escape(title)}</text>']
    if note:
        o.append(f'<text x="{ml}" y="34" class="sub2">{html.escape(note)}</text>')
    _ax(o, px0, px1, py0, py1, lo, hi)
    zero = _scale(0, lo, hi, py1, py0)
    if lo < 0:
        o.append(f'<line x1="{px0}" y1="{zero:.1f}" x2="{px1}" y2="{zero:.1f}" class="axis"/>')
    for i, d in enumerate(days):
        for seat in sorted(by_seat):
            v = by_seat[seat].get(d, 0)
            x = px0 + slot * i + slot / 2 + (seat - 0.5) * (bw + 1.5) - bw / 2
            y = _scale(v, lo, hi, py1, py0)
            o.append(f'<rect x="{x:.1f}" y="{min(y,zero):.1f}" width="{bw:.1f}" '
                     f'height="{max(0.8, abs(y-zero)):.1f}" fill="{SEAT_COLOR[seat]}">'
                     f'<title>第{d}天 seat{seat}: {v:+,.0f}</title></rect>')
        if d % 3 == 0:
            o.append(f'<text x="{px0+slot*i+slot/2:.1f}" y="{py1+18}" class="ax mid">{d}</text>')
    o.append(f'<text x="{(px0+px1)/2:.0f}" y="{height-4}" class="ax mid">第几天</text>')
    lx = ml
    for seat in sorted(by_seat):
        o.append(f'<rect x="{lx}" y="{mt-18}" width="11" height="11" rx="2" '
                 f'fill="{SEAT_COLOR[seat]}"/>')
        o.append(f'<text x="{lx+15}" y="{mt-9}" class="lg">seat {seat}</text>')
        lx += 76
    o.append("</svg>")
    return "\n".join(o)


SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}
LAND_COST = (1000, 2000, 4000)


def revenue_mix(steps, seat):
    """Gross revenue split by product, plus the numbers that justify the split.

    Two ways to attribute revenue were tried and one was thrown away:

      * bound each SELL by the shed we can read -> covered only 19% of the real
        cash inflows, because these tapes harvest and sell inside the same turn
        and the harvest never appears in the observation we read. A pie built on
        19% of the money is worse than no pie.
      * sum the EMITTED sell orders at the quoted price -> $98,333 against
        $89,515 of real inflows, a ratio of 1.10. The order stream carries the
        product mix faithfully; the overshoot is the orders that only partly
        filled.

    So the mix comes from the order stream and the total is anchored to the real
    cash inflows. The ratio is returned as a metric in its own right: it is the
    share of what we tried to sell that actually executed.
    """
    emitted = collections.Counter()
    inflow = outflow = 0.0
    prev = None
    for r in steps:
        if not r.get(seat):
            continue
        d = r[seat]
        if prev is not None:
            delta = d["money"] - prev
            if delta > 0:
                inflow += delta
            else:
                outflow -= delta
        prev = d["money"]
        for o in d["order_list"]:
            if o and o[0] == "SELL" and len(o) >= 3:
                emitted[o[1]] += int(o[2]) * float(d["prices"].get(o[1], 0))
    total = sum(emitted.values())
    scale = (inflow / total) if total else 0.0
    mix = collections.Counter({k: v * scale for k, v in emitted.items()})
    return mix, inflow, outflow, total


def pie_panel(items, title, note="", width=980, height=300):
    """items: [(label, value)] -- sorted descending, one slice each."""
    items = [(k, v) for k, v in items if v > 0]
    if not items:
        return ""
    items.sort(key=lambda kv: -kv[1])
    total = sum(v for _, v in items)
    cx, cy, rad = 190, height / 2, min(height / 2 - 34, 108)
    o = [f'<svg viewBox="0 0 {width} {height}" class="chart">',
         f'<text x="24" y="20" class="ttl">{html.escape(title)}</text>']
    if note:
        o.append(f'<text x="24" y="37" class="sub2">{html.escape(note)}</text>')
    ang = -90.0
    palette = ["#c0392b", "#2471a3", "#1e8449", "#7d3c98", "#b9770e", "#5d6d7e",
               "#d94f8a", "#16a085", "#8e44ad", "#2c3e50"]
    for i, (k, v) in enumerate(items):
        frac = v / total
        sweep = 360.0 * frac
        a0, a1 = math.radians(ang), math.radians(ang + sweep)
        x0, y0 = cx + rad * math.cos(a0), cy + rad * math.sin(a0)
        x1, y1 = cx + rad * math.cos(a1), cy + rad * math.sin(a1)
        large = 1 if sweep > 180 else 0
        color = palette[i % len(palette)]
        cn = TILE_CN.get(k, MKT_CN.get(k, k))
        if frac > 0.9999:
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="{color}">'
                     f'<title>{cn} {v:,.0f} (100%)</title></circle>')
        else:
            o.append(f'<path d="M {cx} {cy} L {x0:.1f} {y0:.1f} '
                     f'A {rad} {rad} 0 {large} 1 {x1:.1f} {y1:.1f} Z" fill="{color}">'
                     f'<title>{cn} {v:,.0f} ({100*frac:.1f}%)</title></path>')
        ang += sweep
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{rad*0.52:.0f}" fill="#fff"/>')
    o.append(f'<text x="{cx}" y="{cy-4}" class="ax mid" style="font-size:13px;fill:#16302a">'
             f'合计</text>')
    o.append(f'<text x="{cx}" y="{cy+16}" class="ax mid" '
             f'style="font-size:15px;font-weight:700;fill:#16302a">${total:,.0f}</text>')
    # Legend, in descending order, with the share spelled out.
    ly = 62
    lx = 350
    for i, (k, v) in enumerate(items):
        color = palette[i % len(palette)]
        cn = TILE_CN.get(k, MKT_CN.get(k, k))
        o.append(f'<rect x="{lx}" y="{ly-10}" width="12" height="12" rx="3" fill="{color}"/>')
        o.append(f'<text x="{lx+18}" y="{ly}" class="lg">{html.escape(cn)}</text>')
        o.append(f'<text x="{width-24}" y="{ly}" class="lg" text-anchor="end">'
                 f'${v:,.0f} &nbsp; {100.0*v/total:.1f}%</text>')
        ly += 21
        if ly > height - 12:
            break
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ narrative
def summarise(steps, seat, name):
    """One plain sentence per seat: what actually happened, in order."""
    rs = [r[seat] for r in steps if r.get(seat)]
    if not rs:
        return ""
    first, last = rs[0], rs[-1]
    money = {r["step"]: r["money"] for r in rs}
    idle = sum(r["idle"] for r in rs)
    units = sum(r["units"] for r in rs)
    end_tiles = last["tiles"]
    planted = sum(end_tiles.get(c, 0) for c in CROPS)
    sheds = "、".join(f"{SHOP_CN.get(s, s)}" for s in last["shops"])
    peak = max(r["money"] for r in rs)
    return (f"<b>{html.escape(name)}（seat {seat}）</b> 终局 "
            f"<b>${last['money']:,.0f}</b>，峰值 ${peak:,.0f}。"
            f"忙碌度：{units - idle:,}/{units:,} 个单位·回合在干活"
            f"（闲置 {100.0 * idle / max(1, units):.1f}%）。"
            f"终局地里 {planted}/25 格是作物，店铺：{sheds or '无'}。")


def gap_day(steps, s0, s1):
    """The day the eventual winner first took a decisive lead -- the 'when'."""
    rs = [(r[s0], r[s1]) for r in steps if r.get(s0) and r.get(s1)]
    if not rs:
        return None, 0.0
    final = rs[-1][0]["money"] - rs[-1][1]["money"]
    win = 0 if final >= 0 else 1
    thr = abs(final) * 0.25
    peak = 0.0
    for a, b in rs:
        d = (a["money"] - b["money"]) * (1 if win == 0 else -1)
        peak = max(peak, d)
        if d >= thr:
            return a["day"], peak
    return rs[-1][0]["day"], peak


CSS = """
:root{--ink:#16302a;--mut:#64766e;--line:#dbe6e0;--bg:#eff4f1;--card:#fff}
*{box-sizing:border-box}
body{margin:0;padding:24px;background:var(--bg);color:var(--ink);
font:14px/1.6 "Segoe UI","Microsoft YaHei",system-ui,sans-serif}
.wrap{max-width:1060px;margin:0 auto}
h1{font-size:21px;margin:0 0 6px}
h2{font-size:16px;margin:26px 0 10px;padding:9px 14px;background:#fff;
border:1px solid var(--line);border-left:5px solid #1d7b4a;border-radius:10px}
h3{font-size:14px;margin:0 0 2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:12px 14px;margin-bottom:12px;box-shadow:0 3px 12px rgba(20,60,38,.05)}
.lead{color:var(--mut);margin:0 0 16px;max-width:74ch}
.howto{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 16px;
margin-bottom:18px}
.howto li{margin:3px 0;color:var(--mut)}
.howto b{color:var(--ink)}
.chart{width:100%;max-width:980px;height:auto;display:block;margin:0 auto}
.grid{stroke:#e8f0ec;stroke-width:1}
.axis{stroke:#a9bcb2;stroke-width:1}
.ax{fill:var(--mut);font-size:12px}
.axy{text-anchor:end}
.mid{text-anchor:middle}
.sub2{fill:var(--mut);font-size:11.5px}
.ttl{fill:var(--ink);font-size:13px;font-weight:600}
.lg{fill:var(--mut);font-size:12px}
.mark{stroke:#b9cbc2;stroke-width:1;stroke-dasharray:4 4}
.mk{fill:#7f948a;font-size:10.5px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.row>.card{flex:1 1 460px;margin-bottom:0}
.row{margin-bottom:12px}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:6px}
th,td{border-bottom:1px solid var(--line);padding:6px 10px;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600;background:#f6faf8}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 12px}
.kpi div{background:#fff;border:1px solid var(--line);border-radius:10px;padding:9px 14px;min-width:120px}
.kpi span{display:block;color:var(--mut);font-size:11.5px}
.kpi b{font-size:18px}
.win{color:#1d7b4a;font-weight:700}.lose{color:#b85348;font-weight:700}.tie{color:var(--mut);font-weight:700}
.note{color:var(--mut);font-size:12px;margin:8px 0 0}
.sep{border:0;border-top:1px dashed var(--line);margin:24px 0}
"""

HOWTO = """<div class="howto"><b>怎么看这一页</b>
<ul>
<li>每一局分几段：<b>现金曲线</b>（谁什么时候被拉开）&rarr; <b>劳动力</b> &rarr; <b>地块账本</b>（在种什么）&rarr; <b>每日现金变化</b>（钱从哪来、花到哪去）&rarr; <b>市场指令</b>（下单构成）&rarr; <b>终局账本</b>。</li>
<li>左边是 seat 0、右边是 seat 1。两个位置在各种子下基本对称，所以颜色对比就是"谁领先"。</li>
<li><b>竖虚线</b>是商店解锁的时刻，<b>最粗的那条标着 step144</b>：那是磁带选定路线的分叉点，之后策略基本固定。</li>
<li><b>注意</b>：劳动力（闲置）曲线在两边常常一模一样。这不是错——两个 agent 回放的是同一条磁带，而这套架构里所有反射层<b>只改市场指令，从不碰农场动作</b>。所以闲置只反映路线/布局，不反映市场策略。</li>
</ul></div>"""


def build_html(games, names):
    p = ["<!doctype html><meta charset='utf-8'><title>对局账本</title>",
         f"<style>{CSS}</style><div class='wrap'><h1>对局账本</h1>",
         f"<p class='lead'>把一局拆开看：现金、劳动力、地块、收支、下单构成、终局账本。"
         f"左 seat 0 / 右 seat 1。</p>", HOWTO]
    for gi, g in enumerate(games):
        steps, seed, final = g["steps"], g["seed"], g["final"]
        margin = final[0] - final[1]
        res = ("win", "我们赢") if margin > 0 else (("lose", "我们输") if margin < 0 else ("tie", "平"))
        if gi:
            p.append("<hr class='sep'>")
        p.append(f"<h2>第 {gi+1} 局 &middot; 种子 {seed} &middot; "
                 f"<span class='{res[0]}'>{res[1]} ${abs(margin):,.0f}</span></h2>")
        p.append("<div class='kpi'>")
        for s in (0, 1):
            rs = [r[s] for r in steps if r.get(s)]
            last = rs[-1]
            idle = sum(r["idle"] for r in rs)
            units = sum(r["units"] for r in rs)
            p.append(f"<div><span>{html.escape(names[s])}（seat {s}）终局资金</span>"
                     f"<b>${last['money']:,.0f}</b></div>")
            p.append(f"<div><span>seat {s} 干活比例</span>"
                     f"<b>{100.0*(units-idle)/max(1,units):.0f}%</b></div>")
            p.append(f"<div><span>seat {s} 已解锁店铺</span>"
                     f"<b>{len(last['shops'])}</b></div>")
        p.append("</div>")

        d, peak = gap_day(steps, 0, 1)
        who = names[0] if margin >= 0 else names[1]
        p.append("<div class='card'><h3>这一局发生了什么</h3>"
                 f"<p class='note' style='font-size:13px'>"
                 f"分水岭在第 <b>{d}</b> 天出现（{html.escape(who)} 先把差距拉到终局差距的 1/4，"
                 f"最大差距 ${peak:,.0f}）。<br>"
                 + summarise(steps, 0, names[0]) + "<br>" + summarise(steps, 1, names[1])
                 + "</p></div>")

        # 1 cash
        ser, marks = [], [(144, "step144 分叉")]
        seen = 0
        for r in steps:
            if r.get(0) and len(r[0]["shops"]) > seen:
                seen = len(r[0]["shops"])
                marks.append((r[0]["step"], SHOP_CN.get(r[0]["shops"][-1], "店")))
        for s in (0, 1):
            ser.append((f"{names[s]}（seat {s}）", SEAT_COLOR[s],
                        [(r[s]["step"], r[s]["money"]) for r in steps if r.get(s)]))
        p.append("<div class='card'><h3>现金曲线</h3>"
                 "<p class='note'>纵轴是手上的钱。差距在这条线上变宽的地方，就是这局被决定的地方。</p>"
                 + line_panel(ser, "双方现金（逐回合）", "步 →（720 步 = 30 天）", "现金",
                              markers=marks) + "</div>")

        # 2 idle
        ser = [(f"seat {s}", SEAT_COLOR[s],
                [(r[s]["step"], r[s]["idle"]) for r in steps if r.get(s)]) for s in (0, 1)]
        p.append("<div class='card'><h3>闲置的劳动力</h3>"
                 "<p class='note'>每回合什么都不做（PASS）的农民+雇工数。"
                 "<b>两边常常完全一样</b>——因为农场动作来自同一条磁带，所有反射层只改市场指令。"
                 "所以这里要看的是<b>绝对水平</b>（有没有人力被白白养着），不是两者的差。</p>"
                 + line_panel(ser, "每回合闲置单位数", "步 →", "数量",
                              money=False, height=200) + "</div>")

        # 3 tile ledger, two seats side by side
        p.append("<div class='row'>")
        for s in (0, 1):
            per_day = collections.defaultdict(collections.Counter)
            n_by_day = collections.Counter()
            for r in steps:
                if not r.get(s):
                    continue
                for k, v in r[s]["tiles"].items():
                    per_day[r[s]["day"]][k] += v
                n_by_day[r[s]["day"]] += 1
            for dd in per_day:
                n = max(1, n_by_day[dd])
                per_day[dd] = collections.Counter({k: round(v / n) for k, v in per_day[dd].items()})
            keys = [k for k in TILE_ORDER if any(per_day[dd].get(k) for dd in per_day)]
            p.append("<div class='card'><h3>地块账本 &middot; "
                     f"{html.escape(names[s])}（seat {s}）</h3>"
                     "<p class='note'>每天平均有多少格在种什么。"
                     "空/杂草的比例高 = 地没被用上。</p>"
                     + stacked_panel(dict(per_day), keys, "每天的地块构成", "纵轴 = 格数",
                                     label_cn=TILE_CN) + "</div>")
        p.append("</div>")

        # 4 daily cash flow, both seats in one chart
        by_seat = {}
        for s in (0, 1):
            eod = {}
            for r in steps:
                if r.get(s):
                    eod[r[s]["day"]] = r[s]["money"]
            ds = sorted(eod)
            by_seat[s] = {ds[i]: eod[ds[i]] - eod[ds[i - 1]] for i in range(1, len(ds))}
        p.append("<div class='card'><h3>每日现金变化</h3>"
                 "<p class='note'>每天结束时手上的钱比前一天多多少。"
                 "高柱子 = 那天出货多；突然转负 = 那天在大额支出（买动物/买地）。</p>"
                 + grouped_panel(by_seat, "每天现金净变化（同一天两根柱对比）",
                                 "纵轴 = 当日 Δ 现金") + "</div>")

        # 5 market orders, two seats side by side
        p.append("<div class='row'>")
        for s in (0, 1):
            per_day = collections.defaultdict(collections.Counter)
            for r in steps:
                if not r.get(s):
                    continue
                for k, v in r[s]["orders"].items():
                    per_day[r[s]["day"]][k] += v
            keys = [k for k in MKT_ORDER if any(per_day[dd].get(k) for dd in per_day)]
            p.append("<div class='card'><h3>市场指令 &middot; "
                     f"{html.escape(names[s])}（seat {s}）</h3>"
                     "<p class='note'>每天下多少条指令、什么类型。"
                     "每回合最多 10 条槽位，所以“卖出”占比高说明槽位都花在出货上。</p>"
                     + stacked_panel(dict(per_day), keys, "每天的指令构成", "纵轴 = 指令条数",
                                     label_cn=MKT_CN) + "</div>")
        p.append("</div>")

        # 6 revenue sources: pie + descending table, per seat
        p.append("<div class='row'>")
        for s in (0, 1):
            rev, inflow, outflow, emitted = revenue_mix(steps, s)
            ratio = (inflow / emitted) if emitted else 0.0
            kpis = (f"毛收入 ${inflow:,.0f}（= 实际现金流入口径）。"
                    f"品种构成取自下单流：下单卖出合计 ${emitted:,.0f}，"
                    f"<b>执行率 {100*ratio:.0f}%</b>（低于 100% 的部分是没能成交的单）。"
                    f"支出合计 ${outflow:,.0f}。")
            p.append("<div class='card'><h3>收益来源 &middot; "
                     f"{html.escape(names[s])}（seat {s}）</h3>"
                     f"<p class='note'>按品种拆分的毛收入，<b>降序</b>排列；饼图是占比。"
                     f"总额锚定到真实现金流入，构成来自下单流（两者已对账）。</p>"
                     + pie_panel(list(rev.items()), "毛收入构成（降序）", kpis)
                     + "<table><tr><th>品种</th><th>毛收入</th><th>占比</th></tr>"
                     + "".join(
                         f"<tr><td>{TILE_CN.get(k, k)}</td><td>${v:,.0f}</td>"
                         f"<td>{100.0*v/max(1,sum(rev.values())):.1f}%</td></tr>"
                         for k, v in sorted(rev.items(), key=lambda kv: -kv[1]))
                     + "</table></div>")
        p.append("</div>")

        # 7 closing book: one table, both seats as columns
        rows = []
        for k in TILE_ORDER:
            a = sum(r[0]["tiles"].get(k, 0) for r in steps if r.get(0)) / max(
                1, len([r for r in steps if r.get(0)]))
            b = sum(r[1]["tiles"].get(k, 0) for r in steps if r.get(1)) / max(
                1, len([r for r in steps if r.get(1)]))
            if a < 0.5 and b < 0.5:
                continue
            rows.append(f"<tr><td>{TILE_CN.get(k, k)}</td><td>{a:.1f}</td><td>{b:.1f}</td></tr>")
        shed = []
        for s in (0, 1):
            peak_shed = collections.Counter()
            for r in steps:
                if not r.get(s):
                    continue
                for k, v in r[s]["shed"].items():
                    peak_shed[k] = max(peak_shed[k], int(v))
            shed.append(peak_shed)
        keys = sorted(set(shed[0]) | set(shed[1]))
        srows = "".join(
            f"<tr><td>{k}</td><td>{shed[0].get(k, 0)}</td><td>{shed[1].get(k, 0)}</td></tr>"
            for k in keys if shed[0].get(k) or shed[1].get(k))
        p.append("<div class='card'><h3>终局账本</h3>"
                 "<p class='note'>地块 = 整局平均（0 表示一直没用）。"
                 "棚内库存 = <b>整局峰值</b>；峰值高而终局余额低说明该卖的卖掉了。</p>"
                 f"<table><tr><th>地块（整局平均格数）</th>"
                 f"<th>{html.escape(names[0])}</th><th>{html.escape(names[1])}</th></tr>"
                 f"{''.join(rows)}</table>"
                 f"<table><tr><th>棚内库存峰值</th><th>seat 0</th><th>seat 1</th></tr>"
                 f"{srows or '<tr><td>-</td><td>0</td><td>0</td></tr>'}</table></div>")
    p.append("</div>")
    return "\n".join(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="main.py")
    ap.add_argument("--b", default=None, help="对手；用 --replay 时不需要")
    ap.add_argument("--seeds", default="4242")
    ap.add_argument("--out", default="results/ledger/ledger.html")
    ap.add_argument("--replay", default=None,
                    help="已抓取的 episode-*-replay.json（跳过模拟）")
    args = ap.parse_args()

    a_path = args.a if os.path.isabs(args.a) else os.path.join(ROOT, args.a)
    b_path = None if not args.b else (
        args.b if os.path.isabs(args.b) else os.path.join(ROOT, args.b))
    def label_for(path):
        """A name a human recognises, not a file stem: `experiments/v41/cxd.py`
        should read as "我们 v41", and opponents keep their folder name."""
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        parts = rel.split("/")
        if parts[0] == "experiments" and len(parts) > 2:
            return f"我们 {parts[1]}"
        if os.path.basename(path) == "main.py":
            folder = os.path.basename(os.path.dirname(path))
            return "我们 (main.py)" if os.path.dirname(path) in ("", ROOT) else folder
        return os.path.splitext(os.path.basename(path))[0]

    names = [label_for(a_path), label_for(b_path or a_path)]
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
        print(f"回放 {os.path.basename(rp)}: episode {info.get('EpisodeId')} "
              f"seed {seed}  {final[0]:,.0f} : {final[1]:,.0f}")
        games.append({"steps": collect(d["steps"]), "seed": seed, "final": final})
    for seed in ([] if args.replay else [int(x) for x in args.seeds.split(",")]):
        env = make("kaggriculture", configuration={"seed": seed}, debug=True)
        env.run([A, B])
        final = [float(env.steps[-1][s].reward) for s in (0, 1)]
        print(f"种子 {seed}: {final[0]:,.0f} : {final[1]:,.0f}")
        games.append({"steps": collect(env.steps), "seed": seed, "final": final})

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(build_html(games, names))
    print(f"已写入 {out}  ({os.path.getsize(out):,} bytes)")


if __name__ == "__main__":
    main()
