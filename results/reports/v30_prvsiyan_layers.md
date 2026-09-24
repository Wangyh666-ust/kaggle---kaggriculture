# v30 — 移植 prvsiyan 的 R148 / ADV / IG 三层：**命中镜像域，但踩了胜率**（预登记门槛未通过）

- **日期**：2026-09-23
- **分支**：`fix/early-death`（未提交，未 push）
- **基线**：`main.py`（= v28，`sha256 1ffa8782555cfa08…`，7374 行，**本次未改动**）
- **候选**：`experiments/v30/prvsiyan_layers.py`（`sha256 e6111d841f4962a0…`，7751 行，**+377 行**，纯追加）
- **消融控件**：`experiments/v30/{ctl,abl_adv,abl_r148,abl_ig,abl_adv_r148}.py`
- **来源**：公开 notebook `prvsiyan/kaggriculture-frontier-the-soil-remembers-rain`（105 赞，2026-09-23 重跑），抽取文件 `tmp_extract/prvsiyan_frontier.py`，移植区间 **行 6758–7121**（`# R148: overflow reclaim` … `agent.telemetry = _IG_REPORT`）

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 改动 | ❌ **否决**（预登记门槛未通过：4 条里过 2 条） |
| 门槛 1（总胜 ≥ 119/120） | ❌ **失败**：`115 → 103/120`（两块种子池分别 103、108） |
| 门槛 2（mean ≥ +$520） | ✅ **通过**：`+$434 → +$1072` |
| 门槛 3（worst ≥ −$405） | ❌ **失败**：A 池 −$217（过），**B 池 −$952（破线）** |
| 门槛 4（镜像 ≥ 60%） | ✅ **通过**：`78/100 (78.0%)`、`72/100 (72.0%)`，合并 150/200 |
| 逐层归因 | **R148 几乎不触发（3/40 局，每局 1 回合）且为负**；**IG-opening 从不触发（0）**；IG-queue 触发但零收益；**ADV 是全部效应来源** |
| 机制 | ADV **不提高我们自己的收入**（我方 reward Δ `−$63 / +$61`），**只压低对手**（对手 reward Δ `−$701 / −$426`）——纯零和抽取层 |
| 回调耗时 | mean `1.929 → 2.189 ms`，p95 `4.307 → 4.396 ms`，**max `95.4 → 151.7 ms`**（超出本仓 ~100 ms 的自留余量，见 §7） |

**一句话**：这三层是"用胜率换边际"的层。边际涨得极显著（+$562/局，t=10.7），镜像域涨得极显著（50% → 75%，z=5.6/4.4），但**近克隆重启面板上净输 21 局**（24 负 3 正，p=2×10⁻⁵）。

## 1. 动机（数据）

### 1.1 天梯上我们有一半对局在打自己

`results/ladder_top_meta.md` §2：我们 24 个线上对手座位里，**12 个的 d20 农场构成与我们逐字段相同**（`STRA33+WHEA25`），d12/d16/d29 画像也逐字段一致。会话交接 `results/SESSION_STATE.md` 给的线上口径是**克隆类胜率 64.4%（59 局）**；本次任务书写的是 **镜像/克隆占 39.5%、胜率 61.1%（Elo≥2300 的克隆仅 52.4%）**。两个口径都指向同一件事：**镜像域是当前最大的、可测的失分口**。

### 1.2 ADV 是专门打这个域的层

`tmp_extract/prvsiyan_frontier.py` 中 EXP293 的自述：

> when the native tape sells a pure cash product within the next 3 turns and the units already sit in the shed, sell them now, ahead of a rival executing the same tape. … This layer explicitly targets mirror/clone opponents.

即：**在原生 tape 打算卖的前 3 回合就抢先卖**，抢在跑同一份 tape 的对手前面成交。

### 1.3 上一次移植证明这类层可达

`results/reports/v28_v57_layers.md`（v28）同类移植在镜像测试上拿到 98-2，这是本仓唯一被反复验证的正方法。因此本次**预先固定门槛**再测（见 §4.0）。

## 2. 改动内容

### 2.1 移植方式（关键机械细节）

