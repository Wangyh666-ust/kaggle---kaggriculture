"""Mirror-match scan: how much of an online game is our own tape vs the opponent's?

``main.py`` is a tape chassis, and most online opponents replay the same public
route family.  For every replay this measures, over steps 150..719 (i.e. after
the day-6 route switch):

  unit_identity  fraction of steps where our (farmer, hands) ops equal theirs
  market_identity fraction of steps where our market orders equal theirs
  mkt_events     steps with identical unit ops but different market orders
                 (these are the only places a mirror match can be decided)

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_mirror.py \
        --dirs replays_v23:.scratch_ed/replays_v24:.scratch_ed/replays_v24r \
        --json results/early_death_mirror.json
"""
import argparse
import collections
import json
import os
import sys

OUR_NAME = "ReD_MooN_rise"
LO, HI = 150, 719


def unit_sig(entry, seat):
    act = (entry[seat] or {}).get("action") or {}
    return (tuple(act.get("farmer") or ()),
            tuple(tuple(x) for x in (act.get("hands") or [])))


def mkt_sig(entry, seat):
    act = (entry[seat] or {}).get("action") or {}
    return tuple(tuple(o) for o in (act.get("market") or []))


def scan(path):
    rp = json.load(open(path, encoding="utf-8"))
    names = list(rp["info"]["TeamNames"])
    if names[0] == names[1] or OUR_NAME not in names:
        return None
    us = names.index(OUR_NAME)
    opp = 1 - us
    steps = rp["steps"]
    same_u = same_m = tot = 0
    mkt_events = []
    wheat_u = wheat_o = 0
    fish_u = fish_o = 0
    money = []
    for t in range(LO, min(HI + 1, len(steps))):
        su, so = unit_sig(steps[t], us), unit_sig(steps[t], opp)
        mu, mo = mkt_sig(steps[t], us), mkt_sig(steps[t], opp)
        tot += 1
        same_u += su == so
        same_m += mu == mo
        if su == so and mu != mo:
            mkt_events.append({
                "step": t, "day": t // 24, "hour": t % 24,
                "us": [list(o) for o in mu], "them": [list(o) for o in mo],
            })
        for o in mu:
            if len(o) >= 3 and o[0] == "BUY_PRODUCT" and o[1] == "WHEAT":
                wheat_u += o[2]
        for o in mo:
            if len(o) >= 3 and o[0] == "BUY_PRODUCT" and o[1] == "WHEAT":
                wheat_o += o[2]
    obs = steps[HI][us]["observation"] if HI < len(steps) else None
    for t in range(0, min(HI + 1, len(steps)), 24):
        o = steps[t][us].get("observation")
        if o:
            money.append({"day": t // 24,
                          "us": float(o["farms"][us]["money"]),
                          "them": float(o["farms"][opp]["money"])})
    del obs
    return {
        "ep": int(rp["info"]["EpisodeId"]),
        "dir": os.path.basename(os.path.dirname(path)),
        "opp": names[opp],
        "us_seat": us,
        "margin": float(rp["rewards"][us]) - float(rp["rewards"][opp]),
        "win": float(rp["rewards"][us]) > float(rp["rewards"][opp]),
        "unit_identity": same_u / tot,
        "market_identity": same_m / tot,
        "n_steps": tot,
        "n_mkt_events": len(mkt_events),
        "mkt_events": mkt_events,
        "wheat_buy_us": wheat_u,
        "wheat_buy_them": wheat_o,
        "money_h0": money,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", default="replays_v23:.scratch_ed/replays_v24:"
                                     ".scratch_ed/replays_v24r")
    ap.add_argument("--json", default="results/early_death_mirror.json")
    args = ap.parse_args()

    out = []
    for d in [x for x in args.dirs.split(":") if x]:
        if not os.path.isdir(d):
            print("!! missing dir %s" % d, file=sys.stderr)
            continue
        for name in sorted(os.listdir(d)):
            if not (name.startswith("episode-") and name.endswith("-replay.json")):
                continue
            rec = scan(os.path.join(d, name))
            if rec is None:
                continue
            out.append(rec)
            print("ep%-10d %-6s unit_id=%.3f mkt_id=%.3f mkt_events=%2d wheat %d/%d margin=%+.0f"
                  % (rec["ep"], "WIN" if rec["win"] else "LOSS", rec["unit_identity"],
                     rec["market_identity"], rec["n_mkt_events"],
                     rec["wheat_buy_us"], rec["wheat_buy_them"], rec["margin"]),
                  file=sys.stderr)
    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print("wrote %s (%d episodes)" % (args.json, len(out)))


if __name__ == "__main__":
    main()
