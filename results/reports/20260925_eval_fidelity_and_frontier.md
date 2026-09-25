# 评测保真事故 & 公开前线 —— 2026-09-25

> 起因：用户给了三篇 notebook（nathanjacob `beyond-v43`、leoprovorov `god's-mode-hacked-stores`、
> tetsutani `demand-preserving-turn-sale-timing`）。读的过程中发现**我们自己的测试台在测错的东西**。

---

## 〇、一句话结论

**我们的对手面板一直跑错入口点，而这个错误恰好把"层堆叠复合体"这一整类对手变成了"我们能 40-0"的假象。
修正后，公开前线里已经有一份同源复合体稳定压制我们（100 局我们 22 胜 78 负）。**

---

## 一、事故：`tournament.py` 测的不是 Kaggle 会跑的东西

### 事实

Kaggle 的入口规则（`kaggle_environments.agent.get_last_callable` 的源码）：

```python
exec(compile(raw, path_str, "exec"), env)
return [v for v in env.values() if callable(v)][-1]   # 命名空间里最后一个可调用对象
```

`scripts/tournament.py` 的 `load_agent` **注释写着** "mirror that rule"，
**代码却是** `if callable(getattr(mod, "agent", None)): return mod.agent`。

用官方函数逐文件核对：

| 文件 | Kaggle 实际入口 | 我们此前测的 |
|---|---|---|
| **`main.py`（我们自己的提交）** | `agent` ✅ | `agent` ✅ |
| `opponents/v53` | `_e363_agent` | `agent` ❌ |
| `opponents/v55` | `final_price_guard` | `agent` ❌ |
| `opponents/prvsiyan` | `final_price_guard` | `agent` ❌ |
| `opponents/kaito_v27` | `_kaggle_submission_entrypoint` | `agent` ❌ |
| `opponents/beatv48` | `_cxd_agent` | `agent` ❌ |
| `opponents/v50 / v51 / v52` | `_e343_agent` / `_e350_agent` / `_E352_INNER` | `agent` ❌ |
| **`opponents/tetsutani_cha22`** | **`ig_agent`** | `agent` ❌ |
| `opponents/pipe4 / pipe16 / pipe18 / reyhan / guru` | `agent` ✅ | `agent` ✅ |

**这不是意外，是作者的意图**：v55/prvsiyan 结尾写着 `kaggle_submission_agent = final_price_guard`，
tetsutani 的 notebook 里自己断言 `get_last_callable(...).__name__ == "ig_agent"`。

### 修复

`--loader {kaggle,agent}`，默认 `kaggle`。

⚠️ **第一版修复是错的**：用模块级全局 `LOADER`，被 Windows `multiprocessing` 的 **spawn**
重置 → 两次 A/B 结果**逐字相同**（假阴性）。必须用**环境变量**传递到子进程。

### 实测影响：**选择性的**

同一种子集，两种口径：

| 对手 | `--loader agent`（旧） | `--loader kaggle`（真） |
|---|---|---|
| v53 | 52W-8L（86.7%） | 52W-8L（86.7%）→ **无差别** |
| v55 | 56W-4L（93.3%） | 56W-4L（93.3%）→ **无差别** |
| **tetsutani_cha22** | **60W-0L（100%）** | **12W-48L（20%）** ← **天壤之别** |

⇒ 对这些公开 agent 的实验层，**多数是实际 no-op**；但对**真正叠了很多层的复合体**，
错口径会把一个压制我们的对手说成被我们碾压。

---

## 二、公开前线实测（主表，`tools: scripts/tournament.py --loader kaggle`）

### block A：种子 1000-1049（50 种子 × 双座位 = 100 局/对手）

