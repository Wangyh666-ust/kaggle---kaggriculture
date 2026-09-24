# v27 — 移植公开 V56 的两层（EXP402 / EXP410）

- **日期**：2026-09-23
- **基线**：v26（`sha256 8d52c0f76eb3e290…`，7016 行；线上 56469970，评级中）
- **候选**：`sha256` 见 `results/submissions.md`（7123 行）
- **改动量**：追加 107 行（两层），其余为注释

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 改动 | ✅ **采纳** |
| 直接头对头 | **82W-6L-12T（100 局，82.0%）**，均值 +$185，最差 −$633 |
| 面板（17 对手 × 20 种子 × 双座位 = 680 局） | v26 **626/680 (92.1%)** → v27 **632/680 (92.9%)** |
| 边际改善（面板） | guru +$86→**+$312**、prvsiyan +$7→**+$233**、v55 −$32→**+$184**、beatv48 +$3480→+$3712 |
| 冒烟 | ✅ `smoke OK` |
| 未验证风险 | 线上分数；以及面板已饱和（见 §5） |

## 1. 动机（数据）

抓取公开血统的最新版本发现：

- **V56** `ahmedberatozer/kaggriculture-v56-smarter-seeds-and-fertilizer`（09-21）
- **V57** `ahmedberatozer/kaggriculture-v57-funding-order-invariant`（09-22，最新）

逐行 diff 得到：

| 版本 | 相对关系 |
|---|---|
| V55 | 我们的 v26 已完全对齐（见 `v26_v55_parity.md`） |
| **V56** | V55 + **EXP402**（按剩余播种量上限裁剪后期买种）+ **EXP410**（肥料花在无法改变收成的地方就跳过） |
| V57 | V56 + counter-D 精确最优反应排序（`_CXD_*`）+ seedfloat/knock（`_33_SF_*`/`_33_KO*`）+ 资金顺序不变量 |

**另有一处需要辟谣**：V56/V57 的 `_V92_P_BLOB` 看着变了，实测**解压后逐字节相同**
（1,319,827 字节，`sha256 f5c3d06b214d3697`），只是把编码从 base85 换成 base64 以缩小文件。
**它不是一个新库**，不要为它做 A/B。

## 2. 改动内容

把 V56 尾部的两层移植到我们文件末尾，并按本文件的约定重新绑定父层（V56 里父层是
`final_price_guard`；在我们的链里必须接到最后一层，否则会绕过 v25 的早死修复层）：

```python
_E402_PARENT=agent          # V56 原文是 final_price_guard
_E410_PARENT=_e402_agent    # V56 原文是 e402_agent
del agent
def agent(observation, configuration=None):
    return _e410_agent(observation, configuration)
```

`agent` 通过 `del` + 重定义排到命名空间最后，保持 Kaggle "最后一个可调用对象" 的入口规则
（已验证：`mod.agent is last callable → True`）。上游 Apache-2.0 归属写在追加块的注释里。

EXP402 依赖的 `_IMPL` / `_CA_STATE`；EXP410 依赖的 `_PLANNER_NS` / `_ca_visits` /
`_ca_yield_path` / `_R51_INPUT_STATES` / `_v219_native_day` —— **全部已存在于我们文件中**，
无需额外移植。

## 3. 实验方法

固定种子对局、双座位、逐对手统计，指标 = 胜/负/平 + 平均边际 + 最差边际。

## 4. 结果

### 4.1 直接头对头（100 局，v27 vs v26）

```
v27  82W- 6L-12T   均值 +$185   最差 -$633
```

### 4.2 面板（680 局/臂）

| 对手 | v26 | v27 |
|---|---|---|
| prvsiyan | 33W-7L | **38W-2L** |
| beatv48 | 36W-4L | **38W-2L** |
| v55 | 39W-1L | 38W-2L |
| guru | 38W-2L | 38W-2L |
| v51 / v52 / v53 / v49 / v50 | 32-8 / 30-10 / 34-6 | 同 |
| 其余 10 个对手 | 各 40W-0L | 各 40W-0L |
| **合计** | **626/680 (92.1%)** | **632/680 (92.9%)** |

## 5. 方法论：面板正在失去分辨力（重要）

本次出现一个需要记下的现象：**头对头说 82% 胜，面板只说 +6/680。**

原因是**面板饱和**——17 个对手里有 10 个已经是 40W-0L，没有上升空间；剩下 7 个里
v51/v52/v53/v49/v50 逐格完全不变，只有 prvsiyan / beatv48 / v55 三处有 ±1~5 的空间。

**结论（写入协议）**：

> agent 越过约 90% 面板胜率之后，**"面板总胜场"不再是合适的主指标**。
> 主指标改为 **新版本 vs 上一版本的直接头对头**（同种子配对、100 局）；
> 面板降级为**回归护栏**——它的职责是确认"没有对手退化"，而不是显示增益。
> 边际（mean margin）比胜场更敏感，应同时报。

## 6. 决策与后续

采纳，`main.py` 已更新为 v27。

下一步：**V57 的 counter-D 层**（`_CXD_*` + `_33_SF_*`/`_33_KO*` + 资金顺序不变量，约 236 行）。
它比 V56 的两层大得多，且带**每回合预算 800 次排序评估**（`_CXD_BUDGET=800`），
需要先测回调耗时再做 A/B —— 公开作者对回调时间很敏感（V55 自报峰值 ~45ms）。

## 7. 复现

```bash
# 冒烟
.venv/Scripts/python scripts/smoke.py experiments/v26/v56_layers.py
# 头对头
.venv/Scripts/python scripts/tournament.py --candidate experiments/v26/v56_layers.py \
    --opponents experiments/v26/v26_baseline.py --seeds 2000-2099 --seats 0
# 面板
.venv/Scripts/python scripts/tournament.py --candidate main.py --seeds 2000-2019
```
