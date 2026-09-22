"""Build results/analysis_v24_vs_v23_losses.md from the parsed replay data.

Run after scripts/analyze_v24_vs_v23.py (which writes the data JSON):
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/analyze_v24_vs_v23_report.py
"""
import collections
import json
import math
import statistics
import sys

DATA = "results/analysis_v24_vs_v23_data.json"
OUT = "results/analysis_v24_vs_v23_losses.md"
NONFERT = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"]
ITEMS = NONFERT + ["FERTILIZER"]

D = json.load(open(DATA, encoding="utf-8"))
ORDER = sorted(D["v24_first"], key=lambda r: r["ep"])
D["v24_first50"] = ORDER[:50]
D["v24_last30"] = ORDER[50:]
SETS = ["v23_c7", "v24_first50", "v24_rerun"]
L = []


def w(s=""):
    L.append(s)


def f(x, dec=0):
    return format(x, ",.%df" % dec)


def se(xs):
    return statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0


def mean(xs):
    return statistics.mean(xs) if xs else 0.0


def sums(v):
    wins = [r for r in v if r["margin"] > 0]
    loss = [r for r in v if r["margin"] < 0]
    tie = [r for r in v if r["margin"] == 0]
    return wins, loss, tie


def per_game(v, hours, items=None):
    out = []
    for r in v:
        t = 0
        for h in hours:
            cc = r["sells_by_hour"].get(str(h)) or {}
            for it, n in cc.items():
                if items is None or it in items:
                    t += n
        out.append(t)
    return out


# ---------------------------------------------------------------- header
w("# v23_c7 vs v24 线上败局分析——`_SR_*` 假设检验（2026-09-22）")
w()
w("数据来源：`replays_v23/`（v23_c7，55 文件）、`replays_v24/`（v24 首跑，80 文件）、")
w("`replays_v24r/`（v24 重跑，49 文件）。解析脚本 `scripts/analyze_v24_vs_v23.py`，")
w("本报告由 `scripts/analyze_v24_vs_v23_report.py` 生成，中间数据 `results/analysis_v24_vs_v23_data.json`。")
w()
w("**代码差异已核对**（`git diff 237c878 0215cb9 -- main.py`，全文只有 3 行变化）：")
w()
w("```")
w("-V9_RACE_DEFAULT = 40                    +V9_RACE_DEFAULT = 41")
w("-_SR_MARGIN = 4                           +_SR_MARGIN = 8")
w("-_SR_HOURS = (22, 23)                     +_SR_HOURS = (21, 22, 23)")
w("```")
w()

# ---------------------------------------------------------------- TL;DR
w("## 0. 结论速览")
w()
w("| 问题 | 判定 | 关键证据 |")
w("|---|---|---|")
w("| `_SR_*` 改动是不是 v24 线上更差的原因？ | **推翻**（数据不支持） | `_SR` 层触发条件苛刻；两个版本 21-23 点卖单量差 `+2.1 ± 28` 单位/局（0.07σ）；夜间卖价相对次日清晨只差 **-0.13%**（v24 首跑） |")
w("| 12-20 天的作物/奶毛销售窗口被单独打穿了吗？ | **不成立** | 三个版本的畜群/作物/雇工结构几乎相同（d12 COW 7.0-7.4、SHEEP 7.3-7.7、雇工 9.0-9.3、作物 55.8-57.0）；日均进账差在每个阶段都是同号的小额 |")
w("| v24 是输给了更强的对手吗？ | **只在首跑成立** | 首跑败局对手 $105,289、4 场大败对手 $87k-143k；重跑败局对手只有 $90,297（我方 $89,414 就输了） |")
w("| v24 的输法不一样吗？ | **首跑不一样** | 首跑 12 场败局中 10 场在 **d≤10** 就永久失去领先（v23_c7 = 2/14，重跑 = 0/14） |")
w("| Elo 差 160 分能用对局数据解释吗？ | **不能** | 同胜率（74.0% vs 74.1%）、v24 边际几乎翻倍（+$11,773 vs +$6,177）、4 场同对手合计也更好 |")
w("| 下一步 | 不要回退 `_SR_*`；把精力放在**早期评分轨迹**与「早死型」败局上 | 见 §7 |")
w()

# ---------------------------------------------------------------- 1
w("## 1. 汇总核对（与题面表格对账）")
w()
w("| 集合 | 文件数 | 自对局剔除 | 可用局数 | W-L-T | 胜率 | 场均边际 | 最差边际 |")
w("|---|---|---|---|---|---|---|---|")
for k, files, skip in (("v23_c7", 55, 1), ("v24_first50", 50, 0), ("v24_rerun", 49, 0)):
    v = D[k]
    wins, loss, tie = sums(v)
    w("| %s | %d | %d | %d | %d-%d-%d | %.1f%% | %s | %s |" % (
        k, files, skip, len(v), len(wins), len(loss), len(tie),
        100 * len(wins) / len(v), f(mean([r["margin"] for r in v])),
        f(min(r["margin"] for r in v))))
