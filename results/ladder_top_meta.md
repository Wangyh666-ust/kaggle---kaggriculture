# 天梯头部 meta 分析（2026-09-22）

> **数据附录**：`results/ladder_top_meta_data.md`（由 `scripts/ladder_meta_report.py` 自动生成，全部数字可重跑复现）
> **语料**：15 局头部对局 + 24 局我们自己的线上对局
> **抓取工具**：`scripts/fetch_ladder_replays.py`

---

## 0. 结论速览

1. **我们线上遇到的一半对手，就是同一个公开克隆（和我们同一份代码）。** 24 个对手座位里有 12 个的 d20 农场构成是 `STRA33+WHEA25`，与我们的画像逐字段相同。这是"克隆天花板"最直接的证据。
2. **榜首不是克隆，是一个被至少 6 支头部队伍共享的** ***另一个*** **agent**（含 #1 和 #2）。它开局就和我们不同，农场计划也不同。
3. **我们几乎永远碰不到那个家族**——Elo 只配对相近分数，2450 的我们和 3000+ 的队伍不在一局里。**所以只看我们自己的回放，永远看不到差距在哪；必须看他们的对局。**（这条验证了抓头部回放的思路）
4. **"番茄 day12"这条线索是负面结果**：引擎机制决定番茄一株只产 4 次（与种植日无关），早种只是把同样 4 次收成提前卖；而我们的价格数据显示，我们局里番茄价格整季**上涨**（d20 $74 → d27 $120），晚卖反而更贵。所以提前番茄线**不是** 650 分的来源。
5. 真正的结构性差异在 **畜群构成** 和 **作物组合**：头部是"牛为主 + 番茄/胡萝卜"，我们是"羊为主 + 33 草莓"。

---

## 1. 方法

Kaggle 对模拟赛公开三个接口，我们此前没用上：

```bash
kaggle competitions team-submissions <team_id>   # 任意队伍的全部活跃提交
kaggle competitions episodes <submission_id>     # 该提交打过的对局
kaggle competitions replay <episode_id> -p DIR   # 回放 json
```

每条回放里带 **`info.seed`** 和 **双方 720 步完整动作**（`{"farmer":…, "hands":…, "market":…}`）。这就是头部队伍的全部行为观测面。

复现：

```bash
.venv/Scripts/python scripts/fetch_ladder_replays.py --top 12 --episodes 3
.venv/Scripts/python scripts/ladder_meta_report.py \
    --top replays_ladder replays_top replays_ladder_ops \
    --ours replays_v25 --ours-team ReD_MooN_rise
```

> 抓取注意：Kaggle 的 REST 层会按凭证限流（429）。`fetch_ladder_replays.py` 走 CLI 子进程 + 90s 退避重试，可断点续跑（只下缺失文件）。

---

## 2. 发现一：天梯中层一半是我们的同克隆

`results/ladder_top_meta_data.md` §4 里，我们 24 局的对手座位：

| d20 作物构成 | 座位数 |
|---|---|
| **`STRA33+WHEA25`（与我们逐字段相同）** | **12** |
| `MELO14+STRA35+WHEA13` | 2 |
| `STRA4+WHEA9` / `MELO12+STRA39` / 其他 | 10 |

而且不少对手的 d12/d16/d29 画像与我们**完全一致**（同为 `C8+G3+S6 / STRA33+WHEA24 / 25 空地块 / 9 雇工`）：`coke lu`、`democatXamer`、`Pardheev Krishna`、`Pat` 等。

**含义**：2450 这个分数不是"我们的 agent 的能力值"，而是**这份公开文件在天梯上的均衡点**——半个池子跑同一份代码，互相打成 50/50，Elo 就停在那里。对同克隆的胜负由商店抽签和几十美元的微差决定（我们的 4 局败局分差分别是 $2,932 / $1,499 / $286 / $36）。

---

## 3. 发现二：榜首是一个被共享的、与我们不同的 agent

按第 2 步市场单聚类（`ladder_top_meta_data.md` §2），15 局语料里出现：

**家族 2（主流）—— 6 支队伍同签名，含 #1 与 #2**

