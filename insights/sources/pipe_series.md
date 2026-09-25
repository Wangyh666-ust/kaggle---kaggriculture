# pipe-N 系列（nathanjacob）与"层堆叠"复合体 —— **本次最重要的发现**

- **作者**：Nathan Jacob（`nathanjacob`）
- **性质**：一条**公开的实验编号系列**，每个 notebook = 一份完整、自包含、可提交的 agent
- **这条线的价值**：它把社区里所有强层的**抽取与消融过程**公开了，而我们的 `main.py` 就在它的**原料清单**里

## 一、系列清单（`kaggle kernels list --user nathanjacob`，2026-09-25 抓取）

| notebook | 日期 | 票数 | 底座 | 加的东西 |
|---|---|---|---|---|
| `kaggriculture-pipe-2-agent` | 09-14 | 5 | — | 起点 |
| `no-cow-left-behind-v40-autopsy-fix` | 09-14 | 5 | v40 | **"没有一头牛被落下"：v40 尸检 + 修复** ← 与我们的早死 bug 同类 |
| `how-many-twins-strategy-clustering-kaggriculture` | 09-14 | 2 | — | 聚类方法原文 |
| `beyond-v43-what-the-top-clusters-do-on-turn-1`（= pipe-4） | 09-15 | 37 | Ahmed V43 | C9 条件开局 |
| `kaggriculture-pipe-5-terminal-boost` | 09-15 | 10 | — | 终局增强 |
| `kaggriculture-pipe-7-wheat-microstructure` | 09-16 | **63** | Ahmed V43 系 | 小麦微观结构（329,111 B / 3,497 行） |
| `kaggriculture-pipe-8-clean-opening` | 09-16 | 6 | — | 干净开局 |
| `kaggriculture-pipe15-two-layers` | 09-20 | 3 | — | 两层 |
| `kaggriculture-pipe16-idle-workers` | 09-20 | **56** | — | 闲置工人（1,010,931 B / 6,591 行） |
| `kaggriculture-pipe18-six-layers` | 09-21 | 23 | **Tschinkel v13** | **六层**（1,022,762 B / 6,879 行） |

另外 09-15 那篇 `beyond-v43...` 的产物叫 **pipe-4**，说明编号是作者的"管线迭代号"。

## 二、pipe18 自述的六层（`beyond-v43` 的续作）

> "**Six Layers That Beat The Top Public Agents** —— 把三位作者的六个公开微优化堆在 Tschinkel 的
> v13 底座上。14 个对手、650 局，**560胜54负36平 = 88.9% Elo rate**。
> 与 **ahmed v56（排行榜上最强的公开 agent）几乎打平**。"

| 层 | 内容 | 出处（他的署名） |
|---|---|---|
| **CL** | Crop Longevity：作物还有正期望值时延长地块寿命，而不是按固定日程重种 | dmitriigluzdov |
| **Price Guard** | 现价低于生产成本时拒绝卖出，等更好的价格窗口 | ahmed v55/v56 |
| **Race Horizon** | 按对手可能的种植时机调整播种，避开同质供给过剩 | ahmed v55/v56 |
| **EXP402** | Late Seed Cap：剩余回合不足以回本时停止买种 | autoloop 自动消融发现的实验层 |
| **EXP410** | Fertilizer Guard：施肥收益盖不过肥料成本时跳过 | autoloop |
| **IG** | Queue Compaction：合并连续相同的队列项，腾出行动槽 | **lynnsakurai** |

### 他给出的对手强度排序（**这一条对我们直接有用**）

| 对手 | 胜-负-平 | 胜率 |
|---|---|---|
| **ahmed v56** | 28-16-6 | **56.0%** ← 最难 |
| ahmed v55 | 35-10-5 | 70.0% |
| lynnsakurai | 42-4-4 | 84.0% |
| dmitriigluzdov | 44-2-4 | 88.0% |
| tschinkel v13 | 46-1-3 | 92.0% |
| 其余 11 个 | 365-21-14 | 91.3% |

> **"ahmed v56 是排行榜上最强的公开 agent"** —— 我们本地有 v55，**没有 v56**。

## 三、我们自己的测量（这是这份文档的重点）

### 3.1 一个方法学事故：我们的对手面板一直跑错了入口点