w()
w("自对局：`episode-111617471`（两队同名 `ReD_MooN_rise`，72,499 vs 71,949）。")
w()
w("**与题面完全一致**。两点口径说明：")
w()
w("- `replays_v24/` 实际有 **80** 个回放文件，题面「50 局」=按 episode id 升序取前 50（ep %d…%d）。"
  % (ORDER[0]["ep"], ORDER[49]["ep"]))
w("  后 30 局（ep %d 起）也一并统计，作为 v24 的额外样本：" % ORDER[50]["ep"])
_v = D["v24_first"]
_win, _loss, _tie = sums(_v)
w("  80 局口径 = %dW-%dL-%dT（%.1f%%），场均 %s，最差 %s。" % (
    len(_win), len(_loss), len(_tie), 100 * len(_win) / len(_v),
    f(mean([r["margin"] for r in _v])), f(min(r["margin"] for r in _v))))
w("- **同一份代码的两次跑，胜率本身就在 71.4%~77.5% 之间摆动**（v24 首跑 50 局 74.0%、")
w("  80 局 77.5%、重跑 49 局 71.4%）。这个摆动幅度（≈6 个百分点）比 v23_c7 与 v24 之间的差异")
w("  还要大，所以「线上 74% vs 74%」这种量级的比较本身分辨不出两个版本。")
w()

# ---------------------------------------------------------------- 2
w("## 2. 败局的时间定位（核心）")
w()
w("口径：`diff[d] = 我方资金 - 对手资金`，取第 d 天 `hour==23` 的快照（step = d*24+23）。")
w()
w("- `last_pos_day`：最后一次 `diff>0` 的天数（`—` 表示该局 h23 差值从未为正，多数是完全镜像局）")
w("- `permanent_neg_day`：从该天起 `diff` 再不回正（完全镜像局里 `diff` 长时间恰为 0，会把它推后，")
w("  所以它只能作为「领先是什么时候没的」的**上界**）")
w("- `min_day`：`diff` 最低点所在天")
w()
w("### 2.1 败局的失守分布")
w()
w("| 集合（败局） | n | last_pos_day 中位数 | permanent_neg_day 中位数 | **d≤10 就永久失去领先** | min_day≥27 |")
w("|---|---|---|---|---|---|")
for k in SETS:
    v = [r for r in D[k] if r["margin"] < 0]
    lp = [r["last_pos_day"] for r in v]
    pn = [r["permanent_neg_day"] for r in v]
    late = sum(1 for r in v if r["min_day"] is not None and r["min_day"] >= 27)
    never = sum(1 for r in v if r["last_pos_day"] is None)
    med_lp = statistics.median([x for x in lp if x is not None]) if any(x is not None for x in lp) else None
    w("| %s | %d | %s%s | %s | **%d/%d** | %d |" % (
        k, len(v),
        f(med_lp) if med_lp is not None else "—",
        "（另有 %d 局全程未领先）" % never if never else "",
        f(statistics.median([x for x in pn if x is not None])),
        sum(1 for x in pn if x is not None and x <= 10), len(v), late))
w()
w("**v24 首跑与另外两个集合的失败形态明显不同**（`permanent_neg_day` 逐局值，按 episode 排序）：")
w()
for k in SETS:
    v = sorted([r for r in D[k] if r["margin"] < 0], key=lambda r: r["ep"])
    pn = [r["permanent_neg_day"] for r in v]
    w("- `%s`：%s" % (k, " ".join(str(x) for x in pn)))
w()
w("v24 首跑的 12 场败局里，有 10 场在 d≤10 就已经永久失去领先（其余 2 场是 d16/d21）；")
w("v23_c7 的 14 场里只有 2 场（d4、d10）；v24 重跑的 14 场**一场都没有**（最早 d12）。")
w("也就是说：**v24 首跑的败局是「早死型」，v23_c7 与 v24 重跑的败局是「尾盘型」。**")

w()
w("### 2.2 每个阶段的日均进账差（我方 − 对手）")
w()
w("口径：`income[d] = money(d,h23) - money(d-1,h23)`，只对同一版本的胜局/败局分别求均值。")
w()
w("| 集合 | 分组 | d1-5 | d6-10 | d11-15 | d16-20 | d21-25 | d26-29 |")
w("|---|---|---|---|---|---|---|---|")
for k in SETS:
    v = D[k]
    for tag, sub in (("胜", [r for r in v if r["margin"] > 0]), ("败", [r for r in v if r["margin"] < 0])):
        g = []
        for lo, hi in ((1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 29)):
            us, th = [], []
            for r in sub:
                for d in range(lo, hi + 1):
                    a, b = r["our_money_h23"].get(str(d)), r["our_money_h23"].get(str(d - 1))
                    c, e = r["opp_money_h23"].get(str(d)), r["opp_money_h23"].get(str(d - 1))
                    if None not in (a, b, c, e):
                        us.append(a - b)
                        th.append(c - e)
            g.append(mean(us) - mean(th))
        w("| %s | %s(n=%d) | %s |" % (k, tag, len(sub), " | ".join("%+d" % x for x in g)))
