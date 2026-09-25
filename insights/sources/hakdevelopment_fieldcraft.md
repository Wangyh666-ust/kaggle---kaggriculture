# Fieldcraft（hakdevelopment）—— **自称历史分 2887.4；我们赢它 86.7%**

- **链接**：https://www.kaggle.com/code/hakdevelopment/kaggriculture-2887-score-fieldcraft-agent
- **产物**：两个文件，一起放进 `opponents/fieldcraft/`
  - `main.py` — 41,203 B / 904 行，sha256 **`4aa771451850e688…`**，入口 **`agent`**
  - `mirror_plan.py` — 502,035 B / 61 行，sha256 `65727d56185b2d61…`（**路线/磁带数据模块**，`main.py` 会 `import mirror_plan`）
- **性质**：**新的**（本地此前没有）

## 一、它最诚实的地方（三处，在公开 agent 里罕见）

1. **创下标注 2887.4 的分，但自己说明这不是承诺**：
   > "The **2887.4** figure belongs to original submission **56258004**, submitted 15 September 2026 …
   > It is a **historical rating, not a promised score** for a new submission or a local cash result."
2. **它主动指出了"下单 ≠ 成交"这个测量陷阱**：
   > "Cash curves show the balance, **not profit per crop**. **An emitted `SELL` is a request; its
   > quantity is not proof of a fill.** Action counts therefore describe decisions, not completed transactions."
   ⇒ **这正是我们今晚在自己账本里踩到并修掉的那个陷阱**（`revenue_mix` 把下单当成交、
   棚存快照在收割前导致无法分离）。**两个团队独立撞上同一点，说明它是这个比赛的真实测量难点。**
3. **它承认载荷是混淆不是加密**：
   > "It is **obfuscation, not encryption**: runnable public code is recoverable."

它还自带一套小诊断（现金轨迹 / 动作构成 / **双座位**查座位依赖），思路与我们的账本一致。

## 二、我们实测：**52 胜 8 负 = 86.7%**

| | |
|---|---|
| 战绩（30 种子 × 双座位 = 60 局） | **52-8** |
| 均差 | +$2,059 |
| 最差单局 | −$2,677 |
| 单局对拍（seed 1000 / 1001） | 我们 $78,964 vs $78,803（**只赢 $161**）／ $95,290 vs $90,792 |

**它是我们测过的公开 agent 里第二接近我们的**（仅次于 `tetsutani_cha22` 的 55%）：

| 对手 | 我们胜率 |
|---|---|
| `tetsutani_cha22` | 55% |
| **`fieldcraft`** | **86.7%** |
| `hybrid2965` | 90% |
| `pipe18` / `v55` / `v56` / `v57` | 93–100% |
| 其余 24 个 | 40-0 或 38-2 |

**2887.4 的历史分没有转化成对我们的优势** —— 与我们 R2 的结论一致：**分数衡量的是被扔进哪个档位，
不是打得多好**。

## 三、它顺带暴露了我们测试台的两个缺口（都已修）

| 缺口 | 后果 | 修法 |
|---|---|---|
| **`tournament.py` 不把对手目录加进 `sys.path`** | 任何**带同目录模块**的公开 agent 会 `ModuleNotFoundError` → agent 什么都不做 → **我们读成 40-0 大胜**。这和昨天那个 loader bug **是同一类错误：系统性地把对手看弱** | `load_agent` 现在先 `sys.path.insert(dirname(path))`（Kaggle 官方 loader 也这么做） |
| 抽取器不支持 **`PAYLOADS = {'main.py': …, 'mirror_plan.py': …}` 字典载荷**，且"源码必须含 `def `"的启发式**把 502KB 的纯压缩模块漏掉了** | 只抽出 `main.py`，`import mirror_plan` 失败 | 字典载荷分支 + 判据改为"**可打印字符比例 > 92%**" |

## 四、结论与待办

| # | 结论 |
|---|---|
| 1 | **收进对手池**（已完成）。它是**除 tetsutani 之外第二有用的验收对手**——hybrid2965 均差 +$650、fieldcraft 均差 +$2,059，其余都是 40-0 |
| 2 | 🔶 **值得读它的 `mirror_plan.py`**：502KB 的路线/磁带数据，和我们 `_R108_SHOP_ROUTES`+`_V92_TABLE` 是同一用途。**可以对比"它的磁带表覆盖了哪些商店对、我们有没有漏掉的组合"** |
| 3 | ✅ 它的"下单≠成交"警告与我们的 `revenue_mix` 修正**独立互证**，这条方法学教训应当写进 `local_findings` |
| 4 | ⚠️ **一条对"高历史分"的提醒**：2887.4 的 agent 我们也赢 86.7%。**看到高分不要预设它更强，要测**（与 R2、G9 一致） |
