# Kaggriculture-Man: Reverse-Engineering Top-Agents Meta —— leoprovorov

- **链接**：https://www.kaggle.com/code/leoprovorov/kaggricult-man-reverse-engineering
- **产物**：`MarketShock-M1-WR1K`（= 冻结的 **Seven-Turn Rescue** 底座 + 一个 T4 干预）

## 一、最有价值的一条：**最终评分是 Bradley-Terry 重算，不是天梯分**

> "The competition uses **continued agent matches and a final Bradley-Terry recomputation**.
> The real unknown is **the future opponent population**: which agents remain active,
> how the public meta converges, and which matchups dominate the post-deadline evidence."

**这条直接影响我们的收尾策略。** 我们的 E2/E4（分数 ≈ 对手平均分 + 300、Elo 非对称）解释的是
*过程中的天梯分*；而**最终名次是按对局集合做 BT 重算**的。含义：

- 中途的高分不等于最终名次——它取决于**截止后哪些 agent 还在跑、以及我们和谁配对**。
- 所以"保持一个高分锚"有用，但**不能替代"对强的对手也能赢"**。单靠抽签抽到高分配对，最终重算时不成立。
- 这一条把"我们该把资源投在**真实胜率**上"从直觉变成了赛制依据。

## 二、他的 T4 干预 = **我们已经否证过的那个家族**（而他只有 6 局证据）

> "**T4** … In likely mirror games it can sell selected parent-planned inventory
> **one turn earlier**. If a real probe shows that the opponent also preempts sales,
> the lead can become **two turns**. Every moved unit becomes a **credit** against the
> original sale, so the overlay cannot liquidate the same stock twice."

```python
if mirror_gate_is_open and 336 <= step < 647:
    lead = 2 if counter_preemption_was_observed else 1
    for item, qty in parent_sales(step + lead):
        qty = min(qty, projected_shed[item])
        if 4 <= qty < 100 and market_order_slot_exists:
            sell_now(item, qty)
        credit_original_sale(item, qty)
```

| 他的主张 | 我们的对应证据 |
|---|---|
| **mirror gate**（只在"像镜像"的局里开） | 我们的 B3：`_clone_distance` 对全部 8 个对手**恒为 0**（包括 v55/guru）→ 这类门控很可能**根本不会开**，T4 实际是 no-op |
| **提前 1–2 回合卖 + 记账抵扣（"补还"）** | 我们的 B2：v30/v31/v32 三次失败；消融显示 **"补还"贡献为零**，伤害随**前视长度**缩放（3–4 回合 −24/320 → 1 回合 −7/320） |
| 证据：**"three fixed worlds … all six seat-swapped games"** = **6 局** | 我们的是 **320 局**。他的声称 gate 是 336–647 步，与我们的 `_PREEMPT_START=120 / STOP=680` 同一区间 |

⇒ **我们对同一机制有强得多的否定证据**。他自评也很克制（"the crop-value guard added +196 in one
world and exactly 0 in two, so I treat it as weak and world-specific"）。

## 三、他的"agent map"（`Field Skeleton`）—— 与我们结构一致

> "The shared opener runs until **day 6, step 144**. The agent then reads the **first two
> unlocked shops as an ordered pair**. **Fourteen named pairs select ten distinct
> continuations**; every unlisted pair falls back to plan 0. At **day 27, step 648**,
> every route enters plan 2 for final liquidation."

| 他的结构 | 我们的 |
|---|---|
| 共用开局到 step 144 | ✅ 相同（我们的 `_router` 在 step 144 / day 6 选路） |
| 读**前两家已解锁商店**作为有序对 | ✅ 相同（`tuple(unlocked_shops[:2])`） |
| 14 个具名对 → 10 条续带 | 我们的是 64 对 → 41 条磁带（`_R108_SHOP_ROUTES`），加 `_V92_TABLE` 覆盖 15 个 |
| **step 648 全部进入"清算计划"** | 我们也有（`state['route']=2` 在 step ≥ 648 触发）——**同一条链** |
| "**The useful unit of analysis is therefore a route inside a world, not one global win rate**" | 🔶 **这条我们没做** |

### 他这条方法学主张值得单独拿出来

> "The useful unit of analysis is therefore **a route inside a world**, not one global win rate.
> The map exposes missing worlds, low-sample branches, route-specific economics, and the
> exact matches behind each plan."

他的 `Field Worlds` 面板自述是"**all 64 possible shop worlds measured across 2,835 public episodes**"。

**对我们的意义**：我们的 L4 说"本地测试台有结构性空洞：真正伤我们的 40.6% 档本地复现不出来"。
他的框架给出**怎么找那个洞**：把评测按 **(route, shop-world) 单元格**切开，而不是只报全局胜率。
我们本地有 1800 局回放 parquet，**可以直接跑这个切分**——这会告诉我们**我们在哪 64 个世界里输**。
⇒ 列为高优先待办。

## 四、他的可视化面板（用户点名想要的那个）

`Field Ledger` —— **一个对局一张页**，他说是"every economic layer"，面板清单：

1. projected score（预测落点）
2. trend
3. market execution
4. revenue（收入）
5. spending（支出）
6. free cash
7. **idle hands**（闲置劳动力）
8. planted value
9. final harvest book（最终账本）

`Field Skeleton`（agent map）：day-6 分叉、**观察到的路线频率与结果**、路线经济学、每条计划下的对局。
`Field Worlds`：64 个商店世界 × 2,835 局。

> ⚠️ **这些不是 notebook 里的代码，是他研究服务器上的整页截图**（"exact full-page captures from the
> live research server … not recreated charts"）。所以拿不到他的实现，只能照着面板清单自己造。

### 我们做了什么：`scripts/field_ledger.py`

自包含 HTML（这个 venv 里**没有 numpy/matplotlib/pandas**，所以用**手写内联 SVG**），
输入一局（种子 + 两个 agent），输出一页：

| 面板 | 内容 |
|---|---|
| KPI 行 | 双方终局资金、**闲置单位·回合数**、解锁商店数 |
| Cash (every turn) | 双方现金逐回合，并**标注 step 144 分叉点与每家商店的解锁步** |
| Idle units | 双方每回合 PASS 的农民+雇工数 |
| Tile ledger | 双方**每日平均地块构成**堆叠柱（作物/牧场/杂草/空/锁） |
| Daily cash flow | 日内银行余额变化 |
| Market orders per day | 按类型（SELL/BUY_PRODUCT/BUY_SEED/BUY_ANIMAL/BUY_LAND/HIRE）堆叠 |
| Closing book | 终局地块表 + 棚内库存（峰值 vs 终值） |

**做的时候撞出的一个真结论**：一个对局里双方 idle 曲线**逐日完全相同**（30/40/27/19/23/19/14/12）。
不是 bug——两个 agent 回放**同一条磁带**，而这套架构里**所有反射层只改 `market` 列表，
从不碰 `farmer`/`hands`**。所以：

> **劳动力闲置是磁带决定的，不是市场策略决定的。** idle 曲线的差异只意味着**路线或布局不同**，
> 不意味着市场政策不同。这一点必须标在图上，否则会读错。

（面板清单里 **projected score / trend / revenue / spending / planted value** 我们还没做——
收入与支出的逐笔分解需要把已执行的成交与未执行的重建出来，留作下一步。）
