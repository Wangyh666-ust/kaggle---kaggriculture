"""Extract (public state -> "what did this unit plant on this tile") from top-10 replays.

Question it answers: is the crop-planting choice of a top agent PREDICTABLE from the
public observation? If yes, behaviour cloning has a signal; if it is at the majority-class
baseline, the choice is driven by hidden context (the tape's own scheduling state) that an
imitator cannot see, and cloning is dead on arrival.

Source data: the public dataset `ashok205/kaggriculture-top10-replay-archive`, daily
parquet files whose `replay_json` column holds the full 33 MB replay.

Usage:
  .venv/Scripts/python scripts/extract_plant_choices.py --limit 120 --out data/plant_choices.jsonl
"""
import argparse
import collections
import glob
import json
import os
import sys

import pyarrow.parquet as pq

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
        "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}


def crop_counts(farm):
    c = collections.Counter()
    empty = 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                c[t["crop"]] += 1
            elif t is None:
                empty += 1
    return c, empty


def rows_from_replay(raw, min_day=0):
    d = json.loads(raw)
    names = d["info"]["TeamNames"]
    if names[0] == names[1]:
        return
    steps = d["steps"]
    for seat in (0, 1):
        for st in steps:
            if st[seat].get("action") is None:
                continue
            o = st[seat]["observation"]
            day, hour = o["day"], o["hour"]
            if day < min_day:
                continue
            act = st[seat]["action"]
            units = [act.get("farmer")] + list(act.get("hands") or [])
            if not any(isinstance(u, list) and len(u) > 1 and u[0] == "PLANT" for u in units):
                continue
            farm = o["farms"][seat]
            pos = [farm["farmer"]] + [list(p) for p in farm["hands"]]
            prices = o["market"]["prices"]
            counts, empty = crop_counts(farm)
            shops = tuple(sorted(o["town"]["unlocked_shops"]))
            for i, u in enumerate(units):
                if not (isinstance(u, list) and len(u) > 1 and u[0] == "PLANT"):
                    continue
                if i >= len(pos):
                    continue
                yield {
                    "team": names[seat], "day": day, "hour": hour,
                    "x": pos[i][0], "y": pos[i][1],
                    "crop": u[1],
                    "money": farm["money"], "hands": len(farm["hands"]),
                    "empty": empty,
                    "n_wheat": counts["WHEAT"], "n_carrot": counts["CARROT"],
                    "n_tomato": counts["TOMATO"], "n_straw": counts["STRAWBERRY"],
                    "n_melon": counts["MELON"],
                    "n_shops": len(shops),
                    "p_wheat": prices["WHEAT"], "p_carrot": prices["CARROT"],
                    "p_tomato": prices["TOMATO"], "p_straw": prices["STRAWBERRY"],
                    "p_melon": prices["MELON"],
                    "n_tomato_shop": sum(s in ("PIZZA_SHOP", "FARMERS_MARKET") for s in shops),
                    "n_yarn": sum(s == "YARN_STORE" for s in shops),
                }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=120, help="how many replays to parse")
    ap.add_argument("--glob", default="data/top10/*.parquet")
    ap.add_argument("--out", default="data/plant_choices.jsonl")
    ap.add_argument("--min-day", type=int, default=0)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(ROOT, args.glob)))
    out_path = os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    n = kept = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for path in files:
            pf = pq.ParquetFile(path)
            for batch in pf.iter_batches(batch_size=8, columns=["replay_json"]):
                for raw in batch.column(0).to_pylist():
                    n += 1
                    try:
                        for row in rows_from_replay(raw, args.min_day):
                            fh.write(json.dumps(row) + "\n")
                            kept += 1
                    except Exception as exc:  # noqa: BLE001
                        print(f"  skip replay {n}: {exc}", file=sys.stderr)
                    if n % 20 == 0:
                        print(f"  {n} replays parsed, {kept} plant events", flush=True)
                    if n >= args.limit:
                        break
                if n >= args.limit:
                    break
            if n >= args.limit:
                break
    print(f"\ndone: {n} replays -> {kept} plant events -> {args.out}")


if __name__ == "__main__":
    main()
