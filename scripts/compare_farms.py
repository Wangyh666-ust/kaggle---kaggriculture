"""Side-by-side comparison of our farm vs the opponent's, per episode.

Focus: herd composition/timing and land-use (tile) planning — the two things
the player suspected.  Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/compare_farms.py results/ep_<ref>.txt
"""
import collections
import glob
import json
import os
import sys

DAYS = (2, 5, 8, 11, 14, 17, 20, 24, 29)


def snap(obs, p):
    farm = obs["farms"][p]
    herd = collections.Counter()
    crops = collections.Counter()
    structures = 0
    empty = 0
    weeds = 0
    for y, row in enumerate(farm["tiles"]):
        for x, t in enumerate(row):
            if t is None:
                empty += 1
            elif isinstance(t, dict):
                if "animal" in t:
                    herd[t["animal"]] += 1
                    structures += 1
                elif t.get("kind") in ("COOP", "PASTURE"):
                    structures += 1
                elif t.get("kind") == "WEED":
                    weeds += 1
                else:
                    crops[t["crop"]] += 1
    unlocked = len(farm["unlocked_quadrants"]) * 25
    return {
        "money": farm["money"], "hands": len(farm["hands"]),
        "quads": len(farm["unlocked_quadrants"]),
        "herd": sum(herd.values()), "herd_kind": dict(herd),
        "crops": sum(crops.values()), "crop_kind": dict(crops),
        "structures": structures, "empty": empty, "weeds": weeds,
        "used": 100 - empty - weeds - (100 - unlocked),
    }


def main():
    ids = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    rows = []
    for ep in ids:
        path = f"replays_all/episode-{ep}-replay.json"
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        names = d["info"]["TeamNames"]
        rewards = d["rewards"]
        us = names.index("ReD_MooN_rise")
        opp = 1 - us
        rec = {"ep": ep, "opp": names[opp], "us": rewards[us], "them": rewards[opp],
               "margin": rewards[us] - rewards[opp], "days": {}}
        for s in d["steps"]:
            o = s[us]["observation"]
            day, hour = o["day"], o["hour"]
            if hour == 20 and day in DAYS:
                rec["days"][day] = (snap(o, us), snap(o, opp))
        rows.append(rec)

    for r in sorted(rows, key=lambda r: r["margin"]):
        tag = "WIN " if r["margin"] > 0 else "LOSS"
        print(f"\n=== {tag} {r['ep']} vs {r['opp']}  us=${r['us']:.0f} them=${r['them']:.0f} "
              f"margin=${r['margin']:+.0f} ===")
        for day in DAYS:
            if day not in r["days"]:
                continue
            a, b = r["days"][day]
            print(f"  d{day:2d} US  ${a['money']:7.0f} h{a['hands']:2d} q{a['quads']} "
                  f"herd{a['herd']:2d}{a['herd_kind']} crops{a['crops']:2d}{a['crop_kind']} "
                  f"empty{a['empty']:2d} weeds{a['weeds']:2d}")
            print(f"       THEM ${b['money']:7.0f} h{b['hands']:2d} q{b['quads']} "
                  f"herd{b['herd']:2d}{b['herd_kind']} crops{b['crops']:2d}{b['crop_kind']} "
                  f"empty{b['empty']:2d} weeds{b['weeds']:2d}")


if __name__ == "__main__":
    main()
