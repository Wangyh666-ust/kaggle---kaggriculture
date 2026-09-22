"""Record our OWN rival-sale stream library for the v9/2 PREDICT tape hook.

The blob embedded in main.py (`_V92_P_BLOB` / `_V92_P_INDEX`, ~3417) is a
recording of rival premium sales grouped by "the first two shops the town
unlocked" (64 ordered shop pairs).  This script records a replacement from our
own online replays (replays_v21 / replays_v23 / replays_v24).

Format (what `_v92_p_pair` decodes, byte for byte):

    blob   = base64.b85encode(zlib.compress(raw))
    raw    = 64 segments, concatenated in pair order
             pair index k = PAIR_NAMES.index(shop_a) * 8 + PAIR_NAMES.index(shop_b)
    segment= uint16 n_streams, then n_streams streams back to back
    stream = uint16 n_events, then n_events events back to back
    event  = delta_byte            (t = last_tick + delta, 0 <= delta <= 254)
             | 255, uint16 tick    (escape, absolute tick)
             then item_byte, units_byte
    tick   = the turn the rival's SELL order was executed
    item   = index into _V92_P_ITEMS = (MILK, WOOL, STRAWBERRY, EGG, MELON)

Everything is little-endian.  Ticks in a stream must be non-decreasing (the
decoder carries `last` forward); we sort by tick before encoding.

Rival sales are recovered exactly like the live agent does at run time:

    rival_sold[item] = inventory[t+1] - inventory[t] + town_draw(shops, t)
                       - own_sold[item]

where town_draw is the shop / town-centre consumption applied after step t, and
own_sold is OUR committed sales that step (clamped by our own shed, recovered
from the unit PICKUP / PLACE / DROP ops of the same turn).  Sales are recorded
only when the item's price at step t is > 3 and the recovered quantity is >= 2,
i.e. exactly the events the live `_v92_p_update` would have stored.

Recording starts at the turn the SECOND shop unlocks, because that is the first
turn `_v92_p_pair(shops)` has a 2-element key at run time.

Usage:
  .venv/Scripts/python scripts/record_v92_library.py
  .venv/Scripts/python scripts/record_v92_library.py --emit-main versions/main_v25_ownlib.py
"""
import argparse
import base64
import collections
import glob
import importlib.util
import json
import os
import re
import sys
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PAIR_NAMES = ['BAKERY', 'BRUNCH_SPOT', 'FARMERS_MARKET', 'ICE_CREAM_SHOP',
              'PET_CAFE', 'PIZZA_SHOP', 'SMOOTHIE_SHOP', 'YARN_STORE']
ITEMS = ("MILK", "WOOL", "STRAWBERRY", "EGG", "MELON")
OUR_NAME = "ReD_MooN_rise"
DEFAULT_DIRS = ["replays_v21", "replays_v23", "replays_v24"]


