# 对局复盘页

**只有这一个入口：`ladder_review.html`**（双击打开即可，无依赖、单文件）。

- 顶部两个页签：**总览**（胜率、差距分布、全部对局表）/ **对局**（逐局细看）
- 左侧列表可按 全部 / 只看败局 / 只看胜局 过滤；点一行切换对局
- 我们的座位已归一到 seat 0，**左列永远是我们**

## 重新生成

```bash
# 天梯模式：抓某个提交的最近若干局（回放缓存进 tmp_replays/，重跑不用重下）
.venv/Scripts/python scripts/review_losses.py --ref 56539741 --scan 24 --keep 0 --wins-too \
    --out results/ledger/ladder_review.html

# 本地模式：任选版本与对手，固定种子
.venv/Scripts/python scripts/review_losses.py --a experiments/v44/adv6.py \
    --b opponents/tetsutani_cha22/main.py --seeds 1000-1049 --wins-too \
    --out results/ledger/local_review.html
```

参数：`--keep 0` = 全部败局，`--keep N` = 最惨的 N 局，`--wins-too` = 连败局带胜局一起放进左列表。

实现：`scripts/review_losses.py`（抓取 + 归纳数据）+ `scripts/ledger_app.py`（页面与图表 JS）
+ `scripts/field_ledger.py`（数据提取与指标口径）。改完 JS 一定要跑一次 `node --check`——
今晚就有一个未转义的中文引号把整个页面变成白屏。
