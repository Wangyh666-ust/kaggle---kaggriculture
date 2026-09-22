"""Day-0 cash / day-1 hire state for every replay — the early-death knife edge.

For each episode this records the handful of numbers that decide the game:

    money_t1   our bank at step 1  (after the day-0 opening wheat round-trip)
    money_t24  our bank at step 24 (end of day 0)  -> money_t1 - $2,842
    hands_t25  hands actually hired at step 25 (day 1, hour 1) for 3 x HIRE
    herd_dn    animals on each farm at day n h23

`money_t24 < 4` means the three HIREs of day-1 hour 1 cannot all be paid for
(costs 1+1+2), which costs farm hands for the whole of day 1; see
results/early_death_analysis.md §2.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_step1_state.py \
        --dirs replays_v23:.scratch_ed/replays_v24:.scratch_ed/replays_v24r \
        --json results/early_death_hands25.json
"""
import argparse
import json
import os
import sys

OUR_NAME = "ReD_MooN_rise"
DAYS = (1, 2, 3, 5, 6, 10, 29)


def scan(path):
    rp = json.load(open(path, encoding="utf-8"))
    names = list(rp["info"]["TeamNames"])
    if names[0] == names[1] or OUR_NAME not in names:
        return None
    us = names.index(OUR_NAME)
    opp = 1 - us
    steps = rp["steps"]
    rec = {
        "ep": int(rp["info"]["EpisodeId"]),
        "dir": os.path.basename(os.path.dirname(path)),
        "opp": names[opp],
        "us": us,
        "margin": float(rp["rewards"][us]) - float(rp["rewards"][opp]),
        "win": float(rp["rewards"][us]) > float(rp["rewards"][opp]),
        "money_t1_us": float(steps[1][us]["observation"]["farms"][us]["money"]),
        "money_t1_them": float(steps[1][us]["observation"]["farms"][opp]["money"]),
        "money_t2_us": float(steps[2][us]["observation"]["farms"][us]["money"]),
        "money_t24_us": float(steps[24][us]["observation"]["farms"][us]["money"]),
        "money_t25_us": float(steps[25][us]["observation"]["farms"][us]["money"]),
        "money_t25_them": float(steps[25][us]["observation"]["farms"][opp]["money"]),
        "hands_t25_us": len(steps[25][us]["observation"]["farms"][us]["hands"]),
        "hands_t25_them": len(steps[25][us]["observation"]["farms"][opp]["hands"]),
        "us_mkt_t1": [list(o) for o in
                      ((steps[1][us].get("action") or {}).get("market") or [])],
        "them_mkt_t1": [list(o) for o in
                        ((steps[1][opp].get("action") or {}).get("market") or [])],
    }
    for day in DAYS:
        t = day * 24 + 23
        obs = steps[t][us]["observation"]
        for tag, seat in (("us", us), ("them", opp)):
            rec["herd_%s_d%d" % (tag, day)] = sum(
                1 for row in obs["farms"][seat]["tiles"] for tile in row
                if isinstance(tile, dict) and tile.get("animal"))
        rec["diff_d%d" % day] = (obs["farms"][us]["money"] - obs["farms"][opp]["money"])
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", default="replays_v23:.scratch_ed/replays_v24:"
                                     ".scratch_ed/replays_v24r")
    ap.add_argument("--json", default="results/early_death_hands25.json")
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
            print("ep%-10d %-6s $t1=%-6.0f $t24=%-4.0f hands@25=%d (them %d)  margin=%+.0f"
                  % (rec["ep"], "WIN" if rec["win"] else "LOSS", rec["money_t1_us"],
                     rec["money_t24_us"], rec["hands_t25_us"], rec["hands_t25_them"],
                     rec["margin"]), file=sys.stderr)
    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print("wrote %s (%d episodes)" % (args.json, len(out)))


if __name__ == "__main__":
    main()