def _load_env_module():
    """The simulator module — single source of truth for the shop tables."""
    path = os.path.join(ROOT, "env", "kaggriculture.py")
    spec = importlib.util.spec_from_file_location("_kagg_env", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ENV = _load_env_module()
SHOPS = _ENV.SHOPS
TOWN_CENTER_PRODUCTS = _ENV.TOWN_CENTER_PRODUCTS


# ---------------------------------------------------------------------------
# rival-sale reconstruction (mirrors _v92_p_update / _v9_town_draw)
# ---------------------------------------------------------------------------
def town_draw(shops, step):
    """Units consumed by the town after `step`'s market round."""
    draw = {}
    if step % 4 == 0:
        for shop in shops:
            products = SHOPS.get(shop, ())
            mult = 2 if len(products) == 1 else 1
            for item in products:
                draw[item] = draw.get(item, 0) + mult
    if step % 24 == 0:
        for item in TOWN_CENTER_PRODUCTS:
            draw[item] = draw.get(item, 0) + 1
    return draw


def shed_at_market(private, action):
    """Shed contents once this turn's unit actions have run, market not yet."""
    shed = dict(private.get("shed") or {})
    carries = [dict(x) for x in (private.get("inventories") or [])]
    ops = [action.get("farmer") or []] + list(action.get("hands") or [])
    for idx, op in enumerate(ops):
        if not isinstance(op, list) or not op:
            continue
        kind = op[0]
        if kind == "PICKUP" and len(op) >= 2:
            n = int(op[2]) if len(op) >= 3 else 1
            shed[op[1]] = max(0, shed.get(op[1], 0) - n)
        elif kind == "PLACE" and len(op) >= 2 and op[1] not in ("COW", "SHEEP", "GOOSE"):
            n = int(op[2]) if len(op) >= 3 else 1
            shed[op[1]] = shed.get(op[1], 0) + n
        elif kind == "DROP" and idx < len(carries):
            for item, n in carries[idx].items():
                shed[item] = shed.get(item, 0) + n
    return shed


def own_sales(private, action):
    """Units WE actually sold this turn (shed-limited), for the tracked items."""
    shed = shed_at_market(private, action)
    out = {}
    for order in action.get("market") or []:
        if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
            continue
        item = order[1]
        if item not in ITEMS:
            continue
        n = min(int(order[2]), shed.get(item, 0))
        if n > 0:
            shed[item] -= n
            out[item] = out.get(item, 0) + n
    return out


def rival_orders(action):
    """The rival's raw SELL order quantities this turn (diagnostic only)."""
    out = {}
    for order in action.get("market") or []:
        if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
            continue
        if order[1] in ITEMS:
            out[order[1]] = out.get(order[1], 0) + int(order[2])
    return out


def episode_pair(steps):
    """The ordered (first, second) shop pair, or None while only <2 shops."""
    for step in steps:
        shops = step[0]["observation"]["town"]["unlocked_shops"]
        if len(shops) >= 2:
            return tuple(shops[:2])
    return None


def record_episode(path, our_name=OUR_NAME, min_units=2, min_price=3):
    """Return (episode_id, opponent, pair, events, stats) for one replay."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    names = data["info"]["TeamNames"]
    steps = data["steps"]
    if our_name in names:
        us = names.index(our_name)
    else:
        us = 0
    them = 1 - us
    opponent = names[them] if them < len(names) else "?"

    pair = episode_pair(steps)
    events = []
    stats = dict(turns=0, skipped_pre_pair=0, est_only=0, truth_only=0, agree=0)
    if pair is None:
        return data.get("id"), opponent, None, events, stats

    # Replay alignment: `steps[t]` holds the observation of turn t together with
    # the action taken on turn t-1 (the framework stores the action after the
    # interpreter ran).  So the DECISION made while looking at turn t is
    # steps[t+1][p]["action"], and its effect is inventory[t] -> inventory[t+1].
    # The live agent indexes its history the same way (`_v92_p_update` compares
    # the observation of step t with the one saved at t-1).
    for t in range(len(steps) - 1):
        obs = steps[t][0]["observation"]
        shops = obs["town"]["unlocked_shops"]
        if len(shops) < 2 or tuple(shops[:2]) != pair:
            stats["skipped_pre_pair"] += 1
            continue
        stats["turns"] += 1
        prices = obs["market"]["prices"]
        inv = obs["market"]["inventory"]
        inv_next = steps[t + 1][0]["observation"]["market"]["inventory"]
        draw = town_draw(shops, t)
        own = own_sales(steps[t][us]["observation"].get("private") or {},
                        steps[t + 1][us].get("action") or {})
        truth = rival_orders(steps[t + 1][them].get("action") or {})
        for i, item in enumerate(ITEMS):
            if prices.get(item, 0) <= min_price:
                continue
            sold = inv_next[item] - inv[item] + draw.get(item, 0) - own.get(item, 0)
            est_hit = sold >= min_units
            true_hit = truth.get(item, 0) >= min_units
            if est_hit and true_hit:
                stats["agree"] += 1
            elif est_hit:
                stats["est_only"] += 1
            elif true_hit:
                stats["truth_only"] += 1
            if est_hit:
                events.append((t, i, int(min(sold, 255))))
    return data.get("id"), opponent, pair, events, stats


# ---------------------------------------------------------------------------
# encoding
# ---------------------------------------------------------------------------
def _u16(n):
    return bytes((n & 0xFF, (n >> 8) & 0xFF))


def encode_events(events):
    """[(tick, item, units)] -> delta-encoded bytes (ticks non-decreasing)."""
    out = bytearray()
    last = 0
    for tick, item, units in sorted(events):
        delta = tick - last
        if delta < 255:
            out.append(delta)
        else:
            out.append(255)
            out += _u16(tick)
        out.append(item & 0xFF)
        out.append(max(0, min(255, units)) & 0xFF)
        last = tick
    return bytes(out)


def as_events(stream):
    """Accept either [(tick, item, units)] or {(tick, item): units}."""
    if isinstance(stream, dict):
        return [(t, i, q) for (t, i), q in stream.items()]
    return list(stream)


def build_library(pair_streams):
    """pair_streams: {pair: [stream, ...]} -> (blob, index, raw)."""
    raw = bytearray()
    index = []
    for a in PAIR_NAMES:
        for b in PAIR_NAMES:
            streams = [as_events(s) for s in pair_streams.get((a, b), []) if s]
            start = len(raw)
            raw += _u16(len(streams))
            for events in sorted(streams, key=lambda e: (e[0][0], len(e))):
                raw += _u16(len(events))
                raw += encode_events(events)
            index.append((start, len(raw) - start))
    blob = base64.b85encode(zlib.compress(bytes(raw), 9)).decode("ascii")
    return blob, index, bytes(raw)


def decode_pair(raw, index, a, b):
    """Independent decoder used by the self-test (mirrors _v92_p_pair)."""
    start, length = index[PAIR_NAMES.index(a) * 8 + PAIR_NAMES.index(b)]
    pos = start
    end = start + length
    n = raw[pos] | raw[pos + 1] << 8
    pos += 2
    streams = []
    for _ in range(n):
        m = raw[pos] | raw[pos + 1] << 8
        pos += 2
        ev = {}
        last = 0
        for _ in range(m):
            d = raw[pos]
            pos += 1
            if d == 255:
                t = raw[pos] | raw[pos + 1] << 8
                pos += 2
            else:
                t = last + d
            ev[(t, raw[pos])] = raw[pos + 1]
            pos += 2
            last = t
        streams.append((-1, ev))
    assert pos == end, (a, b, pos, end)
    return streams


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dirs", nargs="*", default=DEFAULT_DIRS,
                    help="replay directories to record from (default: our 3 online sets)")
    ap.add_argument("--extra-dirs", nargs="*", default=[],
                    help="additional replay directories (older archives)")
    ap.add_argument("--our-name", default=OUR_NAME)
    ap.add_argument("--min-units", type=int, default=2)
    ap.add_argument("--min-price", type=int, default=3)
    ap.add_argument("--out", default="results/v92_ownlib.json")
    ap.add_argument("--emit-blob", default="results/v92_ownlib_blob.py")
    ap.add_argument("--emit-main", default=None,
                    help="write main.py with the new blob into this path")
    ap.add_argument("--no-dedup", action="store_true",
                    help="do not drop duplicate episode ids across directories")
    ap.add_argument("--merge-with", default=None,
                    help="python file whose library is kept and extended with ours "
                         "(e.g. main.py) — tests 'same-meta streams ON TOP of the big one'")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    dirs = list(args.dirs) + list(args.extra_dirs)
    files = []
    for d in dirs:
        files += sorted(glob.glob(os.path.join(ROOT, d, "*.json")))

    pair_streams = collections.defaultdict(list)
    per_pair = collections.Counter()
    ep_rows = []
    seen_ids = set()
    stats = collections.Counter()
    dup = 0
    for path in files:
        try:
            ep_id, opponent, pair, events, est = record_episode(
                path, args.our_name, args.min_units, args.min_price)
        except Exception as exc:  # a malformed replay must not kill the run
            print(f"  !! {os.path.relpath(path, ROOT)}: {exc!r}")
            continue
        if not args.no_dedup and ep_id in seen_ids:
            dup += 1
            continue
        seen_ids.add(ep_id)
        stats.update(est)
        if pair is None:
            stats["no_pair"] += 1
            continue
        pair_streams[pair].append(events)
        per_pair[pair] += 1
        ep_rows.append(dict(ep=ep_id, opponent=opponent, pair=list(pair),
                            events=len(events), turns=est["turns"]))

    merged_from = None
    if args.merge_with:
        base_path = os.path.join(ROOT, args.merge_with)
        base_lib = decode_library_file(base_path)
        merged = {}
        for key in [(a, b) for a in PAIR_NAMES for b in PAIR_NAMES]:
            merged[key] = list(base_lib.get(key, [])) + \
                [{(t, i): q for (t, i, q) in ev} for ev in pair_streams.get(key, []) if ev]
        merged_from = rel_to_root(base_path)
        pair_streams = merged

    blob, index, raw = build_library(pair_streams)
    n_streams = sum(_u16_count(raw, index[k]) for k in range(64))
    n_events = sum(len(e) for v in pair_streams.values() for e in v)

    old = old_library_stats()
    report = dict(
        episodes_recorded=len(ep_rows), duplicates_skipped=dup,
        turns_recorded=stats["turns"], streams=n_streams, events=n_events,
        merged_from=merged_from,
        reconstruction=dict(agree=stats["agree"], est_only=stats["est_only"],
                            truth_only=stats["truth_only"]),
        blob_chars=len(blob), raw_bytes=len(raw),
        zlib_bytes=len(zlib.compress(raw, 9)),
        blob_path=rel_to_root(os.path.join(ROOT, args.emit_blob)) if args.emit_blob else None,
        pairs=dict(covered=sum(1 for v in pair_streams.values() if any(v)),
                   missing=[f"{a}|{b}" for a in PAIR_NAMES for b in PAIR_NAMES
                            if not any(pair_streams.get((a, b), []))]),
        per_pair={f"{a}|{b}": dict(streams=len([e for e in pair_streams.get((a, b), []) if e]),
                                   events=sum(len(e) for e in pair_streams.get((a, b), [])),
                                   old_streams=old["per_pair"].get(f"{a}|{b}", (0, 0))[0],
                                   old_events=old["per_pair"].get(f"{a}|{b}", (0, 0))[1])
                  for a in PAIR_NAMES for b in PAIR_NAMES},
        old=old["totals"],
        episodes=ep_rows,
    )

    os.makedirs(os.path.dirname(os.path.join(ROOT, args.out)), exist_ok=True)
    with open(os.path.join(ROOT, args.out), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print(f"episodes: {len(ep_rows)}  streams: {n_streams}  events: {n_events}  "
          f"(old: {old['totals']['streams']} streams / {old['totals']['events']} events)")
    print(f"reconstruction vs rival SELL orders: agree {stats['agree']} "
          f"est_only {stats['est_only']} truth_only {stats['truth_only']}")
    print(f"pair coverage: {report['pairs']['covered']}/64"
          + (f"  missing: {report['pairs']['missing']}" if report["pairs"]["missing"] else ""))

    if args.emit_blob:
        write_blob_module(os.path.join(ROOT, args.emit_blob), blob, index)
        print("wrote", args.emit_blob)
    if args.emit_main:
        write_main(os.path.join(ROOT, args.emit_main), blob, index)
        print("wrote", args.emit_main)
    print("saved ->", args.out)
    return report


def _u16_count(raw, entry):
    start, _ = entry
    return raw[start] | raw[start + 1] << 8


def rel_to_root(path):
    """Relative to the repo when possible — os.path.relpath breaks across drives."""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def read_constants(path):
    """Pull `_V92_P_BLOB` / `_V92_P_INDEX` out of a single-file agent."""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    blob = re.search(r"^_V92_P_BLOB = '(.*)'$", src, re.M).group(1)
    index = eval(re.search(r"^_V92_P_INDEX = (\[.*?\])$", src, re.M).group(1))
    return blob, index


def decode_library_file(path):
    """{(shop_a, shop_b): [{(tick, item): units}, ...]} for an existing agent."""
    blob, index = read_constants(path)
    raw = zlib.decompress(base64.b85decode(blob))
    return {key: [ev for _ep, ev in decode_pair(raw, index, *key)]
            for key in [(a, b) for a in PAIR_NAMES for b in PAIR_NAMES]}


def old_library_stats():
    """Decode the blob currently embedded in main.py, for the size comparison."""
    blob, index = read_constants(os.path.join(ROOT, "main.py"))
    raw = zlib.decompress(base64.b85decode(blob))
    per_pair = {}
    total_s = total_e = 0
    for k, (start, _length) in enumerate(index):
        n = raw[start] | raw[start + 1] << 8
        pos = start + 2
        ev = 0
        for _ in range(n):
            m = raw[pos] | raw[pos + 1] << 8
            pos += 2
            for _ in range(m):
                pos += 1 if raw[pos - 1] != 255 else 3
                pos += 2
            ev += m
        key = f"{PAIR_NAMES[k // 8]}|{PAIR_NAMES[k % 8]}"
        per_pair[key] = (n, ev)
        total_s += n
        total_e += ev
    return dict(per_pair=per_pair,
                totals=dict(streams=total_s, events=total_e,
                            raw_bytes=len(raw), blob_chars=len(blob)))


def write_blob_module(path, blob, index):
    literal = "[" + ", ".join(f"({a}, {b})" for a, b in index) + "]"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('"""Generated by scripts/record_v92_library.py — do not edit."""\n')
        fh.write(f"_V92_P_BLOB = {blob!r}\n\n")
        fh.write(f"_V92_P_INDEX = {literal}\n")


def write_main(path, blob, index):
    """Copy main.py, swapping only the two library constants."""
    with open(os.path.join(ROOT, "main.py"), encoding="utf-8", newline="") as fh:
        src = fh.read()
    crlf = "\r\n" in src
    literal = "[" + ", ".join(f"({a}, {b})" for a, b in index) + "]"
    new, n1 = re.subn(r"^(_V92_P_BLOB = )[^\r\n]*", lambda m: m.group(1) + repr(blob),
                      src, count=1, flags=re.M)
    new, n2 = re.subn(r"^(_V92_P_INDEX = )[^\r\n]*", lambda m: m.group(1) + literal,
                      new, count=1, flags=re.M)
    assert n1 == 1 and n2 == 1, (n1, n2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    with open(path, "rb") as fh:
        assert (b"\r\n" in fh.read()) == crlf, "line endings changed"
    changed = sum(1 for a, b in zip(src.splitlines(), new.splitlines()) if a != b)
    assert changed == 2, f"expected exactly 2 changed lines, got {changed}"


if __name__ == "__main__":
    main(sys.argv[1:])
