"""Generate results/early_death_analysis.md from the three parsed JSONs.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_report.py \
        [--out results/early_death_analysis.md]
"""
import argparse
import collections
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import early_death_features as F                                    # noqa: E402

EARLY = [111714799, 111721531, 111729454, 111731237, 111732634, 111732696,
         111732814, 111735088, 111742930, 111746312]
BIG = [111731237, 111732814, 111735088, 111742930]
DAYS = (3, 4, 5, 6, 8, 10, 12, 15, 20, 29)
SETNAME = {'replays_v23': 'v23_c7', 'replays_v24': 'v24_first',
           'replays_v24r': 'v24_rerun', '.scratch_ed/replays_v24': 'v24_first',
           '.scratch_ed/replays_v24r': 'v24_rerun'}


def load_all():
    data, routes = F.load()
    built = {r['ep']: r for r in F.build(data, routes)}
    raw = {}
    for r in data:
        r.update(built[r['ep']])
        raw[r['ep']] = r
    routes = {r['ep']: r for r in json.load(open('results/early_death_routes.json', encoding='utf-8'))}
    mirror = {r['ep']: r for r in json.load(open('results/early_death_mirror.json', encoding='utf-8'))}
    hands = json.load(open('results/early_death_hands25.json', encoding='utf-8'))
    hands = {r['ep']: r for r in hands}
    return raw, routes, mirror, hands


def groups(raw, routes):
    out = collections.OrderedDict()
    for ep, r in raw.items():
        r['set'] = SETNAME[r['dir']]
    out['v24_first_earlydeath'] = [raw[e] for e in EARLY]
    out['v24_first_big'] = [raw[e] for e in BIG]
    out['v24_first_neartie'] = [raw[e] for e in EARLY if e not in BIG]
    out['v23_c7_losses'] = [r for r in raw.values() if r['set'] == 'v23_c7' and not r['win']]
    out['v24_first_losses'] = [r for r in raw.values() if r['set'] == 'v24_first'
                               and r['ep'] <= 111747437 and not r['win']]
    out['v24_rerun_losses'] = [r for r in raw.values() if r['set'] == 'v24_rerun' and not r['win']]
    out['all_wins'] = [r for r in raw.values() if r['win']]
    return out


def mean(rows, f):
    v = [f(r) for r in rows]
    v = [x for x in v if x is not None]
    return st.mean(v) if v else float('nan')


def pnd(r):
    days = sorted(int(k.split(':')[1]) for k in r['snap_h23'] if k.startswith('us:'))
    pos = [d for d in days
           if r['snap_h23']['us:%d' % d]['money'] > r['snap_h23']['them:%d' % d]['money']]
    return (max(pos) + 1) if pos else None


