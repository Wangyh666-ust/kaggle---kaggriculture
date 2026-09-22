"""Attribute each online replay to the tape route ``main.py`` actually replayed.

``main.py`` is a tape chassis: ``_router`` returns route 0 until step 143 and then
picks a route at step 144 (= day 6, hour 0) from the first two unlocked town
shops.  This script recovers that route two independent ways:

  (a) *logic*  — replicate ``_router`` on the day-6 ``town.unlocked_shops`` pair
                 (optionally refined with the step-2 rival key);
  (b) *match*  — count how many steps in a window the observed main-farmer op
                 equals each route tape's main-farmer op, and take the argmax.

Agreement between (a) and (b) is the check that the mechanism is real.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_routes.py \
        [--dirs replays_v23:.scratch_ed/replays_v24:.scratch_ed/replays_v24r] \
        [--json results/early_death_routes.json] [--lo 150] [--hi 719]
"""
import argparse
import collections
import importlib.util
import json
import os
import sys

OUR_NAME = "ReD_MooN_rise"


def load_main(path="main.py"):
    spec = importlib.util.spec_from_file_location("kaggri_main", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["kaggri_main"] = mod
    spec.loader.exec_module(mod)
    return mod


def router_decision(m, shops, rkey=None):
    """Replicate main.py:_router's step-144 branch (returns route id + expert tag)."""
    shops = tuple(shops)
    use_new = shops.count("YARN_STORE") <= 0
    expert = "EXP240" if use_new else "V39"
    route = (m._R108_SHOP_ROUTES.get(shops, 100) if use_new
             else m._R110_OLD_SHOPS.get(shops, 0))
    route = m._V92_TABLE.get(shops, route)
    if "YARN_STORE" in shops and rkey in m._V93_ROUTE_BY_RIVAL:
        route = m._V93_ROUTE_BY_RIVAL[rkey]
    return route, expert


def op_key(act):
    if not isinstance(act, dict):
        return None
    farmer = act.get("farmer")
    if not isinstance(farmer, list) or not farmer:
        return None
    key = [str(farmer[0])]
    if len(farmer) >= 2:
        key.append(str(farmer[1]))
    return "|".join(key)


def match_route(steps, us, routes, lo, hi, offset=-1, discriminating=True):
    """Score each route tape against the observed actions.

    The route tables in ``main.py`` are stored one step early (``tape[t-1]`` is
    the action for game step ``t``, which is what the replays show), hence
    ``offset=-1``.  With ``discriminating`` the score only counts steps where
    the candidate route's op differs from at least one other route's op, which
    is what actually identifies a route; without it every route scores ~0.97
    because the tapes share most of their steps.
    """
    obs_ops = {}
    for step in range(lo, min(hi + 1, len(steps))):
        entry = steps[step][us]
        if not isinstance(entry, dict):
            continue
        got = op_key(entry.get("action"))
        if got is not None:
            obs_ops[step] = got
    if not obs_ops:
        return {}, {}, 0

    tape_ops = {}
    for rid, tape in routes.items():
        for step in obs_ops:
            j = step + offset
            if 0 <= j < len(tape):
                op = op_key(tape[j])
                if op is not None:
                    tape_ops[(rid, step)] = op

    per_step_ops = {}
    for (rid, step), op in tape_ops.items():
        per_step_ops.setdefault(step, set()).add(op)

    raw = {}
    disc = {}
    for rid in routes:
        hits = tot = dhits = dtot = 0
        for step, got in obs_ops.items():
            op = tape_ops.get((rid, step))
            if op is None:
                continue
            tot += 1
            hits += op == got
            if discriminating and len(per_step_ops.get(step, ())) == 1:
                continue
            dtot += 1
            dhits += op == got
        if tot:
            raw[rid] = hits / tot
        if dtot:
            disc[rid] = dhits / dtot
    return raw, disc, len(obs_ops)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", default="replays_v23:.scratch_ed/replays_v24:"
                                     ".scratch_ed/replays_v24r")
    ap.add_argument("--json", default="results/early_death_routes.json")
    ap.add_argument("--main", default="main.py")
    ap.add_argument("--lo", type=int, default=150)
    ap.add_argument("--hi", type=int, default=719)
    ap.add_argument("--offset", type=int, default=-1,
                    help="tape index offset vs game step (tables are stored 1 step early)")
    args = ap.parse_args()

    m = load_main(args.main)
    routes = m._ROUTES
    print("routes=%d  main.py settings=%s" % (len(routes), m._SETTINGS), file=sys.stderr)

    out = []
    dirs = [d for d in args.dirs.split(":") if d]
    for d in dirs:
        if not os.path.isdir(d):
            print("!! missing dir %s" % d, file=sys.stderr)
            continue
        for name in sorted(os.listdir(d)):
            if not (name.startswith("episode-") and name.endswith("-replay.json")):
                continue
            path = os.path.join(d, name)
            with open(path, encoding="utf-8") as fh:
                rp = json.load(fh)
            names = list(rp["info"]["TeamNames"])
            if OUR_NAME not in names or names[0] == names[1]:
                continue
            us = names.index(OUR_NAME)
            opp = 1 - us
            steps = rp["steps"]
            # day-6 shop pair (first unlock is at end of day 2 -> day 3 h0,
            # second at end of day 5 -> day 6 h0, exactly when the router fires)
            shops_d6 = []
            obs144 = steps[144][us].get("observation")
            if obs144:
                shops_d6 = list((obs144.get("town") or {}).get("unlocked_shops") or [])
            obs2 = steps[2][us].get("observation")
            rkey = None
            if obs2:
                rv = obs2["farms"][opp]
                try:
                    rkey = (round(float(rv["money"]), 3),
                            int(obs2["market"]["inventory"]["WHEAT"]))
                except Exception:                        # noqa: BLE001
                    rkey = None
            logic_route, expert = router_decision(m, shops_d6[:2], rkey)
            ratios, disc, n_obs = match_route(steps, us, routes, args.lo, args.hi,
                                              offset=args.offset)
            ranked = sorted(disc.items(), key=lambda kv: -kv[1])
            best_id = ranked[0][0] if ranked else None
            second = disc.get(logic_route) if ranked else None
            # a route is "identified" when the best score also matches the router
            margin = (ranked[0][1] - ranked[1][1]) if len(ranked) > 1 else None
            rec = {
                "dir": os.path.basename(d),
                "ep": int(rp["info"]["EpisodeId"]),
                "opp": names[opp],
                "reward_us": float(rp["rewards"][us]),
                "reward_opp": float(rp["rewards"][opp]),
                "margin": float(rp["rewards"][us]) - float(rp["rewards"][opp]),
                "win": float(rp["rewards"][us]) > float(rp["rewards"][opp]),
                "shops_d6": shops_d6,
                "shops_pair": list(shops_d6[:2]),
                "rkey": list(rkey) if rkey else None,
                "expert": expert,
                "logic_route": logic_route,
                "match_route": best_id,
                "disc_score": ranked[0][1] if ranked else None,
                "logic_score": second,
                "score_margin": margin,
                "raw_score": ratios.get(best_id),
                "runner_up": ranked[1][0] if len(ranked) > 1 else None,
                "runner_up_score": ranked[1][1] if len(ranked) > 1 else None,
                "n_obs_steps": n_obs,
                "top5": [[r, round(v, 4)] for r, v in ranked[:5]],
            }
            out.append(rec)
            print("ep%-10d %-6s shops=%-24s logic=%-4s match=%-4s disc=%.3f "
                  "logic_disc=%s%s" % (
                      rec["ep"], "WIN" if rec["win"] else "LOSS",
                      ",".join(rec["shops_pair"]), rec["logic_route"], rec["match_route"],
                      rec["disc_score"] or 0,
                      "%.3f" % second if second is not None else "-",
                      "" if rec["logic_route"] == rec["match_route"] else "  <-- MISMATCH"),
                  file=sys.stderr)

    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    agree = sum(1 for r in out if r["logic_route"] == r["match_route"])
    print("wrote %s (%d episodes, logic==match on %d/%d)"
          % (args.json, len(out), agree, len(out)))


if __name__ == "__main__":
    main()