`tmp_extract/prvsiyan_frontier.py` 的 tail 结构与我们的 `main.py` 不同，逐条对齐：

| 源文件 | 我们的文件 | 处理 |
|---|---|---|
| `# Bridge: chain e410 -> R148 -> ADV -> IG` + `agent = e410_agent` | 我方链尾已经是 `agent`（v57 入口） | **删除该行**（照任务书的移植要求） |
| 块尾 `agent = globals().pop("agent")` / `kaggle_submission_agent = agent` | 我方约定是 `agent` 必须是命名空间里**最后一个 callable** | **删除两行**（pop 会让最后一个 callable 变成 `_ig_close_queue`） |
| 块内 `_R148_PARENT=agent` / `_ADV_PARENT=agent` / `_IG_PARENT=agent` + `del agent` + `def agent(...)` | 我方 `main.py` 末尾已有 `def agent(...): return v57_agent(...)` | 原样保留；追加后 `agent` 被重绑为 IG 入口，**插入序仍在最后** |
| 源文件在 IG 之后还有 `_33_SF` / `_33_KO`（我方已有）、`_VQ` 队列压实、`_final_submission_entrypoint`、`_FRO` | 我方**没有** `_VQ` / `_FRO` | **不在本次范围**：本次只移植任务书指定的 R148 → ADV → IG |

插入位置：`main.py` 全文之后**纯追加**（`diff <(cat main.py) <(head -7374 候选)` 为空）。这样**不重绑任何既有层**——`_CXD_HOST`、`_33_SF_PARENT`、`_33_KO_PARENT`、`_V57` 全部保持原状。

> **踩过的坑（已纠正）**：第一次把块插在 `agent.telemetry = _E410_REPORT` 之后（即 `_CXD_HOST = [callable][-1]` 之前），结果把 counter-D 的 host 从 e410 入口改成了 IG 入口，**连带了既有层的接线**。那次测得 107/120 / +$1218；改成纯追加后是 103/120 / +$1072。
> **两种接线给出同一量级、同一方向的结论**，所以下面的结论对插入位置不敏感；但报告与复现一律以**纯追加版（`sha256 e6111d84…`）**为准。

### 2.2 层的定义

- **R148（EXP277，overflow reclaim）**：`step % 24 == 23` 时，若黎明落仓会因货棚 100 上限销毁货物，就**只卖被丢掉的那部分后缀**，并保证"落仓后的完整仓向量与原始计划逐项相同"（`_r148_same_stock` 合约检查、`_R148_PENDING` 下回合校验）。`_R148_OVERFLOW=True`、`_R148_SEEDS=False`。
- **ADV（EXP293，sale advance）**：两个子层。
  - `_adv_apply`：`_ADV_LOOK=4`、`_ADV_FROM=144`、`_ADV_TO=718`，在 `step%24 != 23` 时，若原生 tape 未来 4 回合里有 `SELL` 纯现金产品（STRAWBERRY/WOOL/EGG/MILK/MELON/CARROT/TOMATO）且货已在棚里，**现在就卖**；保护"下一回合第一单"（若它是 SELL，则不碰该品类）。
  - `_adv_frontload`：把市场单重排为 `纯SELL → BUY_PRODUCT(及同类自买自卖) → 其余原序`。
- **IG（保守闭合）**：`_ig_standard` 配置门 + `_ig_guard_opening`（step 29 的 `HybridOpening` 小麦缺口回退）+ `_ig_close_queue`（把"投影仓里无货"的现金 `SELL` 变成空洞，再把右侧可动 SELL 左移填洞）。**不改任何物理动作与数量。**
- 源文件里的 **seed float trim**（busyaprime）我方 `main.py` **早已有**（`_33_SF_*`），未重复移植。

### 2.3 被引用符号的存在性核对（逐个查过）

