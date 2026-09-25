"""Is the "yarn store unlocks late" deficit real, yarn-specific, or just "a shop opened late"?

The claim under test: games where a YARN_STORE unlocks after day 6 (our router locks the
route at step 144 from tuple(unlocked_shops[:2]) and never revisits it) are worse for us.

Three ways it could be wrong, each with its own control:
  1. any shop unlocking late is equally bad  -> control on a NON-yarn late unlock
  2. it is one corpus's quirk               -> split v34 / v36
  3. the draw itself is endogenous          -> noted; shop draws share the per-day RNG with
     weed spawns, and weed draw count depends on both farms' empty tiles, so the shop
     sequence is partly a product of play, not purely exogenous. A correlation here cannot
     establish that the ROUTE is the cause. Report it as a limit, not a result.

Usage: .venv/Scripts/python scripts/late_shop_analysis.py replays_v34 replays_v36
"""
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"
ROUTE_STEP = 144           # day 6, where the router decides
SNAPSHOT_DAY = 16


def herd(farm):
    h = collections.Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict) and "animal" in t:
                h[t["animal"]] += 1
    return h


def read(path):
    d = json.load(open(path, encoding="utf-8"))
    names = list(d["info"]["TeamNames"])
    if OURS not in names or names[0] == names[1]:
        return None
    us = names.index(OURS)
    key = None
    first_seen = {}
    snap = None
    for st in d["steps"]:
        o = st[us]["observation"]
        day = o["day"]
        for s in o["town"]["unlocked_shops"]:
            first_seen.setdefault(s, day)
        if o["step"] == ROUTE_STEP and key is None:
            key = tuple(sorted((o["town"]["unlocked_shops"] or [])[:2]))
        if day == SNAPSHOT_DAY and o["hour"] == 23 and snap is None:
            snap = herd(o["farms"][us])
    if key is None or snap is None or len(key) < 2:
        return None
    return {"margin": d["rewards"][us] - d["rewards"][1 - us],
            "key": key, "first_seen": first_seen, "herd": snap,
            "yarn_early": "YARN_STORE" in key,
            "late": sorted(s for s, day in first_seen.items() if day > 6),
            "late_yarn": any(s == "YARN_STORE" and day > 6 for s, day in first_seen.items()),
            "late_other": any(s != "YARN_STORE" and day > 6 for s, day in first_seen.items())}


def show(label, sub):
    if not sub:
        print(f"  {label:34s} (无样本)")
        return
    w = sum(1 for r in sub if r["margin"] > 0)
    n = len(sub)
    sheep = statistics.median([r["herd"]["SHEEP"] for r in sub])
    cow = statistics.median([r["herd"]["COW"] for r in sub])
    print(f"  {label:34s} n={n:3d}  胜率 {w/n:5.1%}  均值 {statistics.mean([r['margin'] for r in sub]):+9,.0f}  "
          f"中位 {statistics.median([r['margin'] for r in sub]):+8,.0f}  羊{cow and ''}{sheep:.0f}/牛{cow:.0f}")


def main():
    dirs = sys.argv[1:] or ["replays_v34", "replays_v36"]
    rows, by_dir = [], collections.defaultdict(list)
    for a in dirs:
        p = a if os.path.isabs(a) else os.path.join(ROOT, a)
        for f in sorted(glob.glob(os.path.join(p, "episode-*-replay.json"))):
            try:
                r = read(f)
            except Exception:  # noqa: BLE001
                continue
            if r:
                rows.append(r)
                by_dir[os.path.basename(p)].append(r)
    print(f"样本 {len(rows)} 局\n")

    print("== 主分类 ==")
    show("① 前两家店含毛线店", [r for r in rows if r["yarn_early"]])
    show("② 毛线店晚开（>d6）", [r for r in rows if not r["yarn_early"] and r["late_yarn"]])
    show("③ 没有晚开的店", [r for r in rows if not r["yarn_early"] and not r["late"]])
    show("④ 有别的店晚开、无晚开毛线店",
         [r for r in rows if not r["yarn_early"] and r["late_other"] and not r["late_yarn"]])
    show("⑤ 有晚开店（任意种类）",
         [r for r in rows if not r["yarn_early"] and r["late"]])

    print("\n== 按语料拆开（检验是否只是一份语料的怪癖）==")
    for d, sub in sorted(by_dir.items()):
        print(f" {d}:")
        show("  ① 毛线店在前两家", [r for r in sub if r["yarn_early"]])
        show("  ② 毛线店晚开", [r for r in sub if not r["yarn_early"] and r["late_yarn"]])
        show("  ③ 无晚开店", [r for r in sub if not r["yarn_early"] and not r["late"]])

    print("\n== 晚期毛线店的解锁日分布 ==")
    days = [r["first_seen"]["YARN_STORE"] for r in rows
            if not r["yarn_early"] and r["late_yarn"]]
    if days:
        print(f"  {sorted(collections.Counter(days).items())}  中位 {statistics.median(days):.0f}")


if __name__ == "__main__":
    main()