| 对手 | 战果 | 我们胜率 | 均差 | 最差 |
|---|---|---|---|---|
| **tetsutani_cha22** | **22W-78L** | **22%** | **−$578** | **−$3,222** |
| pipe18（"六层"，23 票） | 93W-7L | 93% | +$1,033 | −$1,152 |
| pipe16（"闲置工人"，56 票） | 93W-7L | 93% | +$1,282 | −$1,001 |
| pipe7（"小麦微观结构"，63 票） | 100W-0L | 100% | +$4,448 | +$810 |
| tetsu_market（`market-smart-farming`，105 票） | 100W-0L | 100% | +$4,293 | +$315 |
| v53 | 86W-14L | 86% | +$916 | −$1,558 |
| v55 | 93W-7L | 93% | +$1,206 | −$971 |
| **合计** | **587/700** | **83.9%** | +$1,800 | −$3,222 |

### 关键读法

**不是"层堆叠复合体"这一类压我们，是 tetsutani 那一个栈压我们。**

它借了 F5/F6 的 **pipe18**，我们反而 **93-7 赢**；pipe16 也一样 93-7；pipe7 / tetsu_market 我们 100-0。
所以差距**不在** IG 队列闭合、也不在 EXP402/EXP410（那些我们的 `main.py` 里本来就有）。

⇒ 这把消融范围从"十几个层"缩到 **cha20 链 + F4**。

---

## 三、层消融：设计

tetsutani 的栈是逐层包裹的，每层都把父函数存下来（`_FX_PARENT`、`_DP_ENTRY`…），
所以每个中间态都以模块级名字**存活**。Kaggle 取命名空间里最后一个可调用对象 ⇒
在源码副本末尾追加 `_ABLATION_ENTRY = <stage>` 就能把入口**冻在任意一层**，不动一行原代码。

`scripts/build_ladder.py` 生成 12 级阶梯（全部通过身份校验，不是名字校验）：

| 级 | 入口 | 含义 |
|---|---|---|
| 00 | `_FX_PARENT` | 底座（无 cha20 层） |
| 01 | `_FX_ENTRY` | + FX (FLOWPX 跟随对手流量抢先卖) |
| 02 | `_DP_ENTRY` | + DP (DAWNPX 黎明窗口分块抢先卖) |
| 03 | `_MP_ENTRY` | + MP (hours 10-13 抢先卖) |
| 04 | `_BD_ENTRY` | + BD (BUYDIP 大额小麦买跌) |
| 05 | `_MPX_ENTRY` | + MPX (MODELPX 对 MILK/STRAWBERRY/WOOL 的模型化抢先卖) |
| 06 | `_SM_ENTRY` | + **SM (SHIELD-MILK 现金偿付护栏)** |
| 07 | `_E410_PARENT` | + F4 (`_CXD` 精确最优响应排序) |
| 08 | `_E402_PARENT` | + F5 (EXP410 施肥护栏) |
| 09 | `_MG_PARENT` | + F6 (EXP402 晚季种子帽) |
| 10 | `_IG_PARENT` | + MERGE (同项 SELL 压缩) |
| 11 | `ig_agent` | + IG (队列空洞闭合) = 完整栈 |

### 代码阅读给出的先验

cha20 六层里有**四层是我们已经否证过的"抢先卖"家族**（B2：RACE 抢跑，三次失败）：

```python
# FLOWPX —— 触发阈值 999 单位/8 回合窗口 ⇒ 实际上永远不会触发
_FX_FLOW_MIN = 999        # units sold by the rival in the window to trigger a lead
```

**`_FX` 实际上是关掉的。** 而 **`_SM` (SHIELD-MILK) 是唯一机制上不同的一个**：

> 仅在**有奶店**（PIZZA_SHOP / ICE_CREAM_SHOP / SMOOTHIE_SHOP）的世界里激活。
> 把本回合计划的 `SELL` 收入与 `BUY_ANIMAL` / `BUY_SEED` / `BUY_PRODUCT` / `BUY_LAND`
> 支出逐笔投影，**若现金会转负**，就按价格从高到低**插入额外 SELL**，
> 插在**第一个 BUY 之前**，把买不起的那笔买成。