| 符号 | 我方 `main.py` | 说明 |
|---|---|---|
| `_r97_budget(obs,orders)` | ✅ 行 2792 | 签名一致 |
| `_r97_market_stock(shed,orders)` | ✅ 行 2771 | |
| `_r97_delivery(stock,private,night)` | ✅ 行 2782 | |
| `_r127_fields(obs,action)` | ✅ 行 5910 | |
| `_r127_last_hour(obs,action)` | ✅ 行 5922 | |
| `projected_shed(action,view)` / `class FarmView` | ✅ 行 1236 / 1233 | |
| `_RACE_STATE`、`_ALT_STATE`（含 `'mode'=='HybridOpening'`）、`_IMPL`、`_PLANNER_NS` | ✅ | |
| 瓦片 `tile['kind']=='PLANT'`、`native['sell_state']['r36_debts']` | ✅ | |
| **`_r128_future(obs)`** | ❌ **缺失** | 只被 `_r148_seed_prefund` 引用，而该函数被 `_R148_SEEDS=False` 关死 → **潜在 NameError，当前不可达**。`_r128_future` 在我方旧线（`opponents/beatv48`、`opponents/reyhan`、`kernels/saga v49–v53`）存在（`def _r128_future(obs,offset=1)`），在本线被删。**必须记录**：若日后打开 `_R148_SEEDS`，会抛错并被外层 `except` 吞掉（`targeted_errors` +1，同时**跳过该回合的 `_r148_overflow`**）。 |

## 3. 实验方法

- **面板**：`opponents/{v55,prvsiyan,guru}` × 40 seeds × seat 0 = **120 局/变体**
  - A 池：`--seeds 2000-2039`（任务书指定的池）；B 池：`--seeds 2100-2139`（**独立复现池**，我自己加的）
- **镜像**：候选 vs `main.py`，`--seeds 2000-2099` 与 `2100-2199`，各 100 局，seat 0
- **指标**：总胜 W/L/T、**平均边际**、**最差边际**；另记**双方各自的绝对 reward 增量**（用来分辨"我变强"还是"对手变弱"）
- **归因**：`ctl`（空 shim，控 AB 机制本身）+ 三个单层消融 + 一个双层消融
- 所有变体的入口检查：`.venv/Scripts/python -c "…print(c[-1][0], m.agent is c[-1][1])"` → 全部 `agent True`

### 3.1 预登记门槛（**在看到任何结果之前固定**）

1. 总胜 **≥ 119/120**；且
2. 总 mean margin **≥ +$520**（比基线 +$434 至少 +$86）；且
3. worst margin **不差于 −$405**；且
4. 镜像测试 **≥ 60% 胜率**（等强度改动的中性值是 50%）

## 4. 结果

### 4.1 面板（A 池，任务书指定）

| 对手 | 基线 W/L/T | 候选 W/L/T | 基线 mean / worst | 候选 mean / worst |
|---|---|---|---|---|
| guru | 39-1-0 | 36-4-0 | +$510 / −$131 | +$1269 / −$122 |
| prvsiyan | 38-2-0 | 35-5-0 | +$430 / −$205 | +$1199 / −$217 |
| v55 | 38-2-0 | 36-4-0 | +$362 / −$405 | +$1185 / −$217 |
| **合计** | **115/120 (95.8%)** | **103/120 (85.8%)** | **+$434 / −$405** | **+$1072 / −$217** |

### 4.2 面板（B 池，独立种子，我自己加的复现）

| 对手 | 基线 W/L/T | 候选 W/L/T | 基线 mean / worst | 候选 mean / worst |
|---|---|---|---|---|
| guru | 39-1-0 | 37-3-0 | +$550 / −$321 | +$1056 / −$869 |
| prvsiyan | 39-1-0 | 36-4-0 | +$418 / −$401 | +$890 / −$952 |
| v55 | 39-1-0 | 35-5-0 | +$399 / −$401 | +$879 / −$452 |
| **合计** | **117/120 (97.5%)** | **108/120 (90.0%)** | **+$455 / −$401** | **+$942 / −$952** |

**两池合并（n=240 对局）**：

| 指标 | 基线 | 候选 | Δ | 显著性 |
|---|---|---|---|---|
| 总胜 | 232/240 (96.7%) | 211/240 (87.9%) | **−21 局** | 翻转 **24 负 : 3 正**，单边二项 **p = 2×10⁻⁵** |
| mean margin | +$445 | +$1007 | **+$562/局** | 配对 **t = 10.7** |
| worst（A/B） | −$405 / −$401 | −$217 / **−$952** | A 池改善、**B 池破线** | — |
| **我方 reward** | — | — | **−$63 / +$61（噪声）** | — |
| **对手 reward** | — | — | **−$701 / −$426** | — |

