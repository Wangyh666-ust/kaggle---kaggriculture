# Demystifying 2900+ Meta: The Reflex Engine, PnL Audit & Submission Bot — haideptry

- **链接**：https://www.kaggle.com/code/haideptry/demystifying-2900-meta-reflex-engine-and-bot
- **票数**：6（重跑 2026-09-19）
- **产物**：内嵌 `main.py` 与我们 v21 的底盘**同一份**（v9/3，sha256 `4f3ca95dd12d9a94…`）
- ⚠️ **这份 notebook 自称"2850–2945 Elo"，我们实测不成立**：把它内嵌的 agent 抽出来当对手，
  **我们 40 局全胜、均值 +$1,441**。

## 关键原文

### §1 架构

> "the modern SOTA architecture cleanly decouples:
> 1. **The Route Chassis**: a rock-solid 720-turn action schedule handling spatial layout, seed
>    planting, land acquisitions, and hand hiring parallelism (fib(n−1) marginal pricing).
> 2. **The Reflex Stack**: a fast, reactive layer that reads the public observation on every turn
>    and edits decisions in real time."

### §1.2 RACE（抢跑）

> "Rival sales are public if computed from state deltas:
> `rival_sold = inventory' − inventory + town_draw − own_sold`
> The **RACE** reflex monitors this exact signal. When a competitor starts dumping premium goods,
> the reflex intercepts the route's scheduled sales and pulls them forward by **up to 40 turns**."

### §1.3 day-11 羊放置

> "Sheep first produce 6 days after placement, and then every 3 days thereafter. The season
> terminates at the end of Day 29.
> - Placed on Day 12: produces on days 18, 21, 24, 27 → **4 harvests**
> - Placed on Day 11: produces on days 17, 20, 23, 26, 29 → **5 harvests (+25%)**"

### §1.4 CARE 倍率

> "Cared Cow: **3 Milk** per production cycle (vs 1 uncared). Cared Sheep: **4 Wool**. Cared Goose: **2 Eggs**."

### §1.5 Kaggle 入口陷阱

> "Kaggle's simulation runner … resolves the entrypoint by selecting `[v for v in namespace.values()
> if callable(v)][-1]`. If any helper function is defined after `def agent(...)`, Kaggle executes
> that helper instead of your controller!"

### §4.1 番茄主张（**我们已否证**）

> "forensic analysis of private ladder replays shows that private top-10 teams maintain one
> decisive advantage: **Tomatoes**. Top-tier private agents buy ~9 tomato seeds starting around
> **Day 12** and hold 10+ tomato tiles by Day 20. … **Extending the route chassis with a
> non-interfering tomato expansion remains the highest-EV path toward 3000+ Elo.**"

### §4.2 两槽提交策略

> "Slot 1 (Anchor): keep your best verified version and allow it to age past 100+ games.
> Slot 2 (Challenger): test experimental mutations."

## 我们做了什么

| 主张 | 状态 | 我们的证据 |
|---|---|---|
| Route chassis + reflex stack 架构 | ✅ | 就是我们用的（720 步磁带 + ~40 层反射） |
| RACE 抢跑（提前最多 40 回合） | ❌ **已否证** | v30/v31/v32 三次失败；镜像赢 70–94% 但真实对手掉胜场；**"补还"贡献为零**，伤害随前视长度缩放 |
| day-11 羊（5 次 vs 4 次剪毛） | ⚪ 视为已覆盖 | 我们这条链有 V50 "early yarn commit"；未单独验证 |
| CARE 是主收益（3 奶/4 毛/2 蛋） | ✅ | 引擎机制，已实现 |
| Kaggle last-callable 陷阱 | ✅ | `submit.py` 会拒绝构建入口点不对的文件 |
| **"day-12 番茄是通往 3000 的最高 EV 路径"** | ❌ **已否证** | ①引擎：番茄每株恰好产 4 次，与种植日无关 ②价格：我们局里番茄整季上涨（$78→$118）③作者本人三试三败 ④我们放宽 V219 门槛 → **435→415→357 单调剂量-反应** |
| "2850–2945 Elo" 的自评 | ❌ **不可复现** | 抽出来当对手：**我们 40-0，均值 +$1,441** |
| 两槽提交策略 | ✅ | 我们实测确认窗口 = 2、取较高分（E5） |
