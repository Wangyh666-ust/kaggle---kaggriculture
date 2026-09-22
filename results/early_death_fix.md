# 早死 bug 修复报告（fix/early-death 分支）

数据与复现命令均为本机实测（Windows，`.venv/Scripts/python`，2026-09-22）。分支 `fix/early-death`
从 `main`（= v23_c7，`main.py` 6662 行）开出，**未 commit、未 push、未提交 Kaggle**。

改动只动一个文件：`main.py`（+2 处：第 3354 行的常量、文件末尾追加的两层），另有诊断脚本
`scripts/early_death_local_repro.py` 的一处修正（见 §5.1）。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| (a) 止血 | ✅ 采纳，但**实现方式与任务描述不同**：不是"少买 1-2 单位小麦"，而是把 step 0 的 `BUY 20 / SELL 15` 换成 `BUY 10 / SELL 5`（净小麦仍 +5） |
| (b) 护栏层 | ✅ 采纳（`_HR_*`，按任务原文实现），实测在正式对局里**从不触发**（保险） |
| (c) 喂食救援层 | ⚠️ 采纳**严格版**（`_ER_*`）。原始设计（可挪用 PASS/移动单位）实测**使巡回赛从 244/300 掉到 191/300**，已改成"只挪用动作本身就是空转的单位"，改后与只上 (a) 的战绩**逐对手完全相同**，同时在压力用例里仍能救回那头牛 |
| 复现验证 | ✅ 修复前 `money_t24=1 / hands@25=1 / d3 畜群 3`（2/2 局触发）；修复后 `$12 / 3 / 5`（0/2） |
| 烟测 | ✅ guru、prvsiyan 各 18/18 DONE，`smoke OK` |
| 回归巡回赛 | ✅ 244/300 (81.3%) → **256/300 (85.3%)**；逐对手**无一处胜场退化**，`win/loss flips: 12 gained, 0 lost` |
| 性能 | ✅ 每回合均值 0.77ms → 0.83ms，p95 1.49→1.32ms，峰值不变（~39ms） |
| 唯一未验证风险 | 两张"对手指纹表"`CT_TABLE` / `_V93_ROUTE_BY_RIVAL` 的键是用旧开局标定的，本改动会移动对手 step-2 的现金（实测 −$6~+$30），这两张表**可能不再命中**；本地对手面板本来就不命中它，无法在本地验证（详见 §7） |

---

## 1. 改动位置与代码要点

### 1.1 (a) 开局小麦单 —— `main.py:3354`（含上方注释重写）

```python
V9_OPENING_STEP0 = (("BUY_PRODUCT", "WHEAT", 10), ("SELL", "WHEAT", 5))
```

- 原值 `(("BUY_PRODUCT","WHEAT",20), ("SELL","WHEAT",15))`。
- 该常量是 `_v9_opening()`（`main.py:3359`）在 step 0 覆盖 tape 小麦单的唯一来源；41 条 route 的
  step 0/1 开局完全相同（实测：41/41 都是 `BUY 13, BUY 30, SELL 30` / `SELL 13, BUY 5, HIRE×5,
  BUY_ANIMAL COW 2, SHEEP 2`），所以改这一处对所有 route 一致生效。
- 净小麦保持 **+5**（step 0 得 5、step 1 不再有小麦单），因此 d0/d1 的棚内小麦链条与原来的
  20/15 开局**逐格相同**（实测 step-24 边界棚内小麦都 = 3，而 3 正是 d1 三条 FEED 需要的量）。

### 1.2 (b) 雇工准备金护栏 —— 文件末尾 `_hr_guard`

按任务原文实现：`step ∈ {24, 25}` 且 `farm.money < 5` 时，从市场单里删掉所有 `BUY_*`
（`BUY_PRODUCT` → `BUY_SEED` → `BUY_ANIMAL` → `BUY_LAND` 的优先级写在 `_HR_ORDER` 里，注释说明理由），
保证 step 24 的 3 个 `HIRE`（$1+$1+$2 = $4）一定付得起。纯函数，直接单元测试通过：

