# boatlee 两份：V14 Clone Preemption（180 票）与 V16-RC5 8C/4S（317 票）

## 一、`boatlee/84-84-base-public-holdout-v14-clone-preemption`

- **链接**：https://www.kaggle.com/code/boatlee/84-84-base-public-holdout-v14-clone-preemption
- **票数**：**180**（2026-08-08）
- **产物**：抽取后 472 行（`experiments/boatlee_v14.py`）

### 关键原文

> "**near-clone preemption** … V14 aims to move ahead of an opponent's large premium `SELL` on the
> **next turn**. It does not jump ahead of its own valuable Market orders on the **current turn**.
> The execution order is: 1. Generate and repair the baseline action. 2. **Repay quantities shifted
> on the previous turn.** 3. Rank the existing `SELL` slots with the **V23 price-impact scorer**.
> 4. …"

> "**Preemption is a bounded overlay on a complete agent**, not a Market-only script detached from
> production."

代码里的关键结构（我们逐行读过）：
- `_public_signature(farm)` + `_clone_distance(obs)` + **`_PREEMPT_MAX_CLONE_DISTANCE = 6`**
- **`_preempt_shift` + `_repay_shift` + `_SHIFT_STATE`**（卖单前移一回合、下回合把数量**补还**）
- `_PREEMPT_FRACTION=2.0`、`_PREEMPT_MAX_BATCH=30`、`_PREEMPT_START=120`、`_PREEMPT_STOP=680`
- `_PREMIUM = ("STRAWBERRY","MELON","MILK","WOOL")`
- `_rank_sell_slots` / `_impact_score` / `_order_score`（价格冲击评分排序）
- `_weed_repair_action`（杂草修复）

### 我们做了什么 —— **两条都否证了**

| 主张 | 状态 | 证据 |
|---|---|---|
| 克隆距离门控能区分对手 | ❌ **彻底 no-op** | `_clone_distance` 对全部 8 个对手**恒为 0（最大 1）**，**包括 v55 / guru / prvsiyan**；加了门控与不加**逐局位完全相同**（120 局） |
| "补还"（总量不变、只改时机）能避免 v30 的伤害 | ❌ **贡献为零** | 去掉补还的对照与补还版**逐局相同**（公开 113/120 +$595 vs 113/120 +$593；克隆 149/160 vs 148/160） |
| 提前卖能赢镜像 | ❌ **净负** | v32：真实对手 **−7/320**（前视 1 回合）vs v30 的 −24/320（前视 3–4）。**真正影响伤害的是前视长度，不是补还** |
| 整份 agent | —— | **我们 40-0 赢它**（均值 +$48,545） |

---

## 二、`boatlee/v16-rc5-high-score-8c-4s-premium-market-lead`

- **链接**：https://www.kaggle.com/code/boatlee/v16-rc5-high-score-8c-4s-premium-market-lead
- **票数**：**317**（最高票的非入门 agent notebook，2026-08-12）
- **产物**：246 行（`experiments/v16rc5.py`）

### 关键原文

> "**V16-RC5** combines a compact **8 `COW` / 4 `SHEEP`** production route with a one-turn market
> lead for `MELON`, `MILK`, `STRAWBERRY`, and `WOOL`. The production schedule was reconstructed
> from three publicly available Kaggriculture replays of **Nikita Lugovoy's high-ranking submissions**"

> "expands to three unlocked quadrants; **reaches 4 SHEEP immediately and [8 COW]**"

### 我们做了什么

**我们 40-0 赢它（均值 +$34,218，最差 +$20,910）。**
它是 8 月的老 meta——**"8C/4S"这个畜群目标本身不构成优势**。

> ⚠️ 别把它和"扩张/填地"那条线索混起来：我们一度因为"它目标 8 牛而我们只有 3–5 牛"而关注它，
> 但后来用**我们自己的 117 局线上回放**查明：我们还手的那 6 场崩盘里，对手是**比我们多 3 头牛 +
> 草莓满 33**——而那**不是** V16-RC5（这是一份 8 月的、我们打得赢的 agent）。两条线索不同。
