"""Per-day deep dive into the "early death" v24 online losses.

Reads replay dirs (v24 first run / v24 rerun / v23_c7), computes a per-day
side-by-side feature table for both players plus per-day action-event counts
(BUILD_PASTURE / BUY_ANIMAL / PLACE / BUY_LAND / HIRE / SELL units ...), and
dumps everything to results/early_death_data.json.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_deepdive.py \
        [--dirs replays_v23:replays_v24:replays_v24r] [--json results/early_death_data.json]
"""
import argparse
import collections
import json
import os
import sys

OUR_NAME = "ReD_MooN_rise"
DAYS = 30
ANIMALS = ("COW", "SHEEP", "GOOSE")

# Focus window for the early-death question.
FOCUS = tuple(range(3, 13))

UNIT_OPS = (
    "BUILD_COOP", "BUILD_PASTURE", "PLACE", "PICKUP", "DROP", "FEED", "CARE",
    "COLLECT_FERTILIZER", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG",
)
MARKET_OPS = ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND")


def tile_map(farm):
    """{(x, y): tag} where tag is ('A', animal) / ('S', coop|pasture) / ('P', crop) / ('W',)."""
    out = {}
    for y, row in enumerate(farm["tiles"]):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind in ("COOP", "PASTURE"):
                animal = t.get("animal")
                out[(x, y)] = ("A", animal) if animal else ("S", kind)
            elif kind == "PLANT":
                out[(x, y)] = ("P", t.get("crop"))
            elif kind == "WEED":
                out[(x, y)] = ("W", None)
    return out


def snap_farm(farm):
    herd = collections.Counter()
    crops = collections.Counter()
    structures = 0
    empty_struct = 0
    weeds = 0
    empty_tiles = 0
    locked = 0
    fed_today = 0
    unfed_today = 0
    unfed_streak1 = 0      # consecutive_unfed >= 1  (one more miss -> escape)
    fed_streak1 = 0        # consecutive_unfed == 0 (safe)
    cared_today = 0
    unwatered_today = 0
    unwater_streak1 = 0
    for row in farm["tiles"]:
        for t in row:
            if t is None:
                empty_tiles += 1
                continue
            if not isinstance(t, dict):
                locked += 1
                continue
            kind = t.get("kind")
            if kind in ("COOP", "PASTURE"):
                structures += 1
                animal = t.get("animal")
                if animal:
                    herd[animal] += 1
                    if t.get("fed_today"):
                        fed_today += 1
                    else:
                        unfed_today += 1
                    if t.get("consecutive_unfed", 0) >= 1:
                        unfed_streak1 += 1
                    else:
                        fed_streak1 += 1
                    if t.get("cared_today"):
                        cared_today += 1
                else:
                    empty_struct += 1
            elif kind == "WEED":
                weeds += 1
            elif kind == "PLANT":
                crops[t.get("crop")] += 1
                if not t.get("watered_today"):
                    unwatered_today += 1
                if t.get("consecutive_unwatered", 0) >= 1:
                    unwater_streak1 += 1
    quads = list(farm.get("unlocked_quadrants") or ["NW"])
    return {
        "money": float(farm["money"]),
        "hands": len(farm.get("hands") or []),
        "hires_today": int(farm.get("hires_today", 0)),
        "quads": quads,
        "n_quads": len(quads),
        "herd": dict(herd),
        "herd_total": sum(herd.values()),
        "coop": sum(1 for row in farm["tiles"] for t in row
                    if isinstance(t, dict) and t.get("kind") == "COOP"),
        "pasture": sum(1 for row in farm["tiles"] for t in row
                       if isinstance(t, dict) and t.get("kind") == "PASTURE"),
        "struct_total": structures,
        "struct_empty": empty_struct,
        "empty_pasture": sum(1 for row in farm["tiles"] for t in row
                             if isinstance(t, dict) and t.get("kind") == "PASTURE"
                             and not t.get("animal")),
        "empty_coop": sum(1 for row in farm["tiles"] for t in row
                          if isinstance(t, dict) and t.get("kind") == "COOP"
                          and not t.get("animal")),
        "crops": dict(crops),
        "crops_total": sum(crops.values()),
        "weeds": weeds,
        "empty_tiles": empty_tiles,
        "locked": locked,
        "fed_today": fed_today,
        "unfed_today": unfed_today,
        "unfed_streak1": unfed_streak1,
        "fed_streak1": fed_streak1,
        "cared_today": cared_today,
        "unwatered_today": unwatered_today,
        "unwater_streak1": unwater_streak1,
    }