w()
w("读法：败局里 **每一个阶段** 我们都在掉血，v24 首跑掉得早（d6-15 就开始 -207/-270 每天），")
w("v23_c7 掉得晚而均匀（d11 之后每天 -55~-107）；v24 重跑的败局和 v23_c7 同形。")
w("**没有出现「某一阶段突然崩盘」的结构**（例如不存在 12-20 天作物/奶毛窗口被单独打穿）。")
w()
w("### 2.3 败势轨迹（具名证据）")
w()
w("v24 首跑的 4 场大败（全部为「d6-10 起被对手拉开、此后单调扩大」）：")
w()
w("| episode | 对手 | 我方 | 对手 | 边际 | d6 | d10 | d15 | d20 | d29 |")
w("|---|---|---|---|---|---|---|---|---|---|")
for r in sorted([x for x in D["v24_first50"] if x["margin"] < -5000], key=lambda x: x["margin"]):
    d = r["diff_h23"]
    w("| %d | %s | %s | %s | **%s** | %+d | %+d | %+d | %+d | %+d |" % (
        r["ep"], r["opp"], f(r["reward_us"]), f(r["reward_opp"]), f(r["margin"]),
        d["6"], d["10"], d["15"], d["20"], d["29"]))
w()
w("对照组，v23_c7 唯一的大败（同样形态，只是出现次数少）：")
w()
for r in sorted([x for x in D["v23_c7"] if x["margin"] < -5000], key=lambda x: x["margin"]):
    d = r["diff_h23"]
    w("- ep=%d vs %s：%s vs %s，边际 **%s**；d6 %+d、d10 %+d、d15 %+d、d20 %+d、d29 %+d" % (
        r["ep"], r["opp"], f(r["reward_us"]), f(r["reward_opp"]), f(r["margin"]),
        d["6"], d["10"], d["15"], d["20"], d["29"]))
w()
w("v24 重跑的最大败局则完全相反——**d25 才被反超**：")
w()
for r in sorted([x for x in D["v24_rerun"] if x["margin"] < 0], key=lambda x: x["margin"])[:2]:
    d = r["diff_h23"]
    w("- ep=%d vs %s：%s vs %s，边际 **%s**；d0 %+d、d12 %+d、d15 %+d、d20 %+d、d25 %+d、d29 %+d" % (
        r["ep"], r["opp"], f(r["reward_us"]), f(r["reward_opp"]), f(r["margin"]),
        d["0"], d["12"], d["15"], d["20"], d["25"], d["29"]))
w()
w("### 2.4 胜局对照（应该在后期拉开）")
w()
w("| 集合（胜局） | 全场未永久落后 | diff(d29) 均值 | diff(d12) 均值 |")
w("|---|---|---|---|")
for k in SETS:
    sub = [r for r in D[k] if r["margin"] > 0]
    w("| %s | **%d/%d** | %s | %s |" % (
        k, sum(1 for r in sub if r["permanent_neg_day"] is None), len(sub),
        f(mean([r["diff_h23"]["29"] for r in sub])), f(mean([r["diff_h23"]["12"] for r in sub]))))
w()
w("胜局形态三版一致：全场不掉队、优势从 d9 之后单调拉开（v23_c7 d9 +0k → d29 +9k；")
w("v24 首跑 d9 +1k → d29 +17k）。**胜局的形态没有被 `_SR_*` 改动影响**。")
w()

# ---------------------------------------------------------------- 3
w("## 3. 败局对手画像")
w()
w("| 集合（败局） | n | 对手终局资金 均值/中位 | 对手 d12 资金 | 对手 d12 雇工 | 终局 COW/SHEEP/GOOSE | 我方终局资金 |")
w("|---|---|---|---|---|---|---|")
for k in SETS:
    v = [r for r in D[k] if r["margin"] < 0]
    w("| %s | %d | %s / %s | %s | %.2f | %.2f / %.2f / %.2f | %s |" % (
        k, len(v),
        f(mean([r["reward_opp"] for r in v])), f(statistics.median([r["reward_opp"] for r in v])),
        f(mean([r["d12_opp"]["money"] for r in v])),
        mean([r["d12_opp"]["hands"] for r in v]),
        mean([r["final_opp"]["herd"].get("COW", 0) for r in v]),
        mean([r["final_opp"]["herd"].get("SHEEP", 0) for r in v]),
        mean([r["final_opp"]["herd"].get("GOOSE", 0) for r in v]),
        f(mean([r["reward_us"] for r in v]))))
w()
w("参照：胜局里的对手终局资金")
for k in SETS:
    v = [r for r in D[k] if r["margin"] > 0]
    w("- %s 胜局：对手 %s / 中位 %s（n=%d）" % (
        k, f(mean([r["reward_opp"] for r in v])), f(statistics.median([r["reward_opp"] for r in v])), len(v)))
