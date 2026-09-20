"""Kaggriculture agent — v7 (livestock-industrial).

Strategy overview
-----------------
Bootstrap    : 6 geese on NW coops.  Every surviving animal yields 1
               FERTILIZER per day (~$100 early) — that funds land + cows.
Engine       : 8 cows + 4 sheep on SW pastures.  Fed+cared daily, a cow pays
               1+2=3 milk every 2 days, a sheep 1+3=4 wool every 3 days.
               Milk/wool are town-drained (pizza / ice cream / smoothie / yarn
               shops) so prices hold near base instead of crashing.
Staple       : wheat rotation on every spare tile (feed stock + late-season
               sale into town-driven scarcity).
Melon        : one disciplined 16-tile wave on NE (days 3-8).  Melon has no
               town drain, so we plant few and sell at harvest — never enough
               to crash the sq-curve ourselves.
Market       : sells go out every turn (hour>0), premium unit-price first.
               Purchases only at hour 0/12 so the 10-orders/turn cap can never
               eat a sell order.  Wheat is held through gluts (town drain
               recovers the price); fertilizer/melon are sold at once.
Labor        : hire up to 9 hands/day at hour 0 (fib cost ~$90/day total).
Endgame      : day 28+ — stop all investment, liquidate the shed.

Pure stdlib; comfortably below the 1s/turn limit.
"""

# ---------------------------------------------------------------- constants
CROPS = {
    "WHEAT":      {"seed": 10,  "first_yield_day": 2,  "max_yield_day": 4,  "ongoing": False},
    "CARROT":     {"seed": 20,  "first_yield_day": 2,  "max_yield_day": 3,  "ongoing": False},
    "TOMATO":     {"seed": 50,  "first_yield_day": 8,  "max_yield_day": 8,  "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "ongoing": True},
    "MELON":      {"seed": 80,  "first_yield_day": 10, "max_yield_day": 12, "ongoing": False},
}
# harvest_at: harvest once yield_units reaches this (keeps production uncapped)
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "product": "EGG",  "harvest_at": 2},
    "COW":   {"cost": 400, "structure": "PASTURE", "product": "MILK", "harvest_at": 3},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "product": "WOOL", "harvest_at": 4},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"]
I0 = 10000

TURNS_PER_DAY = 24
SEASON_DAYS = 30
BOARD = 10
CENTER = [(4, 4), (5, 4), (4, 5), (5, 5)]  # shed-access tiles

# ---- production plan -------------------------------------------------------
GEESE_TARGET = 6
COW_CORE = 6                 # base herd, viable even with no milk shops
SHEEP_CORE = 2
COW_MAX = 10                 # +2 per milk-draining shop (pizza/ice cream/smoothie)
SHEEP_MAX = 6                # +2 per yarn store

# structure spots, laid out in tight rows so keeper routes stay short
COOP_SPOTS = [(4, 3), (3, 3), (4, 2), (3, 2), (2, 3), (4, 1)]
PASTURE_SPOTS = [(3, 5), (2, 5), (1, 5), (0, 5),
                 (4, 6), (3, 6), (2, 6), (1, 6),
                 (0, 6), (4, 7), (3, 7), (2, 7),
                 (1, 7), (0, 7), (4, 8), (3, 8)]

MELON_QUAD = "NE"
MELON_TILES = 14
MELON_DAYS = (12, 16)        # plant after the herd is funded; harvest days 22-26

FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
HAND_CAP = 9                 # hires per day (farmer + 9 = 10 units)

WHEAT_SEED_BUF = 12
KEEPER_PER = 4               # animals per keeper route (quadrant-pure chains)

# ---------------------------------------------------------------- state
G = {}


def _reset():
    G.clear()
    G.update({
        "turn": -1,
        "keepers": {},          # unit_idx -> [(x, y), ...] animal route (today)
        "missions": {},         # unit_idx -> animal-placement mission
        "sticky": {},           # unit_idx -> last worker task key
        "shed_wheat_shadow": 0,
    })


# ---------------------------------------------------------------- helpers
def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(pos, target):
    """One greedy step (locked tiles are passable, units may overlap)."""
    x, y = pos
    tx, ty = target
    if tx > x:
        return ["EAST"]
    if tx < x:
        return ["WEST"]
    if ty > y:
        return ["SOUTH"]
    if ty < y:
        return ["NORTH"]
    return ["PASS"]