```
step24 money=1 with BUY_* -> strip  -> [['HIRE'], ['HIRE'], ['HIRE']]
step25 money=3 with BUY_* -> strip  -> [['HIRE'], ['HIRE'], ['HIRE']]
step24 money=12 -> keep             -> [... 保留 BUY_PRODUCT WHEAT 3, BUY_SEED WHEAT 1]
step26 money=1 -> untouched         -> 不在窗口内，不动
step24 money=1, no BUY -> untouched -> 没有可删的单
```

实测在 300 局巡回赛 + 各压力用例里 `hr_fires = 0`（即 (a) 生效后它永不触发）。

### 1.3 (c) 喂食救援层 —— 文件末尾 `_er_*`

逐回合（hour ≥ 1、day ≤ 28）执行：

1. 收集所有 `animal` 格，取 `fed_today == False and consecutive_unfed >= 1`（今晚刷新就逃逸）的格子；
2. **覆盖判定**：用 tape 重放"今天剩余回合 + 现存单位"的动作流（含位置、手上小麦、棚内小麦、
   PICKUP/DROP/FEED 的作物与存量），任何落在该格上的 FEED 都算覆盖；覆盖则完全不干预；
3. 只有判定为"今天不会有人喂"时，才把该格交给一个**动作本身就是空转**的单位
   （`_er_is_idle`：`PASS`，或走一步但会被引擎忽略的出界移动）：站在该格且手上有麦 → 改 `FEED`；
   站在该格、没麦、且**下一回合的 tape 动作也是空转** → 改 `PICKUP WHEAT`（下一回合再 FEED）；
4. 所有单位都在干活（`WATER/HARVEST/BUILD/PLACE/FEED/CARE/...`）→ 不干预；
5. `_ER_REPORT` 计数器挂在 `agent.telemetry` 上（`er_fired / er_feeds / er_pickups / er_covered /
   er_busy / er_nowheat / er_errors`）。

两层都沿用文件既有约定（`_X_PARENT = agent; del agent; def agent(...)` + `agent.telemetry` +
`agent = globals().pop("agent")`），因此 `mod.agent` 与"命名空间里最后一个可调用对象"都指向包含新层的完整链
（实测：`last callable in namespace: agent`）。`kaggle_submission_agent` 仍按原有设计指向
prvsiyan 的 `final_price_guard` 包装（注释里写明它**故意**不是入口点），未改动。

关键约束与它们各自的实测依据（见 §4.2、§4.3）：

| 约束 | 依据 |
|---|---|
| 只挪用 `_er_is_idle` 的单位（原来的 PASS 或真移动都算"闲"→ 改成只认 PASS/出界移动） | 借用一个"正在移动"的单位会让它当天余下所有 tape 动作的落点全错：巡回赛 244 → **191**/300 |
| 距离 0（必须已经站在动物格上，`_ER_MAX_DRIFT = 0`） | 允许走 1 格：244 → 188/300；走 2 格：单局 −$90k |
| hour ≥ 1（`_ER_MIN_HOUR`） | d1/d2/... 的 HIRE 在 h0 执行，h0 时农场看起来"没有雇工"，会把所有动物都判成无人喂 |
| day ≤ 28（`_ER_LAST_DAY`） | d29 逃逸不影响收益，而尾盘路线最紧：仅 d29 的三次救援就值 −$1.6k |

---

## 2. (a) 为什么不按"少买 1-2 单位小麦"实现

任务给的改法是"把 step 0-25 的小麦单数量下调 1-2 个单位"。实测（engines 内跑 720 步，对手 = 脚本化
`BUY 10 / SELL 10` co-sell，seed 1234）：

| step-0 小麦单 | money_t24 | hands@25 | d3 畜群 | step24 棚内小麦 | 结论 |
|---|---|---|---|---|---|
| `BUY 20 / SELL 15`（原版） | $1 | 1 | 3 | 3 | 触发 bug |
| `BUY 19 / SELL 15`（−1 单位） | $30 | 3 | **4** | **2** | 现金够了，但 d1 少一袋麦 → 换一种死法 |
| `BUY 18 / SELL 15`（−2 单位） | $57 | 3 | **3** | **1** | 同上，更糟 |
| `BUY 19 / SELL 14`（净 +5 不变） | $3 | 2 | 5 | 3 | 净小麦保住，但只多 $3，仍不够 $4 |
| `BUY 20 / SELL 16`（净 +4） | $28 | 3 | 4 | 2 | 同 BUY19 |
| `BUY 10 / SELL 5`（**采纳**） | **$12** | **3** | **5** | **3** | ✅ |

