# The Shepherds Ledger / Herd Safe Sovereign — haideptry

- **链接**：https://www.kaggle.com/code/haideptry/the-shepherds-ledger-herd-safe-sovereign
- **票数**：3（重跑 2026-09-24 03:28）
- **产物**：`main.py` 1,038,953 字节，sha256 `ae44d83baf39ae2cf203d3617d0e9d7846d4a8b379b00c3ebd3734f1cfb5fbf3`
- **血统**：与我们同底盘（"Pipe-16 HybridOpening controller"），比我们多 `herdsafe_forecast_agent` + `herdsafe_risk_feed_agent` 两层（`_HP_WINDOW = 4`）

## 关键原文

> "## 1 · Philosophy: The Herd-Safe Sale Window vs Speculative Shock
> A systematic evaluation of the top ladder replays reveals a critical meta vulnerability:
> 1. **The Speculative Opening Trap**: Early wheat round-trips expose farms to catastrophic
>    turn-1 slippage if the opponent dumps simultaneously or consumes high-value shop orders.
> 2. **The Herd-Safe Solution**: - **Preserves exactly the vital initial 5 wheat and 1 planting seed**"

## 为什么这条对我们最重要

**它从原理推出的是我们 v37 那个修复**——而我们是从**自己的天梯回放**里发现的：

| | 他们 | 我们 |
|---|---|---|
| 路径 | 从"顶队回放 + 引擎原理"推出开盘往返是陷阱 | 从 v36 的 62 局回放里量到 **5 局（8.1%）** 走"step-24 现金 $1 → 少雇 2 工 → 牛饿死 → d3 畜群 3"，且这 5 局正是最大的 5 场败局 |
| 结论 | 保住初始 5 麦 + 1 粒种 | `V9_OPENING_STEP0` 20/15 → 10/5（净小麦仍 +5） |
| 证据强度 | 他的（未给样本量） | 我们的：本地 step-24 现金中位 **$12 → $18**；修复前 2/19 触发、修复后 0/32（p≈0.07）；对 herdsafe 320 局**无退化** |

**两条独立路径得出同一机制——这是 v37 目前最强的一条外部支撑**，
因为 v37 是唯一一个**本地复现不出触发条件**的改动（本地两边都 0/60）。

## 我们做了什么

- 把整份 agent 抽出来（`experiments/shepherd.py`，7162 行）**当对手测**：**我们 40 局里赢 30 局（75%）**
  → **它整体不如我们，那两层 herd-safe 不采纳**
- 但它的**开盘陷阱论断**被记为 B1，状态 ✅（机制已被我们独立验证并采纳进 v37）