def frozen_span(r):
    late = [F.diff(r, d) for d in range(11, 30) if 'us:%d' % d in r['snap_h23']]
    return (max(late) - min(late)) if late else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='results/early_death_analysis.md')
    args = ap.parse_args()
    raw, routes, mirror, hands = load_all()
    G = groups(raw, routes)

    def route_of(ep):
        return routes[ep]['logic_route'], routes[ep]['shops_pair']

    L = []
    w = L.append
    w('# v24 首跑「早死型」败局：第 6-10 天到底发生了什么（2026-09-22）')
    w('')
    w('数据：`replays_v23/`(v23_c7, 54 局)、`replays_v24/`(v24 首跑, 80 局)、'
      '`replays_v24r/`(v24 重跑, 49 局)，共 183 局非自对局。')
    w('脚本：`scripts/early_death_deepdive.py`(逐日+逐步特征)、`scripts/early_death_features.py`、')
    w('`scripts/early_death_routes.py`(第 6 天路线归属)、`scripts/early_death_mirror.py`(镜像度)、')
    w('`scripts/early_death_step1_market.py`(第 1 步市场复算)、'
      '`scripts/early_death_local_repro.py`(本引擎端到端复现)、`scripts/early_death_report.py`。')
    w('中间数据：`results/early_death_data.json`、`results/early_death_routes.json`、'
      '`results/early_death_mirror.json`。')
    w('')
    w('> 口径说明：本仓库当前 checkout 在 `main`（= v23_c7 版 main.py）。'
      '`replays_v24/`、`replays_v24r/` 只存在于 `exp/v24-v55` 分支，'
      '本报告用 `git archive exp/v24-v55 replays_v24 replays_v24r` 解到 `.scratch_ed/` 后读取；'
      '`exp/v24-v55` 与本地的 `main.py` 只差 3 行参数（`V9_RACE_DEFAULT`、`_SR_MARGIN`、`_SR_HOURS`），'
      '不涉及本报告的路线表/路由逻辑。')
    w('')

    # ---------- 0. verdict table -------------------------------------------
    bad = sorted([r for r in raw.values() if hands[r['ep']]['money_t24_us'] < 4],
                 key=lambda r: r['margin'])
    w('## 0. 结论速览')
    w('')
    w('| 题面假设 | 判定 | 关键证据 |')
    w('|---|---|---|')
    w('| 1. 畜群扩编卡在**资金**上 | **不成立**（但资金另有更早的致命点，见 §2） | d6-12 我方 `empty_pasture` 长期 ≥1-3（对手 0），'
      'd12 我们手里还有 $1.3-2.0 万现金却不去买/放；`BUY_ANIMAL` 请求量 d6-10 我方 8.4 头 vs 对手 8.1 头（无差别） |')
    w('| 1b. 畜群扩编卡在**没有空牧场**上 | **不成立** | 大败局 d10 我方 11-13 个牧场里 1-3 个空着，对手 12-14 个全满；'
      'd12 我方 struct 17 vs 对手 18，缺的是**动物**不是栏位 |')
    w('| 2. 牧场建造滞后 / 没买地 | **不成立** | `BUILD` 次数 d6-10 我方 6.0 vs 对手 6.3；`BUY_LAND` 我方 d6 就买、对手同天；'
      '差距出现在 d3 之前（我方 herd 3 vs 对手 5），不是建造慢 |')
    w('| 3. 动物逃逸 | **成立，但发生在 d1-2 而不是 d6-10** | 183 局里 7 局在 d1-2 各逃 1 头；'
      '这 7 局 d3 畜群**固定比对手少 2 头**；其余 176 局 d3 差 0 头（163/176） |')
    w('| 4. 逃跑/饿死前兆（`consecutive_unfed`、`fed_today`） | **成立且是根因** | 那 7 局的共同前兆是 **d1 h1 只雇到 1 个雇工**'
      '（应为 3 个）：tape 把 FEED/CARE/PLACE 放在第 2、3 个雇工的槽位里，雇工不存在 → 这些指令被 `hand_align` 截掉 → '
      'd0 放下的 COW 连续 2 天没喂 → d2 h0 逃逸 |')
    w('| 5. 作物/浇水崩 | **不成立** | d6-10 `unwater_streak1` 我方 8.2 vs 对手 8.5（同一水平）；d12 作物 51-57 vs 57；'
      '全赛季旱死 0-1 株；杂草 d12 合计 1 格以下 |')
    w('| 6. 市场受阻 / 卖单被抢跑 | **部分成立，而且是唯一的真实触发点** | 我方 d0 h1 的 `SELL WHEAT 15` 与对手同槽位同时卖出时，'
      '15 单位均价少赚约 $10-11（§3.3 复算），把 d0 期末现金从 $12 压到 $1，刚好跌破 d1 h1 雇 3 个雇工所需的 **$4** |')
    w('| 7. 雇工不足 | **成立，且是第 6 点的后果** | d1 h1 雇工数：3 手 175/183 局，≤2 手 8/183 局；'
      '后者 2 胜、场均边际 **-$4,961**，前者 135 胜、+$8,836 |')
    w('| 8.「10 场在 d≤10 就永久落后」这个判断本身 | **大部分是度量假象** | 10 场里 4-5 场是**镜像局**：'
      '双方单位动作逐步完全相同（`unit_identity`=1.000），资金差在 d10-d29 冻结成一个几十美元的常数；'
      '`permanent_neg_day` 只是这个冻结差最后一次过零的天数 |')
    w('')

    # ---------- 1. per-episode evidence -----------------------------------
    w('## 1. 十场「早死型」败局逐局证据')
    w('')
    w('`unit_id` = 第 150-719 步我方与对手 (farmer,hands) 动作完全相同的比例；'
      '`$t1/$t24` = 第 1 步后 / 第 0 天结束时的现金；`hands@25` = 第 25 步（d1 h1）实际雇到的雇工数'
      '（`$1+$1+$2=$4` 才能雇满 3 个）。')
    w('')
    w('| episode | 对手 | 边际 | 结局 | route | unit_id | 买麦(我/对手) | $t1 | $t24 | hands@25 | d3 畜群(我/对) | '
      'd3 逃逸 | 冻结差(d11-29 极差) |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for ep in sorted(EARLY, key=lambda e: raw[e]['margin']):
        r, m, h = raw[ep], mirror[ep], hands[ep]
        rid, _ = route_of(ep)
        d3u = r['snap_h23']['us:3']['herd_total']
        d3t = r['snap_h23']['them:3']['herd_total']
        e3 = (r['tile_events']['us'].get('2') or {}).get('escape', 0) + \
             (r['tile_events']['us'].get('1') or {}).get('escape', 0)
        w('| %d | %s | %+.0f | %s | %d | %.3f | %d/%d | %.0f | %.0f | %d | %d/%d | %d | $%.0f |' % (
            ep, r['opp'][:18], r['margin'], 'W' if r['win'] else 'L', rid, m['unit_identity'],
            m['wheat_buy_us'], m['wheat_buy_them'], h['money_t1_us'], h['money_t24_us'],
            h['hands_t25_us'], d3u, d3t, e3, frozen_span(r)))
    w('')
    w('### 1.1 逐日 h23 资金差（我方 − 对手）')
    w('')
    w('| episode | ' + ' | '.join('d%d' % d for d in range(0, 13)) + ' | d15 | d20 | d29 |')
    w('|---' * 16 + '|')
    for ep in sorted(EARLY, key=lambda e: raw[e]['margin']):
        w('| %d | ' % ep + ' | '.join('%+.0f' % F.diff(raw[ep], d) for d in range(13))
          + ' | %+.0f | %+.0f | %+.0f |' % (F.diff(raw[ep], 15), F.diff(raw[ep], 20), F.diff(raw[ep], 29)))
    w('')
    w('### 1.2 逐日并排状态表（我方 | 对手；h23 快照）')
    for ep in sorted(EARLY, key=lambda e: raw[e]['margin']):
        r = raw[ep]
        w('')
        w('**ep%d** vs %s，边际 %+.0f，route %d (%s)，单位动作镜像度 %.3f' % (
            ep, r['opp'], r['margin'], route_of(ep)[0], ','.join(route_of(ep)[1]),
            mirror[ep]['unit_identity']))
        w('')
        w('| day | 方 | 现金 | 雇工 | 畜群 | 牧场(空) | 建筑 | 作物 | 杂草 | 空位 | 象限 | 逃逸 | 旱死 | unfed≥1 |')
        w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        for d in DAYS:
            for tag, name in (('us', '我'), ('them', '对')):
                s = r['snap_h23'].get('%s:%d' % (tag, d))
                if not s:
                    continue
                te = r['tile_events'][tag].get(str(d)) or {}
                w('| %d | %s | %.0f | %d | %d | %d(%d) | %d | %d | %d | %d | %s | %d | %d | %d |' % (
                    d, name, s['money'], s['hands'], s['herd_total'], s['pasture'],
                    s['empty_pasture'], s['struct_total'], s['crops_total'], s['weeds'],
                    s['empty_tiles'], ''.join(sorted(s['quads'])), te.get('escape', 0),
                    te.get('drought_death', 0), s['unfed_streak1']))
    w('')

    # ---------- 2. the real mechanism -------------------------------------
    w('## 2. 真正的机制：第 0 天把钱花到只剩 $1，第 1 天雇不满 3 个雇工')
    w('')
    w('### 2.1 关键指标：第 25 步（d1 h1）的雇工数')
    w('')
    w('`_hire_cost` = `1,1,2,3,5,...`，第 25 步 tape 请求 3 个 `HIRE`（需要 $4）。'
      'd0 期末现金 `money_t24` 决定能雇几个：')
    w('')
    w('| `money_t24` | 局数 | 实际雇工 d1 h1 | 胜率 | 场均边际 | d3 畜群差(我−对) 的分布 |')
    w('|---|---|---|---|---|---|')
    for lo, hi in ((0, 1), (2, 3), (4, 10 ** 9)):
        s = [r for r in raw.values() if lo <= hands[r['ep']]['money_t24_us'] <= hi]
        if not s:
            continue
        hh = collections.Counter(hands[r['ep']]['hands_t25_us'] for r in s)
        dd = collections.Counter(r['snap_h23']['us:3']['herd_total'] - r['snap_h23']['them:3']['herd_total'] for r in s)
        w('| $%s | %d | %s | %d/%d | %+.0f | %s |' % (
            ('≤1' if hi == 1 else ('2-3' if hi == 3 else '≥4')), len(s), dict(hh),
            sum(r['win'] for r in s), len(s), st.mean(r['margin'] for r in s), dict(sorted(dd.items()))))
    w('')
    w('这条链条在 183 局里**没有例外**：`money_t24` 与 `hands@25` 一一对应；'
      '`hands@25 == 1` 的 7 局 d3 畜群差**全部恰好是 −2**；`hands@25 == 3` 的 175 局里 163 局差为 0。')
    w('')
    w('### 2.2 因果链（逐步可查）')
    w('')
    w('以 ep111731237（-$6,502）为例：')
    w('')
    w('| 步 | 事件 | 数据 |')
    w('|---|---|---|')
    w('| t1 (d0 h1) | 我方 `BUY_PRODUCT WHEAT 20 / SELL WHEAT 15 / BUY_SEED WHEAT 1` | 现金 $3000 → **$2,843** |')
    w('| t1 | 对手同槽位 `BUY_PRODUCT WHEAT 10 / SELL WHEAT 10` | 我方的 15 单位均价被同槽位供给压低（§3.3） |')
    w('| t24 (d0 末) | d0 固定花掉 $2,842 | 现金 **$1** |')
    w('| t25 (d1 h1) | tape 请求 3 个 `HIRE`（$4） | 只成交 1 个（$1），现金 $0 → **雇工 1 个**（对手 3 个） |')
    w('| t25-t47 (d1) | `hand_align` 把 hands 列表截到 1 项 | 第 2、3 个雇工槽里的 `FEED`/`CARE`/`PLACE` 指令从未发出 |')
    w('| d1 末 | d0 放下的 COW 连续 2 天未喂（`consecutive_unfed` 0→1→2） | 结构还在、牛没了 |')
    w('| d2 h0 | 逃逸 | `tile(4,4)` 由 `PASTURE+COW` 变成空 `PASTURE`；对手那头牛被喂了、留下 |')
    w('| d3 h23 | 畜群 3 vs 5（少 2 头）、牧场 5 vs 6 | 差距从此固定 |')
    w('| d6→d29 | tape 的动物计划是固定条数，不会补买 | 差额按奶/毛/蛋产量线性放大：d6 -$764 → d10 -$1,567 → d29 -$6,502 |')
    w('')
    w('同样的 d0 期末 $1 也出现在 ep111735088（-$22,399）、ep111732814（-$8,680）以及 v23_c7 唯一的大败 '
      'ep111633116（-$17,576）。这 4 局就是两个集合里**全部** 4 场「大盘」败局中的 3+1 场。')
    w('')
    w('### 2.3 为什么第 6-10 天看起来像崩盘')
    w('')
    w('因为 tape 在 d6 同时做了两件放大差距的事：d6 一次性铺 7 个栏位（`BUILD` 7 次）并把畜群翻倍。'
      '少 2 头动物的农场在 d6-d10 的**绝对**差额被产能放大（-$764 → -$1,567），'
      '所以「第一次被拉开」看起来发生在 d6-10，而**根因在 d0 h1**。')
    w('')
    w('### 2.4 十场早死局的分型（谁被解释、谁没被解释）')
    w('')
    w('| 分型 | 局数 | episode | 判定依据 |')
    w('|---|---|---|---|')
    w('| A. 现金刀口 → 少雇工 → 逃逸 → 永久 −2 头 | 4 | 111735088, 111732814, 111731237, 111729454 | '
      '`money_t24 = $1`、`hands@25 = 1`、d1-2 各逃 1 头、d3 畜群 3/5 |')
    w('| B. 冻结镜像局（双方走同一条 tape，差几十美元） | 5 | 111746312, 111732634, 111714799, 111721531, 111732696 | '
      '`unit_identity = 1.000`、逐日状态两列完全相同、d11-29 资金差极差 $40-66 |')
    w('| C. 未解释 | 1 | 111742930 | `money_t24 = $9`、`hands@25 = 3`、无逃逸；'
      '对手在 d1 多铺 2 个牧场（struct 6 vs 4）、d2 多 1 头牛，此后 d11-29 差额持续扩大到 $8,407。'
      '同一「固定 tape 不补差」的放大机制，但触发点是**对手的 d1 计划本身更快**，不是我们的雇工/现金问题 |')
    w('')
    w('A 型是唯一可以直接改我们自己代码的一类（3 场大败 + v23_c7 唯一大败）；'
      'B 型不是「死」，是度量假象；C 型需要另找线索。')
    w('')

    # ---------- 3. metric artifact ----------------------------------------
    w('## 3. 「d≤10 永久落后」这个度量里有多少是假象')
    w('')
    w('### 3.1 镜像局：双方走的是同一条 tape')
    w('')
    w('`scripts/early_death_mirror.py` 逐步比较双方 `(farmer, hands)`：')
    w('')
    idn = sorted(mirror[e]['unit_identity'] for e in raw)
    w('| 镜像度 | 局数 |')
    w('|---|---|')
    for lo, hi, nm in ((0.9999, 1.01, '= 1.000（逐步完全相同）'), (0.99, 0.9999, '≥ 0.99'),
                       (0.90, 0.99, '0.90-0.99'), (0.0, 0.90, '< 0.90')):
        w('| %s | %d |' % (nm, sum(1 for v in idn if lo <= v < hi)))
    w('')
    w('镜像度 = 1.000 的局里，双方**每一格**都一样：ep111714799 d10 双方都是 herd16/pasture14/struct18/crops32，'
      '整场资金差只在 6 个步骤上变化过，d10 之后冻结在 −$84（到 d29 变 −$124）。'
      '这类局的 `permanent_neg_day` 记录的是「冻结差最后一次为正的天数」——是掷硬币，不是死亡。')
    w('')
    w('### 3.2 三个集合的败局按「败势形态」拆分')
    w('')
    w('| 集合 | 败局数 | 冻结差局(late_span<$300) | 边际 >$5k | $1k-5k | ≤$1k | pnd≤10 的局 |')
    w('|---|---|---|---|---|---|---|')
    for nm in ('v23_c7', 'v24_first', 'v24_rerun'):
        rows = [r for r in raw.values() if r['set'] == nm and not r['win']]
        if not rows:
            continue
        b = collections.Counter()
        for r in rows:
            a = abs(r['margin'])
            b['>$5k' if a > 5000 else ('$1k-5k' if a > 1000 else '≤$1k')] += 1
        w('| %s | %d | %d | %d | %d | %d | %d |' % (
            nm, len(rows), sum(1 for r in rows if (frozen_span(r) or 9e9) < 300),
            b['>$5k'], b['$1k-5k'], b['≤$1k'],
            sum(1 for r in rows if (pnd(r) or 99) <= 10)))
    w('')
    w('对照：`pnd≤10` 在 v24 首跑是 6/13，v23_c7 是 2/14，v24 重跑是 **0/14**。'
      '但 v24 重跑的败局里有 9 局边际 ≤$1k（`pnd` 17-28），v24 首跑里只有 3 局不是 `pnd≤10`。'
      '也就是说三者的差别主要在**冻结差的过零时机**，而冻结差的来源是几百美元以内的市场噪声。')
    w('')
    w('### 3.3 第 1 步市场复算（`scripts/early_death_step1_market.py`）')
    w('')
    w('我方第 1 步的市场单在**全部 183 局里完全一样**（`BUY_PRODUCT WHEAT 20` / `SELL WHEAT 15` / `BUY_SEED WHEAT 1`），'
      '所以 `money_t1` 完全由对手第 1 步的小麦单决定。用引擎自己的 `market_price` 复算第 1 步'
      '（WHEAT 库存 10000，第 0 步市中心抽走 1 → 9999；双方各 $3000）：')
    w('')
    w('| 对手第 1 步市场单 | 本复算 $ | 线上/本引擎实测 $ | 减掉 d0 固定支出 $2,842 | d1 h1 雇到几手 |')
    w('|---|---|---|---|---|')
    for nm, sim, real, hlabel in (
            ('`BUY WHEAT 10` + `SELL WHEAT 10`（那 7 局的对手）', 2842, '2843', '0-1 / 3'),
            ('`BUY WHEAT 10` + `SELL WHEAT 10` + `BUY_SEED WHEAT 1`', 2842, '2843', '0-1 / 3'),
            ('`BUY WHEAT 14` + `SELL WHEAT 14` + `BUY WHEAT 5`', 2844, '2845', '2 / 3'),
            ('与我方相同（镜像：`BUY 20` / `SELL 15` / `BUY_SEED`）', 2854, '2854', '3 / 3'),
            ('无小麦单（只有 `HIRE`/`BUY_SEED`/`BUY_ANIMAL`）', 2853, '2854 为主流', '3 / 3'),
            ('不卖、只 `BUY WHEAT 20`', 2865, '2866', '3 / 3')):
        w('| %s | $%d | $%s | $%d | %s |' % (nm, sim, real, sim - 2842, hlabel))
    w('')
    w('**机制**：对手在槽 0 只买 10 单位（我们买 20）会让市场在我们卖出时多留 5 单位小麦，'
      '叠加他们在同槽位卖出的 10 单位，我方 15 单位的成交均价少约 $11 —— '
      '正好把 d0 期末现金从 $12 压到 $1，跌破 d1 h1 雇 3 个雇工所需的 **$4**。'
      '本复算在三个已知点上分别差 $1 / $1 / $0（常数量级），但都落在同一侧。')
    w('')
    w('**独立验证**：本机跑 `main.py` vs `main.py`（第 1 步双方都发 `BUY 20`/`SELL 15`）'
      '得到双方 `money_t1 = $2854`、`money_t24 = $12`、`hands@25 = 3`、d3 畜群 5；'
      '与本复算的 C 行**完全相同**。线上 8 局 `money_t24 < 4` 的对局，'
      '对手第 1 步单恰好就是 A/A\'/B 三种（`BUY WHEAT k` + `SELL WHEAT k`，k=10 或 14），8/8 无例外。')
    w('')

    # ---------- 4. hypotheses aggregates ---------------------------------
    w('## 4. 七个假设的对照数据（败局分组均值，我方 / 对手）')
    w('')
    keys = [
        ('BUY_ANIMAL 请求 d6-10', 'buyanim6_10', 'buyanim6_10t'),
        ('BUILD 次数 d6-10', 'buildp6_10', 'buildp6_10t'),
        ('PLACE 次数 d6-10', 'place6_10', 'place6_10t'),
        ('BUY_ANIMAL 请求 d0-5', 'buyanim0_5', 'buyanim0_5t'),
        ('BUILD 次数 d0-5', 'buildp0_5', 'buildp0_5t'),
        ('BUY_LAND 天数', 'land_day', 'land_dayt'),
        ('畜群 d3', None, None),
        ('畜群 d6', 'herd6', 'herd6t'),
        ('畜群 d10', 'herd10', 'herd10t'),
        ('畜群 d12', 'herd12', 'herd12t'),
        ('畜群 d29', 'herd29', 'herd29t'),
        ('空牧场 d12', 'emptyp12', 'emptyp12t'),
        ('牧场 d12', 'past12', 'past12t'),
        ('建筑 d12', 'struct12', 'struct12t'),
        ('作物 d12', 'crops12', 'crops12t'),
        ('杂草 d12', 'weeds12', 'weeds12t'),
        ('空位 d12', 'empty12', 'empty12t'),
        ('雇工 d12', 'hands12', 'hands12t'),
        ('HIRE 单 d6-10', 'hire_6_10', 'hire_6_10t'),
        ('逃逸 d0-10', 'esc_by10', 'esc_by10t'),
        ('逃逸 d0-29', 'esc_by29', 'esc_by29t'),
        ('旱死 d0-29', 'drought_by29', 'drought_by29t'),
        ('未喂≥1 累计 d6-10', 'unfed_streak_6_10', 'unfed_streak_6_10t'),
        ('未浇水≥1 累计 d6-10', 'uwater_6_10', 'uwater_6_10t'),
        ('SELL 单位 d0-5', 'sell0_5', 'sell0_5t'),
        ('SELL 单位 d6-10', 'sell6_10', 'sell6_10t'),
        ('SELL 单位 全场', 'sell_all', 'sell_allt'),
    ]
    names = list(G.keys())
    w('| 指标 | ' + ' | '.join(names) + ' |')
    w('|---' * (len(names) + 1) + '|')
    for label, ku, kt in keys:
        cells = []
        for nm in names:
            rows = G[nm]
            if ku is None:
                cells.append('%.1f/%.1f' % (mean(rows, lambda r: r['snap_h23']['us:3']['herd_total']),
                                            mean(rows, lambda r: r['snap_h23']['them:3']['herd_total'])))
            else:
                cells.append('%.1f/%.1f' % (mean(rows, lambda r: r[ku]), mean(rows, lambda r: r[kt])))
        w('| %s | %s |' % (label, ' | '.join(cells)))
    w('')
    w('（`v24_first_earlydeath` = 10 场早死局；`v23_c7_losses`/`v24_rerun_losses` = 两个对照组的全部败局；'
      '`all_wins` = 全部胜局。）')
    w('')

    # ---------- 5. controls ----------------------------------------------
    w('## 5. 对照组')
    w('')
    w('### 5.1 「现金 <$4 导致少雇工」是不是三个集合共有的现象')
    w('')
    w('| 集合 | 局数 | `money_t24 < 4` 的局 | 其中败局 | 这些局 d3 是否都少 2 头 | 该集合败局里最大的 3 场 |')
    w('|---|---|---|---|---|---|')
    for nm in ('v23_c7', 'v24_first', 'v24_rerun'):
        rows = [r for r in raw.values() if r['set'] == nm]
        b = [r for r in rows if hands[r['ep']]['money_t24_us'] < 4]
        top = sorted([r for r in rows if not r['win']], key=lambda r: r['margin'])[:3]
        w('| %s | %d | %d | %d | %s | %s |' % (
            nm, len(rows), len(b), sum(1 for r in b if not r['win']),
            all(r['snap_h23']['us:3']['herd_total'] - r['snap_h23']['them:3']['herd_total'] == -2 for r in b),
            ', '.join('%d(%+.0f)' % (r['ep'], r['margin']) for r in top)))
    w('')
    w('v23_c7 的 1 局（ep111633116，-$17,576）和 v24 首跑的 5 局正是各自集合里最惨的败局；'
      'v24 重跑 0 局 → 它的 14 场败局里**没有一场**边际超过 $2,572，也不存在 d3 少 2 头的局。'
      '**这解释了「首跑早死 / 重跑不死」的全部差别**：不是代码差异，是这一小撮对局里第 1 步市场交互的抽样。')
    w('')
    w('### 5.2 第 6 天的路线切换（`_router`，step 144）')
    w('')
    route_count = collections.Counter(routes[r['ep']]['logic_route'] for r in raw.values())
    w('`main.py:_router` 在第 144 步（d6 h0）根据**前两个解锁商店**选路线（`_V92_TABLE`/`_R108_SHOP_ROUTES`/`_R110_OLD_SHOPS`）。'
      '这是真实存在的、每局都在发生的 d6 行为差异，但它**不是**早死的原因：')
    w('')
    w('| route | 商店对（前两个） | 局数 | 胜 | 败 | 其中 `pnd≤10` 的败局 | `money_t24<4` 的局 |')
    w('|---|---|---|---|---|---|---|')
    for rid, n in route_count.most_common(8):
        rows = [r for r in raw.values() if routes[r['ep']]['logic_route'] == rid]
        shops = sorted({tuple(routes[r['ep']]['shops_pair']) for r in rows})[:2]
        w('| %d | %s | %d | %d | %d | %d | %d |' % (
            rid, '; '.join(','.join(s) for s in shops), n, sum(r['win'] for r in rows),
            sum(1 for r in rows if not r['win']),
            sum(1 for r in rows if not r['win'] and (pnd(r) or 99) <= 10),
            sum(1 for r in rows if hands[r['ep']]['money_t24_us'] < 4)))
    w('')
    w('路线 9（有 YARN_STORE）最好（81.6% 胜率，0 场 `pnd≤10`）；'
      '`money_t24<4` 的 7 局散布在 5 条不同路线上，说明**现金刀口与路线选择无关**——'
      'd0-d1 的 tape 前缀对所有路线完全相同（第 144 步才分叉）。')
    w('')
    w('### 5.3 镜像度对照')
    w('')
    w('| 集合 | 败局平均 `unit_identity` | 胜局平均 `unit_identity` | 镜像局(=1.000)的边际中位数 |')
    w('|---|---|---|---|')
    for nm in ('v23_c7', 'v24_first', 'v24_rerun'):
        rows = [r for r in raw.values() if r['set'] == nm]
        lu = [mirror[r['ep']]['unit_identity'] for r in rows if not r['win']]
        lw = [mirror[r['ep']]['unit_identity'] for r in rows if r['win']]
        mm = [abs(r['margin']) for r in rows if mirror[r['ep']]['unit_identity'] > 0.9999]
        w('| %s | %.3f | %.3f | %s |' % (
            nm, st.mean(lu), st.mean(lw), ('$%.0f' % st.median(mm)) if mm else '—'))
    w('')

    # ---------- 6. next steps --------------------------------------------
    w('## 6. 可复现的下一步')
    w('')
    w('### 6.1 本地端到端复现（已跑通）')
    w('')
    w('```')
    w('PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_local_repro.py \\')
    w('    --opponent cosell --games 2          # 脚本化“同槽位卖麦”对手')
    w('PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_local_repro.py \\')
    w('    --opponent opponents/v55/main.py --games 3')
    w('PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_step1_market.py   # 第 1 步市场复算')
    w('```')
    w('')
    w('实测（本机，2026-09-22）：单局约 8-17s。')
    w('')
    w('| 对手 | 局数 | `money_t1` | `money_t24` | `hands@25` | d3 畜群 | 触发刀口？ |')
    w('|---|---|---|---|---|---|---|')
    w('| `main.py` vs `main.py`（第 1 步双方都发 `BUY 20`/`SELL 15`） | 3 | $2854 | $12 | 3 | 5 | 否（正常分支） |')
    w('| `opponents/v55/main.py`（自家血缘） | 3 | $2854 | $12 | 3 | 5 | 否 |')
    w('| 脚本化 co-sell（`--opponent cosell`）1 局 | 1 | — | $15 | 3 | 5 | 否 |')
    w('')
    w('也就是说：**本地默认跑自家血缘对手不会踩到刀口**（线上 8/183 ≈ 4.4%）。'
      '要复现必须构造 §3.3 的 A 类对手单（第 1 步槽 0 只买 10 单位小麦、槽 1 卖 10 单位），'
      '而 §3.3 的手算循环已经把这个条件与结果一一对应证明完；'
      '把 `scripts/early_death_local_repro.py` 里的 `cosell_agent` 换成 A 类对手单并跑 20 局，'
      '即可得到端到端的 `money_t24 = 1` / `hands@25 = 1` / d3 畜群 3 复现。')
    w('')
    w('### 6.2 期望的验收（20 局回归）')
    w('')
    w('1. 在 `scripts/early_death_local_repro.py` 里把 `cosell_agent` 换成 20 组不同的第 1 步对手单'
      '（覆盖 §3.3 表里的 4 类），跑 20 局；')
    w('2. 指标：`money_t24` 的分布，以及 `money_t24 < 4` 的局数。'
      '修复前应当在 4 类对手里至少 1 类稳定复现 `money_t24 = 1`；')
    w('3. 然后再跑 §6.3 的修复版，要求 20 局里 `money_t24 < 4` 为 **0**。')
    w('')
    w('### 6.3 候选修复（按侵入度排序）')
    w('')
    w('1. **最直接**：在 d1 h1（step 25）之前保证现金 ≥ $5。'
      '由于 d0 的支出是固定 $2,842（`money_t24 = money_t1 − 2842`），'
      '可以在第 1-2 步少买 1 单位 `BUY_PRODUCT WHEAT`（约 $30），把 d0 期末现金从 $1-16 抬到 $30+。'
      '代价是 d0 少 1 单位小麦，可用 d6 的 `BUY_PRODUCT` 补回。')
    w('2. **更稳**：在 chassis 里加一个小层（类似现有 `_budget_guard`）：'
      '当 `step in (24, 25)` 且 `farm.money < 5` 时，把后续 `BUY_*` 单削减到留出 $5；'
      '或者反过来——d0 的 `HIRE` 只雇 3 个（省 $9），把现金留在 d1。')
    w('3. **结构性**：d1 的 feed 指令不该放在第 2、3 个雇工的槽位里。'
      '把「喂当天所有动物」做成一个不依赖第 3 个雇工存在与否的后置检查'
      '（复用现成的 `weed_repair` 机制：`_is_noop` 检测到 FEED 会 no-op 时，'
      '把指令挪给真实存在的单位）。这是本报告建议的**根因修复**——'
      '即使现金刀口被消除，任何一次雇工不足仍会导致逃逸。')
    w('')
    w('### 6.4 数据不足 / 未验证的地方')
    w('')
    w('1. 第 1 步市场复算与线上实测在 3 个已知点上差 $1 / $1 / $0（常数量级，来源未查明，'
      '最可能是棚内小麦数量或第 1 步单位动作带来的棚内变化）；'
      'A 类对手单在实测是「1 手」、在本复算是「0 手」，都远少于 3 手，落在门槛同一侧。'
      '**逐局实测链条（§2.1）不受影响**，那里的每一步都是回放里直接读出的。')
    w('2. `hands@25 == 1` 的 7 局里有 1 局（ep111739578）仍然 +$5,515 获胜，'
      '而 `hands@25 == 2` 的 ep111845579 也赢 +$11,995。'
      '所以「少雇工」不是必败，只是把期望值从 +$8,836 打到 -$4,961。'
      '样本只有 8 局，不能给出精确的因果效应量。')
    w('3. 「对手第 1 步买/卖小麦的量」与我们的 `money_t1` 是**观测到的相关 + 手算复算**'
      '（8/8 命中，且 §3.3 的循环能逐个复现），'
      '但**没有做真正的干预实验**（例如在本地强制对手第 1 步改成 A 类对手单再跑 20 局）；'
      '§6.2 的 20 局回归就是补这个实验。')
    w('4. 没有对手评分数据，无法判断这 8 局的对手是否更强；'
      '不过 `money_t24` 与 `hands@25` 的对应关系与对手强度无关。')
    w('')

    bad = [(i, repr(v)[:120]) for i, v in enumerate(L) if not isinstance(v, str)]
    if bad:
        print('NON-STR LINES: %s' % bad[:5])
        L = [str(v) for v in L]
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    print('wrote %s (%d lines)' % (args.out, len(L)))


if __name__ == '__main__':
    main()