原因：#0 天固定支出 $2,842，开局这 5 袋小麦是 d0 两次喂食 + d1 三次喂食的唯一来源（棚内 5 → d0 用 2 →
d1 边界剩 3 → step 24/26 三次 PICKUP 正好用光）。少买 1 袋就把 d1 边界压到 2，第三条 FEED 断粮，牛照样跑。
"净小麦不变"的改法（少买 1 也少卖 1）只值 $3，差 $1。

真正的钱不在"买多少"，而在**那 15 单位的 SELL 排在同一 market slot**：对手在 slot 1 同时倾销 10 单位时，
我方 15 单位的均价被压低约 $11，把 d0 期末现金从 $12 压到 $1。把 SELL 调小到 5 单位以后，这个敞口按比例缩小。

**对手开局鲁棒性面板**（13 种脚本化对手开局 × 2 seed，取最差）：

| step-0 形状 | 最差 money_t24 | 说明 |
|---|---|---|
| `BUY 20 / SELL 15`（原版） | **$1** | 遇 `BUY 10/SELL 10`、`BUY 10/SELL 10/BUY_SEED` 归零；`BUY 12/SELL 12` 也只 $2 |
| `BUY 15 / SELL 10` | $8 | |
| `BUY 5`（纯买） | $12 | 全 13 种对手都是 $12–15 |
| `BUY 10 / SELL 5`（采纳） | **$12** | 最差 $12（co-sell 10 单位），常见 $18–30；对"对手大买"型开局还能吃到 $28–30 的顺差 |

对手开局面板：`BUY 10/SELL 10`、`BUY 10/SELL 10/BUY_SEED`、`BUY 14/SELL 14/BUY 5`、
镜像 `BUY 20/SELL 15/BUY_SEED`、无小麦单、`BUY 20`、`BUY 43/SELL 20/SELL 22`、`BUY 30/SELL 30`、
PASS、`BUY 20/SELL 20`、`BUY 25/SELL 25`、`BUY 50/SELL 50`、`BUY 12/SELL 12`。
（即"少买"型与"大买"型两头都测过：原版在 co-sell 型归零，采纳版两头都在 $12 以上。）

---

## 3. 复现验证（同一脚本，前后对比）

`scripts/early_death_local_repro.py` 的脚本化对手原本在 **engine step 1** 发单，而我们的卖单在
step 0，所以按注释用法跑不出来（`money_t24 = 15`，不触发）。已把它改成 step 0 发单（§5.1），
改后即为 §3.1 的"修复前"输出。

### 3.1 修复前（`main.py` = v23_c7）

```
$ .venv/Scripts/python scripts/early_death_local_repro.py --opponent cosell --games 2
opponent=scripted-cosell  games=2  (a game needs money_t24 >= $4 to buy 3 hands)
game  money_t1   money_t24  hands_t25 herd_d3  esc_d3   margin
0     2843       1          1         3        0        +177709
1     2843       1          1         3        0        +172186

2/2 games with fewer than 3 hands at day-1 hour 1
```

### 3.2 修复后（`fix/early-death`）

```
$ .venv/Scripts/python scripts/early_death_local_repro.py --opponent cosell --games 2
opponent=scripted-cosell  games=2  (a game needs money_t24 >= $4 to buy 3 hands)
game  money_t1   money_t24  hands_t25 herd_d3  esc_d3   margin
0     2854       12         3         5        0        +176225
1     2854       12         3         5        0        +150407

0/2 games with fewer than 3 hands at day-1 hour 1
```

验收口径：`money_t24 1 → 12`（> 5 ✅）、`hands@25 1 → 3`（== 3 ✅）、`d3 畜群 3 → 5`（== 5 ✅）。

---

## 4. (c) 的三个版本：怎么从 −56 局修到 0 局

### 4.1 同一批种子（2000-2019，单座位，15 个对手，300 局）的巡回赛对照

