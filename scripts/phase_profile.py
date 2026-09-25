"""Phase-by-phase profile: what does a team do in each 6-day block?

Metav4's §6 measures route-match per 6-day phase and reports that the teams beating it
abandon the tape from day 12-18 onward (route match 0.12-0.14 vs 0.82-1.00 for tape
replayers), gaining $5-7k. This script asks the follow-up question that diagnostic does
not answer: **what, concretely, differs in each phase** -- labour, herd, crops, land,
purchases and cash -- between that family and us.

Usage:
  .venv/Scripts/python scripts/phase_profile.py --ours replays_v36 --theirs reverse/replays
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"
FAMILY2 = {"mtmr_s1", "DSM", "Vadim Vasilenko", "DECEM", "Unknown Mother-Goose",
           "TheEggman", "ymg_aq", "吃白饭的大肥鱼"}
PHASE_END = (11, 17, 23, 29)          # last day of each 6-day block


def snap(farm):
    herd, crops, empty = collections.Counter(), collections.Counter(), 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if "animal" in t:
                    herd[t["animal"]] += 1
                elif t.get("kind") == "PLANT":
                    crops[t["crop"]] += 1
            else:
                empty += 1
    return herd, crops, empty


def profile(path, team):
    d = json.load(open(path, encoding="utf-8"))
    names = list(d["info"]["TeamNames"])
    if team not in names or names[0] == names[1]:
        return None
    us = names.index(team)
    out = {}
    buys = collections.Counter()
    for st in d["steps"]:
        o = st[us]["observation"]
        day = o["day"]
        if day in PHASE_END and o["hour"] == 23 and day not in out:
            herd, crops, empty = snap(o["farms"][us])
            out[day] = {"money": o["farms"][us]["money"],
                        "hands": len(o["farms"][us]["hands"]),
                        "herd": dict(herd), "crops": dict(crops),
                        "empty": empty,
                        "seed": dict(o["private"].get("seeds", {}))}
        act = st[us].get("action")
        if isinstance(act, dict):
            for o2 in act.get("market", []) or []:
                if isinstance(o2, list) and len(o2) >= 3 and o2[0] == "BUY_SEED":
                    buys[(o2[1], "p" if day <= 11 else "mid" if day <= 23 else "late")] += int(o2[2])
    out["buys"] = dict(buys)
    return out


def agg(rows, label):
    if not rows:
        print(f"  {label}: 无样本"); return
    n = len(rows)
    print(f"  {label}  n={n}")
    for d in PHASE_END:
        vals = [r[d] for r in rows if d in r]
        if not vals:
            continue
        m = statistics.median([v["money"] for v in vals])
        h = statistics.median([v["hands"] for v in vals])
        e = statistics.median([v["empty"] for v in vals])
        cow = statistics.median([v["herd"].get("COW", 0) for v in vals])
        sheep = statistics.median([v["herd"].get("SHEEP", 0) for v in vals])
        goose = statistics.median([v["herd"].get("GOOSE", 0) for v in vals])
        stra = statistics.median([v["crops"].get("STRAWBERRY", 0) for v in vals])
        whea = statistics.median([v["crops"].get("WHEAT", 0) for v in vals])
        carr = statistics.median([v["crops"].get("CARROT", 0) for v in vals])
        toma = statistics.median([v["crops"].get("TOMATO", 0) for v in vals])
        print(f"    d{d:<2d} 钱${m/1000:6.0f}k 雇{h:4.0f} 空{e:3.0f} | "
              f"牛{cow:4.0f} 羊{sheep:4.0f} 鹅{goose:3.0f} | "
              f"草莓{stra:4.0f} 麦{whea:4.0f} 胡{carr:4.0f} 番{toma:3.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", nargs="+", default=["replays_v36"])
    ap.add_argument("--theirs", nargs="+", default=["reverse/replays"])
    args = ap.parse_args()

    def files(dirs):
        out = []
        for a in dirs:
            p = a if os.path.isabs(a) else os.path.join(ROOT, a)
            out += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))
        return out

    mine = [profile(f, OURS) for f in files(args.ours)]
    mine = [r for r in mine if r]
    strong = []
    for f in files(args.theirs):
        try:
            names = list(json.load(open(f, encoding="utf-8"))["info"]["TeamNames"])
        except Exception:
            continue
        for t in names:
            if t in FAMILY2:
                r = profile(f, t)
                if r:
                    strong.append(r)
                break
    print(f"语料: 我们 {len(mine)} 局, family-2 {len(strong)} 局\n")
    agg(mine, "[我们 v36/v37]")
    print()
    agg(strong, "[family 2: DSM/Vadim/mtmr_s1/...]")


if __name__ == "__main__":
    main()
