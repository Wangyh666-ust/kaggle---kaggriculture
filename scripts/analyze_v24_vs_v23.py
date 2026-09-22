"""Compare v23_c7 vs v24 online loss data.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/analyze_v24_vs_v23.py [--json out.json]

Reads replays_v23 / replays_v24 / replays_v24r, excludes self-play (both seats
named ReD_MooN_rise), and emits the numbers for results/analysis_v24_vs_v23_losses.md.
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

OUR_NAME = "ReD_MooN_rise"
SETS = {
    "v23_c7": "replays_v23",
    "v24_first": "replays_v24",
    "v24_rerun": "replays_v24r",
}
TPD = 24
DAYS = 30

SHOPS = {
    "BAKERY": ["EGG", "WHEAT"],
    "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
TOWN_CENTER = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"]
PRODUCTS = TOWN_CENTER + ["FERTILIZER"]
ANIMALS = ("COW", "SHEEP", "GOOSE")


def _snap_farm(farm):
    herd = collections.Counter()
    crops = collections.Counter()
    structures = 0
    for row in farm["tiles"]:
        for t in row:
            if not isinstance(t, dict):
                continue
            if "animal" in t and t.get("animal"):
                herd[t["animal"]] += 1
                structures += 1
            elif t.get("kind") in ("COOP", "PASTURE"):
                structures += 1
            elif t.get("kind") == "PLANT":
                crops[t["crop"]] += 1
    return {
        "money": farm["money"],
        "hands": len(farm["hands"]),
        "hires_today": farm.get("hires_today", 0),
        "herd": dict(herd),
        "herd_total": sum(herd.values()),
        "crops": dict(crops),
        "crops_total": sum(crops.values()),
        "structures": structures,
    }


def _town_draw(town, step):
    """Per-step market inventory drain caused by the town (env `_town_consume`)."""
    out = collections.Counter()
    if step % 4 == 0:
        for name in town.get("unlocked_shops", []):
            products = SHOPS.get(name)
            if not products:
                continue
            mult = 2 if len(products) == 1 else 1
            for item in products:
                out[item] += mult
    if step % 24 == 0:
        for item in TOWN_CENTER:
            out[item] += 1
    return out


def _own_sells(step_entry, seat):
    """Units this player *asked* to sell, per item, this turn."""
    out = collections.Counter()
    act = step_entry[seat].get("action") if isinstance(step_entry[seat], dict) else None
    if not isinstance(act, dict):
        return out, []
    orders = act.get("market") or []
    for o in orders:
        if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL":
            try:
                n = int(o[2])
            except (TypeError, ValueError):
                continue
            if n > 0:
                out[o[1]] += n
    return out, orders


def load_episode(path):
    d = json.load(open(path, encoding="utf-8"))
    names = list(d["info"]["TeamNames"])
    if names[0] == OUR_NAME and names[1] == OUR_NAME:
        return None
    if OUR_NAME not in names:
        return None
    us = names.index(OUR_NAME)
    opp = 1 - us
    steps = d["steps"]
    rec = {
        "path": path,
        "ep": int(d["info"]["EpisodeId"]),
        "us_seat": us,
        "opp": names[opp],
        "opp_seat": opp,
        "reward_us": float(d["rewards"][us]),
        "reward_opp": float(d["rewards"][opp]),
    }
    rec["margin"] = rec["reward_us"] - rec["reward_opp"]
    rec["win"] = rec["margin"] > 0

    # --- per-day money difference (snapshot at hour 23 of each day) ---
    diffs = {}
    our_money = {}
    opp_money = {}
    for day in range(DAYS):
        i = day * TPD + 23
        if i >= len(steps):
            continue
        f = steps[i][0]["observation"]["farms"]
        our_money[day] = f[us]["money"]
        opp_money[day] = f[opp]["money"]
        diffs[day] = f[us]["money"] - f[opp]["money"]
    rec["diff_h23"] = diffs
    rec["our_money_h23"] = our_money
    rec["opp_money_h23"] = opp_money

    # same trajectory sampled at hour 0 (start of day, after the night drop)
    diffs0 = {}
    for day in range(DAYS):
        i = day * TPD
        if i >= len(steps):
            continue
        f = steps[i][0]["observation"]["farms"]
        diffs0[day] = f[us]["money"] - f[opp]["money"]
    rec["diff_h0"] = diffs0

    neg = [d for d in sorted(diffs) if diffs[d] < 0]
    rec["first_neg_day"] = neg[0] if neg else None
    if diffs:
        mn = min(diffs.values())
        rec["min_day"] = min([d for d in diffs if diffs[d] == mn])
        rec["min_diff"] = mn
        mx = max(diffs.values())
        rec["peak_day"] = min([d for d in diffs if diffs[d] == mx])
        rec["peak_diff"] = mx
        # last day on which we still held a lead in the hour-23 snapshot
        pos = [d for d in diffs if diffs[d] > 0]
        rec["last_pos_day"] = max(pos) if pos else None
        # earliest day from which the lead is gone for good
        cross = None
        for d in sorted(diffs):
            if all(diffs[x] < 0 for x in diffs if x >= d):
                cross = d
                break
        rec["permanent_neg_day"] = cross
        # crossover with a 3-day grace: first day after which the 3-day mean never
        # returns positive
        mean3 = {}
        for d in range(2, DAYS):
            w = [diffs[x] for x in (d - 2, d - 1, d) if x in diffs]
            mean3[d] = sum(w) / len(w) if w else None
        sm = None
        for d in sorted(mean3):
            if all(mean3[x] < 0 for x in mean3 if x >= d):
                sm = d
                break
        rec["smooth_neg_day"] = sm
    else:
        rec["min_day"] = rec["peak_day"] = rec["last_pos_day"] = None
        rec["min_diff"] = rec["peak_diff"] = None
        rec["permanent_neg_day"] = rec["smooth_neg_day"] = None

    # --- d12 snapshot for both seats ---
    i12 = 12 * TPD + 23
    if i12 < len(steps):
        f = steps[i12][0]["observation"]["farms"]
        rec["d12_us"] = _snap_farm(f[us])
        rec["d12_opp"] = _snap_farm(f[opp])
    # --- final snapshot ---
    last = steps[-1][0]["observation"]["farms"]
    rec["final_us"] = _snap_farm(last[us])
    rec["final_opp"] = _snap_farm(last[opp])

    # --- our sell behaviour by hour, and shed pressure ---
    sells_by_hour = collections.defaultdict(collections.Counter)   # hour -> item -> units
    revenue_by_hour = collections.Counter()
    night_sell_units = collections.Counter()   # item -> units sold in h21-23
    night_sell_value = 0.0
    next_morning_value = 0.0
    next_morning_units = 0
    shed_by_day_hour = collections.defaultdict(dict)
    carried_by_day_hour = collections.defaultdict(dict)
    overflow_est = {}
    sell_units_total = 0
    for i, entry in enumerate(steps):
        day, hour = divmod(i, TPD)
        obs = entry[0]["observation"]
        priv = entry[us]["observation"].get("private") or {}
        shed = priv.get("shed") or {}
        carried = sum(sum(max(0, int(v)) for v in inv.values())
                      for inv in (priv.get("inventories") or []))
        if hour in (20, 21, 22, 23):
            shed_by_day_hour[day][hour] = sum(max(0, int(v)) for v in shed.values())
            carried_by_day_hour[day][hour] = carried
        sells, _ = _own_sells(entry, us)
        if sells:
            prices = obs["market"]["prices"]
            for item, n in sells.items():
                sells_by_hour[hour][item] += n
                sell_units_total += n
                p = int(prices.get(item, 1))
                revenue_by_hour[hour] += p * n
                if hour in (21, 22, 23):
                    night_sell_units[item] += n
                    night_sell_value += p * n
                    # what the same units would fetch next morning (h0/h1)
                    j = min(len(steps) - 1, (day + 1) * TPD + 1)
                    np_ = int(steps[j][0]["observation"]["market"]["prices"].get(item, 1))
                    next_morning_value += np_ * n
                    next_morning_units += n
    rec["sells_by_hour"] = {h: dict(c) for h, c in sells_by_hour.items()}
    rec["revenue_by_hour"] = dict(revenue_by_hour)
    rec["night_sell_units"] = dict(night_sell_units)
    rec["night_sell_value"] = night_sell_value
    rec["next_morning_value"] = next_morning_value
    rec["sell_units_total"] = sell_units_total
    rec["shed_by_day_hour"] = {d: dict(v) for d, v in shed_by_day_hour.items()}
    rec["carried_by_day_hour"] = {d: dict(v) for d, v in carried_by_day_hour.items()}
    # overflow risk: what the night drop would have discarded, from the h23 state
    for day in sorted(shed_by_day_hour):
        s = shed_by_day_hour[day].get(23)
        c = carried_by_day_hour[day].get(23)
        if s is not None and c is not None:
            overflow_est[day] = max(0, s + c - 100)
    rec["overflow_est_h23"] = overflow_est

    # --- rival sales reconstructed from the public market inventory ---
    inv_prev = dict(steps[0][0]["observation"]["market"]["inventory"])
    rival_sold = collections.Counter()
    own_sold_total = collections.Counter()
    town_total = collections.Counter()
    for i, entry in enumerate(steps[:-1]):
        own, _ = _own_sells(entry, us)
        draw = _town_draw(entry[0]["observation"]["town"], i)
        inv_next = steps[i + 1][0]["observation"]["market"]["inventory"]
        for item in PRODUCTS:
            d_inv = inv_next.get(item, 0) - inv_prev.get(item, 0)
            own_sold_total[item] += own.get(item, 0)
            town_total[item] += draw.get(item, 0)
            # d_inv = own + rival - town - (buyers) ... wheat/fert buys by either side
            rival_sold[item] += d_inv + draw.get(item, 0) - own.get(item, 0)
        inv_prev = dict(inv_next)
    rec["rival_sold_recon"] = dict(rival_sold)
    rec["own_sold_total"] = dict(own_sold_total)
    rec["town_draw_total"] = dict(town_total)
    return rec


def load_set(dirname):
    recs = []
    skipped = 0
    for p in sorted(glob.glob(os.path.join(dirname, "episode-*.json"))):
        r = load_episode(p)
        if r is None:
            skipped += 1
            continue
        recs.append(r)
    return recs, skipped


def summarize(recs):
    wins = [r for r in recs if r["margin"] > 0]
    losses = [r for r in recs if r["margin"] < 0]
    ties = [r for r in recs if r["margin"] == 0]
    return {
        "n": len(recs),
        "wins": len(wins),
        "losses": len(losses),
        "ties": len(ties),
        "winrate": len(wins) / len(recs) if recs else 0.0,
        "mean_margin": statistics.mean([r["margin"] for r in recs]) if recs else 0.0,
        "worst_margin": min([r["margin"] for r in recs]) if recs else 0.0,
        "mean_win_margin": statistics.mean([r["margin"] for r in wins]) if wins else 0.0,
        "mean_loss_margin": statistics.mean([r["margin"] for r in losses]) if losses else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="results/analysis_v24_vs_v23_data.json")
    args = ap.parse_args()

    data = {}
    for key, dirname in SETS.items():
        recs, skipped = load_set(dirname)
        data[key] = {"recs": recs, "skipped_selfplay": skipped, "dir": dirname}
        s = summarize(recs)
        print(f"== {key} ({dirname})  files={len(glob.glob(dirname + '/episode-*.json'))} "
              f"selfplay_skipped={skipped} usable={s['n']}")
        print(f"   {s['wins']}W-{s['losses']}L-{s['ties']}T  winrate={s['winrate']*100:.1f}%  "
              f"mean_margin={s['mean_margin']:+,.0f}  worst={s['worst_margin']:+,.0f}  "
              f"avgWin={s['mean_win_margin']:+,.0f} avgLoss={s['mean_loss_margin']:+,.0f}")

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump({k: v["recs"] for k, v in data.items()}, f)
    print("\nwrote", args.json)


if __name__ == "__main__":
    main()