| 候选 | 胜 | tournament_results/ 里的文件 | 说明 |
|---|---|---|---|
| `main`（v23_c7） | **244/300 (81.3%)** | `base-v23c7-20260922-182718.json` | 基线 |
| 只上 (a)（把 (c) 设成 inert） | **256/300 (85.3%)** | `var-a-only-20260922-183544.json` | (a) 单独就是 +12 局 |
| (a) + (c) 宽松版（PASS 或移动都能挪用；drift≤2） | 191/300 (63.7%) | `fix-early-death-20260922-183227.json` | ❌ 灾难 |
| (c) 单独（原开局 + 宽松版 (c)） | 188/300 (62.7%) | `var-c-only-20260922-183856.json` | ❌ 与 (a) 无关，是 (c) 的问题 |
| **(a)+(b)+(c) 严格版（最终，= main.py）** | **256/300 (85.3%)** | `fix-early-death-v2-20260922-184333.json` | ✅ 与"只上 (a)"逐对手完全相同 |

逐局审计（vs `guru`，seed 2000-2007，`scripts/.scratch_ed/fire_audit.py` 之类逐局对比）说明"宽松版"的破坏方式：

```
seed 2000  off      +85   on     -2342   delta -2427   fires={'er_fired': 2, 'er_feeds': 2, ...}
seed 2001  off     +125   on     -1005   delta -1130   fires={'er_fired': 1, 'er_pickups': 1, ...}
seed 2002  off     +113   on     -6105   delta -6218   fires={'er_fired': 3, ...}
seed 2003  off      +92   on       +92   delta    +0   fires={}                       <- 没触发就逐分相同
seed 2004  off      +86   on     -2652   delta -2738   fires={'er_fired': 3, ...}
seed 2005  off     +537   on     -1174   delta -1711   fires={'er_fired': 3, ...}
seed 2006  off      +87   on     -1355   delta -1442   fires={'er_fired': 1, ...}
seed 2007  off      -13   on       -13   delta    +0   fires={}
```

根因：**借用一个"正在移动"的单位，它当天余下所有 tape 动作的落点就全错了**（喂完牛它停在原地，
而 tape 以为它已经走开，后面的 HARVEST/DROP/交付全落空）。一次触发就值 −$1.1k~−$6.2k。
把"闲"重新定义为"动作本身是空转"（PASS / 出界移动）以后，同一批 8 局全部 `delta +0`，
`off 7/8` 与 `on 7/8` 完全一致。

### 4.2 严格版仍然能完成原本要救的场景（压力用例）

构造"d1 只雇到 3 手但棚内小麦少 1 袋"（把 (a) 换成 `BUY 19 / SELL 15`，即"少买 1 单位"那一档）：

```
buy19 stress (net +4)  layer=False seed=1234  $ 30 hands=3 herd d3=4 d6=7 d29=16 escapes=[(2, 1)]  margin= +169494
buy19 stress (net +4)  layer=False seed=1235  $ 30 hands=3 herd d3=4 d6=7 d29=15 escapes=[(2, 1), (27, 1)] margin= +151320
buy19 stress (net +4)  layer=True  seed=1234  $ 30 hands=3 herd d3=5 d6=8 d29=17 escapes=[]  margin= +176204
buy19 stress (net +4)  layer=True  seed=1235  $ 30 hands=3 herd d3=5 d6=8 d29=16 escapes=[(27, 1)] margin= +150386
fix (a) buy10/sell5    layer=False seed=1234  $ 12 hands=3 herd d3=5 d6=8 d29=17 escapes=[]  margin= +176225
fix (a) buy10/sell5    layer=True  seed=1234  $ 12 hands=3 herd d3=5 d6=8 d29=17 escapes=[]  margin= +176225
```

读法：
- 压力档（d1 feed 断粮）：救援层用 **1 次 FEED + 1 次 PICKUP** 把那头本该在 d2 逃逸的牛救回来，
  `d3 畜群 4 → 5`、逃逸从 `[(2,1)]` 变空、边际 **+$6,710**；
- 正式档（(a) 已修好）：救援层 `er_fired = 0`，前后边际逐分相同 → **不动的保险丝**。

---

## 5. 验证清单（原始输出）

### 5.1 复现脚本修正

