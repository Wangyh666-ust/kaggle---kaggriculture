"""Turn a corpus of ladder replays into results/ladder_top_meta.md.

Reads replays_ladder/ (top teams, fetched by scripts/fetch_ladder_replays.py)
and, optionally, our own replay dirs, and writes a markdown report covering:

  1. every game in the corpus (seed, teams, result)
  2. opening-signature clustering -> which teams are running the same agent
  3. farm profile at d12/d16/d20/d29 per seat
  4. crop-seed and animal purchases per seat
  5. per-day price trajectories, and the early(20-23) vs late(26-29) split

Everything is derived from the replays themselves; no external data.

Usage:
  .venv/Scripts/python scripts/ladder_meta_report.py \
      --ours replays_v25 --ours-team ReD_MooN_rise \
      --top replays_ladder replays_top reserach_ops \
      --out results/ladder_top_meta.md
"""
import argparse
import collections
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DAYS = (12, 16, 20, 29)
PRICE_DAYS = (8, 12, 16, 20, 22, 24, 26, 27, 28, 29)
PRICE_ITEMS = ("TOMATO", "CARROT", "STRAWBERRY", "MELON", "WHEAT", "EGG", "MILK", "WOOL")
EARLY, LATE = (20, 21, 22, 23), (26, 27, 28, 29)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def tile_mix(farm):
    herd, crops, empty = collections.Counter(), collections.Counter(), 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if "animal" in t:
                    herd[t["animal"]] += 1
                elif t.get("kind") == "PLANT":
                    crops[t["crop"]] += 1
                elif t.get("kind") in ("COOP", "PASTURE"):
                    pass
            else:
                empty += 1
    return herd, crops, empty


def sig(step_actions):
    """Canonical opening signature: the market orders of the first three steps."""
    parts = []
    for act in step_actions:
        mk = act.get("market") if isinstance(act, dict) else None
        parts.append(json.dumps(mk, separators=(",", ":")) if mk is not None else "-")
    return " | ".join(parts)


def analyse(path):
    d = load(path)
    names = d["info"]["TeamNames"]
    rewards = d["rewards"]
    steps = d["steps"]
    rec = {"file": os.path.basename(path), "seed": d["info"].get("seed"),
           "names": names, "rewards": rewards, "seats": {}}

    for p in (0, 1):
        r = {"opening": sig([steps[i][p].get("action") for i in range(3)]),
             "snaps": {}, "seed_buy": collections.Counter(),
             "animal_buy": collections.Counter(), "sell": collections.Counter(),
             "prices": {}}
        for st in steps:
            o = st[p]["observation"]
            day, hour = o["day"], o["hour"]
            if hour == 23 and day in DAYS and day not in r["snaps"]:
                herd, crops, empty = tile_mix(o["farms"][p])
                r["snaps"][day] = {
                    "money": o["farms"][p]["money"], "herd": dict(herd),
                    "crops": dict(crops), "empty": empty,
                    "hands": len(o["farms"][p]["hands"]),
                    "quads": len(o["farms"][p].get("unlocked_quadrants", [])),
                }
            if hour == 0 and day in PRICE_DAYS and day not in r["prices"]:
                r["prices"][day] = {k: o["market"]["prices"].get(k) for k in PRICE_ITEMS}
            act = st[p].get("action")
            if isinstance(act, dict):
                for o2 in act.get("market", []) or []:
                    if not isinstance(o2, list) or len(o2) < 3:
                        if isinstance(o2, list) and o2 and o2[0] == "HIRE":
                            r["hires"] = r.get("hires", 0) + 1
                        continue
                    if o2[0] == "BUY_SEED":
                        r["seed_buy"][o2[1]] += int(o2[2])
                    elif o2[0] == "BUY_ANIMAL":
                        r["animal_buy"][o2[1]] += int(o2[2])
                    elif o2[0] == "SELL":
                        r["sell"][o2[1]] += int(o2[2])
        rec["seats"][p] = r
    return rec


def fmt(counter, limit=6):
    items = sorted(counter.items(), key=lambda kv: -kv[1])[:limit]
    return ", ".join(f"{k} {v}" for k, v in items) or "-"


def seats_of(games):
    """Flatten games into per-seat records (the unit every price/plan stat uses)."""
    return [g["seats"][p] for g in games for p in (0, 1)]