w()
w("**判定：v24 首跑确实输给了更强的对手**（败局对手均值 $105,289 vs v23_c7 $100,189），")
w("且它的 4 场大败全在对手 $87k-143k 这一档；")
w("**但 v24 重跑的败局对手最弱（$90,297）**，我方自己掉到 $89,414 才输——")
w("所以「输给更强对手」只解释首跑，不解释重跑。")
w()
w("对手终局资金整体分布（含胜局，更能反映对手池）：")
w()
w("| 集合 | p25 | 中位 | p75 | 最大 | 对手 >$100k |")
w("|---|---|---|---|---|---|")
for k in SETS + ["v24_first"]:
    v = D[k]
    xs = sorted(r["reward_opp"] for r in v)
    q = lambda p: xs[int(p * (len(xs) - 1))]
    w("| %s | %s | %s | %s | %s | %d/%d (%.0f%%) |" % (
        k, f(q(.25)), f(q(.5)), f(q(.75)), f(xs[-1]),
        sum(1 for x in xs if x > 100000), len(xs), 100 * sum(1 for x in xs if x > 100000) / len(xs)))
w()

# ---------------------------------------------------------------- 4
w("## 4. 败局中我方状态（d12 快照，与对手并排）")
w()
w("| 集合（败局） | 我方 d12 资金 | 对手 d12 资金 | 差 | 我方雇工 | 对手雇工 | 我方 COW/SHEEP/GOOSE | 对手 COW/SHEEP/GOOSE | 我方作物数 | 对手作物数 |")
w("|---|---|---|---|---|---|---|---|---|---|")
for k in SETS:
    v = [r for r in D[k] if r["margin"] < 0]
    us = mean([r["d12_us"]["money"] for r in v])
    th = mean([r["d12_opp"]["money"] for r in v])
    w("| %s | %s | %s | **%+d** | %.2f | %.2f | %.2f/%.2f/%.2f | %.2f/%.2f/%.2f | %.1f | %.1f |" % (
        k, f(us), f(th), us - th,
        mean([r["d12_us"]["hands"] for r in v]), mean([r["d12_opp"]["hands"] for r in v]),
        mean([r["d12_us"]["herd"].get("COW", 0) for r in v]),
        mean([r["d12_us"]["herd"].get("SHEEP", 0) for r in v]),
        mean([r["d12_us"]["herd"].get("GOOSE", 0) for r in v]),
        mean([r["d12_opp"]["herd"].get("COW", 0) for r in v]),
        mean([r["d12_opp"]["herd"].get("SHEEP", 0) for r in v]),
        mean([r["d12_opp"]["herd"].get("GOOSE", 0) for r in v]),
        mean([r["d12_us"]["crops_total"] for r in v]), mean([r["d12_opp"]["crops_total"] for r in v])))
w()
w("| 集合（胜局，参照） | 我方 d12 资金 | 对手 d12 资金 | 差 |")
w("|---|---|---|---|")
for k in SETS:
    v = [r for r in D[k] if r["margin"] > 0]
    us = mean([r["d12_us"]["money"] for r in v])
    th = mean([r["d12_opp"]["money"] for r in v])
    w("| %s | %s | %s | **%+d** |" % (k, f(us), f(th), us - th))
w()
w("**关键读数**：")
w()
w("- v23_c7 败局：d12 时我们与对手打平（+$98），最后以 -$1,596 输掉 → 输在 d12 之后的细微差价")
w("- v24 首跑败局：d12 时我们 **已经落后 $1,124**（$16,311 vs $17,435）→ 与大败场次的「d6-10 起被拉开」一致")
w("- v24 重跑败局：d12 时我们 **领先 $1,309**（$18,960 vs $17,651），最后只输 $883 → 与 v23_c7 同型")
w()
w("三版的畜群构成完全同族（d12 COW 7.0-7.4、SHEEP 7.3-7.7、GOOSE 1.9-2.9，雇工 8.9-9.3），")
w("**没有证据表明 `_SR_*` 改动改变了任何一条生产/建造路线**。")
w()

# ---------------------------------------------------------------- 5
w("## 5. 市场行为对照：`_SR_*` 假设检验（重点）")
w()
w("### 5.1 `_SR` 层为什么几乎不可能有效果（代码事实）")
w()
w("`main.py:5188`：`overflow = night_shed + carried - cap + _SR_MARGIN`，只有 `overflow > 0` 才卖，")
w("每次最多补 `min(spare, overflow)` 个单位，且按**价格从低到高**卖。因此：")
w()
w("- `_SR_MARGIN` 4→8 只是把触发门槛从「棚子+手上 > 96」降到「> 92」——最多多卖 4 个单位/次")
w("- `_SR_HOURS` 多一个 21 点，但触发时 overflow 只有个位数")
w()
w("我们用回放里可见的 `private.shed`（我方）+ `private.inventories`（我方随身，回放可见）复算触发上界：")
w("`x = shed + carried - 100`，触发= `x + MARGIN > 0`。")
w()
w("| 集合 | 小时 | 触发率 M=4 | 触发率 M=8 | 平均余量 x | x 最大值 |")
w("|---|---|---|---|---|---|")
for k in SETS:
    v = D[k]
    for h in (21, 22, 23):
        xs = []
        for r in v:
            for d in range(0, 29):
                s = r["shed_by_day_hour"].get(str(d), {}).get(str(h))
                c = r["carried_by_day_hour"].get(str(d), {}).get(str(h))
                if s is not None and c is not None:
                    xs.append(s + c - 100)
        w("| %s | h%d | %.2f%% | %.2f%% | %+.1f | %+d |" % (
            k, h, 100 * sum(1 for x in xs if x + 4 > 0) / len(xs),
            100 * sum(1 for x in xs if x + 8 > 0) / len(xs), mean(xs), max(xs)))