`kaggle_environments.agent.get_last_callable`（权威实现，我们直接调用验证）：

```
main.py                        -> agent              ← 我们自己的提交，正确
opponents/tetsutani_cha22/...  -> ig_agent           ← 不是 agent
opponents/v53/main.py          -> _e363_agent        ← 不是 agent
opponents/v55/main.py          -> final_price_guard  ← 不是 agent
opponents/pipe4|pipe16|pipe18  -> agent
```

`scripts/tournament.py` 的 `load_agent` 注释写着"mirror the Kaggle rule"，**代码却优先取 `agent`**。
v50/v51/v52/v53/v55/prvsiyan/tetsutani/kaito_v27/beatv48 的最后一个可调用对象都**不是** `agent`
（这些作者把实验层写在 `def agent` 之后，并用 `kaggle_submission_agent = <最后一层>` 显式指定入口）。
**已修**：`--loader {kaggle,agent}`，默认 `kaggle`，且经环境变量传进 spawn 出来的 worker
（第一版用模块级全局，被 Windows 的 spawn 重置，A/B 假阴性——已修）。

**实测影响（同一批种子，30 种子 × 双座位）：**

| 对手 | `--loader agent`（旧） | `--loader kaggle`（真） |
|---|---|---|
| v53 | 52W-8L（86.7%） | 与上者同量级（34W-6L / 40 局 = 85%） |
| v55 | 56W-4L（93.3%） | 38W-2L / 40 局 = 95% |
| **tetsutani_cha22** | **60W-0L（100%）** | **6W-34L（15%）** ← 天壤之别 |

⇒ **对多数对手，旧 bug 无害；对"层堆叠复合体"这一个类别，旧 bug 会把一个 85% 压制我们的
对手，误判成被我们 100% 压制。** 这就是为什么我们一直以为"公开 agent 我们动辄 40-0"。

### 3.2 复合体确实压着我们

`tetsutani_cha22`（tetsutani 的 2026-09-24 notebook，88 票，即 `demand-preserving-turn-sale-timing`）
在 Kaggle 保真 loader 下：**我们 6胜34负，均差 −$697，最差 −$3,222**。

它的**底座就是我们的底座**：`_R42_OPENING=[13,30,30]` + **`V9_OPENING_STEP0=(BUY 20, SELL 15)`**
——即我们的**v36（v37 早死修复之前）**，再叠它自己的层。

### 3.3 它的层是"点名可查"的合并栈

```
_FX, _DP, _MP, _BD, _MPX, _SM         ← cha20 链（它自己的实验）
F4: Layer D - exact best-response ordering   (_CXD from elo_2615 order-book)
F5: EXP410 fertilizer guard                  (pipe18 的 e410_agent)
F6: EXP402 late seed cap                     (pipe18 的 e402_agent)
MERGE: same-item SELL compaction             (port of 2695 的 E334)
IG:  queue hole-closure
```

**关键**：`e402_agent` / `e410_agent` **我们的 `main.py` 里已经有了**
（`grep` 结果：main.py 含 `e334_agent`/`e335_agent`/`e402_agent`/`e410_agent`）。
所以复合体不是"另一个物种"，而是**在我们同一底座上多叠了若干层**。

## 四、结论与待办

| 主张 | 状态 | 证据 |
|---|---|---|
| 社区存在公开的 **pipe-N 层堆叠复合体** | ✅ 已核实 | 见 §1 清单，逐个拉到本地 |
| 复合体能稳定压制我们 | ✅ **已测得（两块种子一致）** | tetsutani_cha22：种子 1000-1049 **22W-78L**；种子 2000-2049 **22W-78L**。合计 200 局，我们胜率 **22%** |
| 但**不是"复合体"这一整类**压我们 | ✅ **已测得** | 同两块种子：pipe18 **93-7 / 92-8**、pipe16 **93-7 / 98-2**、pipe7 **100-0 / 100-0**、tetsu_market **100-0 / 100-0**、v55 **93-7 / 96-4**、v53 **86-14 / 86-14**。**只有 tetsutani 那一个栈压我们** |
| 我们此前"公开 agent 我们动辄 40-0"的结论 **不成立** | ✅ **已否证** | 见 §3.1：评测入口点 bug 造成的抽样偏差，被抽掉的正是"层堆叠"这一类 |
| pipe18 自述的 650 局 / 88.9% | 🔶 待确认 | 他自报，无回放可查。**注意我们 93-7 赢 pipe18**，所以他的对手集合与我们不同 |
| **ahmed v56 是当前最强公开 agent** | 🔶 待确认 | 已抓到 `v56`（1,056,142 B / 6,751 行，sha `a1ad0fd1…`）与更新的 **`v57-funding-order-invariant`**（1,067,076 B / 6,987 行，sha `2ee689fd…`）。**尚未与我们对局** |
| `beyond-v43` 的 C9 开局（"小麦往返浪费一回合"） | ❌ **已否证** | 见 [nathanjacob_turn1_clusters](nathanjacob_turn1_clusters.md)：C15 与 C9 **在同一回合雇工**，整项改动值 **+$26** |

