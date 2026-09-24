# 2026-09-22 研究：天梯头部 meta 与三项负面结果

- **日期**：2026-09-22
- **分支**：`fix/early-death`（工作区）；本次**未改动 `main.py`**，只有新增脚本与文档
- **基线**：`main.py` = v25（`sha256 d40d0619aca482ca…`，7016 行）；线上最好成绩仍是 v23_c7 的 **2452.2**
- **结论**：没有采纳任何 agent 改动。产出一个诊断、三项负面结果、五个工具、一条必须遵守的提交纪律。

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 番茄行提前（原计划的第一步） | ❌ **否决**——机制上不增产量，价格上更差，作者本人三试三败 |
| 降低空转人工（idle%） | ❌ **否决**——本地数据里 idle% 与边际**正**相关（+0.378），是获胜的结果而非原因 |
| 同 seed 重放头部对局来量差距 | ❌ **否决**——机制上不可能，商店序列本身就依赖双方打法 |
| 天梯头部观测 | ✅ 建成（工具 + 报告），并定位到主流家族 |
| 提交可追溯性 | ✅ 建成（`scripts/submit.py`，强制记录哈希） |
| 线上 Elo | 未变（本次无提交） |

---

## 1. 动机

起点是用户的问题"为什么打不过别人"。先做了三件取证：

1. 把 `main.py` 与本地已下载的全部公开 kernel 做结构化 diff；
2. 用 Kaggle API 拉全量榜单 + 我们自己全部提交记录；
3. 用 `team-submissions → episodes → replay` 拉头部队伍的真实对局。

## 2. 取证结果

### 2.1 我们就是公开最强 agent 的克隆

| 对比对象 | 差异 |
|---|---|
| 公开 **V55**（6658 行） | **仅 4 处**：2 行注释、`path=None` vs `os.environ`、`_SR_MARGIN 4/8`、尾部常量 |
| 公开 "Demystifying 2900+ Meta"（haideptry）内嵌 v9/3 | **4 个常量** + 我们的 prvsiyan 尾部 |
| 公开 "The 2945 Farm"（thomastschinkel）内嵌 main.py | 与 haideptry 那版 **sha256 完全相同** |

把这两个 "2900+" notebook 的 agent 抽出来当对手跑 40 局：**我们 40W-0L-0T，均值 +$1441**。它们自报的 2850–2945 无法复现。

### 2.2 天梯分布（7999 队，自有 API）

top 3110.7 / ≥3000: 6 / ≥2900: 23 / ≥2800: 64 / ≥2500: 707 / ≥2450: 848 / 中位 1010。
我们最好 2452.2 ≈ 第 850 名。

### 2.3 我们线上遇到的一半对手是自己

24 局 v25 对手里，**12 个座位的 d20 作物构成是 `STRA33+WHEA25`**，与我们逐字段相同（`coke lu`、`democatXamer`、`Pardheev Krishna`、`Pat` …）。2450 是**这份公开文件的均衡点**，不是我们的能力值。

### 2.4 头部是另一个 agent，被至少 6 支队伍共享