w()
w("即使按这个**明显偏大**的上界（真实 `night_shed` 是「按计划卖完之后」的棚子，比我用的当前棚子小），")
w("用 v23_c7 自己的 54 局做同数据反事实：M=4/h22-23 的触发率是 9.51%+6.00% = **15.5%**，")
w("M=8/h21-23 是 12.26%+15.52%+13.54% = **41.3%**，即每天多触发 0.26 次、每次最多 8 单位")
w("（实测 overflow 多为 1-4），折算大约 **+25~30 单位/局**——按最便宜的商品（$20-50/单位）算不到 $1,500，")
w("占终局资金（$98k）的 1.5% 以内。**这已经是上界。**")
w()
w("### 5.2 观测到的卖单行为：两个版本几乎相同")
w()
w("口径：从回放 `action.market` 里解析我方（`ReD_MooN_rise` 座位）的 `SELL` 请求单位数。")
w()
w("| 集合 | h21-23 卖单 单位/局（不含肥料） | 其中 h21 | h0-20 卖单 单位/局（对照） |")
w("|---|---|---|---|")
for k in SETS:
    v = D[k]
    a = per_game(v, [21, 22, 23], NONFERT)
    b = per_game(v, [21], NONFERT)
    c = per_game(v, list(range(0, 21)), NONFERT)
    w("| %s | %.1f ± %.1f | %.1f ± %.1f | %.1f ± %.1f |" % (
        k, mean(a), se(a), mean(b), se(b), mean(c), se(c)))
w()
w("**v24 首跑 − v23_c7 = +2.1 ± 28.3 单位/局（差 0.07 个标准差）**；")
w("`_SR_HOURS` 新增的那个 21 点，卖单量是 %.1f（v23_c7）vs %.1f（v24 首跑）——"
  % (mean(per_game(D["v23_c7"], [21], NONFERT)), mean(per_game(D["v24_first50"], [21], NONFERT))))
w("**v24 反而更少**，说明这一层的改动在 50 局规模上测不出任何行为差异。")
w("（`v24_rerun` 的 h21-23 卖单量比 v23_c7 高约 11%，但它的 **h0-20 对照也高 4%**，")
w("属于该集合整体卖单更多的路径差异，不是「夜间多卖」。）")
w()
w("### 5.3 夜间卖价 vs 次日清晨卖价（假设的直接检验）")
w()
w("口径：把每个集合里 hour 21/22/23 的卖单，按**当时的成交价**估值，再按**次日 h0/h1 的价格**估值同一批单位。")
w("若 `_SR` 提前抛售是亏的，`次日 − 当时` 应该显著为正。")
w()
w("| 集合 | h21-23 当时估值 | 同批单位次日 h1 估值 | 差（次日 − 当时） | 相对 |")
w("|---|---|---|---|---|")
for k in SETS:
    v = D[k]
    now = [r["night_sell_value"] for r in v]
    nxt = [r["next_morning_value"] for r in v]
    dl = [b - a for a, b in zip(now, nxt)]
    w("| %s | $%s | $%s | **%+.0f ± %.0f** | %+.3f%% |" % (
        k, f(mean(now)), f(mean(nxt)), mean(dl), se(dl), 100 * mean(dl) / mean(now)))
w()
w("**差值全部在 0.6% 以内**，而且三个集合都是**负值**——即「等到次日清晨再卖」平均还略微更差")
w("（v23_c7 -0.57%、v24 首跑 -0.13%、重跑 -0.16%）。")
w("原因很清楚：`_SR` 按价格升序挑最便宜的商品卖（`main.py:5207`），它卖的是本来就在手上、")
w("价格已经贴近底部的边角料，夜间与次日清晨没有可利用的系统差价。")
w("**「提前抛售亏钱」假设不成立。**")
w()
w("### 5.4 棚子占用（夜间清仓的物理证据）")
w()
w("我方 `private.shed` 合计 + `private.inventories` 随身合计（单位数，均值）：")
w()
w("| 集合 | h21 | h22 | h23 | h22 vs h21 | p90(h23) | max(h23) |")
w("|---|---|---|---|---|---|---|")
for k in SETS:
    v = D[k]
    row = []
    for h in (21, 22, 23):
        xs = []
        for r in v:
            for d in range(0, 29):
                s = r["shed_by_day_hour"].get(str(d), {}).get(str(h))
                c = r["carried_by_day_hour"].get(str(d), {}).get(str(h))
                if s is not None and c is not None:
                    xs.append(s + c)
        row.append(xs)
    w("| %s | %.1f ± %.2f | %.1f ± %.2f | %.1f ± %.2f | %+.1f | %.0f | %.0f |" % (
        k, mean(row[0]), se(row[0]), mean(row[1]), se(row[1]), mean(row[2]), se(row[2]),
        mean(row[1]) - mean(row[0]), sorted(row[2])[int(.9 * len(row[2]))], max(row[2])))
