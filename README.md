# Kaggriculture Agent — 策略说明与战绩

## 提交文件
- `main.py` — 单文件 agent（纯标准库，定义 `agent(obs)`），可直接提交
- `submission.tar.gz` — 打包版（根级 main.py），与单文件等效

## 策略架构（v9 — 对手模板重构）
头部玩家回放分析（见 `scripts/analyze_losses.py` 对 `loss_replays/` 的画像）后按胜方模板重建：

1. **第 0-1 天全押牛羊**：NW 直接建 8 牧场（无需买地），2 牛 + 2 羊开局，
   现金主动打到接近零。所有存活动物每天白送 1 肥料，构成最早期现金流。
2. **甜瓜过桥**：NW 第一波 10 棵（第 0-3 天种，第 10-13 天收割，~$250/个），
   正好接上扩张资金；NE 第二波 12 棵（第 12-16 天种）。
3. **草莓主力**：20 棵滚动补种（第 2-14 天），四类商店消耗草莓，价格扛得住。
4. **小麦机器**：喂畜自给 + 季末 $45-55 稀缺卖出。
5. **买地推迟**：NE 第 5 天（$1000）、SW 第 8 天（$2000）——先把 NW 榨干。
   （v6 的教训：过早买地是早期资金链断裂的主因。）
6. **商店响应调群**：奶店（披萨/冰淇淋/奶昔）每个 +2 牛（上限 8），毛线店每个
   +2 羊（上限 8）；鸡蛋稀缺（>$75）时 opportunistic 养 4 只鹅。
7. **雇工优先**：hour 0 先预留雇工预算再投资（v8 的教训：买地把雇工钱挤光，
   作物成批枯死）；hour 12 补雇；末日不停雇。
8. **市场纪律**：卖单 premium 单价优先、每回合都出（hour>0）；买单只在 hour 0/12。

## 战绩
本地（座位轮换）：
| 对手 | 胜率 | 我方平均资金 |
|---|---|---|
| pass | 4/4 | $87,520 |
| starter | 4/4 | $84,400 |
| v9（上一线上版） | 14/20 | +$1.5k~3.4k 场均净胜 |

线上 Elo：v6 397.7 → v7 496.6 → v7.1 526.4 → v9 502.2 → v11 提交中。
注意：本地资金高低与线上胜负脱节——真人对手共享市场，甜瓜/肥料/蛋价格
会被双方合谋砸穿；头对头胜率才是有效的本地代理指标。

## 对手模板要点（77 局全量回放分析，results/loss_analysis_20260920.md）
- 所有人第 0-2 天就把 $3000 押光（牛羊+甜瓜种子+雇工），没人养鹅
- 甜瓜 NW 第一波是标准过桥手段；草莓 33-46 棵滚动 + 外购肥料灌草莓
- 雇工第 2 天即 8 个，中期 11-14 个；NE 第 6 天、SW 第 11 天才买
- 小麦后期 25-45 棵囤到 $45-48 集中卖；胡萝卜 d24+ 快周转；末日倾销清仓
- 商店抽取因对局而异（RNG 与杂草共生），必须读 `town.unlocked_shops` 适配
- 已证伪：对手渠道反制（减种对手泛滥的作物）——价格照样崩，白让份额

## 工具链
- `scripts/evaluate.py` — 多 seed/座位/对手评测（结果存 `results/eval_log.json`）
- `scripts/diagnose.py` — 单局每日经济快照
- `scripts/trace.py` — 单局现金流 + 单位动作分布追踪
- `scripts/analyze_losses.py` — 败局回放对手画像
- `env/` — 官方环境源码与文档（kaggle-environments 1.32.7）
- `main_v6_backup.py` / `main_v71.py` / `main_v9.py` — 历史版本留存
- `replays/` `loss_replays/` — 线上对局回放

## 提交方法
网页：比赛页 → Submit → 上传 `main.py` 或 `submission.tar.gz`。
CLI：`kaggle competitions submit kaggriculture -f submission.tar.gz -m "v9"`
查分：`kaggle competitions submissions kaggriculture -v`
