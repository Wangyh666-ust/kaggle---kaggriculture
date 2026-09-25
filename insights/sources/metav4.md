# The Metav4 Farm (Submission v13) — thomastschinkel

- **链接**：https://www.kaggle.com/code/thomastschinkel/the-metav4-farm-submission-v13
- **票数**：88（重跑 2026-09-20）
- **性质**：他最新的天梯 agent，**完整开源**。产物 `main.py` 1,004,288 字节，sha256 `9d634946…`
- **重要**：**这份 payload 与我们面板里的 `opponents/guru/main.py` 逐字节一致**（同一个 sha256）。
  也就是说 `guruprasaathas111/kaggriculture-master-engine-v3` 是它的再发布。
  我们对这个 agent 的成绩：**38胜2负**（v34+，580 局面板里）。

## 关键原文（保留原句）

### §6 夺冠队伍怎么拉开差距（最重要的一条）

> "While submissionv13 dominates all public notebooks and its predecessors, dissecting the top 10
> on the live leaderboard reveals an intriguing architectural evolution. Using our route-match
> diagnostic (`rdiff.py`), we measured how closely the top teams follow the standard route library
> across each 6-day phase of the game"

| Team | Days 0–5 | Days 6–11 | Days 12–17 | Days 18–23 | Days 24–29 | Edge over our tape |
|:--|:--:|:--:|:--:|:--:|:--:|--:|
| Kaggriculture Agent | 1.00 | 0.99 | 0.96 | 0.92 | 0.82 | +$0.8k |
| Driz Lo | 0.82 | 0.98 | 0.74 | 0.77 | 0.53 | +$0.2k |
| **mtmr_s1** | 0.95 | 0.95 | 0.95 | **0.12** | **0.12** | **+$5.2k** |
| **feel the agi** | 0.47 | 0.81 | **0.14** | **0.13** | **0.14** | **+$7.0k** |
| **keiz / DeeperNet** | 0.32 | 0.51 | **0.13** | **0.12** | **0.14** | **+$5.5k** |

> "**The revelation:** Teams with similar scores to us replay the tape all the way through day 29.
> But every single team that beats us by $5k–$7k **abandons the tape completely around days 12–18**!
> At day 12–18, they hand farm execution over to an **adaptive planner** that dynamically
> re-allocates labour, purchases seeds to match real-time shop demand, and staggers harvests.
> **Replicating this handover is the primary open research question in Kaggriculture today.**"

### §7 失败清单（负面结果，省我们重复踩坑）

| Idea | Result | Why it failed |
|:--|:--|:--|
| **Full greedy LP scheduler** | **−$4.4k ~ −$16.8k** | "A hand-crafted greedy task/distance scheduler lacks the turn-by-turn routing density of the tuned offline tape." |
| FSHIFT per-unit turn delays | −$1.4k ~ −$1.9k | inserting fertilize before tape waterings drops critical waters |
| **Complete tomato project on tape land** | **−$945 ~ −$2.3k** | 地块上的番茄要打赢 ~$460 被挤掉的小麦 + $144/天工资；饱和的商店只值 ~$50 |
| CSHEEP: early cow→sheep swap | **Inert (0 fired)** | 开局现金余量只有 ~$6，羊贵 $100 会饿死后续采购 |
| **Holding premium goods for peak price** | **−$1.2k ~ −$3.2k** | 对手先卖，价格在我們卖出前就崩到 $1 |
| **CARROT2 margin increases (+20, +50)** | **−$148 ~ −$258** | 过度限制胡萝卜转换会丢掉高毛利销售 |
| Wheat dumped early / reserve 20 | −$38 ~ −$10.7k | 动核心饲料储备会破坏畜群生产 |

### §8 四条评测教训

1. **Kaggle 跑"最后一个可调用对象"，不是 `agent`** —— 定义在 `agent` 之后的辅助函数会静默改变执行入口。
2. **回放面板会过时**：meta 从磁带队转向自适应队后，旧面板失去预测力，必须持续重采样。
3. **必须过滤"对手不完整"的局**：对手采购失败或偏差 >5% 的对局，"胜利"是假象。
4. **对决要用共同随机数**：对称座位、相同的商店开锁序列，才能消掉方差。

## 我们做了什么

- 把 payload 抽出、与 `opponents/guru` 核对 sha256（一致），并**确认我们打它 38-2**
- §6 的结论写进了 `results/SESSION_STATE.md` §六之五（**A1**）
- §7 的番茄/CARROT2 两条**被我们独立复现**（见 `claims.md` B6/B10/C2）
- §8 的四条与我们的实践一致（D1/D3/D4/E1）
