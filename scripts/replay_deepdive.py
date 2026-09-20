"""Deep-dive a single replay: opponent revenue mix, timing, and market behavior."""
import collections
import json
import sys


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "loss_replays/111100200.json"
    d = json.load(open(path))
    names = d["info"]["TeamNames"]
    rewards = d["rewards"]
    steps = d["steps"]
    us = names.index("ReD_MooN_rise")
    opp = 1 - us
    print(f"players: {names}  rewards: {[int(r) for r in rewards]}")
    print(f"analyzing opponent: {names[opp]}\n")

    # --- revenue by product/day: SELL qty x price-at-that-turn (prices from obs) ---
    rev = collections.Counter()
    cnt = collections.Counter()
    daily_rev = collections.defaultdict(collections.Counter)
    buys = collections.Counter()
    hires_by_day = collections.Counter()
    land_days = []
    for s in steps:
        o = s[opp]["observation"]
        day, hour = o["day"], o["hour"]
        prices = o["market"]["prices"]
        act = s[opp].get("action") or {}
        for order in act.get("market", []):
            if not order:
                continue
            op = order[0]
            if op == "SELL" and len(order) >= 3:
                item, qty = order[1], order[2]
                rev[item] += prices.get(item, 0) * qty
                cnt[item] += qty
                daily_rev[day][item] += prices.get(item, 0) * qty
            elif op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL") and len(order) >= 3:
                buys[(op, order[1])] += order[2]
            elif op == "HIRE":
                hires_by_day[day] += 1
            elif op == "BUY_LAND":
                land_days.append(day)
    print("== revenue by product ==")
    tot = 0
    for it, r in rev.most_common():
        print(f"  {it:12s} n={cnt[it]:4d} rev=${r:8.0f} avg=${r / cnt[it]:6.1f}")
        tot += r
    print(f"  TOTAL revenue ${tot:.0f}")
    print("\n== buys ==")
    for k, v in sorted(buys.items()):
        print(f"  {k}: {v}")
    print(f"\n== land buys on days: {land_days} ==")
    print(f"== hires by day: {dict(sorted(hires_by_day.items()))} ==")

    print("\n== daily revenue (top channels) ==")
    for day in sorted(daily_rev):
        items = daily_rev[day]
        top = ", ".join(f"{k}:${int(v)}" for k, v in items.most_common(4))
        print(f"  d{day:2d} total=${int(sum(items.values())):6d}  {top}")

    # town shops (shared)
    town = steps[-1][opp]["observation"]["town"]["unlocked_shops"]
    print(f"\n== town shops (final): {sorted(town)} ==")


if __name__ == "__main__":
    main()