def _nearest_center(pos):
    return min(CENTER, key=lambda c: _dist(pos, c))


def _is_center(pos):
    return (pos[0], pos[1]) in CENTER


def _quad(x, y):
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _scan(me):
    """Classify my tiles once per turn."""
    plants, animals, empty_coops, empty_pastures, weeds, empty = [], [], [], [], [], []
    for y in range(BOARD):
        row = me["tiles"][y]
        for x in range(BOARD):
            t = row[x]
            if t is None:
                empty.append((x, y))
            elif t == "LOCKED" or not isinstance(t, dict):
                continue
            elif t.get("kind") == "PLANT":
                plants.append((x, y, t))
            elif t.get("kind") == "WEED":
                weeds.append((x, y))
            elif t.get("kind") == "COOP":
                if "animal" in t:
                    animals.append((x, y, t))
                else:
                    empty_coops.append((x, y))
            elif t.get("kind") == "PASTURE":
                if "animal" in t:
                    animals.append((x, y, t))
                else:
                    empty_pastures.append((x, y))
    return plants, animals, empty_coops, empty_pastures, weeds, empty


def _feed_reserve(day, n_animals):
    if day >= 27:
        return n_animals + 2       # still feeding through day 29
    return n_animals + 6           # ~1 day of cover; shed space is precious