```
step1: [["BUY_ANIMAL","COW",1],["BUY_PRODUCT","WHEAT",5]]
step2: [["SELL","WHEAT",1],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",3]]
```

成员：`Vadim Vasilenko`(#1, 3110.7)、`DECEM`(#2, 3060.6)、`mtmr_s1`(#6, 3026.0)、`ymg_aq`(#9, 2985.3)、`Unknown Mother-Goose`(#10, 2980.1)、`TheEggman`(#11, 2979.9)；`吃白饭的大肥鱼`(#8) 的第 2 步为空但第 1 步等价。

**我们的开局**（同表家族 1，24 个座位全是这个）：

```
step1: [["BUY_PRODUCT","WHEAT",10],["SELL","WHEAT",5],["BUY_SEED","WHEAT",1]]
step2: [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

两者的第 1、2 步动作**完全不同**（他们 `SELL WHEAT 1` + 4 雇工 + 1 牛 1 羊 3 羊；我们 5 雇工 + 2 牛 2 羊）。

同一份语料里还有 **家族 9** = 未经任何改动的地道公开磁带开局（`BUY 13, BUY 30, SELL 30` / `SELL 13, BUY 5, HIRE×5, COW 2, SHEEP 2`）——即我们 README 里记录的那条基线。它在中游，不在头部。

---

## 4. 发现三：农场计划的结构差异

`ladder_top_meta_data.md` §3 与 §4 的 d20 快照（$k / 畜群 / 作物 / 空地块 / 雇工）：

| 阵营 | 畜群 | 作物 |
|---|---|---|
| 家族 2（Vadim、mtmr_s1 等） | `C10+G3+S11`、`C13+S10`、`C10+G2+S10` | `STRA10-24 + TOMA10-16 + WHEA17-28 + CARR5-20` |
| **我们** | `C6+S17`、`C8+G3+S6`、`C6+G2+S9` | **`STRA33 + WHEA24-25`**（多数局到 d29 都不变） |

三个可量化的差异：

1. **畜群：他们养 ~10 头牛，我们 6-8 头牛 + 6-17 只羊。** 牛（first_yield 8 天 / interval 2）比羊（6 天 / 3）产出频率高得多。
2. **我们 33 棵草莓从 d12 一路挂到 d20 之后不动**；他们 d20 只剩 10-24 棵草莓，把地让给番茄和胡萝卜。
3. **番茄触发率**：他们 12/12 局都买番茄种；我们 24 局里只有 4 局（17%）。

---

## 5. 发现四：番茄时机是负面结果（重要）

`results/top_notebooks_findings.md` 里我们自己记过"头部第 12 天起买 ~9 粒番茄种子 → 番茄是头部 meta 必备项"，haideptry 的公开 notebook 也把"day-12 番茄"称为通往 3000+ 的路。**但引擎机制和价格数据都不支持"提前番茄线能带来分数"。**

### 5.1 引擎机制：番茄一株只产 4 次，与种植日无关

`env/kaggriculture.py`：

```python
"TOMATO": {"first_yield_day": 8, "max_yield": 4, "interval": 1, "ongoing": True}
```

`_daily_refresh_plants` 里 `production_count = days_since_first // interval + 1`，且 `production_count > max_yield` 时**直接 continue**。所以每株番茄**恰好产 4 次**，种植日只决定这 4 次落在哪几天：

| 种植日 | 收获日 | 次数 |
|---|---|---|
| 18（我们现状） | 26、27、28、29 | 4 |
| 12（头部） | 20、21、22、23 | 4 |

**产量完全相同**，只有销售窗口不同。我们层里的注释"day26..29 生产窗口"是对的，不是 off-by-one。

### 5.2 价格数据：我们局里番茄整季**上涨**，晚卖更贵

`scripts/price_trace.py` 跑 24 局我们的线上对局：

| 产品 | d16 | d20 | d24 | d26 | d27 | d29 | early(20-23) | late(26-29) | Δ |
|---|---|---|---|---|---|---|---|---|---|
| **TOMATO** | 68.7 | 74.5 | 95.7 | 115.6 | 120.2 | 119.6 | **78.4** | **118.2** | **+39.9** |
| STRAWBERRY | 199.2 | 137.2 | 63.0 | 68.6 | 57.5 | 63.2 | 108.5 | 65.4 | -43.2 |

（基准价：番茄 60、草莓 120。番茄**高于**基准且整季升 → 小镇消耗 > 供给 → 捂到 d26-29 卖比 d20-23 卖贵 51%。）

同样的脚本跑 15 局头部对局：

| 产品 | d16 | d20 | d24 | d26 | d29 | early | late | Δ |
|---|---|---|---|---|---|---|---|---|
| TOMATO | 68.3 | 71.7 | 70.1 | 67.9 | 63.9 | 71.8 | 66.1 | **-5.7** |

**在我们局里番茄涨到 $120，是因为半个池子不种番茄；在头部局里平在 $64，是因为那个家族全都种。** 也就是说：番茄这条线的价值会**在我们爬分的过程中自动消失**——这正是"对着弱克隆面板调参"会骗人的典型例子。

**决策：不改番茄行的启动日。** 省下的一天工时投到发现三里更硬的结构差异上。

### 5.3 外部佐证：作者本人试过，也是负面结果

thomastschinkel（我们的底盘作者，"The 2945 Farm"）在 2026-09-19 的公开 notebook 里写下了同一条结论，而且更狠：

> v9/4 beats every public notebook, yet against seven of today's top-10 teams it went **0 – 36** on the ladder (September 15–17). **We lead until day 10, because the melon race is ours, and lose it all after day 11.** The biggest single hole is **tomatoes**. The farms that beat us buy about **9 tomato seeds from day ~12** and hold about **10 tomato tiles on day 20**. We buy 1.6, and the first on day 18. **They sell 71 tomatoes at $114 each. We sell 7, at $316.**

然后他试了三种番茄方案，**全部失败**：

| 方案 | 结果 |
|---|---|
| 用 tape 的小麦地块做番茄覆盖（day 13 起） | **0 胜 / 85 负** |
| 新开地做 20 格番茄 | **0 / 56** —— "the crews cannot water 20 more tiles" |
| 放宽现有番茄层的门槛 | +4 / −11 |

他的结论：**"The route tape is the constraint. Its workers are busy from dawn to dusk, so a tomato program needs a different *labour* plan, not just a different crop choice. The adaptive farms don't replay a tape. They plan the crew around the crops."**

这段佐证了两件事：
1. 番茄是**差距的特征**，不是**可复制的药方**——他的数量级（对手 71 颗 @$114，他 7 颗 @$316）说明差距在**量**上，而量受**劳动力**约束。
2. 我们 5.1/5.2 的负面结论独立成立：**问题不在"什么时候种番茄"，在"没有多余的人工去种/浇番茄"。** 这也解释了为什么我们的番茄层触发率只有 17%——不是门槛设错，是人手不够时它会合理地放弃。

另外注意他给出的一个反直觉数据：**每一笔卖出同时也是压制**（"every sale is also denial"）——他去掉 103 颗草莓，自己少赚 $5.5k，**对手多赚 $5.5k**。这是"我们 33 颗草莓 vs 头部 20 颗"那条差异的另一面，值得单独立项。

---

## 6. 这改变了什么

| 原计划 | 数据后的修正 |
|---|---|
| 把番茄线从 day 18 提到 day 12 | **取消**（机制上不增产量，价格上更差；作者本人三试三败且失败原因是劳动力） |
| 对着 15 个公开 agent 的面板调参 | **降级**：面板已饱和（256/300，且 v55 21-19、其余 20-0）。它测不出与头部的差距 |
| 抓头部回放 | **保留**，但优先级下调——见 §8 的语料捷径 |
| —— | **新增候选**：把"劳动力规划"当成一等公民（而不是继续在 tape 上打补丁） |

---

## 7. 一个必须记住的方法论事实：同种子 ≠ 同世界

我们一度想用"拿头部的 seed 在本地重放"来直接量差距。**这条路是堵死的**，而且原因是机制性的。

`env/kaggriculture.py:_end_of_day` 里的顺序是：

```python
rng = random.Random((seed * 1_000_003) ^ day)
_spawn_weeds(farm, board_size, weed_chance, rng)   # 双方各自的空地格各消耗一次 rng.random()
...
town["unlocked_shops"].append(rng.choice(sorted(SHOPS)))   # 同一台 rng，之后才抽商店
```

而 `_spawn_weeds` 是 `if farm["tiles"][y][x] is None and rng.random() < weed_chance` —— **只有空格子才消耗随机数**。所以：

> **商店解锁序列取决于双方当时有多少空地，也就是取决于双方自己的打法和对方的打法。**

实测（`scripts/seed_probe.py`）：seed 8823651 上，头部那局的第一家店是 d3 `BAKERY`；我们用同一 seed 跑镜像，第一家店是 d3 `FARMERS_MARKET`。**从第一家店就不一样。**

含义：
- 任何"把我们的 agent 放到他们的 seed 上比钱"的做法**都是无效的**，必须放弃这个念头。
- 我们**永远无法在本地和头部家族对局**——除了在天梯上。
- 相对的：**本地固定的 A/B 面板是有效的**（两臂同 seed、同对手、同初始状态），这是本项目一直在用的协议，继续用。

复现：

```bash
.venv/Scripts/python scripts/seed_probe.py --seed 8823651 --cand main.py --opp main.py
.venv/Scripts/python scripts/panel_shop_keys.py --seeds 2000-2019 --opp opponents/v55/main.py
```

---

## 8. 语料捷径与可行动项（2026-09-22 补充）

后续调研发现三件改变优先级的事：

1. **有更新的公开血统：V56 / V57。** 同一位作者（Ahmed Berat Ozer）在 V55 之后又发布了
   `kaggriculture-v56-smarter-seeds-and-fertilizer`（09-21）和
   `kaggriculture-v57-funding-order-invariant`（09-22，最新）。我们当前是 V55 等价体。
   "追血统拿层"是本项目唯一被反复验证过的正向手段（v21→v23_c7 +289 Elo），所以这是
   **当下性价比最高的一步**。

2. **已经有人放出了现成的天梯对局语料。** Kaggle 讨论区 `737034`（VijaiKurianMathew）
   公开了 **537 局完整 720 步天梯对局 / 25 万+ 动作**，含 `matches_meta.csv`、
   `market_orders.csv`、`farmer_actions.csv`、`town_shop_schedules.csv`。
   这比 `scripts/fetch_ladder_replays.py` 逐局抓取快得多（而且现在 API 正在限流）。

3. **比赛 2026-09-30 截止**，还剩 8 天；当前 #1 = 3116.9，top-10 门槛 ≈ 2979.9，共 9838 队。

### 因此的下一步排序

| 优先级 | 动作 | 理由 |
|---|---|---|
| 1 | 拉 V57（+V56）源码，按老办法做消融/合并，面板 A/B | 唯一被验证过的正向手段；成本低 |
| 2 | 下载 537 局语料，跑 `ladder_meta_report.py` 的同款分析 | 把头部观测从 15 局扩到 500+ 局 |
| 3 | 用 `scripts/submit.py` 提交，固定哈希纪律 | 排除"提交错文件"这一类事故 |
| 4 | 立项"劳动力规划"（而不是继续加 crop 线） | 作者本人和我方数据都指向这里 |

---

## 9. 局限

- 头部语料只有 15 局、12 支队伍，且都来自同一时段（2026-09-22 下午）。家族判定基于前 3 步签名，可能有行为等价但字符串不同的成员未被归入。
- 价格轨迹是**各局自己的报价均值**，不是同世界对照。它回答的是"整季形状"，不是"A 方案比 B 方案多赚多少钱"。
- 绝对资金**不可跨局比较**（商店组合决定经济量级）。§3/§4 的对比只看结构和比例，不看绝对额。
- 我们 24 局里没有一局对上头部家族，**没有任何直接头对头证据**，且 §7 说明这在本地无法补。
- §5.3 引用的 thomastschinkel notebook 内容来自二次调研（子代理读取公开 notebook 原文），未由我逐字复核。