`scripts/early_death_local_repro.py` 的 `cosell_agent` 原为 `if observation["step"] == 1`，
而我们要卖小麦的那一步是 engine step 0（分析报告里的"第 1 步"= `env.steps[1]` 的那个观测，
即 step 0 的动作）。改成 `== 0` 后与 §3 的实测一致，并补了注释说明。

### 5.2 烟测

```
$ .venv/Scripts/python scripts/smoke.py main.py opponents/guru/main.py
  seed 1000 seat 0: DONE $74494 (opp $74879)
  ... （18 行，全部 DONE）
smoke OK

$ .venv/Scripts/python scripts/smoke.py main.py opponents/prvsiyan/main.py
  seed 1000 seat 0: DONE $74475 (opp $74933)
  ... （18 行，全部 DONE）
smoke OK
```

（第一次烟测是在 (c) 宽松版上调的，最终版又跑了一遍，两次都 `smoke OK`、18/18 DONE、无崩盘。）

### 5.3 回归巡回赛（新面板、单座位）

```
$ .venv/Scripts/python scripts/tournament.py --candidate .scratch_ed/base_v23c7.py --seeds 2000-2019 --seats 0 --workers 16 --tag base-v23c7
$ .venv/Scripts/python scripts/tournament.py --candidate main.py --seeds 2000-2019 --seats 0 --workers 16 --tag fix-early-death-v2
$ .venv/Scripts/python scripts/compare_tournaments.py \
      tournament_results/base-v23c7-20260922-182718.json \
      tournament_results/fix-early-death-v2-20260922-184333.json --labels v23_c7 fixed
```

| opponent | baseline | fixed | base mean | fixed mean | Δmean | base worst | fixed worst |
|---|---|---|---|---|---|---|---|
| beatv48   | 18W-2L-0T  | 18W-2L-0T  | +3472   | +3476   | +4    | -327  | -323  |
| guru      | 15W-5L-0T  | 15W-4L-1T  | +70     | +83     | +13   | -162  | -149  |
| ourv21    | 20W-0L-0T  | 20W-0L-0T  | +1425   | +1438   | +13   | +289  | +302  |
| pilkwang  | 20W-0L-0T  | 20W-0L-0T  | +7384   | +7360   | -25   | +3970 | +3945 |
| **prvsiyan** | 5W-12L-3T | **13W-7L-0T** | -9   | +3      | +12   | -241  | -229  |
| reyhan    | 20W-0L-0T  | 20W-0L-0T  | +5093   | +4050   | -1043 | +1292 | +1266 |
| rule_v15  | 20W-0L-0T  | 20W-0L-0T  | +92864  | +92864  | 0     | +71764| +71764|
| salem     | 20W-0L-0T  | 20W-0L-0T  | +33795  | +33795  | 0     | +18908| +18908|
| tetsutani | 20W-0L-0T  | 20W-0L-0T  | +38968  | +38968  | 0     | +24704| +24704|
| v49branch | 17W-3L-0T  | 17W-3L-0T  | +1182   | +1186   | +4    | -1335 | -1331 |
| v50       | 17W-3L-0T  | 17W-3L-0T  | +1182   | +1186   | +4    | -1335 | -1331 |
| v51       | 16W-4L-0T  | 16W-4L-0T  | +890    | +894    | +4    | -1980 | -1976 |
| v52       | 15W-5L-0T  | 15W-5L-0T  | +385    | +389    | +4    | -1980 | -1976 |
| v53       | 15W-5L-0T  | 15W-5L-0T  | +385    | +389    | +4    | -1980 | -1976 |
| **v55**   | 6W-14L-0T  | **10W-10L-0T** | -47  | -35     | +12   | -419  | -407  |
| **TOTAL** | **244W-53L-3T** | **256W-43L-1T** | **+12469** | **+12403** | -66 | -1980 | -1976 |

```
games identical (bit-for-bit reward): 60/300
win/loss flips: 12  (gained 12, lost 0)
```

- 六个"护栏对手"（beatv48 / ourv21 / rule_v15 / tetsutani / reyhan / salem）**无一退化**：
  beatv48/ourv21/rule_v15/tetsutani/salem 逐局相同或持平，reyhan 仍 20W-0L（均值 −$1043，但最差边际反而好 $26）。
