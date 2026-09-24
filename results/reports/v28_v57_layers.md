# v28 — 移植公开 V57 的「克制克隆」层（counter-D / seedfloat / 资金顺序不变量）

- **日期**：2026-09-23
- **基线**：v27（`sha256 4af6b0bad0155bea…`，7123 行）
- **候选**：`sha256 1ffa8782555cfa08…`（7419 行）
- **改动量**：追加约 236 行

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 改动 | ✅ **采纳** |
| 直接头对头 vs v27 | **98W-2L-0T（100 局，98.0%）** |
| 我方历史版本面板（4 个 × 40 种子 = 160 局） | **151/160（94.4%）** |
| 公开对手面板（17 对手 × 20 种子 × 双座位 = 680 局） | 632→**634/680（93.2%）**，且边际普遍改善 |
| 回调耗时 | mean 0.973→1.057 ms（+8.6%），**峰值 40.6→46.5 ms** |
| 冒烟 | ✅ `smoke OK` |

## 1. 动机（数据）

用户提出一个假设：**天梯上很多人用的就是这一份公开模型（或其微改版），所以胜率由"近似镜像局"决定。**

用我们自己的 115 局线上回放按"对手自己的开局签名"分类，假设成立且很极端：

| 对手类型 | 局数 | 战绩 | 胜率 | 平均边际 | 最差 |
|---|---|---|---|---|---|
| **克隆（开局签名与我们完全相同）** | **59（51%）** | 38-21 | **64.4%** | **+$527** | −$2,152 |
| 其他 | 56（49%） | 46-10 | 82.1% | +$16,963 | −$19,254 |

- **每两局就有一局是打自己**；
- 对克隆的边际（+$527）比对其他对手（+$16,963）**小 32 倍** —— 镜像局是靠几十到几百美元的微差决定的。

**结论：泛泛"变强"是在优化那 49%（已经 82% 胜率）；专攻镜像的 51% 才是杠杆。**
（复现：`scripts/mirror_share.py replays_v25 replays_v27`）

而公开 V57 新增的主层注释写的正是这件事：

> `counter D: exact best-response ordering against a copy of ourselves (shiiin9, 2026-09-18)`
> …against a V48 clone the rival's market list is exactly the list this stack produces before D
> touches it … so `_v44y_factor_margin` scores any ordering of our own list exactly.

## 2. 改动内容

从公开 V57（`ahmedberatozer/kaggriculture-v57-funding-order-invariant`，Apache-2.0）移植三块：

| 层 | 作用 |
|---|---|
| **counter-D**（`_cxd_*`） | 每回合在卖单槽位上做**有预算的最优反应搜索**（`_CXD_BUDGET=800`），用 `_v44y_factor_margin` 对"我方原始订单列表"打分——对克隆对手就是精确打分 |
| **seedfloat / knock**（`_33_SF_*` / `_33_KO*`） | 末期种子/化肥采购的浮动与敲出 |
| **资金顺序不变量**（`_V57_*`） | 固定价单（HIRE/BUY_SEED/BUY_ANIMAL/BUY_LAND）只能留在原位或后移，**绝不提前于父队列**——保护依赖资金的动作不被只对商品建模的排序器打乱 |

移植要点：V57 那块的父层是**自解析**的（`[v for v in list(globals().values()) if callable(v)][-1]`），
所以整块可以直接接到我们的链尾；只需删掉它开头的 `agent = e410_agent`（我们已有自己的链尾），
并在最后 `del agent` + 重定义，保证 `agent` 仍是命名空间最后一个可调用对象
（已验证 `mod.agent is last callable → True`）。

## 3. 实验方法

固定种子、单座位、配对；指标 = 胜/负/平 + 平均边际 + 最差边际。
**耗时检查先行**（`scripts/callback_timing.py`），因为 counter-D 每回合最多评估 800 个排序。

## 4. 结果

### 4.1 耗时（采纳门槛）

| | v27 | v28 |
|---|---|---|
| mean | 0.973 ms | 1.057 ms（+8.6%） |
| p95 | 1.987 ms | 2.247 ms |
| **峰值** | **40.6 ms** | **46.5 ms** |

公开作者自报 V55 峰值约 45 ms，我们落在同一档，**不是障碍**。

### 4.2 克制克隆（本层的目标）

| 对手（我方历史版本 = 克隆的最接近代理） | 战绩 | 平均边际 |
|---|---|---|
| v23_c7 | 37W-3L | +$422 |
| v25 | 37W-3L | +$410 |
| v26 | 38W-2L | +$350 |
| v27 | 39W-1L | +$173 |
| **合计** | **151/160（94.4%）** | +$339 |

### 4.3 公开对手面板（680 局）

| 对手 | v27 | v28 |
|---|---|---|
| guru | 38W-2L（+$312） | **40W-0L（+$466）** |
| prvsiyan | 38W-2L（+$233） | 38W-2L（**+$385**） |
| v55 | 38W-2L（+$184） | 38W-2L（**+$337**） |
| beatv48 | 38W-2L（+$3744） | 38W-2L（+$3744） |
| v51 / v52 / v53 / v49 / v50 | 32-8 / 30-10 / 34-6 | 同 |
| 其余 10 个对手 | 各 40W-0L | 各 40W-0L |
| **合计** | 632/680 | **634/680**，最差边际 −$1976 → −$1533 |

胜场只 +2（面板饱和），但**边际普遍改善 20–80%**——这才是本层起作用的地方。

## 5. 未验证风险（重要）

1. **迁移性**：本地 94.4% 的镜像优势能否转移到天梯的克隆类（线上 64.4%），**未经验证**。
   历史教训：v25 本地对 v23_c7 是 68.8%，线上分数反而更低。
2. **过拟合镜像**：本层专门优化"对手和我方订单列表一致"的情形。若线上克隆其实是**微改版**
   （订单列表已不同），打分器的精确性会下降。面板显示对公开 V5x 系（30-10、32-8）**无退化**，
   是弱证据。
3. **2 槽位窗口**：提交 v28 会顶掉较老的 v26（我们的当前最高分 2270.1），
   分数立刻变成 `max(v27 的 2240.7, v28 的新抽签)`。见 `results/SESSION_STATE.md` §〇之二。

## 6. 复现

```bash
.venv/Scripts/python scripts/mirror_share.py replays_v25 replays_v27     # 克隆占比与胜率
.venv/Scripts/python scripts/callback_timing.py --cand main.py --seeds 2000,2001,2002
.venv/Scripts/python scripts/tournament.py --candidate experiments/v28/v57_layers.py \
    --opponents experiments/v23c7_baseline.py experiments/v25/baseline_v25.py \
                experiments/v26/v26_baseline.py experiments/v28/v27_baseline.py \
    --seeds 2000-2039 --seats 0 --tag CLONE_PANEL_v28
.venv/Scripts/python scripts/tournament.py --candidate main.py --seeds 2000-2019
```
