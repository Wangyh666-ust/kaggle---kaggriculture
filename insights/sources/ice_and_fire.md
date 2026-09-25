# ❄️🔥 A Song of Ice and Fire — leoprovorov

- **链接**：https://www.kaggle.com/code/leoprovorov/a-song-of-ice-and-fire-fixed-flexible
- **票数**：23（重跑 2026-09-24）
- **性质**：**诊断工具 + 分析**，不是 agent。附一份 companion dataset（三个 dashboard 文件）。
- 同一系列还有：`leoprovorov/kaggricult-man-reverse-engineering-part-1`、`god-s-mode-hacked-stores`

## 核心方法："冰与火"

取一支队伍**同一 agent 版本的所有胜局**（Majkel1337 有 **461 局**），把 720 步叠起来，
逐回合问：**有多少局在这一步提交了同样的指令？**

- **冰（Ice）** = 每一局都提交的指令 → 固定脚本
- **火（Fire）** = 只有部分局提交的 → 对局面/商店/市场/对手的反应

指令以 `类:商品` 表示（`PICKUP:WHEAT`、`SELL:WOOL`、`BUY_SEED:WHEAT`），方向合并为 `MOVE`。
**"指令单元"** = 某个指令在某个 step（如 step 144 的 `PICKUP:WHEAT`）。

## 关键原文

> "A command that **every** game submits at that step is **ice**: a fixed part of the agent.
> Ice sits below the line, in blue. A command that only **some** games submit is **fire**: the
> agent reacted to something in that game."

**测量结果**：Majkel1337 全部指令单元的平均一致率 = **30.6%**
→ **只有约三成是脚本，其余都是因局而异的反应。**

### §2/§4：每支队伍的"脚本"在哪一步结束

判据：某队胜局中，**≥25% 的局开始不按多数派做**的第一步。

| 队伍 | 胜局数 | p10 | **p25** | p50 |
|---|---|---|---|---|
| feel the agi | 66 | 6 | **151** | 151 |
| AI是我的豆包 | — | — | **146** | — |
| THIRD FARM CLUB | — | — | **145** | — |
| Majkel1337 | 461 | — | **4** | — |
| SpaTaro | — | — | **2** | — |
| **M & M & P & Q** | — | — | **1** | — |

> "feel the agi (151), AI是我的豆包 (146) and THIRD FARM CLUB (145) part ways within 7 steps of
> the second shop opening at step 144. Majkel1337 (4), SpaTaro (2) and M & M & P & Q (1) part
> ways within the first four steps."
>
> "**The ranking by this number is not a ranking by strength: M & M & P & Q, the shortest script
> here, has the highest average winning score in the sample.**"

**即：前几名里，有的是"磁带党"（可以照抄 6 天），有的第 1 步就不一样。而脚本最短的那个分最高。**

### §3 商店世界的样本警告

> "A world holds at most 8 games here. The longest shared opening in Majkel1337's table is
> PET_CAFE then FARMERS_MARKET (3 games) against PET_CAFE then YARN_STORE (6 games): they agree
> up to step 145, and over the whole game only 22.5%. **With samples that small, a long shared
> prefix is a lead to check with more games and not a result.**"

（他也给出了商店开锁时点：**step 72, 144, 216, 288, 360, 432, 504, 576**，每局相同——
这与我们 `_router` 在 step 144 用 `unlocked_shops[:2]` 的做法一致。）

### §5 配方表（可执行的部分）

| 段落 | 怎么识别 | 怎么造 | 例子 |
|---|---|---|---|
| **Fixed** | 热图全蓝格、分歧≈0 | 录一条磁带 | Majkel1337 第 0 天；THIRD FARM CLUB 的 step 0–144 |
| **Conditional** | 分歧恰好出现在开店之后 | 按**揭示的商店**查表 | 他的 agent：15 个商店对 → 11 个计划（step 144 选） |
| **Flexible** | 红橙柱很高、分歧与开店无关 | **读实时状态的规则**：价格、棋盘、工人、对手 | Majkel1337 第 1 天之后 |

> "The graphs say where each stretch starts and ends for a given player.
> **Which flexible rule wins is decided by the games against real opponents.**"

## 对我们最有用的两点

1. **这是一个我们本地就能跑的方法**——不需要对手的代码，只要有他们的**回放**。
   我们刚下载的 `data/top10/*.parquet` 里有 **1800+ 局顶级对局**（每天 605 局）。
2. **它能把"该在哪一步交接"变成一个逐回合可测的曲线**，而不是 Metav4 那种按 6 天分段的粗说法。

**尚未做**：我们还没在自己的回放上跑过这个诊断（见 `claims.md` A7/A8）。
