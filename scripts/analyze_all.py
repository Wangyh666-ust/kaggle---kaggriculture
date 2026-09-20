"""Batch-analyze all downloaded replays: per-episode results + opponent fingerprints.

Usage: PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/analyze_all.py
Reads replays_all/episode-*.json; maps episodes to submission refs via env var
or /tmp/ep_<ref>.txt files.
"""
import collections
import glob
import json
import os
import sys

REFS = {"56376075": "v6", "56378494": "v7", "56378579": "v7.1", "56384254": "v9"}


def load_id_map():
    m = {}
    for ref, name in REFS.items():
        p = f"results/ep_{ref}.txt"
        if os.path.exists(p):
            for line in open(p):
                line = line.strip()
                if line:
                    m[line] = name
    return m


def fingerprint(obs, farm_key):
    farm = obs["farms"][farm_key]
    herd = collections.Counter()
    crops = collections.Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if "animal" in t:
                    herd[t["animal"]] += 1
                elif t.get("kind") == "PLANT":
                    crops[t["crop"]] += 1
    return farm, herd, crops


def analyze(path, ver):
    d = json.load(open(path))
    names = d["info"]["TeamNames"]
    rewards = d["rewards"]
    steps = d["steps"]
    us = names.index("ReD_MooN_rise")
    opp = 1 - us

    rec = {
        "ver": ver, "opp_name": names[opp],
        "us": rewards[us], "them": rewards[opp],
        "margin": rewards[us] - rewards[opp],
    }
    # snapshots
    want_days = {1: "d1", 8: "d8", 12: "d12", 20: "d20", 29: "d29"}
    got = set()
    for s in steps:
        o = s[opp]["observation"]
        day, hour = o["day"], o["hour"]
        if day in want_days and hour == 20 and day not in got:
            got.add(day)
            farm, herd, crops = fingerprint(o, opp)
            tag = want_days[day]
            rec[f"{tag}_opp_money"] = farm["money"]
            rec[f"{tag}_opp_herd"] = sum(herd.values())
            rec[f"{tag}_opp_hands"] = len(farm["hands"])
            if day == 29:
                rec["opp_herd_final"] = dict(herd)
                rec["opp_crops_final"] = dict(crops)
        # our own side day-12 money for ramp comparison
        o_us = s[us]["observation"]
        if o_us["day"] == 12 and o_us["hour"] == 20:
            rec["our_d12_money"] = o_us["farms"][us]["money"]
    return rec


def main():
    id_map = load_id_map()
    recs = []
    for path in sorted(glob.glob("replays_all/episode-*-replay.json")):
        ep = path.split("-")[1]
        ver = id_map.get(ep, "?")
        try:
            recs.append(analyze(path, ver))
        except Exception as e:
            print(f"{path}: {e}", file=sys.stderr)

    # --- per-version summary ---
    print("== per-version record ==")
    for ver in REFS.values():
        rs = [r for r in recs if r["ver"] == ver]
        if not rs:
            continue
        wins = sum(1 for r in rs if r["margin"] > 0)
        avg_us = sum(r["us"] for r in rs) / len(rs)
        avg_them = sum(r["them"] for r in rs) / len(rs)
        avg_margin = sum(r["margin"] for r in rs) / len(rs)
        print(f"  {ver:5s} {wins:2d}/{len(rs):2d} wins  us=${avg_us:7.0f} "
              f"them=${avg_them:7.0f} margin=${avg_margin:+8.0f}")

    # --- worst losses across all versions ---
    print("\n== worst 15 losses (all versions) ==")
    losses = sorted((r for r in recs if r["margin"] < 0), key=lambda r: r["margin"])
    for r in losses[:15]:
        print(f"  {r['ver']:4s} vs {r['opp_name'][:22]:22s} us=${r['us']:6.0f} "
              f"them=${r['them']:6.0f} | opp d12=${r.get('d12_opp_money', 0):6.0f} "
              f"hands12={r.get('d12_opp_hands', 0)} herd29={r.get('opp_herd_final')}")

    # --- opponent frequency / who beats us ---
    print("\n== opponents we lost to (count, avg their money) ==")
    opp_stats = collections.defaultdict(list)
    for r in losses:
        opp_stats[r["opp_name"]].append(r)
    for name, rs in sorted(opp_stats.items(), key=lambda kv: -len(kv[1])):
        avg = sum(r["them"] for r in rs) / len(rs)
        print(f"  {name[:24]:24s} beat us {len(rs)}x, avg ${avg:7.0f}")

    # --- what correlates with our losses ---
    print("\n== loss correlations ==")
    for key, label in (("d12_opp_money", "opp money@d12"), ("d12_opp_hands", "opp hands@d12"),
                       ("d12_opp_herd", "opp herd@d12")):
        vals_w = [r.get(key) for r in recs if r["margin"] > 0 and r.get(key) is not None]
        vals_l = [r.get(key) for r in recs if r["margin"] <= 0 and r.get(key) is not None]
        if vals_w and vals_l:
            print(f"  {label:16s} wins-avg={sum(vals_w)/len(vals_w):8.1f}  "
                  f"losses-avg={sum(vals_l)/len(vals_l):8.1f}")
    # our ramp in wins vs losses
    vals_w = [r.get("our_d12_money") for r in recs if r["margin"] > 0 and r.get("our_d12_money")]
    vals_l = [r.get("our_d12_money") for r in recs if r["margin"] <= 0 and r.get("our_d12_money")]
    if vals_w and vals_l:
        print(f"  OUR money@d12     wins-avg={sum(vals_w)/len(vals_w):8.1f}  "
              f"losses-avg={sum(vals_l)/len(vals_l):8.1f}")

    # save machine-readable
    with open("results/all_episodes.json", "w") as f:
        json.dump(recs, f, indent=1, default=str)
    print(f"\nsaved {len(recs)} episode records -> results/all_episodes.json")


if __name__ == "__main__":
    main()
