# Herd-Safe Sale Window | LB 2700 — Dmitrii Gluzdov

- **链接**：https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-herd-safe-sale-window-lb-2700
- **票数**：73（重跑 2026-09-22）
- **产物**：`main.py` 7046 行（tar 内），**与我们的 v34/v35/v36/v37 同底盘**
  （其 notebook 的 `EVALUATION_MANIFEST` 里对手入口写的就是 `e410_agent`）
- 它比我们多：`opening_liquidity_agent`、`_CXTB`（番茄收益门控）
- **同链还有一份 `statma/kaggriculture-herd-safe-sale-window-race-ca25`**（8 票），只改常量

## 关键原文

> "## Kaggriculture: Herd-Safe Sale Window
> The farm must keep enough cash and inputs to complete its productive routes, then sell stock
> that actually reaches the shed. This version … **reduces the opening wheat round trip** while
> retaining five wheat and the planting seed, limits …"

> Credits: builds on **shiiin9's Order Book**, Ahmed Berat Özer's **V55 and V56 input rules**,
> Thomas Tschinkel's **Metav4** …

### 文件内那条自述调参（最有价值的一条）

```python
# ==== round 2: _V92_P_EVERY=2, _CA_MARGIN=-15.0, V9_RACE_DEFAULT=44, _OR2_SLOT_MARGIN=8.0 ====
```

### `_CXTB`（counter T-B，shiiin9 2026-09-20）的原话

> "counter T-B: gate the tomato investment on the price it will actually get
> … Only the pizza shop and the farmers market buy tomatoes, one per instance every four turns —
> six a day each — and the town centre takes one a day. The investment produces ten tiles over
> days 26..29, twenty units a day. So three such shops drain 19 a day against our 20: the author's
> threshold is the point where the town absorbs exactly what we grow.
> **That is the right quantity to care about, but a count is a coarse way to measure it, because
> what sets the price is the market inventory, not the shops:**
>
> ```
> inventory  9,600 -> 1st unit 300, 80 units fetch 18,355
> inventory 10,000 -> 1st unit  60, 80 units fetch  3,599
> inventory 10,200 -> 1st unit  24, 80 units fetch  1,653
> inventory 10,600 -> every unit 1
> ```
>
> TOMATO has T=200, the narrowest anchor of any crop, so six hundred units decide everything."

它的两个常量是**实测**出来的：

```python
_CXTB_THEIR_UNITS = 0.75    # units a day per rival tomato tile (measured)
_CXTB_DRAIN_SLACK = 2.4     # units a day the town does not take after all (measured)
```

## 我们做了什么

| 主张 | 状态 | 我们的证据 |
|---|---|---|
| 常量组 `_V92_P_EVERY=2 / _CA_MARGIN=-15 / _OR2_SLOT_MARGIN=8` | ✅ **已采纳（v35）** | 对手群 480 局：v34 的 435 → v35 同数 435，但**镜像头对头 69.3%**（n=500 中 285胜/126负/89平） |
| `V9_RACE_DEFAULT=44` | ✅ **已采纳（v36）** | 对 herdsafe 320 局 **87.8% → 94.7%**（CI 不重叠）；镜像 70.9% |
| "降低开盘小麦往返、保住 5 麦 + 1 种" | ✅ **与我们独立得出的 v37 一致** | 见 [shepherds_ledger](shepherds_ledger.md) |
| `_CA_MARGIN=-25`（statma 版本） | ❌ **已否证** | 镜像两块**方向矛盾**：58.7%（种子 3000-3399）vs **39.8%**（种子 4000-4399） |
| `_CXTB` 收益门控取代店数门控 | ❌ **已否证（无效）** | telemetry：3 局调用 3 次、**全部被基础门控先拒**（`base: False`）→ 实际是 no-op；实测中性 |
| 我们整个 agent 对它的战绩 | —— | 我们 **32胜8负**（v37 对 herdsafe），均值 +$876 |

**注**：这份 notebook 是**我们目前唯一找到"同底盘 + 更靠后"的公开版本**，
它对我们的价值远高于其它公开 agent（那些我们动辄 40-0）。