- 提升集中在**自家血缘的近镜像对手**（prvsiyan +8 局、v55 +4 局），正是刀口 bug 原来杀得最狠的地方。
- TOTAL 均值 −$66 完全来自 reyhan 的 −$1043（20 胜里少赚），胜局数不降；其余 14 个对手均值持平或微升。

### 5.4 性能

```
$ .venv/Scripts/python .scratch_ed/perf.py         # 同一颗 seed，719 次调用
base   calls=719 mean=0.77ms  p50=0.47ms  p95=1.49ms  p99=3.70ms  max=39.41ms
fixed  calls=719 mean=0.83ms  p50=0.49ms  p95=1.32ms  p99=4.22ms  max=38.70ms
```

每回合均值 +0.06ms（主要是"扫描 100 个格子找有风险的动物"），p95 反而略降，峰值不变，离 1s 上限极远。

---

## 6. 与任务描述的偏离（需要确认的地方）

1. **(a) 没有按"少买 1-2 单位小麦"做**：那样做现金够了但 d1 小麦链条断粮，`d3 畜群` 从 3 变 4/3，
   等于换个死法（§2 有完整实测表）。采纳的是"净小麦不变、把 SELL 从 15 缩到 5"，等价于改注释里
   早就推荐的 `BUY 10 / SELL 5` 备选开局（`main.py:3349` 原文："Replacing it with BUY 10, SELL 5 at
   step 0 (still net +5, nothing at step 1) ..."）。
2. **(c) 的门槛比任务描述紧得多**：任务要求"找最近的动作是 PASS 或纯移动的单位"；实测那样会破坏既有
   行为（244→191/300）。最终版只挪用"动作本身就是空转"的单位，并且必须已经站在动物格上（距离 0）。
   代价是救援覆盖率变低（多数情况 `er_busy`/`er_nowheat` 后放弃），收益是**在正式配置下与不加层逐分相同**。
   换句话说：(c) 现在是**保险丝**，不是主要修复手段；(a) 才是主要修复。
3. **(b) 保持原样**（窗口、$5、削 `BUY_*`），虽然它实测从不触发。若希望它真的有用，(b) 的窗口应往前
   挪到 d0 的采购段（例如 `money - 5 < 本步 BUY 总价` 就砍单），但那会牺牲 d0 的种子/动物，需要单独评估，
   本次未做。

---

## 7. 风险与未验证项

1. **对手指纹表可能失效（唯一实质风险）**。`CT_TABLE`（`main.py:4075`，2 条）与 `_V93_ROUTE_BY_RIVAL`
   （`main.py:1010` 附近，1 条）都用"对手 step-2 的 `(money, market WHEAT inventory)`"精确识别对手 tape。
   实测这组指纹确实被本改动移动了（本地 15 个对手，seed 2100-2102）：

   | 对手 | 旧开局指纹 | 新开局指纹 |
   |---|---|---|
   | beatv48 | (154.000, 9959) | (152.000, 9959) |
   | guru | (1052.000, 9989) | (1046.000, 9989) |
   | ourv21 | (1052.000, 9989) | (1046.000, 9989) |
   | pilkwang | (1035.000, 9989) | (1047.000, 9989) |
   | prvsiyan | (1042.000, 9989) | (1036.000, 9989) |
   | reyhan | (996.000, 9989) | (1026.000, 9989) |
   | rule_v15 / salem / tetsutani | (2398, 9994) / (3, 9989) / (103, 9992) | 不变 |
   | v49-v53 | (154.000, 9959) | (152.000, 9959) |
   | v55 | (1042.000, 9989) | (1036.000, 9989) |

   第二项（市场小麦库存）不变（我们的净小麦不变），第一项（对手现金）被移动了几美元到几十美元，
   而表键的精度是 0.001 → **凡是会在 step 0/1 动小麦的对手，这两张表都可能不再命中**。
   本地面板本来就不命中这两张表（键值对不上），所以巡回赛看不出这个代价，**线上到底损失多少无法在本地验证**。
   建议后续用录制语料重新标定这两张表的键（或者在键上按"库存 + 现金区间"放宽），本次未做（无法验证）。