def action_events(step_entry):
    """Count unit ops and market orders for one player at one step."""
    ev = {
        "unit_ops": collections.Counter(),
        "buys": collections.Counter(),
        "sells": collections.Counter(),
        "hire_orders": 0,
        "buy_land_orders": 0,
        "n_market_orders": 0,
        "place_by_animal": collections.Counter(),
        "build_by_kind": collections.Counter(),
    }
    if not isinstance(step_entry, dict):
        return ev
    act = step_entry.get("action")
    if not isinstance(act, dict):
        return ev
    ops = []
    farmer = act.get("farmer")
    if isinstance(farmer, list) and farmer:
        ops.append(farmer)
    for h in act.get("hands") or []:
        if isinstance(h, list) and h:
            ops.append(h)
    for op in ops:
        name = op[0] if op else None
        if not isinstance(name, str):
            continue
        ev["unit_ops"][name] += 1
        if name == "PLACE" and len(op) >= 2:
            ev["place_by_animal"][op[1]] += 1
        if name in ("BUILD_COOP", "BUILD_PASTURE"):
            ev["build_by_kind"][name] += 1
    orders = act.get("market") or []
    ev["n_market_orders"] = len(orders)
    for o in orders:
        if not isinstance(o, list) or not o or not isinstance(o[0], str):
            continue
        name = o[0]
        if name not in MARKET_OPS:
            continue
        if name == "HIRE":
            ev["hire_orders"] += 1
        elif name == "BUY_LAND":
            ev["buy_land_orders"] += 1
        elif name in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"):
            if len(o) >= 3:
                try:
                    n = int(o[2])
                except (TypeError, ValueError):
                    continue
                if n > 0:
                    ev["buys"][f"{name}:{o[1]}"] += n
        elif name == "SELL":
            if len(o) >= 3:
                try:
                    n = int(o[2])
                except (TypeError, ValueError):
                    continue
                if n > 0:
                    ev["sells"][o[1]] += n
    return ev


