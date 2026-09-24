# v<NN> — <一句话改动>

- **日期**：YYYY-MM-DD
- **分支 / 提交 ref**：
- **基线**：v<NN-1>（线上 Elo …，本地面板 …/…）
- **产物哈希**：`sha256(main.py)` = …（提交前后各记一次）

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 改动 | ✅ 采纳 / ❌ 否决 / ⚠️ 部分采纳 |
| 本地面板 | A/B：… vs … |
| 线上 | … |
| 未验证风险 | … |

## 1. 动机（为什么改）

**必须给数据，不给直觉。** 至少包含一项：
- 观测数据（本地面板 / 线上回放 / 头部回放语料），注明来源文件与样本量
- 引擎机制（`env/kaggriculture.py` 的行号与语义）
- 已有负面结果中**没有**覆盖它的证据

## 2. 改动内容

改了哪些文件、哪些常量/层，逐条列出。附关键代码片段。

## 3. 实验方法

- 面板与种子（例：`--seeds 2000-2019 --seats 0`，20 局/对手）
- 指标：**胜/负/平 + 平均边际 + 最差边际**（只看胜率会被运气骗）
- 门槛：写清楚什么条件下采纳（例：0 负 且 至少 +3 胜）

## 4. 结果

| 对手 | 基线 W/L/T | 候选 W/L/T | 平均边际 | 最差边际 |
|---|---|---|---|---|
| … | | | | |

**逐对手无退化** 是默认要求；有退化必须单列说明。

## 5. 被否决的变体（负面结果同样记录）

| 变体 | 结果 | 否决理由 |
|---|---|---|

## 6. 决策与后续

## 7. 复现

```bash
# 冒烟（改任何东西之前）
.venv/Scripts/python scripts/smoke.py main.py
# 面板
.venv/Scripts/python scripts/tournament.py --candidate <file> --seeds 2000-2019 --seats 0
# 提交
tar -czf submission.tar.gz main.py && .venv/Scripts/python -m kaggle competitions submit kaggriculture -f submission.tar.gz -m "v<NN>: …"
```
