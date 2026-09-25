# The 2945 Farm: 96% vs the Top-10 Public Bots — thomastschinkel

- **链接**：https://www.kaggle.com/code/thomastschinkel/the-2945-farm-96-vs-the-top-10-public-bots
- **票数**：**146**（重跑 2026-09-19）
- **性质**：他 v9/4 版本的公开 notebook。**我们这条链的共同源头**（我们的 `main.py` 文件头就写着 "v9/3"）
- 注意：该 notebook 内嵌的 `main.py` 与 haideptry 那篇 "Demystifying 2900+ Meta" 内嵌的是**同一份**
  （sha256 都是 `4f3ca95dd12d9a94…`），只是各自加了自己的话

## 关键原文

### 公开最强 vs 头部私队：0–36

> "v9/4 beats every public notebook, yet against seven of today's top-10 teams it went
> **0 – 36** on the ladder (September 15–17). … **We lead until day 10**, because the melon race
> is ours, **and lose it all after day 11.** The biggest single hole is **tomatoes**. The farms
> that beat us buy about **9 tomato seeds from day ~12** and hold about **10 tomato tiles on day
> 20**. We buy 1.6, and the first on day 18. **They sell 71 tomatoes at $114 each. We sell 7, at $316.**"

### 他试过的番茄方案：**三试三败**

| 方案 | 结果 |
|---|---|
| 用 tape 的小麦地块做番茄覆盖（day 13 起） | **0 胜 / 85 负** |
| 新开地做 20 格番茄 | **0 / 56** —— "the crews cannot water 20 more tiles" |
| 放宽现有番茄层的门槛 | +4 / −11 |

> "**The route tape is the constraint. Its workers are busy from dawn to dusk, so a tomato
> program needs a different *labour* plan, not just a different crop choice. The adaptive farms
> don't replay a tape. They plan the crew around the crops.**"
>
> "**If you have a tomato program that works on top of a route tape, or you know why the
> adaptive farms win the second half, I would love to hear it in the comments.**"

### 其他反直觉数据

> "**Every sale is also denial**"——他去掉 103 颗草莓，**自己少赚 $5.5k，对手多赚 $5.5k**。

### 他自己列的负面结果（同源，与 metav4 §7 部分重叠）

- 持有溢价品等价：**−$7.5k ~ −$34k/局**
- 把 v9 重基到公开 V48 上：497 vs 506 / 840
- 让自适应规划器在第 12 或 18 天后接手：**6–24 和 7–23**（磁带是 24–6）← **他试过交接，失败了**
- 从零写的需求驱动规划器：线上 990–1,578 vs 磁带 2,945
- 第 11 天跳过草莓（没有浆果店）：−$1.5k
- 多雇人给小麦施肥：每个工 $144/天，比多收的小麦还贵
- 只有一个毛线店的小镇里做羊扩张：他 −$11k~−$17k，对手只 −$2k~−$3k

### 评测课（与 metav4 §8 同源）

1. Kaggle 跑**最后一个可调用对象**
2. **冻结回放会骗你**：他的回放面板从 589→648 胜/1000，而线上分数**从 2956.6 掉到 2944.7**
3. 同码两处测出 **2686.0 与 2579.3**（≈±107 的抽签差）
4. **销售即压制**（见上）
5. Kaggle notebook 镜像的 `kaggle-environments` 是 **1.29.3**（旧引擎），与 1.32.7 的镜像局结果差 5 个数量级

## 我们做了什么

- 这篇是**我们 README 里"头部 0-36"那条结论的原始出处**，我们独立复核了它的方向（phase 对比）
- "磁带是约束 / 需要劳动力计划"（A5）与我们的结论一致
- 番茄三试三败（B6/B10）与我们的独立测量一致
- "销售即压制"（B9）我们**尚未验证**，记为待确认
- 评测第 2 条（**回放面板会骗人**）我们亲身撞上：`_SR_*` 的假阴性、以及面板饱和