**这条是关键**：候选**没有让我们自己赚更多钱**，全部边际增益来自**把对手的钱打下去**。这就是文档自称的"抢跑同 tape 对手"，机制上完全吻合。

**逐种子 Δ 分布（A 池，40 个种子的 3 对手均值）**：mean `+$638`、median `+$479`、min `−$323`、max `+$2687`；**28 正 / 12 负**。负的那些全是原本就贴着的窄胜（基线 +$105 … +$207 → 候选 −$115 … −$217）。

**翻转明细（A 池，18 局决胜局）**：`seed 2006`（+2 胜）、`2012/2017/2024/2027/2030`（−15 胜）、`2021`（+1 胜）。**注意同一 seed 的三个对手几乎同时翻转** —— 说明是**我方自己的行为**在决定，而不是对手差异。

### 4.3 镜像测试（本层的目标域）

| 种子池 | 候选 vs `main.py` | 基线（等强度中性值） | z |
|---|---|---|---|
| 2000-2099 | **78W-22L-0T = 78.0%** | 50% | **5.60** |
| 2100-2199 | **72W-28L-0T = 72.0%** | 50% | **4.40** |
| 合并 | **150/200 = 75.0%** | 50% | **7.07** |

镜像池 mean margin `+$733 / +$519`，worst `−$1011 / −$1372`。**0 平局**（200 局全部决胜）——ADV 制造了系统性不对称，两个 agent 不再走同一条路。

### 4.4 逐层归因（A 池 120 局 + 镜像 2000-2039 40 局）

| 变体 | 面板 W/120 | 面板 mean / worst | 镜像 W/40 |
|---|---|---|---|
| `main.py` 基线 | 115 | +$434 / −$405 | （自对局 = 40 平） |
| **候选（全开）** | **103** | **+$1072 / −$217** | **30 (75.0%)** |
| `ctl`（空 shim，验证消融机制） | 103 | +$1072 / −$217 | 30 (75.0%) |
| `abl_adv`（关 ADV） | **115** | +$442 / −$363 | 12W-3L-**25T**（得分 61.3%） |
| `abl_r148`（关 R148） | 103 | +$1069 / −$217 | 30 (75.0%) |
| `abl_ig`（关 IG） | 103 | +$1068 / −$217 | 30 (75.0%) |
| `abl_adv_r148` | 115 | +$438 / −$405 | 11W-3L-26T（得分 60.0%） |

**`ctl` 与候选逐位相同** → 消融 shim 本身是惰性的，上述所有差异都来自被关掉的那一层。`abl_adv` ≈ 基线（115/120，+$442 vs +$434）→ **关掉 ADV 后，整块追加层在面板上等于没加**。

**结论**：R148 与 IG 在面板上贡献 ≈ 0（±$4），**ADV 是全部效应**。

### 4.5 各层实际触发情况（遥测）

在 `seed ∈ {2000,2001,2002,2003,2005,2017,2021,2033}` × 4 对手的单局运行中 dump 模块级计数器：

| 计数器 | 观测 |
|---|---|
| `_R148_REPORT['overflow_turns']` | **只有 seed 2005 / 2021 / 2033 触发，每局恰好 1 回合**（3/40 = 7.5%） |
| `…['overflow_units_reclaimed']` | 1–2 件 |
| `…['overflow_quote_exposure']` | $44–$68 |
| `…['overflow_contract_checks']` / `['overflow_contract_errors']` / `['targeted_errors']` | `1 / 0 / 0` —— 合约（落仓后仓向量不变）成立 |
| `…['atomic_turns']`、`['seed_prefund_turns']` | **恒为 0**（`_R148_SEEDS=False` 关死） |
| `_ADV_REPORT['adv_turns']` | **3–36 回合/局**，`adv_units` 9–116 |
| `_ADV_REPORT['front_turns']` | **3–22 回合/局** |
| `_ADV_REPORT['adv_errors']` | 0 |
| `_IG_REPORT['queue_changed_turns']` | 9–18 回合/局，`zeroed_orders` 7–18 |
| `_IG_REPORT['pulled_orders']` / `['pulled_slots']` | 0–2 / 0–7（很弱） |
| **`_IG_REPORT['opening_repairs']`** | **恒为 0 —— `_ig_guard_opening` 从未触发** |
| `_IG_REPORT['errors']` / `_R148_REPORT['targeted_errors']` | 0 |