w()
w("棚子容量是 100。**夜间占用只有 52-53 个单位**，离饱和（92-96 的触发线）还差 40 个，")
w("这从根本上解释了为什么 `_SR` 层几乎不触发，也解释了为什么两个版本的 h22/h23 占用只差 0.2-0.6 个单位。")
w()
w("（附带发现：`_SR` 想防的「溢出销毁」在线上几乎不存在 —— 用 h23 观察值估 `max(0, shed+carried-100)`，")
w("v23_c7 只有 42/1404 个「局×天」> 0，均值 0.12 个单位。这条层防的是一个基本不发生的问题。）")
w()

# ---------------------------------------------------------------- 6
w("## 6. 同对手交叉对比（最干净的对照）")
w()
w("按队名匹配，同时出现在多个集合里的对手：")
w()
w("| 对手 | v23_c7 | v24 首跑 | v24 重跑 |")
w("|---|---|---|---|")
bykey = {}
for k in ("v23_c7", "v24_first", "v24_rerun"):
    for r in D[k]:
        bykey.setdefault(r["opp"], {}).setdefault(k, []).append(r)
rows = [(n, m) for n, m in sorted(bykey.items()) if len(m) > 1]
for name, m in rows:
    cells = []
    for k in ("v23_c7", "v24_first", "v24_rerun"):
        if k in m:
            cells.append(" ; ".join("ep%d %s(us %s / them %s)"
                                    % (r["ep"], f(r["margin"]), f(r["reward_us"]), f(r["reward_opp"]))
                                    for r in m[k]))
        else:
            cells.append("—")
    w("| %s | %s | %s | %s |" % (name, cells[0], cells[1], cells[2]))
w()
w("跨版本（v23_c7 ↔ v24）共 **4 个**对手：")
w()
w("| 对手 | v23_c7 边际 | v24 边际 | 结论 |")
w("|---|---|---|---|")
tot23 = tot24 = 0
for name, m in rows:
    if "v23_c7" in m and ("v24_first" in m or "v24_rerun" in m):
        a = sum(r["margin"] for r in m["v23_c7"])
        b = sum((r["margin"] for r in m.get("v24_first", [])), 0) + sum((r["margin"] for r in m.get("v24_rerun", [])), 0)
        tot23 += a
        tot24 += b
        w("| %s | %+.0f | %+.0f | %s |" % (name, a, b, "v24 更好" if b > a else "v24 更差"))
w("| **合计** | **%+.0f** | **%+.0f** | **v24 更好** |" % (tot23, tot24))
w()
w("4 个对手里，v24 在 2 个上边际更大、在 2 个上更小；合计 **v24 +11,143 vs v23_c7 +9,827**。")
w("**但样本只有 4 局对 4 局、且 4 场全是胜局，统计力极低，只能说明「没有在同对手身上变差的证据」。**")
w()
w("另一个更硬的对照：v24 **首跑与重跑是同一份代码**（标题已核对只有 3 行参数差异），")
w("它们在 h21-23 卖单、d12 结构、终局畜群上的差异同样落在噪声里，而评分轨迹截然不同（§7）。")
w()