# ---------------------------------------------------------------- market
def _market_orders(obs, me, priv, ctx, day, hour):
    """Sells every turn except hour 0; purchases only at hour 0/12.

    The 10-orders/turn cap is real and silently drops extras, so the hour-0
    list is reserved for hires+investment and sells fill the other turns.
    """
    money = me["money"]
    shed = priv["shed"]
    seeds = priv["seeds"]
    prices = obs["market"]["prices"]
    inv = obs["market"]["inventory"]
    unlocked = ctx["unlocked"]
    endgame = day >= SEASON_DAYS - 2
    n_animals = len(ctx["animals"])
    shed_total = sum(shed.values())
    carried_wheat = sum(i.get("WHEAT", 0) for i in priv["inventories"])
    wheat_total = shed.get("WHEAT", 0) + carried_wheat
    orders = []

    if hour == 0:
        # ---- land: SW (livestock) first, NE (melon wave) once cash flows ----
        if not endgame:
            if "SW" not in unlocked and day >= 2 and money >= 2000:
                orders.append(["BUY_LAND"]); money -= 2000
            elif "NE" not in unlocked and day >= 5 and money > 1300:
                orders.append(["BUY_LAND"]); money -= 1000

        # ---- animals (shed -> structure via ferry missions) ----
        if not endgame:
            room = 100 - shed_total
            carry = ctx["carry"]
            if room > 4:
                gt = ctx["animal_total"]["GOOSE"] + shed.get("GOOSE", 0) + carry.get("GOOSE", 0)
                if gt < min(GEESE_TARGET, ctx["n_coops"]) and day <= 6 and money > 400:
                    nb = int(min(2, min(GEESE_TARGET, ctx["n_coops"]) - gt,
                                 (money - 250) // 300, room))
                    if nb > 0:
                        orders.append(["BUY_ANIMAL", "GOOSE", nb]); money -= 300 * nb; room -= nb
                ct = ctx["animal_total"]["COW"] + shed.get("COW", 0) + carry.get("COW", 0)
                if ("SW" in unlocked and day <= 14 and money > 600
                        and ct < min(ctx["cow_target"], ctx["n_pastures"])):
                    nb = int(min(2, min(ctx["cow_target"], ctx["n_pastures"]) - ct,
                                 (money - 400) // 400, room))
                    if nb > 0:
                        orders.append(["BUY_ANIMAL", "COW", nb]); money -= 400 * nb; room -= nb
                st = ctx["animal_total"]["SHEEP"] + shed.get("SHEEP", 0) + carry.get("SHEEP", 0)
                pasture_free = ctx["n_pastures"] - ctx["animal_total"]["COW"] - shed.get("COW", 0) \
                    - carry.get("COW", 0) - st
                if ("SW" in unlocked and ctx["animal_total"]["COW"] >= 4 and day <= 16
                        and money > 700 and st < min(ctx["sheep_target"], pasture_free)):
                    nb = int(min(2, min(ctx["sheep_target"], pasture_free) - st,
                                 (money - 500) // 500, room))
                    if nb > 0:
                        orders.append(["BUY_ANIMAL", "SHEEP", nb]); money -= 500 * nb; room -= nb

        # ---- seeds (wheat small buffer; melons only once livestock is funded) ----
        if day <= 24:
            need = int(min(max(0, WHEAT_SEED_BUF - seeds.get("WHEAT", 0)),
                           max(0, money - 300) // 10))
            if need > 0:
                orders.append(["BUY_SEED", "WHEAT", need]); money -= 10 * need
        if MELON_QUAD in unlocked and MELON_DAYS[0] <= day <= MELON_DAYS[1] and money > 800:
            have = seeds.get("MELON", 0) + ctx["melons_growing"]
            need = int(min(max(0, MELON_TILES - have), max(0, money - 800) // 80))
            if need > 0:
                orders.append(["BUY_SEED", "MELON", need]); money -= 80 * need

        # ---- feed wheat (2-day cover, counting what units carry) ----
        reserve = _feed_reserve(day, n_animals)
        room = 100 - shed_total
        if n_animals and wheat_total < reserve and money > 400 and room > 10:
            bn = int(min(reserve - wheat_total + n_animals, 30, room - 5,
                         (money - 300) // 30))
            if bn > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", bn]); money -= 30 * bn

        # ---- hires last: they fill whatever order slots remain ----
        # keep hiring through the final day: unkept animals mean lost
        # fertilizer/products, and hands are cheap (<= $88/day)
        pipeline = sum(shed.get(a, 0) + ctx["carry"].get(a, 0) for a in ANIMALS)
        keepers_needed = (n_animals + pipeline + KEEPER_PER - 1) // KEEPER_PER
        workers_needed = int(min(5, 2 + (len(ctx["plants"]) + 8) // 12))
        if endgame:
            workers_needed = min(workers_needed, 1)
        want = min(1 + HAND_CAP, 1 + keepers_needed + workers_needed)
        cur = 1 + len(me["hands"])
        n = me["hires_today"]
        slots = 10 - len(orders)
        while cur < want and n < HAND_CAP and slots > 0 and money > FIB[n] + 100:
            orders.append(["HIRE"]); money -= FIB[n]; n += 1; cur += 1; slots -= 1
        return orders[:10]

    # ---- hour 12: small top-up buys only ----
    if hour == 12 and not endgame:
        reserve = _feed_reserve(day, n_animals)
        room = 100 - shed_total
        if n_animals and wheat_total < reserve and money > 400 and room > 10:
            bn = int(min(reserve - wheat_total + n_animals, 30, room - 5,
                         (money - 300) // 30))
            if bn > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", bn]); money -= 30 * bn

    # ---- sells (every turn; premium unit-price first) ----
    feed_res = _feed_reserve(day, n_animals)
    sells = []
    for item in PRODUCTS:
        qty = shed.get(item, 0)
        if qty <= 0:
            continue
        if item == "WHEAT":
            qty = max(0, qty - feed_res)
            if qty <= 0:
                continue
            # hold wheat through a glut only once cash is comfortable;
            # early game every dollar funds the livestock ramp
            if inv.get("WHEAT", I0) > I0 and day < 24 and shed_total < 80 \
                    and day >= 8 and money > 1500:
                continue
        sells.append((prices.get(item, 1), item, qty))
    sells.sort(key=lambda s: -s[0])
    orders.extend(["SELL", it, q] for _, it, q in sells)
    return orders[:10]


# ---------------------------------------------------------------- keeper
_QUAD_ANCHOR = {"NW": (4, 4), "NE": (5, 4), "SW": (4, 5), "SE": (5, 5)}


def _build_routes(animals, n_units):
    """Split animals into keeper routes that never cross quadrants.

    Each quadrant's animals are ordered as a nearest-neighbour chain starting
    from the shed, then chunked; chunk size grows only if units are scarce.
    """
    by_quad = {}
    for (x, y, _t) in animals:
        by_quad.setdefault(_quad(x, y), []).append((x, y))
    chains = []
    for q in ("NW", "NE", "SW", "SE"):
        pts = by_quad.get(q)
        if not pts:
            continue
        chain = []
        cur = _QUAD_ANCHOR[q]
        while pts:
            nxt = min(pts, key=lambda p: (_dist(cur, p), p[1], p[0]))
            pts.remove(nxt)
            chain.append(nxt)
            cur = nxt
        chains.append(chain)
    for per in (KEEPER_PER, 4, 5, 6):
        routes = []
        for chain in chains:
            routes.extend(chain[i:i + per] for i in range(0, len(chain), per))
        if len(routes) <= n_units:
            return routes
    return routes


def _keeper_action(idx, pos, inv, animal_map):
    """Animal keeper: service every assigned animal each day.

    Order on the tile: COLLECT_FERTILIZER > FEED > HARVEST > CARE.
    Proactively tops up wheat whenever passing the shed.
    """
    route = G["keepers"].get(idx, [])
    if not route:
        return None
    wheat = inv.get("WHEAT", 0)
    unfed = [c for c in route if not animal_map[c]["fed_today"]]

    # resupply: sitting on the shed with too little wheat for today's route
    if _is_center(pos) and wheat < max(1, len(unfed)) and G["shed_wheat_shadow"] > 0:
        take = min(len(route) + 1 - wheat, G["shed_wheat_shadow"])
        if take > 0:
            G["shed_wheat_shadow"] -= take
            return ["PICKUP", "WHEAT", take]
    if unfed and wheat == 0:
        return _step_toward(pos, _nearest_center(pos))

    for c in route:
        t = animal_map[c]
        a = ANIMALS[t["animal"]]
        needs_feed = not t["fed_today"] and wheat > 0
        needs_collect = t["fertilizer_available"]
        needs_harvest = t["yield_units"] >= a["harvest_at"] or \
            (t["yield_units"] > 0 and day_endgame())
        needs_care = not t["cared_today"]
        if not (needs_feed or needs_collect or needs_harvest or needs_care):
            continue
        if (pos[0], pos[1]) != (c[0], c[1]):
            return _step_toward(pos, c)
        if needs_collect:
            return ["COLLECT_FERTILIZER"]
        if needs_feed:
            return ["FEED"]
        if needs_harvest:
            return ["HARVEST"]
        return ["CARE"]
    return None  # route finished -> worker mode


def day_endgame():
    return G.get("endgame", False)


# ---------------------------------------------------------------- missions
def _mission_action(idx, pos, inv, shed, empty_coops, empty_pastures, allow_new):
    """Multi-turn mission: ferry an animal from the shed to its structure."""
    m = G["missions"].get(idx)
    if m is None:
        carrying = [a for a in ANIMALS if inv.get(a, 0) > 0]
        if carrying:
            animal = carrying[0]
        elif allow_new:
            from collections import Counter
            active = Counter(mm["animal"] for mm in G["missions"].values())
            animal = None
            for cand, spots in (("COW", empty_pastures), ("SHEEP", empty_pastures),
                                ("GOOSE", empty_coops)):
                if shed.get(cand, 0) > 0 and spots and active[cand] < 2:
                    animal = cand
                    break
            if animal is None:
                return None
        else:
            return None
        m = {"animal": animal}
        G["missions"][idx] = m
    animal = m["animal"]
    structure = ANIMALS[animal]["structure"]
    spots = empty_coops if structure == "COOP" else empty_pastures
    if inv.get(animal, 0) > 0:
        if not spots:
            return None  # nowhere to place right now; keep carrying
        tgt = min(spots, key=lambda s: _dist(pos, s))
        if (pos[0], pos[1]) == tgt:
            G["missions"].pop(idx, None)
            return ["PLACE", animal]
        return _step_toward(pos, tgt)
    if shed.get(animal, 0) <= 0:
        G["missions"].pop(idx, None)
        return None
    if _is_center(pos):
        return ["PICKUP", animal, 1]
    return _step_toward(pos, _nearest_center(pos))


# ---------------------------------------------------------------- worker
def _worker_tasks(day, ctx, seeds):
    """Crop-task list for this turn: (priority, kind, x, y, arg)."""
    tasks = []
    unlocked = ctx["unlocked"]
    endgame = G["endgame"]
    for (x, y, t) in ctx["plants"]:
        crop = t["crop"]
        cd = CROPS.get(crop)
        if cd is None:
            continue
        age = day - t["planted_day"]
        if crop == "MELON":
            if t["yield_units"] >= 6 or age >= 11 or (endgame and t["yield_units"] > 0):
                tasks.append((8, "HARVEST", x, y, None))
                continue
        else:  # WHEAT (and any other one-time crop)
            if t["yield_units"] >= 4 or age >= cd["max_yield_day"] or \
                    (endgame and t["yield_units"] > 0):
                tasks.append((8, "HARVEST", x, y, None))
                continue
        if not t["watered_today"]:
            urg = 10 if t["consecutive_unwatered"] >= 1 else 6
            tasks.append((urg, "WATER", x, y, None))
    for (x, y) in ctx["weeds"]:
        tasks.append((5, "DIG", x, y, None))

    if not endgame:
        empty_set = ctx["empty_set"]
        if ctx["n_coops"] < GEESE_TARGET:
            for (x, y) in COOP_SPOTS:
                if (x, y) in empty_set:
                    tasks.append((7, "BUILD_COOP", x, y, None))
        if "SW" in unlocked and ctx["n_pastures"] < ctx["cow_target"] + ctx["sheep_target"]:
            for (x, y) in PASTURE_SPOTS:
                if (x, y) in empty_set:
                    tasks.append((7, "BUILD_PASTURE", x, y, None))
        # planting, gated by watering capacity
        if len(ctx["plants"]) < ctx["plant_capacity"]:
            # melon window is short: planting it outranks routine watering
            if MELON_QUAD in unlocked and MELON_DAYS[0] <= day <= MELON_DAYS[1] \
                    and seeds.get("MELON", 0) > 0 \
                    and ctx["melons_growing"] + ctx["melon_claimed"] < MELON_TILES:
                for (x, y) in ctx["empty"]:
                    if _quad(x, y) == MELON_QUAD:
                        tasks.append((9, "PLANT", x, y, "MELON"))
            if day <= 24 and seeds.get("WHEAT", 0) > 0:
                for (x, y) in ctx["empty"]:
                    if (x, y) in COOP_SPOTS or (x, y) in PASTURE_SPOTS:
                        continue
                    if _quad(x, y) == MELON_QUAD and day <= MELON_DAYS[1] + 1:
                        continue  # keep NE clear for the melon wave
                    tasks.append((4, "PLANT", x, y, "WHEAT"))
    return tasks


# ---------------------------------------------------------------- agent
def agent(obs):
    turn = obs.get("day", 0) * TURNS_PER_DAY + obs.get("hour", 0)
    if "turn" not in G or turn <= G["turn"]:
        _reset()
    G["turn"] = turn

    day = obs["day"]
    hour = obs["hour"]
    player = obs["player"]
    me = obs["farms"][player]
    priv = obs["private"]
    shed = priv["shed"]
    seeds = priv["seeds"]
    invs = priv["inventories"]
    unlocked = set(me["unlocked_quadrants"])
    G["endgame"] = day >= SEASON_DAYS - 2
    G["shed_wheat_shadow"] = shed.get("WHEAT", 0)

    plants, animals, empty_coops, empty_pastures, weeds, empty = _scan(me)
    animal_map = {(x, y): t for (x, y, t) in animals}
    carry = {}
    for i in invs:
        for a in ANIMALS:
            if i.get(a, 0):
                carry[a] = carry.get(a, 0) + i[a]
    animal_total = {a: sum(1 for (_, _, t) in animals if t["animal"] == a) for a in ANIMALS}
    # shop-reactive herd sizing: milk/wool prices only hold if the town drains them
    shops = obs.get("town", {}).get("unlocked_shops", [])
    milk_shops = sum(1 for s in shops if s in ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"))
    yarn_shops = sum(1 for s in shops if s == "YARN_STORE")
    ctx = {
        "plants": plants, "animals": animals, "weeds": weeds, "empty": empty,
        "empty_set": set(empty),
        "empty_coops": empty_coops, "empty_pastures": empty_pastures,
        "unlocked": unlocked, "carry": carry, "animal_total": animal_total,
        "melons_growing": sum(1 for (_, _, t) in plants if t["crop"] == "MELON"),
        "melon_claimed": 0,
        "cow_target": min(COW_MAX, COW_CORE + 2 * milk_shops),
        "sheep_target": min(SHEEP_MAX, SHEEP_CORE + 2 * yarn_shops),
    }
    ctx["n_coops"] = len(empty_coops) + animal_total["GOOSE"]
    ctx["n_pastures"] = len(empty_pastures) + animal_total["COW"] + animal_total["SHEEP"]

    n_units = 1 + len(me["hands"])
    routes_preview = _build_routes(animals, n_units) if animals else []
    keepers_now = len(routes_preview)
    ctx["plant_capacity"] = max(10, (n_units - keepers_now) * 11)

    orders = _market_orders(obs, me, priv, ctx, day, hour)

    # keeper routes: rebuild at hour 1 (today's hands have arrived by then;
    # at hour 0 the hands list is always empty, so hour 0 keeps yesterday's
    # routes — only the farmer is around and it services its old route).
    if hour == 1 or G.get("_keepers_day") != day and hour > 1:
        G["keepers"] = {}
        G["missions"] = {}
        if animals:
            for k, route in enumerate(_build_routes(animals, n_units)):
                G["keepers"][k] = route
        G["_keepers_day"] = day
    G["keepers"] = {k: v for k, v in G["keepers"].items() if k < n_units}
    G["missions"] = {k: v for k, v in G["missions"].items() if k < n_units}

    # ---------------- unit actions ---------------------------------------
    tasks = _worker_tasks(day, ctx, seeds)
    tasks.sort(key=lambda t: -t[0])
    task_by_key = {(t[1], t[2], t[3]): t for t in tasks}
    claimed = set()
    plant_budget = {c: seeds.get(c, 0) for c in CROPS}

    farmer_act = ["PASS"]
    hand_acts = []
    unit_positions = [me["farmer"]] + list(me["hands"])
    for idx in range(n_units):
        pos = unit_positions[idx]
        inv = invs[idx] if idx < len(invs) else {}
        allow_new = not G["keepers"].get(idx)
        act = _mission_action(idx, pos, inv, shed, empty_coops, empty_pastures, allow_new)
        if act is None:
            act = _keeper_action(idx, pos, inv, animal_map)
        if act is None:
            t = None
            skey = G["sticky"].get(idx)
            if skey in task_by_key and skey not in claimed:
                cand = task_by_key[skey]
                if not (cand[1] == "PLANT" and plant_budget.get(cand[4], 0) <= 0):
                    t = cand
            if t is None:
                best = None
                for cand in tasks:
                    key = (cand[1], cand[2], cand[3])
                    if key in claimed:
                        continue
                    if cand[1] == "PLANT" and plant_budget.get(cand[4], 0) <= 0:
                        continue
                    d = _dist(pos, (cand[2], cand[3]))
                    score = (cand[0], -d)
                    if best is None or score > best[0]:
                        best = (score, cand)
                t = best[1] if best else None
            if t is not None:
                key = (t[1], t[2], t[3])
                claimed.add(key)
                G["sticky"][idx] = key
                if t[1] == "PLANT":
                    plant_budget[t[4]] -= 1
                    if t[4] == "MELON":
                        ctx["melon_claimed"] += 1
                if (pos[0], pos[1]) == (t[2], t[3]):
                    if t[1] == "WATER":
                        act = ["WATER"]
                    elif t[1] == "HARVEST":
                        act = ["HARVEST"]
                    elif t[1] == "DIG":
                        act = ["DIG"]
                    elif t[1] == "BUILD_COOP":
                        act = ["BUILD_COOP"]
                    elif t[1] == "BUILD_PASTURE":
                        act = ["BUILD_PASTURE"]
                    else:  # PLANT
                        act = ["PLANT", t[4]]
                else:
                    act = _step_toward(pos, (t[2], t[3]))
        if act is None:
            act = ["PASS"]
        if idx == 0:
            farmer_act = act
        else:
            hand_acts.append(act)

    return {"farmer": farmer_act, "hands": hand_acts, "market": orders}