R148 的**方向是负的**：`abl_adv`（R148 开）vs `abl_adv_r148`（R148 关）在 A 池有 **8/120 局不同，且 8 局全部变差**：

```
guru-2005 −$67   prvsiyan-2005 −$87  v55-2005 −$87
guru-2021 −$42   prvsiyan-2021 −$44  v55-2021 −$42
                 prvsiyan-2033 −$44  v55-2033 −$44
```

即 **R148 每次触发都要亏 $42–$87**（合计 −$4/局）。

## 5. 门槛判定

| # | 门槛 | 结果 | 判定 |
|---|---|---|---|
| 1 | 总胜 ≥ 119/120 | 103/120（A 池）、108/120（B 池） | ❌ 失败 |
| 2 | mean ≥ +$520 | +$1072（A）、+$942（B） | ✅ 通过 |
| 3 | worst ≥ −$405 | −$217（A）、**−$952（B）** | ❌ 失败 |
| 4 | 镜像 ≥ 60% | 78.0% / 72.0%，合并 75.0% | ✅ 通过 |

**四条是 AND 关系 → 预登记判定为 ❌ 否决。**

按任务书要求，**把分裂点单独列出来**：这不是"平淡的失败"。

- **镜像域（占线上 39.5–50%）**：极显著正向。真·自镜像 50% → 75%（n=200，z≈6.6）。即使打对折迁移，也是 +10pp 量级。
- **近克隆重启面板**：显著负向。−21/240 胜（p=2×10⁻⁵），且 B 池出现 −$952 的尾差。

**两者不是同一批对局**：面板对手是"能力弱的近亲"（我们基线胜率 96.7%），输掉的 21 局**全是原本就贴着的窄胜**（基线 +$93…+$207）；镜像对手是"能力相同的自己"。ADV 抬高方差：大胜局从 +$400 抬到 +$2000+，同时把窄胜翻成窄负。

**粗略 Elo 外推（明确标注为推测）**：设线上 39.5% 镜像、60.5% 非镜像。镜像 61.1% → 若按真镜像的 +25pp 迁移得到 ~86%（+240 Elo，权重 0.395 → +95）；非镜像按面板 −9pp（基线 95.8%→87.9% 折算 −250 Elo，权重 0.605 → −151）→ **净 ≈ −55 Elo**。**但这个外推不可信**：`results/score_is_opponent_draw.md` 已证明线上分数主要由"被排到谁"决定，本地面板测不出头部档位的对手。**这条只是给量级用，不作为判据。**

## 6. 被否决的变体与负面结果

| 变体 | 结果 | 说明 |
|---|---|---|
| **块插在链中部**（`_E410` 之后、`_CXD_HOST` 之前） | 107/120，+$1218，worst −$217；镜像 78/100 | 会连带重绑既有 `_CXD_HOST`/`_33_SF_PARENT`。与纯追加版同量级同方向 → 结论稳健；但**不能这样交付**（归因不干净） |
| **R148（EXP277）** | 3/40 局触发，8/8 局变差 | **负面**。建议在任何后续移植里**直接删掉或置 `_R148_OVERFLOW=False`** |
| **IG-opening（`_ig_guard_opening`）** | `opening_repairs` **恒为 0** | 在我们这条链上**从不触发**：step 29 的 `(y=4,x=2)` 瓦片检查 + `_ALT_STATE[mode]=='HybridOpening'` 的联合条件在本 tape 上无法同时成立 |
| **IG-queue（`_ig_close_queue`）** | 触发 9–18 回合/局，`zeroed_orders` 7–18 | **零收益**：§4.4 里 `abl_ig` 与候选差 −$4（噪声），镜像 30/40 对 30/40 |
| **`_r148_seed_prefund`** | 依赖我方已删除的 `_r128_future` | 潜在 NameError，被 `_R148_SEEDS=False` 关死；**开着会连带吞掉同回合的 `_r148_overflow`** |