2. **(c) 的收益面很窄**：严格版只在"有单位正好空转站在风险动物格上"时才救。`er_busy`/`er_nowheat` 说明
   相当一部分场景它选择放弃（宁可漏救）。这是有意为之（任务原文："宁可不救也不能破坏正常日程"）。
3. **只做了同种子单座位（seat 0）的 300 局配对回归**，未做双座位；也未跑线上（按要求未提交）。
4. 早死 bug 的样本只有 8/183 局（4.4%），本修复对总体 Elo 的期望增益只能间接估计：其中 prvsiyan +8 局、
   v55 +4 局、guru −1L+1T 的单座位结果与"少 2 头牛 = −$7.4k"的机制一致，但样本量小。
5. `results/early_death_analysis.md` §6.2 要求的"20 组对手单 × 20 局"的完整回归没做；本报告用
   13 种脚本化开局 × 2 seed 的鲁棒性面板 + 300 局真实对手配对回归替代。

---

## 8. 建议

- **建议采用 (a)+(b)+(c 严格版)**：300 局配对回归 12 胜 0 负、六个护栏对手零退化、复现用例按验收口径
  全部达标、性能与稳定性无虞。
- **采用前需要人判断的一件事**：§7.1 的两张对手指纹表（`CT_TABLE` / `_V93_ROUTE_BY_RIVAL`）会因开局形状
  改变而失去精确匹配。它们的收益范围是"少数特定对手 tape 的针对性应对"，代价是 4.4% 的必输局；
  如果认为那两张表更重要，可以退而选择 (a) 的保守档 `BUY 15 / SELL 10`（最差 $8，仍高于 $5 门槛）
  或者干脆只上 (b)（但 (b) 单独无法把 `money_t24` 从 $1 抬到 $5 以上，无法根治）。
- 后续可选工作（未做）：用录制语料重标定指纹表；把 (b) 的窗口前移到 d0 采购段并单独评估；
  给 (c) 增加"借用一个移动单位但事后把落点补回来"的更聪明版本（本次实测的直接挪用代价过高）。

---

## 附：交付物与临时脚本

分支 `fix/early-death`（从 `main` 开出），工作区未提交（按要求不 commit / 不 push / 不提交 Kaggle）。

| 文件 | 状态 |
|---|---|
| `main.py` | 修改（+356/−1）：`V9_OPENING_STEP0` 与文件末尾追加 (b)(c) 两层 |
| `scripts/early_death_local_repro.py` | 新增到本分支（来自 `exp/v24-v55`）+ 修正 step-0 触发器 |
| `results/early_death_fix.md` | 本报告 |
| `tournament_results/{base-v23c7,var-a-only,var-c-only,fix-early-death,fix-early-death-v2}-*.json` | 五轮巡回赛原始结果 |

以下临时脚本都在 `.scratch_ed/`（未纳入版本控制）：

| 脚本 | 用途 |
|---|---|
| `.scratch_ed/repro_step0.py` | 复现脚本的 step-0 触发器版本（§5.1 的正式修正在 `scripts/` 里） |
| `.scratch_ed/variant_sweep.py`、`opening_sweep.py` | step-0/step-1 开局形状扫描（引擎内） |
| `.scratch_ed/opp_sweep.py` | 13 种对手开局 × 5 种我方开局的鲁棒性面板 |
| `.scratch_ed/pair_sweep.py` | 用 `scripts/early_death_step1_market.py` 的市场循环做 (buy, sell) 快速扫描 |
| `.scratch_ed/stress_c.py` | (c) 的压力用例（人为造出 d1 断粮档） |
| `.scratch_ed/fire_audit.py`、`log_fires.py`、`dbg*.py`、`tele*.py` | 逐局审计救援层的触发点与代价 |
| `.scratch_ed/perf.py` | 每回合耗时对比 |
| `.scratch_ed/ct_probe.py` | 对手 step-2 指纹表前后对比（§7.1） |
| `.scratch_ed/var_a_only.py`、`var_c_only.py`、`base_v23c7.py` | 巡回赛隔离实验用的候选文件 |

（注意：kaggle-environments 会吞掉 agent 的 stdout，调试输出必须写文件。）
