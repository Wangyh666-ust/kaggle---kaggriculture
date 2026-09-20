"""Summarize opponent strategy fingerprints from saved loss replays."""
import collections
import glob
import json
import sys


def summarize(path):
    d = json.load(open(path))
    names = d["info"]["TeamNames"]
    rewards = d["rewards"]
    steps = d["steps"]
    us = names.index("ReD_MooN_rise")
    opp = 1 - us
    out = {
        "opp": names[opp],
        "us": int(rewards[us]),
        "them": int(rewards[opp]),
    }
    # opponent fingerprint at selected days (hour-23 snapshots)
    timeline = []
    for day in (1, 3, 5, 8, 12, 16, 20, 24, 27):
        snap = None
        for s in steps:
            o = s[opp]["observation"]
            if o["day"] == day and o["hour"] == 23:
                snap = o
                break
        if snap is None:
            continue
        farm = snap["farms"][opp]
        herd = collections.Counter()
        crops = collections.Counter()
        for row in farm["tiles"]:
            for t in row:
                if isinstance(t, dict):
                    if "animal" in t:
                        herd[t["animal"]] += 1
                    elif t.get("kind") == "PLANT":
                        crops[t["crop"]] += 1
        timeline.append({
            "day": day,
            "money": int(farm["money"]),
            "hands": len(farm["hands"]),
            "quads": "".join(sorted(q[0] + q[1] for q in farm["unlocked_quadrants"])),
            "herd": dict(herd),
            "crops": dict(crops),
        })
    out["timeline"] = timeline
    return out


def main():
    rows = []
    for path in sorted(glob.glob("loss_replays/*.json")):
        try:
            rows.append(summarize(path))
        except Exception as e:
            print(f"{path}: FAILED {e}", file=sys.stderr)
    for r in rows:
        print(f"\n=== vs {r['opp']}  us=${r['us']} them=${r['them']} ===")
        for t in r["timeline"]:
            print(f"  d{t['day']:2d} ${t['money']:6d} h{t['hands']:2d} {t['quads']:10s} "
                  f"herd={t['herd']} crops={t['crops']}")


if __name__ == "__main__":
    main()