### 6.1 唯一一条（弱）正面线索：IG 单独在镜像域可能是正的

`abl_adv`（只有 IG 生效）在镜像 2000-2039 上 `12W-3L-25T`：
- 25 局与我们逐位相同（平局）→ IG 只在 **15/40 = 37.5%** 的对局里改变结果；
- 这 15 局里赢 12 局 → 期望得分 `24.5/40 = 61.3%`，比中性 50% 高 **+11pp**；
- 但二项检验 p ≈ **0.018**（n=15），且**面板代价为 0**（`abl_adv` 115/120 +$442 ≈ 基线 115/120 +$434）。

**这是"可能可以只采纳 IG"的一条线索，不是结论**——n 太小，且 `_ig_guard_opening` 本来就是死的，真正在起作用的是 `_ig_close_queue`。若要走这条路，必须**单独预登记、单独放大 n** 再测。

## 7. 回调耗时

`.venv/Scripts/python scripts/callback_timing.py --cand <file> --seeds 2000,2001,2002`（3 局 × 719 回调 = 2157 次）

| 变体 | mean | p50 | p95 | p99 | **max** |
|---|---|---|---|---|---|
| `main.py`（基线） | 1.929 ms | 1.243 | 4.307 | 9.732 | **95.4 ms** |
| **候选** | 2.189 ms | 1.343 | 4.396 | 10.330 | **151.7 ms** |
| `abl_adv`（关 ADV） | 1.995 ms | 1.247 | 4.204 | 9.871 | **114.3 ms** |

- mean **+13%**，p95 **+2%**，p99 **+6%**；**max 95.4 → 151.7 ms（+59%）**。
- 拆分：**IG + R148 贡献 +19 ms，ADV 再贡献 +37 ms**。
- 绝对量是安全的：`kaggriculture.json` 里 `actTimeout = 1`（秒），全局限时另有 `remainingOverageTime = 60`（秒/局）；候选单局总计 **约 1.6 s**，与预算差两个数量级。
- **但按本仓惯例（v28/v29 报告里峰值 ~100 ms 视为"预算内"）这是超出自留余量的**：151.7 ms 是这条链的历史峰值。计入 §5 的负面判定。

## 8. 决策与后续

**否决本次改动**（不合并进 `main.py`）。

理由排序：
1. 预登记门槛 4 条只过 2 条，且失败的是**胜率**这一条（Elo 只看 W/L/T，不看边际）。
2. 胜率回归**不是噪声**：24 负 : 3 正，p=2×10⁻⁵，且在两块独立种子池上复现（−12、−9 局）。
3. B 池 worst 掉到 **−$952**，破了任务书定的尾差底线。
4. **机制上它是纯零和抽取**：我方收入不动，只压低对手。这类层的收益**只在"差一点就输/赢"的对局里结算**，而面板显示它在这些对局里**净 -21**。尾差因此被放大而不是被压小。
5. 峰值回调 151.7 ms 超出本仓自留余量，收益却是负的。

**若要继续走镜像域这条路**，建议（按优先级）：

1. **只移植 IG-queue，ADV 不要。** 证据弱（§6.1）但面板代价为 0；先按独立预登记放大到 n=400 镜像再定。
2. **把 ADV 门控到"已识别为克隆"的对局**。本仓已有克隆识别（`_RACE_STATE` / `_v44y_clone_gate` / `results/clone_analysis.py`）。ADV 在镜像 z≈6.6，在近亲面板显著负——**这正是"应该只在克隆域打开"的教科书形状**。门控版必须**单独预登记**重测：镜像 ≥60% **且**面板胜率不退化。
3. **R148 直接扔掉**（每次触发都亏，`_R148_OVERFLOW=False` 或删代码）。
4. **同时修 `_r128_future` 缺失**，或删掉 `_r148_seed_prefund`，避免留下一个"打开开关就静默吞掉同回合另一层"的陷阱。

