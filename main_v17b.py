"""Kaggriculture agent — v11 (opponent-template + counter-play).

Strategy overview (from replay analysis of $100k+ leaderboard agents)
-----------------
All-in start : day 0 spends ~$3000 on 2 cows + 2 sheep (NW pastures, no land
               needed), melon seeds and hands.  Cash stays near zero for a
               week — that is the point; every animal also drops 1
               fertilizer/day, which is the early cash bridge.
Melon bridge : 10 melons on NW (days 0-3, harvested early at day 9-10 before
               the opponent's wave crashes the shared price); a second NE wave
               (days 12-16) is skipped if the opponent runs a big melon wave.
Herd         : 4 cows + 5 sheep core, +2 cows per milk-draining shop and
               +2 sheep per yarn store (caps 10/10).  Fed+cared daily, a cow
               pays 3 milk/2d and a sheep 4 wool/3d.
Strawberries : 12 + 4 per strawberry-draining shop (cap 32), fertilized
               through their production window (doubles scheduled yields).
Wheat        : feeds the herd; surplus is stockpiled and sold into the
               late-season town scarcity ($45+).
Counter-play : the opponent's farm is public — if they flood a channel
               (strawberries/melons), we cut our own exposure to it.
Market       : sells every turn (hour>0), premium unit-price first; purchases
               at hour 0/12 with the hire budget reserved before any
               discretionary spend.  Feed wheat is budgeted at the real price.
Labor        : hire-first ordering, up to 13 hands/day, hired through the
               final day (collection never goes dark).
Endgame      : day 28+ — stop investment, liquidate everything.

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
# first_yield_day / interval: used to value an animal bought on a given day
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "product": "EGG",  "harvest_at": 2,
              "first_yield_day": 4, "interval": 1, "care_yield": 2},
    "COW":   {"cost": 400, "structure": "PASTURE", "product": "MILK", "harvest_at": 3,
              "first_yield_day": 8, "interval": 2, "care_yield": 3},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "product": "WOOL", "harvest_at": 4,
              "first_yield_day": 6, "interval": 3, "care_yield": 4},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"]
I0 = 10000

TURNS_PER_DAY = 24
SEASON_DAYS = 30
BOARD = 10
CENTER = [(4, 4), (5, 4), (4, 5), (5, 5)]  # shed-access tiles

# ---- production plan -------------------------------------------------------
# Template from board analysis of $110k agents: all-in livestock from day 0
# (pastures go straight on NW — no land purchase needed), no geese, strawberry
# waves as the crop backbone, heavy labor.
GEESE_TARGET = 0
COW_CORE = 4                 # base herd, viable even with no milk shops
SHEEP_CORE = 5               # wool lands day 6 — earliest premium income
COW_MAX = 10                 # +2 per milk-draining shop (pizza/ice cream/smoothie)
SHEEP_MAX = 10               # +2 per yarn store
# The herd is capped by what we can STAFF: every animal needs a keeper, and
# keepers are units that cannot plant. Measured throughput: ~3 animals per
# keeper route, ~8 crops per worker per day.
HERD_MAX = 18
KEEPER_PER = 3
WORKERS_PER_CROP = 8
WORKER_CAP = 10

# structure spots, laid out in tight rows so keeper routes stay short.
# NW pastures exist from day 0; SW pastures wait for the land purchase.
PASTURE_SPOTS_NW = [(4, 3), (3, 3), (4, 2), (3, 2), (2, 3), (4, 1), (3, 4), (2, 4)]
PASTURE_SPOTS_SW = [(3, 5), (2, 5), (1, 5), (0, 5),
                    (4, 6), (3, 6), (2, 6), (1, 6),
                    (0, 6), (4, 7), (3, 7), (2, 7), (1, 7)]
COOP_SPOTS = [(1, 2), (2, 1), (0, 2), (0, 3)]  # only used if eggs get scarce

# crops: melons bridge the early cash crunch (NW wave planted day 0-3,
# harvested day 10-12 into a NE wave day 12-16); strawberries are the
# backbone (scaled by how many shops drain them); wheat feeds the herd and
# sells late into town scarcity.
STRAWBERRY_DAYS = (2, 14)
MELON_WAVES = [("NW", (0, 3), 6), ("NE", (12, 16), 6)]
# tomato line: the head meta's late channel (deep market T=200, hinge price,
# drained by pizza shops + farmers markets).  Only worth opening when the town
# actually demands it and we have spare cash/labour.
TOMATO_DAYS = (11, 16)
TOMATO_TILES = 10
TOMATO_MIN_PRICE = 70
TOMATO_MIN_DEMAND = 2        # PIZZA_SHOP + FARMERS_MARKET instances

FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
HAND_CAP = 13                # hires per day (farmer + 13 = 14 units)

# fertilize strawberries through their production window (each application
# covers 3 days and doubles scheduled yields; +4 units/plant for 2 apps)
FERT_HOLD_DAYS = (8, 16)     # stop selling fertilizer, stockpile for own use
FERT_KEEP = 15               # shed stock reserved for strawberry fertilizing
CARROT_WAVE_DAYS = (20, 25)  # late quick-cycle carrot wave on spare tiles
CARROT_WAVE_TILES = 8

WHEAT_SEED_BUF = 30

# ---------------------------------------------------------------- state
G = {}


def _reset():
    G.clear()
    G.update({
        "turn": -1,
        "keepers": {},          # unit_idx -> [(x, y), ...] animal route (today)
        "missions": {},         # unit_idx -> animal-placement mission
        "fert_missions": {},    # unit_idx -> strawberry-fertilizing mission
        "sticky": {},           # unit_idx -> last worker task key
        "keep_hired": 0,
        "prev_inv": None,       # last turn's market inventory (for rival reconstruction)
        "prev_our_sold": {},    # what we sold last turn
        "rival_sold": {},       # inferred opponent sells last turn
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


# town shop demand table (from the environment's shop list): each unlocked shop
# instance consumes its recipe every 4 turns; single-product shops consume 2.
SHOP_RECIPES = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
SHOP_INTERVAL = 4
CENTER_INTERVAL = 24


def _town_draw(step, shops):
    """What the town removes from market inventory at this step."""
    draw = {}
    if step % SHOP_INTERVAL == 0:
        for s in shops:
            recipe = SHOP_RECIPES.get(s, ())
            w = 2 if len(recipe) == 1 else 1
            for it in recipe:
                draw[it] = draw.get(it, 0) + w
    if step % CENTER_INTERVAL == 0:
        for it in PRODUCTS:
            if it != "FERTILIZER":
                draw[it] = draw.get(it, 0) + 1
    return draw


def _feed_reserve(day, n_animals):
    if day >= SEASON_DAYS - 1:
        return n_animals            # last day: only what keepers actually need
    if day >= 27:
        return n_animals + 2
    return n_animals + 6           # ~1 day of cover; shed space is precious


def _remaining_value(kind, day, price):
    """Expected gross revenue of placing an animal today, at today's price.

    A cow placed on day d first milks on day d+8, then every 2 days; a sheep
    on d+6 then every 3 — so late purchases are worth steadily less. This is
    the price-aware replacement for hard "buy until day N" gates.
    """
    a = ANIMALS[kind]
    n, d = 0, day + a["first_yield_day"]
    while d <= SEASON_DAYS - 2:
        n += 1
        d += a["interval"]
    return n * a["care_yield"] * price


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
        # ---- hire plan FIRST: hands are the cheapest ROI in the game, and
        # skipping them (broke after land/animal buys) idles the whole farm.
        # Reserve their budget before any discretionary purchase.
        pipeline = sum(shed.get(a, 0) + ctx["carry"].get(a, 0) for a in ANIMALS)
        keepers_needed = (n_animals + pipeline + KEEPER_PER - 1) // KEEPER_PER
        # Staff for the land we INTEND to work, not for what is already planted:
        # the old formula was a deadlock (few crops -> no hands -> few crops).
        # Measured throughput is ~8 crops per worker per day.
        workers_needed = int(min(WORKER_CAP, ctx["plan_crops"] // WORKERS_PER_CROP))
        if endgame:
            workers_needed = min(workers_needed, 1)
        want = min(1 + HAND_CAP, 1 + keepers_needed + workers_needed)
        cur = 1 + len(me["hands"])
        n_hire = me["hires_today"]
        hire_plan = 0
        hire_cost = 0
        while cur + hire_plan < want and n_hire + hire_plan < HAND_CAP:
            hire_cost += FIB[n_hire + hire_plan]
            hire_plan += 1
        if money < hire_cost + 60:          # too broke: shrink the plan
            while hire_plan and money < hire_cost + 60:
                hire_plan -= 1
                hire_cost -= FIB[n_hire + hire_plan]
        money -= hire_cost                  # reserved; spent when orders fire

        # ---- feed wheat: survival-critical, before everything else ----
        reserve = _feed_reserve(day, n_animals)
        room = 100 - shed_total
        wheat_price = max(1, prices.get("WHEAT", 30))
        if n_animals and wheat_total < reserve and money > 100 and room > 10:
            bn = int(min(reserve - wheat_total + n_animals, 30, room - 5,
                         (money - 100) // wheat_price))
            if bn > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", bn]); money -= wheat_price * bn

        # ---- buy cheap fertilizer for the strawberry window (own herd only
        # ramps production later; each fertilized plant pays ~4x the cost) ----
        if (FERT_HOLD_DAYS[0] <= day <= FERT_HOLD_DAYS[1]
                and prices.get("FERTILIZER", 100) < 70
                and shed.get("FERTILIZER", 0) < 8 and money > 1500 and room > 10):
            bn = int(min(6, room - 5, (money - 1500) // max(1, prices.get("FERTILIZER", 60))))
            if bn > 0:
                orders.append(["BUY_PRODUCT", "FERTILIZER", bn])
                money -= prices.get("FERTILIZER", 60) * bn

        if not endgame:
            # ---- animals (shed -> structure via ferry missions) ----
            carry = ctx["carry"]
            if room > 4:
                ct = ctx["animal_total"]["COW"] + shed.get("COW", 0) + carry.get("COW", 0)
                st = ctx["animal_total"]["SHEEP"] + shed.get("SHEEP", 0) + carry.get("SHEEP", 0)
                gt = ctx["animal_total"]["GOOSE"] + shed.get("GOOSE", 0) + carry.get("GOOSE", 0)
                # opportunistic geese when eggs are scarce (town drains them,
                # nobody supplies -> hinge price shoots past $75)
                if ctx["geese_target"] and gt < min(ctx["geese_target"], ctx["n_coops"]) \
                        and money > 800:
                    orders.append(["BUY_ANIMAL", "GOOSE", 1]); money -= 300; room -= 1; gt += 1
                # alternate cows/sheep by whichever lags its target ratio.
                # Buying continues while the animal's *remaining* production at
                # today's price is worth clearly more than it costs — a soft,
                # price-aware gate instead of a fixed "buy until day N".
                # (A sheep-first opening was tried and measured worse: cows pay
                # 1.5 units/day vs 1.33, and turn-0 cash compounds into animals.)
                milk_px = prices.get("MILK", 160)
                wool_px = prices.get("WOOL", 200)
                cow_ok = _remaining_value("COW", day, milk_px) > 400 * 2
                sheep_ok = _remaining_value("SHEEP", day, wool_px) > 500 * 2
                # wool channel clearly richer -> sheep lead the balance
                prefer_sheep = wool_px >= milk_px * 1.25
                for _ in range(2):
                    lag_cow = ct / max(1, ctx["cow_target"]) * (1.4 if prefer_sheep else 1.0)
                    lag_sheep = st / max(1, ctx["sheep_target"])
                    kinds = ("COW", "SHEEP") if lag_cow <= lag_sheep else ("SHEEP", "COW")
                    bought = False
                    for kind in kinds:
                        if kind == "COW" and cow_ok and money > 400 \
                                and ct < min(ctx["cow_target"], ctx["n_pastures"]):
                            orders.append(["BUY_ANIMAL", "COW", 1]); money -= 400; room -= 1; ct += 1
                            bought = True
                            break
                        if kind == "SHEEP" and sheep_ok and money > 500 \
                                and st < min(ctx["sheep_target"], ctx["n_pastures"] - ct):
                            orders.append(["BUY_ANIMAL", "SHEEP", 1]); money -= 500; room -= 1; st += 1
                            bought = True
                            break
                    if not bought:
                        break

            # ---- hires before discretionary land/seeds: on crowded mornings
            # the 10-order cap drops seeds (deferrable), never hands ----
            slots = 10 - len(orders)
            for _ in range(min(hire_plan, slots)):
                orders.append(["HIRE"])

            # ---- land: NE expands crops, SW expands pastures; NW is free ----
            if "NE" not in unlocked and day >= 5 and money > 1100 and len(orders) < 10:
                orders.append(["BUY_LAND"]); money -= 1000
            elif "SW" not in unlocked and day >= 8 and money > 2400 and len(orders) < 10:
                orders.append(["BUY_LAND"]); money -= 2000

            # ---- seeds ----
            if day <= 24:
                need = int(min(max(0, WHEAT_SEED_BUF - seeds.get("WHEAT", 0)),
                               max(0, money - 300) // 10))
                if need > 0:
                    orders.append(["BUY_SEED", "WHEAT", need]); money -= 10 * need
            # melon waves: the NW wave is the early cash bridge (buy even when
            # nearly broke); the NE wave rides the still-warm price later
            for quad, (d0, d1), tiles in MELON_WAVES:
                if quad == "NE" and ctx["melon_wave2_skip"]:
                    continue
                if quad in unlocked and d0 <= day <= d1:
                    tiles = tiles * ctx.get("melon_boost", 1)
                    have = seeds.get("MELON", 0) + ctx["melons_growing"]
                    need = int(min(max(0, tiles - have), 6, max(0, money - 200) // 80))
                    if need > 0:
                        orders.append(["BUY_SEED", "MELON", need]); money -= 80 * need
                    break
            if STRAWBERRY_DAYS[0] <= day <= STRAWBERRY_DAYS[1] and money > 150:
                have = seeds.get("STRAWBERRY", 0) + ctx["strawberries_growing"]
                need = int(min(max(0, ctx["strawberry_target"] - have), 4,
                               max(0, money - 150) // 100))
                if need > 0:
                    orders.append(["BUY_SEED", "STRAWBERRY", need]); money -= 100 * need
            if CARROT_WAVE_DAYS[0] <= day <= CARROT_WAVE_DAYS[1] and money > 400:
                have = seeds.get("CARROT", 0) + ctx["carrots_growing"]
                need = int(min(max(0, CARROT_WAVE_TILES - have), 4, max(0, money - 400) // 20))
                if need > 0:
                    orders.append(["BUY_SEED", "CARROT", need]); money -= 20 * need
            # tomato line: only when the town demands it and cash is comfortable
            if ctx["tomato_line"]:
                have = seeds.get("TOMATO", 0) + ctx["tomatoes_growing"]
                need = int(min(max(0, TOMATO_TILES - have), 4, max(0, money - 2000) // 50))
                if need > 0:
                    orders.append(["BUY_SEED", "TOMATO", need]); money -= 50 * need
        else:
            # endgame days: keep hiring keepers for the final collection rounds
            slots = 10 - len(orders)
            for _ in range(min(hire_plan, slots)):
                orders.append(["HIRE"])

        return orders[:10]

    # ---- hour 12: top-up feed + catch-up hires if the morning was crowded ----
    if hour == 12:
        if not endgame:
            reserve = _feed_reserve(day, n_animals)
            room = 100 - shed_total
            wheat_price = max(1, prices.get("WHEAT", 30))
            if n_animals and wheat_total < reserve and money > 400 and room > 10:
                bn = int(min(reserve - wheat_total + n_animals, 30, room - 5,
                             (money - 300) // wheat_price))
                if bn > 0:
                    orders.append(["BUY_PRODUCT", "WHEAT", bn]); money -= wheat_price * bn
            # half-day catch-up hires, sized to the same work plan as the morning
            keepers_needed = (n_animals + KEEPER_PER - 1) // KEEPER_PER
            workers_needed = int(min(WORKER_CAP, ctx["plan_crops"] // WORKERS_PER_CROP))
            want = min(1 + HAND_CAP, 1 + keepers_needed + workers_needed)
            cur = 1 + len(me["hands"])
            n_hire = me["hires_today"]
            slots = 10 - len(orders)
            while cur < want and n_hire < 11 and slots > 0 and money > FIB[n_hire] + 300:
                orders.append(["HIRE"]); money -= FIB[n_hire]; n_hire += 1; cur += 1; slots -= 1

    # ---- sells (every turn) ----
    # The market clears both lists slot-by-slot, so being early matters most
    # for channels the opponent is about to dump.  Their ripe produce is public
    # (tiles are visible), so we boost exposure for channels they are sitting on.
    feed_res = _feed_reserve(day, n_animals)
    opp_ripe = ctx.get("opp_ripe", {})
    sells = []
    for item in PRODUCTS:
        qty = shed.get(item, 0)
        if qty <= 0:
            continue
        if item == "WHEAT":
            qty = max(0, qty - feed_res)
            if qty <= 0:
                continue
            # wheat only appreciates all season (town drains it): stockpile
            # once cash is comfortable, sell into the late scarcity price
            if day < 24 and prices.get("WHEAT", 25) < 45 and shed_total < 85 \
                    and day >= 10 and money > 2000:
                continue
        elif item == "FERTILIZER" and FERT_HOLD_DAYS[0] <= day <= FERT_HOLD_DAYS[1]:
            qty = max(0, qty - FERT_KEEP)  # stockpile for strawberry fertilizing
            if qty <= 0:
                continue
        score = qty * prices.get(item, 1)
        if opp_ripe.get(item, 0) >= 6:
            score *= 1.5      # they are sitting on ripe produce: dump incoming
        if ctx.get("rival_sold", {}).get(item, 0) >= 4:
            score *= 1.4      # they were already selling this channel last turn
        sells.append((score, item, qty))
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


# ------------------------------------------------------------- fert mission
def _fert_mission_action(idx, pos, inv, shed, fert_targets, allow_new):
    """Multi-turn mission: carry fertilizer to strawberry plants in their
    production window and FERTILIZE them (doubles scheduled yields).

    At most 2 concurrent missions; only idle (non-keeper) units start one.
    """
    m = G["fert_missions"].get(idx)
    if m is None:
        if not allow_new:
            return None
        active = sum(1 for mm in G["fert_missions"].values() if mm)
        if active >= 2 or not fert_targets:
            return None
        if inv.get("FERTILIZER", 0) <= 0 and shed.get("FERTILIZER", 0) <= 0:
            return None
        m = True
        G["fert_missions"][idx] = m

    if inv.get("FERTILIZER", 0) <= 0:
        if shed.get("FERTILIZER", 0) <= 0:
            G["fert_missions"].pop(idx, None)
            return None
        if _is_center(pos):
            return ["PICKUP", "FERTILIZER", min(4, shed.get("FERTILIZER", 0))]
        return _step_toward(pos, _nearest_center(pos))

    # still-valid targets only (someone may have fertilized them already)
    todo = [t for t in fert_targets]
    if not todo:
        G["fert_missions"].pop(idx, None)
        return None
    tgt = min(todo, key=lambda c: _dist(pos, c))
    if (pos[0], pos[1]) == tgt:
        return ["FERTILIZE"]
    return _step_toward(pos, tgt)


def _courier_action(pos, inv, prices):
    """Idle worker carrying sellable goods: walk to the shed and DROP.

    SELL only sees the shed, and the midnight auto-drop means carried goods
    miss the same evening's market.  Only worth a detour when the load is
    valuable or the unit is already close to the shed.
    """
    carrying = sum(inv.get(i, 0) for i in PRODUCTS if i != "WHEAT")
    if carrying <= 0:
        return None
    if _is_center(pos):
        return ["DROP"]
    value = sum(inv.get(i, 0) * prices.get(i, 25) for i in PRODUCTS if i != "WHEAT")
    if value >= 300 and _dist(pos, _nearest_center(pos)) <= 5:
        return _step_toward(pos, _nearest_center(pos))
    return None


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
        if cd["ongoing"]:  # STRAWBERRY: 4 scheduled yields, then decays
            if t["yield_units"] >= 2 or (endgame and t["yield_units"] > 0):
                tasks.append((8, "HARVEST", x, y, None))
                continue
        elif crop == "MELON":
            # harvest a touch early: in head-to-head the opponent's melon wave
            # crashes the shared price within a day or two
            if t["yield_units"] >= 5 or age >= 10 or (endgame and t["yield_units"] > 0):
                tasks.append((8, "HARVEST", x, y, None))
                continue
        else:  # WHEAT / CARROT (one-time)
            if t["yield_units"] >= 3 and crop == "CARROT" or \
                    t["yield_units"] >= 4 and crop == "WHEAT" or \
                    age >= cd["max_yield_day"] or (endgame and t["yield_units"] > 0):
                tasks.append((8, "HARVEST", x, y, None))
                continue
        if not t["watered_today"]:
            urg = 10 if t["consecutive_unwatered"] >= 1 else 6
            tasks.append((urg, "WATER", x, y, None))
    for (x, y) in ctx["weeds"]:
        # weeds only matter where they block a plan; clearing a random far
        # tile is a wasted trip unless labour is genuinely idle
        blocking = (x, y) in COOP_SPOTS or (x, y) in PASTURE_SPOTS_NW \
            or (x, y) in PASTURE_SPOTS_SW or len(ctx["empty"]) < 5
        tasks.append((6 if blocking else 2, "DIG", x, y, None))

    if not endgame:
        empty_set = ctx["empty_set"]
        if ctx["n_pastures"] < ctx["cow_target"] + ctx["sheep_target"]:
            for (x, y) in PASTURE_SPOTS_NW:
                if (x, y) in empty_set:
                    tasks.append((7, "BUILD_PASTURE", x, y, None))
            if "SW" in unlocked:
                for (x, y) in PASTURE_SPOTS_SW:
                    if (x, y) in empty_set:
                        tasks.append((7, "BUILD_PASTURE", x, y, None))
        if ctx["n_coops"] < ctx["geese_target"]:
            for (x, y) in COOP_SPOTS:
                if (x, y) in empty_set:
                    tasks.append((7, "BUILD_COOP", x, y, None))
        # planting, gated by watering capacity
        if len(ctx["plants"]) < ctx["plant_capacity"]:
            # melon waves (short windows; planting them outranks routine work)
            for quad, (d0, d1), tiles in MELON_WAVES:
                if quad == "NE" and ctx["melon_wave2_skip"]:
                    continue
                tiles = tiles * ctx.get("melon_boost", 1)
                if quad in unlocked and d0 <= day <= d1 and seeds.get("MELON", 0) > 0 \
                        and ctx["melons_growing"] + ctx["melon_claimed"] < tiles:
                    for (x, y) in ctx["empty"]:
                        if _quad(x, y) == quad and (x, y) not in PASTURE_SPOTS_NW:
                            tasks.append((9, "PLANT", x, y, "MELON"))
                    break
            # strawberries: our best channel per unit (realised 1.79x base), so
            # they take land first — no quadrant is fenced off any more
            if STRAWBERRY_DAYS[0] <= day <= STRAWBERRY_DAYS[1] \
                    and seeds.get("STRAWBERRY", 0) > 0 \
                    and ctx["strawberries_growing"] < ctx["strawberry_target"]:
                for (x, y) in ctx["empty"]:
                    if (x, y) in PASTURE_SPOTS_NW or (x, y) in PASTURE_SPOTS_SW:
                        continue
                    tasks.append((8, "PLANT", x, y, "STRAWBERRY"))
            if day <= 24 and seeds.get("WHEAT", 0) > 0:
                for (x, y) in ctx["empty"]:
                    if (x, y) in PASTURE_SPOTS_NW or (x, y) in PASTURE_SPOTS_SW:
                        continue
                    tasks.append((5, "PLANT", x, y, "WHEAT"))
            # late carrot wave: 3-day quick cycle into the pet-cafe/farmers drain
            if CARROT_WAVE_DAYS[0] <= day <= CARROT_WAVE_DAYS[1] \
                    and seeds.get("CARROT", 0) > 0 \
                    and ctx["carrots_growing"] < CARROT_WAVE_TILES:
                for (x, y) in ctx["empty"]:
                    if (x, y) in PASTURE_SPOTS_NW or (x, y) in PASTURE_SPOTS_SW:
                        continue
                    tasks.append((5, "PLANT", x, y, "CARROT"))
            # tomato line: the deep, town-drained channel the head meta runs
            if ctx["tomato_line"] and seeds.get("TOMATO", 0) > 0 \
                    and ctx["tomatoes_growing"] < TOMATO_TILES:
                for (x, y) in ctx["empty"]:
                    if (x, y) in PASTURE_SPOTS_NW or (x, y) in PASTURE_SPOTS_SW:
                        continue
                    tasks.append((7, "PLANT", x, y, "TOMATO"))
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

    # ---- infer what the opponent sold last turn -------------------------
    # rival_sold = Δinventory + town draw − our own sales. The town draw is
    # deterministic (shops every 4 turns, centre every 24), so what is left
    # over is the opponent's selling — a leading-ish signal for their dumps.
    shops_now = obs.get("town", {}).get("unlocked_shops", [])
    inv_now = obs["market"]["inventory"]
    if G.get("prev_inv"):
        draw = _town_draw(turn - 1, shops_now)
        ours = G.get("prev_our_sold", {})
        G["rival_sold"] = {it: inv_now.get(it, 0) - G["prev_inv"].get(it, 0)
                           + draw.get(it, 0) - ours.get(it, 0) for it in PRODUCTS}
    else:
        G["rival_sold"] = {}

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
    straw_shops = sum(1 for s in shops if s in
                      ("BRUNCH_SPOT", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "FARMERS_MARKET"))
    # note: counter-reading the opponent's crop channels (cutting our exposure
    # when they flood one) was tested and HURTS — the shared price crashes from
    # their supply regardless, so skipping the channel just forfeits our share.
    # opponent's ripe produce is public — used to order our sells and to know
    # which channels they are about to dump
    opp_ripe = {}
    opp_melons = 0
    for row in obs["farms"][1 - player]["tiles"]:
        for t in row:
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0:
                opp_ripe[t["crop"]] = opp_ripe.get(t["crop"], 0) + t["yield_units"]
            elif "animal" in t and t.get("yield_units", 0) > 0:
                prod = ANIMALS[t["animal"]]["product"]
                opp_ripe[prod] = opp_ripe.get(prod, 0) + t["yield_units"]
            if t.get("kind") == "PLANT" and t.get("crop") == "MELON":
                opp_melons += 1

    # strawberry scale follows both shop demand and the live price: when the
    # channel is already crushed we stop adding instead of feeding the glut
    straw_price = obs["market"]["prices"].get("STRAWBERRY", 120)
    strawberry_target = max(10, min(32, 12 + 4 * straw_shops))
    if straw_price < 110:
        strawberry_target = min(strawberry_target, 20)
    if straw_price < 90:
        strawberry_target = 0
    # second melon wave only if the price is still healthy (soft signal, not law)
    melon_wave2_skip = obs["market"]["prices"].get("MELON", 250) < 200
    # melon scale is opponent-driven: alone, our own wave crashes our own price
    # (measured: 6+6 beats 10+12 vs a passive opponent), but when the opponent
    # is running a melon wave the channel is doomed anyway and planting more
    # free-rides on their crash (measured: 10+12 beats 6+6 head-to-head).
    melon_boost = 2 if opp_melons >= 6 else 1
    # tomato line gate: town demand + price + cash, all three must line up
    tomato_shops = sum(1 for s in shops if s in ("PIZZA_SHOP", "FARMERS_MARKET"))
    tomato_line = (TOMATO_DAYS[0] <= day <= TOMATO_DAYS[1]
                   and obs["market"]["prices"].get("TOMATO", 60) >= TOMATO_MIN_PRICE
                   and tomato_shops >= TOMATO_MIN_DEMAND
                   and me["money"] > 5000)
    # herd targets are shop-reactive but capped by what we can staff: every
    # animal needs a keeper, and keepers are units that cannot work crops
    cow_t = min(COW_MAX, COW_CORE + 2 * milk_shops)
    sheep_t = min(SHEEP_MAX, SHEEP_CORE + 2 * yarn_shops)
    if cow_t + sheep_t > HERD_MAX:
        scale = HERD_MAX / float(cow_t + sheep_t)
        cow_t = max(2, int(cow_t * scale))
        sheep_t = max(2, int(sheep_t * scale))
    ctx = {
        "plants": plants, "animals": animals, "weeds": weeds, "empty": empty,
        "empty_set": set(empty),
        "empty_coops": empty_coops, "empty_pastures": empty_pastures,
        "unlocked": unlocked, "carry": carry, "animal_total": animal_total,
        "opp_ripe": opp_ripe,
        "rival_sold": G.get("rival_sold", {}),
        "melons_growing": sum(1 for (_, _, t) in plants if t["crop"] == "MELON"),
        "melon_boost": melon_boost,
        "strawberries_growing": sum(1 for (_, _, t) in plants if t["crop"] == "STRAWBERRY"),
        "carrots_growing": sum(1 for (_, _, t) in plants if t["crop"] == "CARROT"),
        "tomatoes_growing": sum(1 for (_, _, t) in plants if t["crop"] == "TOMATO"),
        "tomato_line": tomato_line,
        "melon_claimed": 0,
        "strawberry_target": strawberry_target,
        "melon_wave2_skip": melon_wave2_skip,
        "cow_target": cow_t,
        "sheep_target": sheep_t,
        # land we could realistically work (structure spots stay reserved)
        "plan_crops": min(72, len(plants) + sum(
            1 for e in empty if e not in PASTURE_SPOTS_NW and e not in PASTURE_SPOTS_SW)),
        # opportunistic geese when eggs run scarce (hinge price past $75)
        "geese_target": 4 if (obs["market"]["prices"].get("EGG", 50) > 75
                              and 6 <= day <= 20) else 0,
    }
    # strawberry plants in their production window that aren't fertilized yet
    ctx["fert_targets"] = [(x, y) for (x, y, t) in plants
                           if t["crop"] == "STRAWBERRY"
                           and 9 <= day - t["planted_day"] <= 16
                           and t.get("fertilized_until_day", -1) < day]
    ctx["n_coops"] = len(empty_coops) + animal_total["GOOSE"]
    ctx["n_pastures"] = len(empty_pastures) + animal_total["COW"] + animal_total["SHEEP"]

    n_units = 1 + len(me["hands"])
    routes_preview = _build_routes(animals, n_units) if animals else []
    keepers_now = len(routes_preview)
    ctx["plant_capacity"] = max(10, (n_units - keepers_now) * 8)

    orders = _market_orders(obs, me, priv, ctx, day, hour)
    # remember this turn's market state so next turn we can infer the
    # opponent's sales (market inventory + deterministic town draw)
    G["prev_inv"] = dict(inv_now)
    G["prev_our_sold"] = {o[1]: o[2] for o in orders
                          if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL"}

    # keeper routes: rebuild at hour 1 (today's hands have arrived by then;
    # at hour 0 the hands list is always empty, so hour 0 keeps yesterday's
    # routes — only the farmer is around and it services its old route).
    if hour == 1 or G.get("_keepers_day") != day and hour > 1:
        G["keepers"] = {}
        G["missions"] = {}
        G["fert_missions"] = {}
        if animals:
            for k, route in enumerate(_build_routes(animals, n_units)):
                G["keepers"][k] = route
        G["_keepers_day"] = day
    G["keepers"] = {k: v for k, v in G["keepers"].items() if k < n_units}
    G["missions"] = {k: v for k, v in G["missions"].items() if k < n_units}
    G["fert_missions"] = {k: v for k, v in G["fert_missions"].items() if k < n_units}

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
            act = _fert_mission_action(idx, pos, inv, shed, ctx["fert_targets"], allow_new)
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
            act = _courier_action(pos, inv, obs["market"]["prices"])
        if act is None:
            act = ["PASS"]
        if idx == 0:
            farmer_act = act
        else:
            hand_acts.append(act)

    return {"farmer": farmer_act, "hands": hand_acts, "market": orders}
