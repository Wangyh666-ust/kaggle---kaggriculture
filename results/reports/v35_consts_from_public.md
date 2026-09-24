# v35 — 采用公开 LB2700 agent 调好的三个常量

- **日期**：2026-09-24
- **基线**：v34（prvsiyan frontier，线上 **2534.1**）
- **候选**：`experiments/v35/consts.py`（v34 + 三个常量）
- **来源**：`dmitriigluzdov/kaggriculture-herd-safe-sale-window-lb-2700`（73 票，2026-09-22）——
  **与 v34 同底盘（其 manifest 里对手入口写的就是 `e410_agent`）**，多一层 `opening_liquidity_agent`、
  一层 `_CXTB`（读对手番茄供给的门控），以及自己的调参

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 改动 | ✅ 采纳 |
| vs herdsafe（有区分度），两块合计 | v34 **100/120 (83.3%)** → v35 **107/120 (89.2%)** |
| 公共面板 120 局 | v34 114–117/120 → v35 **120/120** |
| 头对头 v35 vs v34 | A **59W-21L-20T**、B **56/100**（两独立块一致） |
| 冒烟 | ✅ |

## 1. 动机

用户判断"扩张/畜群这部分应该已经有开源资源"。搜索证实了：

| notebook | 票 | 内容 |
|---|---|---|
| `boatlee/v16-rc5-high-score-8c-4s-premium-market-lead` | **317** | 公开重建的 **8 COW / 4 SHEEP** 路线（Nikita Lugovoy 的高分回放） |
| `dmitriigluzdov/kaggriculture-herd-safe-sale-window-lb-2700` | 73 | **同 e410 底盘** + 畜群安全卖出窗口 + `_CXTB` 对手供给门控 |
| `ahmedberatozer/...-v35-reactive-sales-sheep-expansion` | 41 | 羊群扩张 |
| `arsgorynich/herd-safe-v3-experimental-risk-aware-feed` | 32 | herd-safe v3 |

**V16-RC5 我们 40-0 碾压它**（老 meta，8 月的路线）。**herdsafe 只输 32-8**，是本地最有区分度的外部对手。

## 2. 改动内容

他们的文件里有一条署名注释直接写着调参：

```
# ==== round 2: _V92_P_EVERY=2, _CA_MARGIN=-15.0, V9_RACE_DEFAULT=44, _OR2_SLOT_MARGIN=8
```

与 v34 对比后，**三个常量不同**（`V9_RACE_DEFAULT` 两边文件内都是 40、都有尾部覆盖，不改）：

| 常量 | v34 | v35 | 含义 |
|---|---|---|---|
| `_CA_MARGIN` | −5.0 | **−15.0** | carrot 替代 wheat 的价格余量 |
| `_OR2_SLOT_MARGIN` | 20.0 | **8.0** | 订单簿槽位重排阈值 |
| `_V92_P_EVERY` | 3 | **2** | 对手卖单库刷新频率 |

## 3. 结果（两独立种子块）

| 测试 | 种子块 | v34 | **v35** |
|---|---|---|---|
| vs herdsafe | A 2000-2019（40 局） | 32W-8L | **34W-6L** |
| vs herdsafe | B 2100-2139（80 局） | 68/80 | **73/80** |
| **合计** | | **100/120 = 83.3%** | **107/120 = 89.2%** |
| 公共面板 | A 2000-2039（120 局） | 114–117/120 | **120/120** |
| 头对头 v35 vs v34 | A 2000-2099 | — | **59W-21L-20T** |
| 头对头 v35 vs v34 | B 2100-2199 | — | **56/100** |

**三组测试方向一致，两个独立种子块复现。** 与本项目此前所有失败的改动（v30/v31/v32：镜像赢、真实对手输）**形态不同**——
这次是面板与镜像**同时**变好。

## 4. 为什么这次形态不同

v30–v32 的机制是"零和抽取"：把对手的钱抢过来，但放大方差、窄胜翻负（天梯只记胜负）。
这三个常量改的是**自己的执行质量**（价格余量、槽位阈值、对手库刷新率），不是从对手身上抽钱——
所以没有那个副作用。

## 5. 还没拿的部分（下一步）

他们文件里还有两层我们没动：

1. **`_CXTB`** —— **读对手番茄供给**的门控，替换 `_V219_qualifies`：
   ```
   _CXTB_THEIR_UNITS = 0.75   # units a day per rival tomato tile (measured)
   _CXTB_DRAIN_SLACK = 2.4    # units a day the town does not take after all (measured)
   _CXTB_MIN_REVENUE = 9000
   ```
   这是**显式的镜像感知决策**，正对我们要解决的问题。
2. **`opening_liquidity_agent`** —— 开盘流动性层。

## 6. 复现

```bash
.venv/Scripts/python scripts/tournament.py --candidate experiments/v35/consts.py \
    --opponents experiments/herdsafe_main.py --seeds 2000-2019 --seats 01
.venv/Scripts/python scripts/tournament.py --candidate experiments/v35/consts.py \
    --opponents experiments/v35/v34_base.py --seeds 2000-2099 --seats 0
```

## 7. 局限

- herdsafe 是**本地代理**，不是天梯；两块的胜率提升（+5.8pp）在天梯上能否复现未经验证。
- 三个常量可能是**对该特定的 herdsafe 版本**调出来的（其注释写 round 2），未必泛化。
- 公共面板已饱和（120/120），对区分度没有贡献，只作护栏。
