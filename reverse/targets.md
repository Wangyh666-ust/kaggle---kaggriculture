# 目标队伍清单（2026-09-23 快照）

榜单来源：`tmp_extract/lb/kaggriculture-publicleaderboard-2026-09-23T01_04_40.csv`（9875 队）。

| # | 队伍 | teamId | 分数 | 已知血统线索 |
|---|---|---|---|---|
| 1 | **DSM** | 16732748 | **3155.1** | **未知**——本次逆向的首要目标 |
| 2 | Unknown Mother-Goose | 16730612 | 3052.1 | 家族 2 成员（开局 `COW 1 + WHEAT 5` / `SELL WHEAT 1, HIRE×4, COW 1, SHEEP 3`） |
| 3 | Majkel1337 | 16718819 | 3049.8 | 开局与家族 2 不同（`COW 2 + SHEEP 2 + WHEAT 6`） |
| 4 | DECEM | 16623559 | 3047.8 | 家族 2 成员 |
| 5 | mtmr_s1 | 16758882 | 3044.3 | 家族 2 成员 |
| 6 | Vadim Vasilenko | 16770421 | 3022.3 | 家族 2 成员（曾长期 #1） |
| 7 | THIRD FARM CLUB | 16730524 | 3018.1 | 独立开局（`WHEAT 3 + HIRE×5 + SHEEP 2 + COW 3 + MELON 7 + WHEAT 13`） |
| 8 | Kaggledew Valley 🏆 | 16633132 | 3012.1 | 独立开局 |
| 12 | ymg_aq | 16732403 | 2959.6 | 第 2 步与家族 2 相同，第 1 步多了一串小麦往返 |
| 14 | SpaTaro | 16640510 | 2947.4 | 独立开局；第 2 步买 `CARROT/EGG/STRAWBERRY/TOMATO` |
| 15 | KawattaTaido | 16654697 | 2940.8 | 独立开局 |

## 已知"家族 2"

前 10 里有 **6 支**队伍共享同一条第 2 步签名（含 #6 Vadim、#4 DECEM、#5 mtmr_s1、#2 Unknown Mother-Goose 等）。
这条签名是本赛道目前最强的共享 agent，但**它的源码不在任何一份我们已下载的公开 notebook 里**
（公开链 V49–V57 的开局都不同）。所以它是**独立于公开血统的**，这正是需要逆向的对象。

## 抓取命令

```bash
.venv/Scripts/python scripts/fetch_ladder_replays.py \
    --teams 16732748,16730612,16770421,16718819,16623559,16758882,16730524,16633132 \
    --episodes 8 --out reverse/replays
```

> 抓取按 429 退避、断点续跑（只下缺失文件）。每个回放约 30MB。