### 4.1 gluzdov 的四份也抽出来了（内嵌格式是 `base64.b64decode` + gzip+tar）

```
more-wheat-smarter-sales (35票)  1,040,401 B / 7,036 行
7-turn-rescue            (67票)  1,033,759 B / 7,047 行
one-more-wheat           (59票)  1,020,006 B / 6,639 行
a-smaller-market-shock   (69票)    862,940 B / 5,881 行
```

**他的 NOTICE.txt 把公开前线的链条写清楚了**：

> Direct base: **shiiin9**, "Your Market List Is An Order Book"；
> V55 controller and V56 input budgeting: **Ahmed Berat Ozer**；
> Metav4: **Thomas Tschinkel**. Hayashi: original ShopRouter.

⇒ 公开前线的上游 = **Hayashi ShopRouter → shiiin9 订单簿 → Ahmed v55/v56 → gluzdov**，
而我们的链条源头是同一批人。**我们和前线是同一祖先的不同分支。**

**⚠️ 他的"评测"不是证据**：`LOCAL_GAMES` 里对手只写 **"Previous notebook v8"**，
5 个 demo 种子上报 `outcome: 1.0`，但实际差额是 **$3 / $123 / $139 / $72 / $…**
（在 $60k–120k 的分数量级上 = **0.005%–0.3%**）。按我们 L1/L2，这是噪声，不是胜势。

### 4.2 标识符 diff：前线到底多了哪几层

`scripts/token_compare.py`（**不要用整体相似度**，见 [local_findings](../local_findings.md) L13）：

| 方向 | 数量 | 代表 |
|---|---|---|
| gluzdov 有、我们 v34_base 没有 | **32 个名字** | `_CXD_*` / `_cxd_agent`（**F4 层**）、`_CXTB_*`（counter-T-B 番茄门控）、`rescue_agent`、`seed_budget` |
| 我们 v34_base 有、他没有 | **85 个名字** | `_33_*`（KO / seedfloat / knock）、`_ADV_BOOK` |

**关键收敛**：`_CXD` 同时出现在 **tetsutani 的栈（F4）** 和 **gluzdov 的 agent** 里——
两个前线 agent 独立收敛到同一层。它也正是"exact best-response ordering"，
属于我们**尚未**测试过的机制（我们测过的是它同族的 RACE 抢跑 B2，已被否证）。

### 待办（按价值排序）

1. **层阶梯定位**（进行中）：`scripts/build_ladder.py` 把 tetsutani 的 12 级栈冻在每一层做入口，
   跑 vs 我们。**预测：跳变落在 05→06，即 `_SM` (SHIELD-MILK 现金偿付护栏)**。
   旁证：ahmed 的公开标题序列里 **v49 "Funded sale timing"**、**v57 "Funding-Order Invariant"**
   是同一主题，三方独立收敛。而 `_SM` 恰好是我们早死 bug（M1）的失败类别。
2. **测 ahmed v56 / v57**（已抽出，未对局）。
3. **若 `_SM` 成立**：把它作为独立层移植到我们 v37，按 L3 纪律（两块种子 ≥500 局）验收。
4. 🔶 `quick_ratio` 作废重估：`insights` 里此前所有引用"相似度 0.99xx"的血缘判断都需重跑
   （已修 `scripts/lineage_id.py`，改为按每 100 个 token 采样后的真实 `ratio()`）。
