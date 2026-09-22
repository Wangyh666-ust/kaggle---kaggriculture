"""Deterministic re-derivation of our money after step 1 (day 0, hour 1).

Re-implements the engine's documented per-unit lockstep market loop
(env/kaggriculture.py:_process_market) for the single step that decides the
whole game, using the engine's own price function, and shows how the opponent's
concurrent WHEAT orders move our day-0 residue across the $4 hire threshold.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_step1_market.py
"""
import importlib.util

spec = importlib.util.spec_from_file_location("kagri", "env/kaggriculture.py")
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)

HIRE = ["HIRE"]
# Calibrated against the real engine: a local `main.py` vs itself mirror (both
# players submit BUY 20 / SELL 15 at step 1) leaves both at $2,854 — which this
# loop reproduces only when the SELL side is quoted one unit deeper than the
# pre-commit inventory.  With depth 0 it gives $2,857.
SELL_QUOTE_DEPTH = 1


def parse(order):
    op = order[0]
    if op == "HIRE":
        return {"type": "HIRE"}
    if op == "BUY_LAND":
        return {"type": "BUY_LAND"}
    if op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL") and len(order) >= 3:
        return {"type": op, "item": order[1], "remaining": int(order[2])}
    return None


def quote(ostate, market):
    op, item = ostate["type"], ostate["item"]
    if op == "BUY_SEED":
        return ("BUY_SEED", item, K.CROPS[item]["seed"])
    if op == "BUY_ANIMAL":
        return ("BUY_ANIMAL", item, K.ANIMALS[item]["cost"])
    inv = market["inventory"][item]
    if op == "SELL":
        return ("SELL", item, K.market_price(item, inv + SELL_QUOTE_DEPTH, market["params"]))
    if op == "BUY_PRODUCT":
        return ("BUY_PRODUCT", item, K.market_price(item, inv - 1, market["params"]))
    return None


def run_step(market, money, shed, orders, hires_today):
    """Return (money, shed, hires_today, trace) after one step's market."""
    queues = [list(q)[:10] for q in orders]
    state = [{"money": money[i], "shed": dict(shed[i]), "hires": hires_today[i]} for i in range(2)]
    max_len = max(len(q) for q in queues)
    trace = []
    for i in range(max_len):
        ostate = [parse(q[i]) if i < len(q) else None for q in queues]
        for pid, o in enumerate(ostate):
            if o is None:
                continue
            if o["type"] == "HIRE":
                cost = K._fib(state[pid]["hires"])
                if state[pid]["money"] >= cost:
                    state[pid]["money"] -= cost
                state[pid]["hires"] += 1
                trace.append("slot%d p%d HIRE cost=%d money=%.0f" % (i, pid, cost, state[pid]["money"]))
                ostate[pid] = None
            elif o["type"] == "BUY_LAND":
                ostate[pid] = None
        while True:
            quoted = [quote(o, market) if (o and o["remaining"] > 0) else None for o in ostate]
            if all(q is None for q in quoted):
                break
            commit = False
            for pid, q in enumerate(quoted):
                if q is None:
                    continue
                op, item, price = q
                st = state[pid]
                if op == "SELL":
                    if st["shed"].get(item, 0) <= 0:
                        trace.append("slot%d p%d SELL %s FAIL(shed)" % (i, pid, item))
                        ostate[pid] = None
                        continue
                    st["shed"][item] -= 1
                    st["money"] += price
                    if price > 1:
                        market["inventory"][item] += 1
                    ostate[pid]["remaining"] -= 1
                    commit = True
                    trace.append("slot%d p%d SELL %s @%d money=%.0f inv=%d"
                                 % (i, pid, item, price, st["money"], market["inventory"][item]))
                else:
                    if st["money"] < price or sum(st["shed"].values()) >= 100:
                        trace.append("slot%d p%d %s %s FAIL(money=%.0f price=%d)"
                                     % (i, pid, op, item, st["money"], price))
                        ostate[pid] = None
                        continue
                    st["money"] -= price
                    if op == "BUY_SEED":
                        pass
                    else:
                        st["shed"][item] = st["shed"].get(item, 0) + 1
                    if op == "BUY_PRODUCT":
                        market["inventory"][item] -= 1
                    ostate[pid]["remaining"] -= 1
                    commit = True
                    shown = market["inventory"].get(item)
                    trace.append("slot%d p%d %s %s @%d money=%.0f inv=%s"
                                 % (i, pid, op, item, price, st["money"], shown))
            if not commit:
                break
    return [s["money"] for s in state], [s["shed"] for s in state], [s["hires"] for s in state], trace