step-2 签名 `SELL WHEAT 1, HIRE×4, COW 1, SHEEP 3` 出现在 **Vadim Vasilenko(#1)、DECEM(#2)、mtmr_s1(#6)、ymg_aq(#9)、Unknown Mother-Goose(#10)、TheEggman(#11)**。我们的开局完全不同（`HIRE×5, COW 2, SHEEP 2`）。

他们的农场：牛为主（`C10-13`）+ `STRA20 + TOMA10-16 + CARR5-20`；我们：**`STRA33 + WHEA24`，d12 之后基本冻住**。

---

## 3. 三项负面结果（本次的主要产出）

### 3.1 番茄行提前：否决

`TOMATO: first_yield_day 8, max_yield 4, interval 1, ongoing` —— `production_count > max_yield` 直接 continue，所以**每株恰好产 4 次，与种植日无关**。day 18 种 → 收 d26/27/28/29；day 12 种 → 收 d20/21/22/23。产量相同，只有窗口不同。

价格数据（`scripts/price_trace.py`，24 局我们 + 15 局头部）：

| | d20 | d24 | d26 | d29 | early(20-23) | late(26-29) | Δ |
|---|---|---|---|---|---|---|---|
| 我们局 TOMATO | 74.5 | 95.7 | 115.6 | 119.6 | 78.4 | **118.2** | **+39.9** |
| 头部局 TOMATO | 71.7 | 70.1 | 67.9 | 63.9 | 71.8 | 66.1 | −5.7 |

我们局里番茄整季**上涨**（半个池子不种），头部局里平在 $64（人人都种）。**这条线的价值会随我们爬分自动消失。**

外部佐证（thomastschinkel 2026-09-19 notebook）：他的 v9/4 对当时 top-10 中的 7 支是 **0–36**，"we lead until day 10 … lose it all after day 11"，最大缺口是番茄（对手 71 颗 @$114，他 7 颗 @$316）。但他试的三种番茄方案**全败**（0/85、0/56、+4/−11），原因写得很明确：

> "The route tape is the constraint. Its workers are busy from dawn to dusk, so a tomato program needs a different **labour** plan, not just a different crop choice."

### 3.2 空转人工：否决（被自身数据反驳）

`scripts/waste_audit.py` 显示我们 idle **7.1%**，而 #1（Vadim）只有 **1.8–2.0%**——看起来是大机会。但在我们自己的 24 局里：

```
pearson r = +0.378
idle 低于均值(<7.3%) 的平均边际 $+15,704  (n=18)
idle 高于均值             的平均边际 $+52,467  (n=6)
```

**正相关**——赢得多的时候雇的人多、闲着的人也多。idle% 是获胜的结果，不是原因。这个指标不能当优化目标用。

（同一次审计的其他数字是好的：`weed_lost` 均值 0.1、`end_stock` 恒为 0，即我们没有"收成烂在地里"或"末日常规忘卖"的浪费，甚至优于头部样本的均值。）

### 3.3 同 seed 重放头部对局：机制上不可能

`env/kaggriculture.py:_end_of_day` 用**同一台 rng** 先抽杂草再抽商店，而 `_spawn_weeds` 只在**空格子**上消耗随机数：

```python
if farm["tiles"][y][x] is None and rng.random() < weed_chance:
```

所以**商店序列取决于双方各自的空地数**。实测（`scripts/seed_probe.py`）seed 8823651：头部那局第一家店是 d3 `BAKERY`，我们镜像跑同一 seed 是 d3 `FARMERS_MARKET`——**第一家店就不同**。

含义：**"把我们的 agent 放到他们的 seed 上比钱"永远无效**；本地也**永远无法**和头部家族对局。相对地，固定 seed 的本地 A/B 面板（两臂同 seed、同对手）依然有效——本项目一直在用的协议不受影响。

---

## 4. 新增工具（全部可重跑）

| 脚本 | 用途 |
|---|---|
| `scripts/fetch_ladder_replays.py` | 抓头部队伍公开回放到 `replays_ladder/`（CLI + 429 退避 + 断点续跑） |
| `scripts/ladder_meta_report.py` | 把语料转成 `results/ladder_top_meta_data.md`（开局签名聚类/农场画像/购买/价格） |
| `scripts/price_trace.py` | 逐日价格轨迹 + early/late 对比 |
| `scripts/waste_audit.py` | 空转人工 / 棚满 / 收成变草 / 终局存货 |
| `scripts/seed_probe.py` | 给定 seed 跑一局并打印商店解锁序列（验证 §3.3） |
| `scripts/panel_shop_keys.py` | 面板 seed 实际走到的 route key 分布（评估 route 替换的检验力） |
| `scripts/harvest_routes.py` | 从回放抽 720 步磁带，按 (前两家店) 建候选 route 表 |
| `scripts/submit.py` | 构建 + 校验入口点 + 记录 sha256 到 `results/submissions.md`，默认 dry-run |

`panel_shop_keys.py` 的实测：20 个面板 seed 对上 **19 个不同的商店对**（64 个可能对里近乎均匀）。**所以单个 route 替换只会影响 ~1/20 的 seed，检验力极弱；要做 route 替换必须批量换（≥14 对才够 ~20% 的世界）。**

`harvest_routes.py` 实测：15 局头部对局 → 14 个商店对、14 条磁带；**14/14 都已有对应 route**（我们的表早已覆盖全部 64 对），所以抓回来的是**替换**而非新增。

---

## 5. 提交纪律（新增，防事故）

同码两次提交：`56428515` = **2452.2**、`56454624` = **1763.7**（差 688）。
而 #1 自己两次提交只差 87（3023.4 / 3110.7）。
（公开资料里 thomastschinkel 报同码差 ~107：2686.0 vs 2579.3。）

**688 的差距超出可解释的噪声范围**，指向"上传的不是那份代码"。由于无法回取历史提交物，改为向前设防：

```bash
.venv/Scripts/python scripts/submit.py --version v26 --note "…"          # dry run，记录哈希
.venv/Scripts/python scripts/submit.py --version v26 --note "…" --submit # 真正提交
```

`submit.py` 还会**拒绝构建**"命名空间最后一个可调用对象不是 `agent`"的文件——这是公开资料里反复出现的静默失效陷阱（Kaggle 按 last callable 解析入口）。

---

## 6. 下一步（按优先级）

| # | 动作 | 依据 |
|---|---|---|
| 1 | 拉 **V57**（`kaggliculture-v57-funding-order-invariant`，09-22 最新）+ V56，按老办法消融/合并，面板 A/B | "追血统拿层"是本项目唯一反复验证过的正向手段（+289 Elo） |
| 2 | 下载讨论区 `737034` 公开的 **537 局 / 25 万动作**天梯语料，替代逐局抓取 | 把头部观测从 15 局扩到 500+ 局 |
| 3 | 提交一律走 `scripts/submit.py` | §5 |
| 4 | 立项"劳动力规划"，而不是继续加作物线 | §3.1 作者结论 + §3.2 |

**阻塞项**：Kaggle API 目前对本凭证全局限流（429），`kernels pull` 与 replay 抓取都失败中；`fetch_ladder_replays.py` 已在后台按 90/180/…s 退避重试。限流恢复后 1、2 可立即执行。

---

## 7. 复现

```bash
.venv/Scripts/python scripts/fetch_ladder_replays.py --top 12 --episodes 3
.venv/Scripts/python scripts/ladder_meta_report.py --top replays_ladder replays_top replays_ladder_ops \
    --ours replays_v25 --ours-team ReD_MooN_rise
.venv/Scripts/python scripts/price_trace.py replays_v25
.venv/Scripts/python scripts/waste_audit.py replays_v25 --team ReD_MooN_rise
.venv/Scripts/python scripts/seed_probe.py --seed 8823651 --cand main.py --opp main.py
.venv/Scripts/python scripts/panel_shop_keys.py --seeds 2000-2019 --opp opponents/v55/main.py
.venv/Scripts/python scripts/submit.py --version v26 --note "…"
```

## 8. 未验证风险

- §2.4 的家族判定基于前 3 步签名，行为等价但字符串不同的成员可能漏判。
- §3.1 引用的 thomastschinkel notebook 内容来自子代理读取公开原文，未逐字复核。
- 头部语料 15 局集中在同一时段，`harvest_routes.py` 出的 14 条磁带各只有 1 个样本，**不足以支撑 route 替换决策**。
- 官方 runner 的 `kaggle-environments` 版本未核实；本地是 1.32.7（公开资料提示 notebook 镜像曾停留在 1.29.3，两者镜像对局结果差 5 个数量级）。若线上 runner 版本不同，本地 A/B 的迁移性需要重新评估。
