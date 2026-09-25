# 25/27 Strict-Future | v27 Midgame Meta Reset — Kaito Fukami

- **链接**：https://www.kaggle.com/code/kaitofukami/25-27-strict-future-v27-midgame-meta-reset
- **票数**：**214**（重跑 2026-08-10）
- **产物**：`main.py` **20,813 字节**，sha256 `f48c21166eac68d1b05a401f04f94a2eb6154e65415af64893672365ff33c7b8`
  — 一条 **719 步路线**，两个座位共用；署名来源是公开队伍的 episode 91493566

## 关键原文

### §0 核心论断

> "**The dominant opening did not fail. Its stale continuation did.**"
>
> ```text
> same low-entropy HIRE4 opening
>   ↓ replace the stale continuation from step 161 onward
> one coherent 719-step route in both seats + actor-local WEED repair
>   + existing-SELL-slot price-impact ordering
> ```

### §2 开局已经坍缩（**这条对我们影响最大**）

> "## 2. The Top-30 opening has almost collapsed to one prior
> Modal Day-0 public signatures across the frozen Top-30 were:
>
> | Opening signature | Teams |
> |---|---:|
> | 1 COW, 4 SHEEP, 5/5 seed, WHEAT 5, **HIRE4** | **14** |
> | same assets, **HIRE5** | **12** |
> | HealthStone HIRE3 | 1 |
> | Seb 2 COW / wheat-heavy HIRE7 | 1 |
> | five-sheep carrot branch | 1 |
> | old v23 opening | 1 |
>
> **26/30 teams now share the same 1-COW/4-SHEEP core.** An opening classifier therefore has
> little information value. **The next edge has moved into continuation timing, labor paths,
> production mix, and market execution after the common opening.**"

### §3 同开局、不同续带

> "The old v26 seat-0 route and the selected v27 route have the same HIRE4 Day-0 queue.
> Their first market difference appears only at **step 161** and their first farmer/hands
> difference at **step 170**. … This is a **coherent continuation reset**, not a late splice
> into a farm whose inventory assumptions came from another policy."

### §5 稀疏控制器（增量很小但有）

> "Route-only control versus official price-impact SELL-slot ordering:
> inner 28/30 → 28/30（+$1,115）；outer 28/30 → **29/30**（+$819）"
> —— 他的市场层**只在已存在的 SELL 槽位之间重排**，不新建/删除/改量。

### §7 他自己承认的局限

> "Both are sub-1,000-coin losses, but they still count as full losses. … Therefore `25/27` is
> **not evidence that every private adaptive branch is solved.**"

（另外注意：他的 `25/27` 是**对一组重放固定动作的对手**——那些对手**无法对他的改动做出反应**。）

## 我们做了什么

- 抽出那份 20,813 字节的产物（sha256 与声称一致），**当对手测：我们 40 局全胜，均值 +$34,547、最差 +$20,910**
  → **"换个更好的续带"这条路对我们不成立**
- §2 的"开局坍缩"与我们的观测**方向一致**（我们线上 90% 对手开局签名与我们逐字节相同），
  但我们**没有复核过他的 26/30**——记为 A6 待确认
- §5 的"只在已有 SELL 槽位间重排"与我们链路里已有的机制**同类**（我们的 counter-D / `_SR_*`）
