"""Kaggriculture agent — v1.

Strategy overview
-----------------
Early engine : geese.  Every surviving animal yields 1 FERTILIZER per day
               (worth ~$100 early) plus eggs.  Geese are cheap ($300) and
               start producing fertilizer the night they are placed.
Mid game     : one big melon wave on the NE quadrant (6 units x ~$250 base,
               harvested at age 10).  Melon has no town drain, so sell at once.
Staple       : continuous wheat rotation on all spare tiles (harvest age 4).
Market sense : goods the town consumes (eggs/wheat/milk/...) are held through
               a glut (the town drains the market and the price recovers);
               fertilizer and melon have no town drain, so sell at once.
Endgame      : stop planting early enough, liquidate the whole shed.

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
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",     "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE",  "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE",  "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE_PRICE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
              "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200,
              "FERTILIZER": 100}
I0 = 10000
# Products the town center / shops consume -> price can recover after a glut.
TOWN_DRAINED = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "EGG", "MILK", "WOOL"}

TURNS_PER_DAY = 24
SEASON_DAYS = 30
BOARD = 10
CENTER = [(4, 4), (5, 4), (4, 5), (5, 5)]  # shed-access tiles (NWSE)

# expected full yield (unfertilized, watered daily) for one-time crops
FULL_YIELD = {"WHEAT": 4, "CARROT": 3, "MELON": 6}

# Fixed layout plans ---------------------------------------------------------
COOP_SPOTS_NW = [(0, 3), (1, 3), (2, 3), (3, 3), (4, 3),
                 (0, 2), (1, 2), (2, 2), (3, 2), (4, 2)]
PASTURE_SPOTS_SW = [(3, 5), (2, 5), (4, 6), (3, 6), (2, 6), (4, 7)]

MAX_GEESE = 10
MAX_COWS = 6

FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

# ---------------------------------------------------------------- state
G = {}


def _reset():
    G.clear()
    G.update({
        "turn": -1,
        "keepers": {},          # unit_idx -> [(x, y), ...] animal route (today)
        "missions": {},         # unit_idx -> animal-placement mission
        "geese_bought": 0,      # total geese ever ordered
        "cows_bought": 0,
        "melon_waves": {"NE": 0, "SE": 0},
        "endgame": False,
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



def _melon_target(day, unlocked):
    """Which quadrant should grow melons now (NE wave 1 -> SE -> NE wave 2)."""
    w = G["melon_waves"]
    if "NE" in unlocked and w["NE"] == 0 and 3 <= day <= 17:
        return "NE"
    if "SE" in unlocked and w["SE"] == 0 and 3 <= day <= 19:
        return "SE"
    if "NE" in unlocked and w["NE"] == 1 and 8 <= day <= 19:
        return "NE"
    return None

# ---------------------------------------------------------------- market
def _market_orders(obs, me, priv, ctx, day, hour):
    """Budget-disciplined market orders.

    Hard rules learned from cash-flow tracing:
    - all *purchases* happen at hour 0 / hour 12 only (per-turn re-buys flood
      the budget and churn the market spread);
    - never let cash drop below CASH_FLOOR (broke -> no hires -> crops die);
    - feed-wheat buys count wheat carried by units, not just the shed.
    """
    CASH_FLOOR = 200
    money = me["money"]
    shed = priv["shed"]
    seeds = priv["seeds"]
    mkt = obs["market"]
    prices = mkt["prices"]
    inv = mkt["inventory"]
    unlocked = ctx["unlocked"]
    orders = []
    shed_total = sum(shed.values())
    endgame = G["endgame"]
    n_animals = len(ctx["animals"])
    n_plants = len(ctx["plants"])
    carried_wheat = sum(i.get("WHEAT", 0) for i in priv["inventories"])
    wheat_total = shed.get("WHEAT", 0) + carried_wheat

    # ---- hiring (hour 0; hands vanish at night) ----
    keepers_needed = (n_animals + 3) // 4
    seeds_avail = seeds.get("WHEAT", 0) + seeds.get("MELON", 0)
    planting_pressure = min(len(ctx["empty"]), seeds_avail) if day <= 24 else 0
    workers_needed = min(7, 2 + (n_plants + planting_pressure) // 12)
    want_units = min(9, 1 + keepers_needed + workers_needed)
    cur_units = 1 + len(me["hands"])
    if hour == 0 and not endgame:
        n = me["hires_today"]
        while cur_units < want_units and n < 8 and money > FIB[n] + 20:
            orders.append(["HIRE"])
            money -= FIB[n]
            n += 1
            cur_units += 1

    # ---- feed wheat (2-day cover, counting what units already carry) ----
    feed_reserve = 0 if endgame else 2 * n_animals + 4
    room = 100 - shed_total
    if hour in (0, 12) and n_animals and wheat_total < feed_reserve \
            and money > CASH_FLOOR + 50 and room > 10:
        buy_n = min(feed_reserve - wheat_total + n_animals, room - 5, 30,
                    int(money - CASH_FLOOR) // 30)
        if buy_n > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", buy_n])
            money -= 30 * buy_n
            room -= buy_n

    if hour in (0, 12):
        # ---- land ----
        if hour == 0:
            if "NE" not in unlocked and money > 1400 and day >= 1:
                orders.append(["BUY_LAND"]); money -= 1000
            elif "SW" not in unlocked and money > 4500 and day >= 3:
                orders.append(["BUY_LAND"]); money -= 2000
            elif "SE" not in unlocked and money > 6500 and day <= 17:
                orders.append(["BUY_LAND"]); money -= 4000

        # ---- animals (hour 0 only; staggered) ----
        if hour == 0 and not endgame and room > 5:
            geese_total = ctx["geese_total"] + shed.get("GOOSE", 0)
            cows_total = ctx["cows_total"] + shed.get("COW", 0)
            goose_cap = min(MAX_GEESE, ctx["n_coops"])
            if geese_total < goose_cap and ctx["empty_coops"] \
                    and shed.get("GOOSE", 0) < 2 and 1 <= day <= 20:
                n_buy = min(1 if money < 1500 else 2,
                            goose_cap - geese_total,
                            2 - shed.get("GOOSE", 0),
                            max(0, int(money - 500) // 300), room)
                if n_buy > 0:
                    orders.append(["BUY_ANIMAL", "GOOSE", n_buy])
                    money -= 300 * n_buy
                    room -= n_buy
            if "SW" in unlocked and cows_total < MAX_COWS and ctx["empty_pastures"] \
                    and shed.get("COW", 0) < 2 and day <= 16 and money > 2500:
                orders.append(["BUY_ANIMAL", "COW", 1])
                money -= 400
                room -= 1

        # ---- seeds ----
        if day <= 24:
            need = max(0, 25 - seeds.get("WHEAT", 0))
            need = min(need, max(0, int(money - CASH_FLOOR) // 10))
            if need > 0:
                orders.append(["BUY_SEED", "WHEAT", need])
                money -= 10 * need
        melon_quad = _melon_target(day, unlocked)
        if melon_quad:
            need = max(0, 25 - seeds.get("MELON", 0))
            need = min(need, max(0, int(money - CASH_FLOOR) // 80))
            if need > 0:
                orders.append(["BUY_SEED", "MELON", need])
                money -= 80 * need

    # ---- selling (every turn; revenue keeps flowing) ----
    sells = []
    for item in PRODUCTS:
        qty = shed.get(item, 0)
        if qty <= 0:
            continue
        if item == "WHEAT":
            qty = max(0, qty - feed_reserve)
            if qty <= 0:
                continue
        price = prices.get(item, 1)
        glut = inv.get(item, I0) > I0
        # only wheat is worth holding through a glut (town drain >> our output)
        if item == "WHEAT" and glut and not endgame and shed_total < 70 \
                and day < SEASON_DAYS - 4:
            continue
        sells.append((price * qty, ["SELL", item, qty]))
    sells.sort(key=lambda s: -s[0])
    orders.extend(s for _, s in sells)

    return orders[:10]


# ---------------------------------------------------------------- keeper
def _keeper_action(idx, pos, inv, animal_map):
    """Animal keeper: service every assigned animal (collect/feed/care/harvest).
    `animal_map` maps (x, y) -> fresh tile dict for all occupied structures."""
    route = G["keepers"].get(idx, [])
    if not route:
        return None
    wheat = inv.get("WHEAT", 0)

    # resupply if any assigned animal is unfed and we are out of wheat
    unfed = [c for c in route if not animal_map[c]["fed_today"]]
    if unfed and wheat == 0:
        if _is_center(pos):
            take = min(len(unfed) + 2, G["shed_wheat_shadow"])
            if take > 0:
                G["shed_wheat_shadow"] -= take
                return ["PICKUP", "WHEAT", take]
        else:
            return _step_toward(pos, _nearest_center(pos))

    for c in route:
        t = animal_map[c]
        x, y = c
        needs_feed = not t["fed_today"] and wheat > 0
        needs_collect = t["fertilizer_available"]
        held = t["yield_units"]
        needs_harvest = held >= 2 or (held >= 1 and G["endgame"])
        needs_care = not t["cared_today"]
        if not (needs_feed or needs_collect or needs_harvest or needs_care):
            continue
        if (pos[0], pos[1]) != (x, y):
            return _step_toward(pos, (x, y))
        if needs_collect:
            return ["COLLECT_FERTILIZER"]
        if needs_feed:
            return ["FEED"]
        if needs_harvest:
            return ["HARVEST"]
        return ["CARE"]
    return None  # route finished -> worker mode


# ---------------------------------------------------------------- missions
def _mission_action(idx, pos, inv, shed, empty_coops, empty_pastures, allow_new):
    """Multi-turn mission: ferry an animal from the shed to its structure.
    At most one active ferry per animal type; keepers never start one."""
    m = G["missions"].get(idx)
    if m is None:
        carrying = [a for a in ANIMALS if inv.get(a, 0) > 0]
        if carrying:
            animal = carrying[0]
        elif allow_new:
            from collections import Counter
            active = Counter(mm["animal"] for mm in G["missions"].values())
            if shed.get("GOOSE", 0) > 0 and empty_coops and active["GOOSE"] < 2:
                animal = "GOOSE"
            elif shed.get("COW", 0) > 0 and empty_pastures and active["COW"] < 2:
                animal = "COW"
            else:
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
    for (x, y, t) in ctx["plants"]:
        crop = t["crop"]
        cd = CROPS[crop]
        age = day - t["planted_day"]
        if cd["ongoing"]:
            if t["yield_units"] >= 2 or (t["yield_units"] >= 1 and G["endgame"]):
                tasks.append((6, "HARVEST", x, y, None))
        else:
            ready = (t["yield_units"] >= FULL_YIELD.get(crop, 4)
                     or age >= cd["max_yield_day"]
                     or (t["yield_units"] > 0 and G["endgame"]))
            if ready:
                tasks.append((8, "HARVEST", x, y, None))
                continue
        if not t["watered_today"]:
            urg = 10 if t["consecutive_unwatered"] >= 1 else 6
            tasks.append((urg, "WATER", x, y, None))
    for (x, y) in ctx["weeds"]:
        tasks.append((3, "DIG", x, y))
    # planned structures (coops first: geese are the early cash engine)
    if not G["endgame"]:
        if ctx["n_coops"] < MAX_GEESE:
            for (x, y) in ctx["empty"]:
                if (x, y) in COOP_SPOTS_NW:
                    tasks.append((7, "BUILD_COOP", x, y, None))
        if "SW" in unlocked and ctx["n_pastures"] < MAX_COWS:
            for (x, y) in ctx["empty"]:
                if (x, y) in PASTURE_SPOTS_SW:
                    tasks.append((7, "BUILD_PASTURE", x, y, None))
    # planting — gated by how much watering capacity the workers have
    if len(ctx["plants"]) < ctx["plant_capacity"]:
        melon_q = _melon_target(day, unlocked)
        for (x, y) in ctx["empty"]:
            if (x, y) in COOP_SPOTS_NW or (x, y) in PASTURE_SPOTS_SW:
                continue
            q = ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
            if melon_q and q == melon_q and seeds.get("MELON", 0) > 0:
                tasks.append((5, "PLANT", x, y, "MELON"))
            elif day <= 24 and seeds.get("WHEAT", 0) > 0:
                tasks.append((5, "PLANT", x, y, "WHEAT"))
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
    ctx = {
        "plants": plants, "animals": animals, "weeds": weeds, "empty": empty,
        "empty_coops": empty_coops, "empty_pastures": empty_pastures,
        "unlocked": unlocked,
        "geese_total": sum(1 for (_, _, t) in animals if t["animal"] == "GOOSE"),
        "cows_total": sum(1 for (_, _, t) in animals if t["animal"] == "COW"),
    }
    ctx["n_coops"] = len(empty_coops) + ctx["geese_total"]
    ctx["n_pastures"] = len(empty_pastures) + ctx["cows_total"]
    # how many plants the current workforce can keep watered each day
    n_units_now = 1 + len(me["hands"])
    keepers_now = min(n_units_now, (len(animals) + 2) // 3)
    ctx["plant_capacity"] = max(6, (n_units_now - keepers_now) * 14)

    # melon wave bookkeeping: once a quadrant's melons are all harvested,
    # mark the wave done (NE first, then SE)
    if seeds.get("MELON", 0) >= 20 or G["melon_waves"]["NE"] >= 1:
        G["melon_secured"] = True
    for quad, (x0, x1, y0, y1) in (("NE", (5, 9, 0, 4)), ("SE", (5, 9, 5, 9))):
        if quad in unlocked and _melon_target(day, unlocked) != quad and G["melon_waves"][quad] < 2:
            mel = [p for p in plants
                   if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and p[2]["crop"] == "MELON"]
            emp = [e for e in empty if x0 <= e[0] <= x1 and y0 <= e[1] <= y1]
            # wave over: no melons growing, none left to plant, day past earliest harvest
            if day > 12 and not mel and seeds.get("MELON", 0) == 0:
                G["melon_waves"][quad] += 1

    orders = _market_orders(obs, me, priv, ctx, day, hour)

    # keeper routes: rebuild at hour 1 (today's hands have arrived by then;
    # at hour 0 the hands list is always empty). Drop routes for dead hands.
    n_units = 1 + len(me["hands"])
    if hour == 1 or (hour == 0 and G.get("_keepers_day") != day):
        G["keepers"] = {}
        G["missions"] = {}
        if animals:
            # cluster by quadrant so a keeper never walks NW<->SW in one route
            tiles_sorted = sorted(animals,
                                  key=lambda a: (a[1] // 5, a[0] // 5, a[1], a[0]))
            n_keepers = min(n_units, (len(tiles_sorted) + 3) // 4)
            per = (len(tiles_sorted) + n_keepers - 1) // n_keepers
            for k in range(n_keepers):
                G["keepers"][k] = [(x, y) for (x, y, _) in tiles_sorted[k * per:(k + 1) * per]]
        G["_keepers_day"] = day
    G["keepers"] = {k: v for k, v in G["keepers"].items() if k < n_units}
    G["missions"] = {k: v for k, v in G["missions"].items() if k < n_units}

    # ---------------- unit actions ---------------------------------------
    tasks = _worker_tasks(day, ctx, seeds)
    tasks.sort(key=lambda t: -t[0])
    task_by_key = {(t[1], t[2], t[3]): t for t in tasks}
    claimed = set()
    plant_budget = {c: seeds.get(c, 0) for c in CROPS}
    if hour == 0 or "sticky" not in G:
        G["sticky"] = {}

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
            # sticky target: keep walking to yesterday's... last turn's task
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