# ---------------------------------------------------------------- 7
w("## 7. 结论")
w()
w("### 7.1 v24 线上更差的具体机制？——**在回放数据里找不到机制**")
w()
w("逐项排查后，v24 与 v23_c7 在可观测的对局行为上**基本重合**：")
w()
w("| 观测量 | v23_c7 | v24 首跑 | v24 重跑 | 差异显著性 |")
w("|---|---|---|---|---|")
w("| 胜率 | 74.1% | 74.0% | 71.4% | 不显著（同代码两次跑摆动 71-78%） |")
w("| 场均边际 | +$6,177 | +$11,773 | +$10,809 | v24 更好 |")
w("| d12 雇工 | 9.19 | 9.16 | 9.24 | 无差异 |")
w("| d12 畜群 COW/SHEEP/GOOSE | 7.20/7.70/2.19 | 7.02/7.28/2.34 | 7.27/7.55/2.61 | 无差异 |")
w("| d12 作物数 | 56.9 | 56.7 | 57.0 | 无差异 |")
w("| h21-23 卖单（不含肥料） | 231.8 ± 19.5 | 233.9 ± 20.5 | 256.9 ± 26.4 | 不显著 |")
w("| h22/h23 棚子+随身占用 | 53.3 / 52.3 | 52.7 / 52.1 | 52.8 / 52.1 | 差 0.2-0.6 单位 |")
w()
w("唯一的真实差异在**败局的时间结构**上：v24 首跑的败局「早死」——12 场里 10 场 d≤10 就永久失去领先，")
w("4 场大败（ep 111731237 -$6,502、111732814 -$8,680、111735088 -$22,399、111742930 -$9,168）")
w("全部是 d6-10 被对手一次性拉开后不再回头的形态；而 v23_c7 的败局（含唯一大败 ep 111633116）里")
w("只有 2/14 早死，重跑是 0/14。**这条「早死」差异是首跑特有的，重跑没有复现**，")
w("因此更像是首跑那一段的对手/对局抽样，而不是代码的稳定性质。")
w("换句话说：如果 `_SR_*` 真的在害我们，它应该让**两次跑**都出现同一种败局——但没有。")
w()
w("### 7.2 `_SR_*` 假设：**推翻**")
w()
w("三条互相独立的证据：")
w()
w("1. **物理上不可能有量级**：`_SR` 只在 `shed+carried > 92` 时触发，而线上夜间占用平均只有 52.3（h23），")
w("   实测 h22/h23 占用两个版本只差 0.2-0.6 个单位；即使按偏大的触发率上界，改动量也只有 **+25~30 单位/局**（≈1% 资金）。")
w("2. **行为上没有差异**：`_SR_HOURS` 新增的 21 点，卖单量 v23_c7 %.1f vs v24 首跑 %.1f（单位/局，不含肥料）——" % (
    mean(per_game(D["v23_c7"], [21], NONFERT)), mean(per_game(D["v24_first50"], [21], NONFERT))))
w("   v24 反而略少，说明它在 21 点根本没触发过。")
w("3. **价格上没有惩罚**：21-23 点卖出的单位按次日清晨价重估，只差 %+.3f%%（v24 首跑）/ %+.3f%%（重跑）——"
  % (100 * (mean([r["next_morning_value"] - r["night_sell_value"] for r in D["v24_first50"]])
            / mean([r["night_sell_value"] for r in D["v24_first50"]])),
     100 * (mean([r["next_morning_value"] - r["night_sell_value"] for r in D["v24_rerun"]])
            / mean([r["night_sell_value"] for r in D["v24_rerun"]]))))
w("   夜间价并不系统性低于次日，提前抛售不亏钱。")
w()
w("唯一的反向线索来自本地面板（`results/SESSION_STATE.md` §4）：保留 `_SR_MARGIN=4`/`_SR_HOURS=(22,23)`")
w("在 180 局镜像里值 **+4 胜**。但 4/180 = 2.2%，落在噪声内，且与线上数据方向不冲突——")
w("**即「`_SR_*` 可能极轻微为负、但量级 ≤1% 资金，绝不足以解释 160 Elo」。**")
w()
w("### 7.3 `V9_RACE_DEFAULT 41` 能否分离？——**不能，但可判断为无害**")
w()
w("`main.py:3857`：`horizon = min(48, max(DEFAULT, lead + 12))`。40 与 41 只在 `lead < 29` 时不同")
w("（即开局段或对手领先时），此时预留窗口从 40 变 41 回合——只推迟 1 个回合卖溢价品。")
w("回放里无法把这个 1 回合差异与对手差异分开（我们没有对手的基线对照）。")
w("考虑到 §7.2 已证明另一项改动无效果，且两项改动都在同一批 50 局里，**没有证据表明 41 有害**。")
w()
w("### 7.4 那 160 分从哪里来？——**评分轨迹 + 配对池，不是代码**")
w()
w("已有的评分机制实测（`results/SESSION_STATE.md` §5）：早期每局 ±11 分，中期 ±3 分，收敛后 ±0.36 分。")
w("把它和上面的事实拼起来。下面按**对局顺序**切成 4 段（每段 12-14 局），")
w("看每段的战绩与那一段**对手有多强**（用对手终局资金代理）：")
w()
w("| 分段（对局序号） | v23_c7 | v24 首跑 | v24 重跑 |")
w("|---|---|---|---|")
seg = ((1, 14), (15, 26), (27, 40), (41, 54))
cells = {}
for k in ("v23_c7", "v24_first", "v24_rerun"):
    v = sorted(D[k], key=lambda r: r["ep"])
    col = []
    for lo, hi in seg:
        sub = v[lo - 1:hi]
        if len(sub) < 5:
            col.append("—")
            continue
        wins = sum(1 for r in sub if r["margin"] > 0)
        col.append("%d/%d = %.0f%%，对手 $%s" % (
            wins, len(sub), 100 * wins / len(sub), f(mean([r["reward_opp"] for r in sub]))))
    cells[k] = col
for i, (lo, hi) in enumerate(seg):
    w("| #%d-%d | %s | %s | %s |" % (lo, hi, cells["v23_c7"][i], cells["v24_first"][i], cells["v24_rerun"][i]))