**这正是我们 M1 早死 bug 的失败类别**（step-24 现金 $1 → 3 个雇工付不起 → d1 的 FEED 被截断
→ 牛饿两天逃逸 → 8.1% 的局、且正是最大的 5 场败局）。我们 v37 的修法是**改开局常量**（20/15→10/5），
他的修法是**条件触发的偿付护栏**——后者更通用。

⇒ **可检验的预测：阶梯的跳变应落在 05→06（`_SM`）这一级。**

---

## 四、附带关闭的线索

| 线索 | 结论 | 证据 |
|---|---|---|
| nathanjacob "C9 开局少一回合节奏" | ❌ **否证** | 逐回合核对：我们 / reyhan / pipe-4 / tetsutani **四方都在同一回合雇工**；往返净花费 $22（不是 $900）；整项改动值 +$26 现金 |
| 引擎"原子播种"陷阱（同作物 PLANT 数 > 种子数 ⇒ 全部变 PASS） | ✅ **规则存在，但不是杠杆** | 直接读引擎源码确认。实测我方 **0/28,760 回合**；v53/reyhan/tetsutani 也是 0；只有 pipe4 触发 2/14,380（WHEAT） |
| leoprovorov "单格 DIG 改变下一家商店 76.6%" | 🔶 **待复核** | 机制与我们 E1 兼容；但**作者本人未测分数影响**，覆盖仅 10–18%。价值在**诊断**（量化我们 A/B 面板里有多少方差来自商店重抽），不在策略 |
| pipe18 自述 650 局 88.9% Elo、与 ahmed v56 接近打平 | 🔶 待确认 | 他自报。**但注意：我们 93-7 赢 pipe18**，所以他那 88.9% 的对手集合与我们的不同 |
| "ahmed v56 是最强公开 agent" | 🔶 待确认 | **我们本地没有 v56**，只有 v55（对其 93%） |

---

## 五、受影响的旧结论（诚实清单）

| 旧结论 | 是否受影响 |
|---|---|
| "公开 agent 我们动辄 40-0"（README / 多份 sources） | ❌ **已推翻** —— 那是入口点 bug 造成的抽样偏差 |
| v34/v35/v36/v37 相互比较 | ✅ 不受影响（候选侧一直是 `agent`，且我们自己的入口就是 `agent`） |
| v30/v31/v32 的 RACE 消融（B2） | ✅ 不受影响（那是我们自己的层） |
| `boatlee` 的 `_clone_distance` no-op（B3） | ✅ 不受影响（测的是我们自己的内部量） |
| 对 `prvsiyan` / `kaito_v27` / `beatv48` / `v50-52` 的战绩 | ⚠️ **未核** —— 这些的入口也错了，但按 v53/v55 的 A/B，实际影响可能为零。**要复核** |
| `guru` / `pipe4` / `pipe16` / `pipe18` / `reyhan` / `salem` 的战绩 | ✅ 不受影响（入口就是 `agent`） |

---

## 六、待办

1. ✅ **层阶梯**（进行中）：定位 05→06 是否跳变，验证 `_SM` 假说。
2. **若 `_SM` 成立**：把 SHIELD-MILK 作为**独立层**移植到我们的 v37 上，用两块种子 × ≥500 局验收
   （遵守 L3 纪律）。这是我们目前唯一有机制支撑、且指向涨分的动作。
3. **拿 ahmed v56** 与 **dmitriigluzdov 的四篇新 notebook**（`more-wheat-smarter-sales` 35 票、
   `7-turn-rescue` 67 票、`one-more-wheat` 59 票、`a-smaller-market-shock` 69 票）——他的内嵌格式
   与 base85/base64 都不同，`scripts/extract_embedded.py` 还抽不出来，需要单独看。
   他正是 **CL（Crop Longevity）** 层的作者。
4. **复核入口点 bug 对 `prvsiyan` / `kaito_v27` / `beatv48` / `v50-52` 战绩的实际影响**（低优先）。
5. **重跑巡检 cron**（session-only，会话一断就消失）。