def price_block(seat_recs, label):
    lines = [f"### {label}", "",
             "| product | " + " | ".join(f"d{d}" for d in PRICE_DAYS) + " | early 20-23 | late 26-29 | late-early |",
             "|---|" + "---|" * (len(PRICE_DAYS) + 3)]
    for it in PRICE_ITEMS:
        cells = []
        for d in PRICE_DAYS:
            vals = [r["prices"][d][it] for r in seat_recs
                    if d in r["prices"] and r["prices"][d].get(it) is not None]
            cells.append(f"{statistics.mean(vals):.0f}" if vals else "-")
        early = [r["prices"][d][it] for r in seat_recs
                 for d in EARLY if d in r["prices"] and r["prices"][d].get(it) is not None]
        late = [r["prices"][d][it] for r in seat_recs
                for d in LATE if d in r["prices"] and r["prices"][d].get(it) is not None]
        e = f"{statistics.mean(early):.0f}" if early else "-"
        l = f"{statistics.mean(late):.0f}" if late else "-"
        dl = f"{statistics.mean(late) - statistics.mean(early):+.0f}" if early and late else "-"
        lines.append(f"| {it} | " + " | ".join(cells) + f" | {e} | {l} | {dl} |")
    lines.append("")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", nargs="*", default=["replays_ladder"])
    ap.add_argument("--ours", nargs="*", default=[])
    ap.add_argument("--ours-team", default="ReD_MooN_rise")
    ap.add_argument("--out", default="results/ladder_top_meta_data.md")
    args = ap.parse_args()

    def files(dirs):
        out = []
        for a in dirs:
            p = a if os.path.isabs(a) else os.path.join(ROOT, a)
            out += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))
        return out

    top_files = files(args.top)
    our_files = files(args.ours)
    top = [analyse(p) for p in top_files]
    ours = [analyse(p) for p in our_files]
    print(f"{len(top)} ladder replays, {len(ours)} of ours")

    all_recs = top + ours
    L = []
    A = L.append
    A("# 天梯头部对手分析（由 scripts/ladder_meta_report.py 生成）")
    A("")
    A(f"语料：**{len(top)} 局头部对局**（replays_ladder/）+ **{len(ours)} 局我们自己的对局**。")
    A("数据来源：`scripts/fetch_ladder_replays.py` 抓取的公开天梯回放；每条回放含 `info.seed`")
    A("与双方 720 步完整动作。**本文件全部数字可由脚本重跑复现**。")
    A("")

    # ---- 1. corpus ----
    A("## 1. 语料")
    A("")
    A("| episode | seed | 双方 | 比分 | 分差 |")
    A("|---|---|---|---|---|")
    for r in top:
        m = r["rewards"][0] - r["rewards"][1]
        A(f"| {r['file'].replace('episode-','').replace('-replay.json','')} | {r['seed']} | "
          f"{r['names'][0]} vs {r['names'][1]} | ${r['rewards'][0]:,.0f} : ${r['rewards'][1]:,.0f} | "
          f"{m:+,.0f} |")
    A("")

    # ---- 2. opening families ----
    A("## 2. 开局签名聚类（前 3 步市场单）")
    A("")
    A("同一签名 = 同一 agent（或同一份共享代码）。")
    A("")
    groups = collections.defaultdict(list)
    for r in all_recs:
        for p in (0, 1):
            groups[r["seats"][p]["opening"]].append((r["names"][p], r["rewards"][p]))
    for i, (k, v) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1])), 1):
        who = sorted({n for n, _ in v})
        A(f"**家族 {i}** — {len(v)} seats, {len(who)} teams: {', '.join(who)}")
        A("")
        A(f"```\n{k}\n```")
        A("")

    # ---- 3. farm profile ----
    for label, recs, is_ours in (("3. 头部座位的农场画像", top, False),
                                 ("4. 我们自己的农场画像", ours, True)):
        A(f"## {label}")
        A("")
        A("| 队伍 | 座位 | " + " | ".join(f"d{d} 金钱/畜群/作物/空地块/雇工" for d in DAYS) + " |")
        A("|---|---|" + "---|" * len(DAYS))
        for r in recs:
            for p in (0, 1):
                s = r["seats"][p]
                cells = []
                for d in DAYS:
                    sn = s["snaps"].get(d)
                    if not sn:
                        cells.append("-")
                        continue
                    herd = "+".join(f"{k[0]}{v}" for k, v in sorted(sn["herd"].items()))
                    crops = "+".join(f"{k[:4]}{v}" for k, v in sorted(sn["crops"].items()))
                    cells.append(f"${sn['money'] / 1000:.0f}k / {herd or '-'} / {crops or '-'} / "
                                 f"{sn['empty']} / {sn['hands']}")
                A(f"| {r['names'][p][:18]} | s{p} | " + " | ".join(cells) + " |")
        A("")

    # ---- 4. purchases ----
    A("## 5. 种子/牲畜购买与雇工（整局累计）")
    A("")
    A("| 队伍 | 座位 | BUY_SEED | BUY_ANIMAL | HIRE 次数 |")
    A("|---|---|---|---|---|")
    for r in all_recs:
        for p in (0, 1):
            s = r["seats"][p]
            A(f"| {r['names'][p][:18]} | s{p} | {fmt(s['seed_buy'], 5)} | "
              f"{fmt(s['animal_buy'], 3)} | {s.get('hires', 0)} |")
    A("")

    # ---- 5. prices ----
    A("## 6. 价格轨迹（每局该座位看到的报价，按天取均值）")
    A("")
    A(f"`early` = 第 {EARLY[0]}-{EARLY[-1]} 天，`late` = 第 {LATE[0]}-{LATE[-1]} 天。")
    A("")
    L += price_block(seats_of(all_recs), "全体座位")
    if ours:
        L += price_block(seats_of(ours), f"仅我们（{args.ours_team} 所在局）")
    if top:
        L += price_block(seats_of(top), "仅头部对局")

    with open(os.path.join(ROOT, args.out), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
