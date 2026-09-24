"""Per-day market price trajectory from ladder replays.

Question it answers: is it better to sell a crop late (endgame days 26-29) or
earlier (days 20-23)? Both are harvest windows a TOMATO tile can land in
(planted day 18 -> yields days 26-29; planted day 12 -> days 20-23), so the
choice is purely a price question.

Usage:
  .venv/Scripts/python scripts/price_trace.py --seat ours  replays_v25
  .venv/Scripts/python scripts/price_trace.py --seat top   replays_top
  .venv/Scripts/python scripts/price_trace.py --seat ours --team ReD_MooN_rise replays_v25
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ITEMS = ("TOMATO", "CARROT", "STRAWBERRY", "MELON", "WHEAT", "EGG", "MILK", "WOOL",
         "FERTILIZER")
DAYS = (8, 12, 16, 20, 22, 24, 26, 27, 28, 29)


def trace(path, team):
    d = json.load(open(path, encoding="utf-8"))
    names = d["info"]["TeamNames"]
    if team and team not in names:
        return None
    seat = names.index(team) if team else 0
    out = collections.defaultdict(dict)
    for st in d["steps"]:
        o = st[seat]["observation"]
        day, hour = o["day"], o["hour"]
        if hour == 0 and day in DAYS and day not in out:
            out[day] = {k: o["market"]["prices"].get(k) for k in ITEMS}
    return {"file": os.path.basename(path), "seat": names[seat], "opp": names[1 - seat],
            "seed": d["info"].get("seed"), "days": dict(out)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--team", default="", help="only replays containing this team name")
    ap.add_argument("--items", default="TOMATO,STRAWBERRY,MILK,WOOL")
    args = ap.parse_args()

    files = []
    for a in args.dirs:
        files += sorted(glob.glob(os.path.join(a, "episode-*-replay.json"))) if os.path.isdir(a) else glob.glob(a)

    rows = []
    for p in files:
        try:
            r = trace(p, args.team)
        except Exception as exc:  # noqa: BLE001
            print("skip", p, exc, file=sys.stderr)
            continue
        if r:
            rows.append(r)
    if not rows:
        print("no matching replays")
        return

    items = [i for i in args.items.split(",") if i]
    print(f"{len(rows)} replays\n")
    for it in items:
        print(f"== {it}: mean price by day (n games reporting that day)")
        head = "  day  " + "".join(f"{d:>8d}" for d in DAYS)
        print(head)
        row1 = "  mean "
        row2 = "  n    "
        for d in DAYS:
            vals = [r["days"][d][it] for r in rows if d in r["days"] and r["days"][d].get(it) is not None]
            if vals:
                row1 += f"{statistics.mean(vals):>8.1f}"
                row2 += f"{len(vals):>8d}"
            else:
                row1 += f"{'-':>8s}"
                row2 += f"{'-':>8s}"
        print(row1)
        print(row2)
        early = [r["days"][d][it] for r in rows for d in (20, 21, 22, 23) if d in r["days"]]
        late = [r["days"][d][it] for r in rows for d in (26, 27, 28, 29) if d in r["days"]]
        if early and late:
            print(f"  early(20-23) mean {statistics.mean(early):7.1f}   "
                  f"late(26-29) mean {statistics.mean(late):7.1f}   "
                  f"delta {statistics.mean(late) - statistics.mean(early):+7.1f}")
        print()


if __name__ == "__main__":
    main()