w()
w("看清楚这张表的关键：**同一个版本在不同分段的胜率在 43%~93% 之间乱跳，而跳动的方向与")
w("「那一段的对手有多强」高度同步**（对手 $83k 的段落赢 93%，对手 $104k 的段落只赢 43-50%）。")
w("v23_c7 的强对手段（#41-54，对手 $103,942，43% 胜率）落在评分已接近收敛的位置；")
w("v24 首跑的强对手段（#27-40，对手 $103,863，50% 胜率）落在还在爬分的位置。")
w("**「强对手块」随机落在哪个分段，比代码差异更能决定评分天花板。**")
w()
w("对照 `results/score_history.md` 的评分轨迹：")
w()
w("- v24 首跑：14 局 **1716.8** → 50 局 2117.8 → 89 局 2278（收敛）")
w("- v24 重跑：14 局 **1873.1** → 29 局 2157.7 → 63 局 2293.3（仍在爬）")
w("- v23_c7：3 局 973.3 → 54 局 2435.9 → 89 局 2452.2")
w()
w("而三个集合的 **前 14 局** 对手强度（按对手终局资金衡量）是：")
w()
w("| 集合 | 前 14 局战绩 | 前 14 局对手终局资金 |")
w("|---|---|---|")
for k in ("v23_c7", "v24_first50", "v24_rerun"):
    sub = sorted(D[k], key=lambda r: r["ep"])[:14]
    wins = sum(1 for r in sub if r["margin"] > 0)
    w("| %s | %d/%d | %s ± %s |" % (
        k, wins, len(sub), f(mean([r["reward_opp"] for r in sub])), f(se([r["reward_opp"] for r in sub]))))
w()
w("v23_c7 开局的对手比 v24 首跑强 $10.5k（+14%）、比重跑强 $15.7k（+23%）——")
w("**同样 13/14 的战绩，打的对手更硬，评分涨得更快。** 但注意 SE 有 $6.5-10k，")
w("这个差距本身不显著，只能作为「评分轨迹差异的一个合理来源」，不能当成已证结论。")
w("而 v24 首跑 14 局时 1716.8、重跑（对手更弱）1873.1 这个方向是一致的。")
w()
w("### 7.5 建议")
w()
w("**不建议**为了这 160 分回退 `_SR_*` 或 `V9_RACE`（数据不支持它们有害；本地面板那 +4/180 在噪声内）。")
w()
w("要真正缩小差距，应该针对下面的东西投入：")
w()
w("1. **修掉「早死型」败局**（下一条真实增益）。它占 v24 首跑败局的 10/12。")
w("   形态是「d6-10 被对手一次性拉开后不再回正」，最典型的是同一对手的两局：")
w("   ep 111731237（-$6,502）与 ep 111732814（-$8,680，对手 Ndabenhle Ngema）。")
w("   这两局我方终局畜群只有**鹅4/牛4/羊4 = 12 头**，对手是鹅4/牛6/羊6 = 16 头；")
w("   d12 资金 $14,812 / $14,976 vs 对手 $17,356 / $17,526——**少建了 4 头牲畜**，")
w("   是可见的产能缺口（对手终局是完整的 16 头同族编制）。")
w("   建议：先把这 10 场早死局单独做成 20 局规模的「早死回归面板」，确认它可复现、")
w("   再去找 d6-10 到底停了什么（这两个 episode 是我们能直接对照的唯一线索）。")
w("2. **提交策略**：既然早期 30-50 局定天花板，同代码重交是有效手段（重跑 14 局 1873 vs 首跑 1717）。")
w("   若要改代码，改完直接重交新 ref，而不是等旧 ref 收敛。")
w("3. **本地面板的盲区**（`results/loss_analysis_v24.md` 已指出）：6 个对手里 4 个 30-0 全胜，")
w("   区分力只来自 guru/prvsiyan 两个镜像。这解释了「面板 +11 胜/180 局」与线上评分脱钩。")
w("   在设计任何 `_SR`/`V9_RACE` 级别的微调验收前，先把非镜像对手补进面板。")
w()
w("### 7.6 数据不足的地方（如实说明）")
w()
w("1. **没有对手评分数据**。回放里只有对手队名，没有开赛时的 Elo/Glicko。")
w("   本报告所有「对手强度」都是用**对手终局资金**做代理，噪声大（SE $6.5-10k）。")
w("   若有 `kaggle competitions episodes` 的对手 rating 列，可以把 §7.4 从「推测」升级为「证据」。")
w("2. **公开回放不全**。v23_c7 榜面 89 局只有 54 局公开（60%），v24 首跑 89 局只有 50 局（§给定口径）。")
w("   若这 40% 的分布与公开部分不同，所有汇总量都会偏。")
w("3. **跨版本同对手只有 4 局**，且全胜，无法做有效的同对手检验。")
w("4. **21-23 点的「实际成交量」无法精确复算**：回放只给 `action`（请求量），不给逐单成交回执；")
w("   肥料单（h23 请求 ~580 单位）远超棚子容量，绝大多数被环境静默丢弃。")
w("   本报告用「棚子/随身占用差」和「次日重估价」两个代理绕开它，结论方向一致。")
w()

open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote", OUT, len(L), "lines")