def load_episode(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    names = list(d["info"]["TeamNames"])
    if OUR_NAME not in names:
        return None
    us = names.index(OUR_NAME)
    opp = 1 - us
    if names[0] == names[1]:
        return None                                  # self-play
    steps = d["steps"]
    rec = {
        "path": path,
        "ep": int(d["info"]["EpisodeId"]),
        "us_seat": us,
        "opp_seat": opp,
        "opp": names[opp],
        "self_play": names[0] == names[1],
        "reward_us": float(d["rewards"][us]),
        "reward_opp": float(d["rewards"][opp]),
        "margin": float(d["rewards"][us]) - float(d["rewards"][opp]),
        "win": float(d["rewards"][us]) > float(d["rewards"][opp]),
        "snap_h23": {},
        "snap_h0": {},
        "events": {},
        "tmap_h23": {},
        "tmap_h0": {},
        "prices_h23": {},
        "market_inv_h23": {},
    }
    for step, entry in enumerate(steps):
        day, hour = divmod(step, 24)
        if day >= DAYS:
            break
        obs = entry[us].get("observation")
        if not obs:
            continue
        if hour in (0, 23):
            for tag, seat in (("us", us), ("them", opp)):
                snap = snap_farm(obs["farms"][seat])
                key = "%s:%d" % (tag, day)
                if hour == 23:
                    rec["snap_h23"][key] = snap
                    rec["tmap_h23"][key] = tile_map(obs["farms"][seat])
                else:
                    rec["snap_h0"][key] = snap
                    rec["tmap_h0"][key] = tile_map(obs["farms"][seat])
            if hour == 23:
                market = obs.get("market") or {}
                rec["prices_h23"][str(day)] = dict(market.get("prices") or {})
                rec["market_inv_h23"][str(day)] = dict(market.get("inventory") or {})
        if hour == 0:
            town = (obs.get("town") or {}).get("unlocked_shops")
            if day == 0:
                rec["shops_d0"] = list(town or [])
            rec.setdefault("shops_by_day", {})[str(day)] = list(town or [])
        for tag, seat in (("us", us), ("them", opp)):
            ev = action_events(entry[seat])
            akey = "%s:%d:%d" % (tag, day, hour)
            rec["events"][akey] = {
                "unit_ops": dict(ev["unit_ops"]),
                "buys": dict(ev["buys"]),
                "sells": dict(ev["sells"]),
                "hire_orders": ev["hire_orders"],
                "buy_land_orders": ev["buy_land_orders"],
                "n_market_orders": ev["n_market_orders"],
                "place_by_animal": dict(ev["place_by_animal"]),
                "build_by_kind": dict(ev["build_by_kind"]),
            }
    rec["events"] = collapse_days(rec["events"])
    rec["tile_events"] = tile_events(rec)
    for key in ("tmap_h23", "tmap_h0"):
        del rec[key]
    return rec


def tile_events(rec):
    """Daily counts of animal disappearances (escapes) and plant->weed deaths.

    Compares the h23 tile map of day d-1 with the h0 tile map of day d: the only
    way an animal leaves a tile is the end-of-day escape check (DIG refuses to
    remove an occupied structure), and the only way a plant leaves without
    becoming empty is the drought check.  Positions that vanish entirely mean
    the tile was dug or harvested, so they are not counted.
    """
    out = {}
    for tag in ("us", "them"):
        rows = {}
        for day in range(1, DAYS):
            prev = rec["tmap_h23"].get("%s:%d" % (tag, day - 1))
            cur = rec["tmap_h0"].get("%s:%d" % (tag, day))
            if prev is None or cur is None:
                continue
            esc = 0
            drought = 0
            for pos, p in prev.items():
                q = cur.get(pos)
                if p[0] == "A":
                    if q is None:
                        continue                    # tile no longer a structure
                    if q[0] != "A":
                        esc += 1
                elif p[0] == "P":
                    if q is None:
                        continue                    # harvested -> tile emptied
                    if q[0] == "W":
                        drought += 1
            rows[str(day)] = {"escape": esc, "drought_death": drought}
        out[tag] = rows
    return out


def collapse_days(events):
    """Group step-level events into per (tag, day) totals."""
    out = collections.defaultdict(lambda: {
        "unit_ops": collections.Counter(),
        "buys": collections.Counter(),
        "sells": collections.Counter(),
        "hire_orders": 0,
        "buy_land_orders": 0,
        "place_by_animal": collections.Counter(),
        "build_by_kind": collections.Counter(),
        "hours": 0,
    })
    for akey, ev in events.items():
        tag, day, _hour = akey.split(":")
        slot = out["%s:%s" % (tag, day)]
        slot["hours"] += 1
        slot["hire_orders"] += ev["hire_orders"]
        slot["buy_land_orders"] += ev["buy_land_orders"]
        for k, v in ev["unit_ops"].items():
            slot["unit_ops"][k] += v
        for k, v in ev["buys"].items():
            slot["buys"][k] += v
        for k, v in ev["sells"].items():
            slot["sells"][k] += v
        for k, v in ev["place_by_animal"].items():
            slot["place_by_animal"][k] += v
        for k, v in ev["build_by_kind"].items():
            slot["build_by_kind"][k] += v
    return {k: {kk: (dict(vv) if isinstance(vv, collections.Counter) else vv)
                for kk, vv in v.items()} for k, v in out.items()}


def discover(dirs):
    found = []
    for d in dirs:
        if not os.path.isdir(d):
            print("!! missing dir %s" % d, file=sys.stderr)
            continue
        for name in sorted(os.listdir(d)):
            if name.startswith("episode-") and name.endswith("-replay.json"):
                found.append((d, os.path.join(d, name)))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", default="replays_v23:replays_v24:replays_v24r")
    ap.add_argument("--json", default="results/early_death_data.json")
    ap.add_argument("--limit-wins", type=int, default=12,
                    help="cap how many wins per dir are parsed (0 = all)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    dirs = [d for d in args.dirs.split(":") if d]
    recs = []
    per_dir_wins = collections.Counter()
    for d, path in discover(dirs):
        try:
            rec = load_episode(path)
        except Exception as exc:                       # noqa: BLE001
            print("!! %s: %s" % (path, exc), file=sys.stderr)
            continue
        if rec is None:
            continue
        if args.limit_wins and rec["win"]:
            if per_dir_wins[d] >= args.limit_wins:
                continue
            per_dir_wins[d] += 1
        rec["dir"] = d
        recs.append(rec)
        print("parsed %-55s %s margin=%+.0f" % (
            os.path.basename(path), "WIN " if rec["win"] else "LOSS", rec["margin"]),
            file=sys.stderr)

    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(recs, fh)
    print("wrote %s (%d episodes)" % (args.json, len(recs)))


if __name__ == "__main__":
    main()