## 9. 复现

```bash
# 0) 入口点自检（必须打印 "agent True"）
.venv/Scripts/python -c "import importlib.util;s=importlib.util.spec_from_file_location('x','experiments/v30/prvsiyan_layers.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);c=[(k,v) for k,v in vars(m).items() if callable(v) and not k.startswith('__')];print(c[-1][0], m.agent is c[-1][1])"

# 1) 冒烟（改任何东西之前）
.venv/Scripts/python scripts/smoke.py experiments/v30/prvsiyan_layers.py

# 2) 基线面板（A 池）
.venv/Scripts/python scripts/tournament.py --candidate main.py \
  --opponents opponents/v55/main.py opponents/prvsiyan/main.py opponents/guru/main.py \
  --seeds 2000-2039 --seats 0
# 3) 候选面板（A 池）
.venv/Scripts/python scripts/tournament.py --candidate experiments/v30/prvsiyan_layers.py \
  --opponents opponents/v55/main.py opponents/prvsiyan/main.py opponents/guru/main.py \
  --seeds 2000-2039 --seats 0
# 4) 独立复现池（B 池）—— 把上面两条的 --seeds 换成 2100-2139

# 5) 镜像（预先登记的主判据）
.venv/Scripts/python scripts/tournament.py --candidate experiments/v30/prvsiyan_layers.py \
  --opponents main.py --seeds 2000-2099 --seats 0
.venv/Scripts/python scripts/tournament.py --candidate experiments/v30/prvsiyan_layers.py \
  --opponents main.py --seeds 2100-2199 --seats 0

# 6) 逐层消融（每个都是 ~120 局面板 + 40 局镜像）
for f in ctl abl_adv abl_r148 abl_ig abl_adv_r148; do
  .venv/Scripts/python scripts/tournament.py --candidate experiments/v30/$f.py \
    --opponents opponents/v55/main.py opponents/prvsiyan/main.py opponents/guru/main.py \
    --seeds 2000-2039 --seats 0
done

# 7) 回调耗时
.venv/Scripts/python scripts/callback_timing.py --cand main.py --seeds 2000,2001,2002
.venv/Scripts/python scripts/callback_timing.py --cand experiments/v30/prvsiyan_layers.py --seeds 2000,2001,2002

# 8) 遥测（R148 / ADV / IG 各层触发计数）
#    见 §4.5；对 seed 2005 / 2021 / 2033 单局 dump 模块级 _R148_REPORT / _ADV_REPORT / _IG_REPORT
```

产物哈希：
```
main.py                              sha256 1ffa8782555cfa08…  7374 行  （本次未改动，git 未提交未 push）
experiments/v30/prvsiyan_layers.py   sha256 e6111d841f4962a0…  7751 行  （+377 行）
experiments/v30/ctl.py               sha256 754087b02aef2681…
experiments/v30/abl_adv.py           sha256 2b2f7704267dab2f…
experiments/v30/abl_r148.py          sha256 e44270b5d06f860d…
experiments/v30/abl_ig.py            sha256 001b8f9060555203…
experiments/v30/abl_adv_r148.py      sha256 b07df5a38f7c9d9a…
```

比赛局 JSON（`tournament_results/`）：
```
agent-20260923-135416.json  基线 A 池        v30-20260923-140205.json  候选 A 池
agent-20260923-143107.json  基线 B 池        v30-20260923-143354.json  候选 B 池
v30-20260923-140309.json    镜像 2000-2099   v30-20260923-143615.json  镜像 2100-2199
v30-20260923-140648.json    ctl A 池         v30-20260923-140743.json  ctl 镜像 2000-2039
v30-20260923-141022.json    abl_adv A 池     v30-20260923-141114.json  abl_adv 镜像
v30-20260923-141400.json    abl_r148 A 池    v30-20260923-141454.json  abl_r148 镜像
v30-20260923-141742.json    abl_ig A 池      v30-20260923-141836.json  abl_ig 镜像
v30-20260923-142123.json    abl_adv_r148     v30-20260923-142217.json  abl_adv_r148 镜像
```