US = [["BUY_PRODUCT", "WHEAT", 20], ["SELL", "WHEAT", 15], ["BUY_SEED", "WHEAT", 1]]
OPPONENTS = {
    "A `BUY WHEAT 10` + `SELL WHEAT 10` (the 7 catastrophic games)":
        [["BUY_PRODUCT", "WHEAT", 10], ["SELL", "WHEAT", 10]],
    "A' same, plus `BUY_SEED WHEAT 1`":
        [["BUY_PRODUCT", "WHEAT", 10], ["SELL", "WHEAT", 10], ["BUY_SEED", "WHEAT", 1]],
    "B `BUY WHEAT 14` + `SELL WHEAT 14` + `BUY WHEAT 5`":
        [["BUY_PRODUCT", "WHEAT", 14], ["SELL", "WHEAT", 14], ["BUY_PRODUCT", "WHEAT", 5]],
    "C the same list we submit (mirror: BUY 20 / SELL 15 / BUY_SEED)":
        [["BUY_PRODUCT", "WHEAT", 20], ["SELL", "WHEAT", 15], ["BUY_SEED", "WHEAT", 1]],
    "D no WHEAT market orders (hires / seeds / animals only)":
        [["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
         ["BUY_SEED", "WHEAT", 7], ["BUY_SEED", "MELON", 12],
         ["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2]],
    "E sells nothing, buys 20 WHEAT":
        [["BUY_PRODUCT", "WHEAT", 20]],
}

REAL = {
    "A `BUY WHEAT 10` + `SELL WHEAT 10` (the 7 catastrophic games)": 2843,
    "B `BUY WHEAT 14` + `SELL WHEAT 14` + `BUY WHEAT 5`": 2845,
    "C the same list we submit (mirror: BUY 20 / SELL 15 / BUY_SEED)": 2854,
}

if __name__ == "__main__":
    print("step-1 market: WHEAT inventory 10000, minus the step-0 town-centre draw = 9999")
    print("both players start with $3000; each holds 20 WHEAT so the 15-unit sale can fill\n")
    print("| opponent step-1 market list | our $ (this loop) | real $ (replay/engine) | residue after -$2842 | hands at d1 h1 |")
    print("|---|---|---|---|---|")
    fib = [1, 1, 2, 3, 5, 8, 13]
    for name, theirs in OPPONENTS.items():
        market = {"inventory": {p: 10000 for p in K.PRODUCTS}, "params": K.MARKET_PARAMS}
        market["inventory"]["WHEAT"] = 9999
        money, _, _, _ = run_step(market, [3000, 3000], [{"WHEAT": 20}, {"WHEAT": 20}],
                                 [US, theirs], [0, 0])
        res = money[0] - 2842
        cum, hands = 0, 0
        for c in fib:
            if cum + c <= res:
                cum += c
                hands += 1
            else:
                break
        real = REAL.get(name)
        print("| %s | %s | %s | $%d | %d/3 |" % (
            name, "$%.0f" % money[0], "$%d" % real if real else "—", res, min(3, hands)))
    print()
    print("本循环与线上实测在 A/B/C 三个已知点上分别差 $1 / $1 / $0（常数量级，来自第 0 步价格细节）；")
    print("A 用实测值 $2843 算是 1 手，本循环算 0 手 —— 两者都远少于 3 手，落在同一侧。")
    print()
    print("读法：我方第 1 步的市场单在所有 183 局里完全一样（`BUY WHEAT 20 / SELL WHEAT 15 / BUY_SEED WHEAT 1`），")
    print("所以 `money_t1` 完全由对手第 1 步的小麦单决定。对手在槽 0 只买 10 单位（我们买 20）会让市场")
    print("在我们卖出时多留 5 单位小麦，叠加他们同槽位卖出的 10 单位，我方 15 单位的均价少约 $11 —— ")
    print("正好把 d0 期末现金从 $12 压到 $1，跌破 d1 h1 雇 3 个雇工所需的 $4。")
