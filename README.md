# Kaggriculture Agent

[Kaggle Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) 比赛的双人农业经营 agent。
每局 720 回合（30 天 × 24 回合），各自经营 10×10 农场，通过种植/养殖/雇工/买卖，在季末资金最多者获胜。
排行榜是 Elo（只计胜负平，资金差距不影响评分）。

## 分支说明

- **`main` 分支**：已收敛的稳定提交 —— `main.py` = v21 磁带底盘（线上 Elo **2162.2**，97 局）
- **`exp/v23-c7` 分支（当前）**：实验分支 —— `main.py` = v23_c7，线上分数尚未收敛，**效果好再合并回 `main`**

## 当前提交（本分支：v23_c7）

`main.py` = 磁带底盘（720 步动作序列 + 反射修补层）+ 后续层与调参。
已提交 Kaggle（ref `56428515`），线上前 3 局 3 胜 0 负（$88k–112k，无报错），分数待收敛。

本地面板证据（6 个公开头部 agent，双座位，种子 2000-2009，每对手 20 局）：

| 对手 | v21 基线 | **v23_c7** |
|---|---|---|
| guru | 0胜20负（-$1,208） | **16胜4负（+$119）** |
| prvsiyan | 0胜20负（-$1,345） | **8胜10负2平（+$41）** |
| pilkwang / reyhan / salem / tetsutani | 各 20胜0负 | 各 20胜0负（无退化） |
| **合计** | 80/120（66.7%） | **104/120（86.7%）** |
| **最差边际** | -$3,011 | **-$214** |

### 血统（逐行 diff 得出）

我们的文件与这两个打不过的对手是**同一条迭代链上的三个快照**：

```
我们 (5760 行)  ──5 处常量/数据差异──►  guru (6467 行)  ──追加 186 行──►  prvsiyan (6655 行)
                                          + 末尾 707 行                    + 1 处改动
```

v23_c7 = **我们的文件 + prvsiyan 的 186 行尾部 + guru/prvsiyan 的 4 个参数**：

| 参数 | 取值 | 依据 |
|---|---|---|
| `_V92_P_BLOB` / `_V92_P_INDEX` | 换成他们的店铺需求预测库 | **决定性**：单独带来对 guru +6 胜、均值 +$811 |
| `_CA_FEED_DAYS` | 2 → 1 | 单独即轻微正收益 |
| `V9_FERT_FIRST_DAY` | 16 → 14 | 单独无效，与上面两项**联合有效**（A/B 14-2-4） |
| `_OR2_SLOT_MARGIN` | 50.0 → 20.0 | 同上 |
| `_SR_MARGIN` / `_SR_HOURS` | ~~保持我们的 4 / (22,23)~~ → **已于 v26 改为 8 / (21,22,23)** | ⚠️ 旧结论"抄这两个会退 4 胜"是 **20 局/对手低检验力下的假阴性**；680 局实测为 **+32 胜**，见 `results/reports/v26_v55_parity.md` |

把 5 个参数全抄（= 完全变成 prvsiyan 行为）对 prvsiyan 是 20 局精确 $0 平局，
即永远赢不了它；所以保留 `_SR_*` 是有意为之。

## 版本与线上分数

| 版本 | 架构 | 线上 Elo | 说明 |
|---|---|---|---|
| v23_c7 | 磁带 + 后续层/调参 | 待收敛（前 3 局 3 胜） | 本分支当前提交 |
| v21 | 磁带底盘 | **2162.2**（97 局） | `main` 分支的稳定版（Apache-2.0，文件内保留归属声明） |
| v15 | 规则引擎 | **565.8** | 规则路线终点：商店响应式畜群、草莓施肥、自适应甜瓜规模、对手销量还原 |
| v11 | 规则引擎 | 540.0 | 羊群优先、响应式草莓规模、雇工预算优先 |
| v9 | 规则引擎 | 503.5 | 按头部模板重构（全押牛羊 + 甜瓜过桥 + 草莓主力 + 延迟买地） |
| v7.1 | 规则引擎 | 508.6 | 畜生引擎 + 商店响应调群 |
| v6 | 规则引擎 | 397.7 | 首版：鹅群肥料引擎 + 甜瓜一波 |

## 仓库结构

```
main.py                 当前提交文件（本分支 = v23_c7；tar 打包后直接提交）
legacy/main_rule_v15.py 规则引擎路线终点（v15）
versions/               规则路线开发快照（v2 … v20）
scripts/                评测与研究工具
  evaluate.py             多种子/双座位/多对手评测，结果追加到 results/eval_log.json
  smoke.py                冒烟测试：9 种子 × 双座位对真人对手，断言 DONE 且资金 > $10k
  tournament.py           多进程配对巡回赛（对手面板 × 种子 × 双座位，报 W-L-T/平均/最差边际）
  extract_opponents.py    从公开 notebook 解出可对战的对手 agent（本地测试用）
  submit.py               构建 + 入口点校验 + sha256 记录 → results/submissions.md（默认 dry-run）
  diagnose.py             单局每日经济快照
  trace.py                单局现金流与单位动作分布
  compare_farms.py        逐日并排对比我方与对手的畜群/作物/空地/雇工
  analyze_all.py          批量回放分析（胜率、对手分层、败因相关性）
  analyze_losses.py       败局对手画像
  replay_deepdive.py      单局深挖（对手逐日资金曲线、棚内库存、买卖构成）
  fetch_ladder_replays.py 抓头部队伍公开回放到 replays_ladder/（CLI + 429 退避 + 断点续跑）
  ladder_meta_report.py   语料 → results/ladder_top_meta_data.md（开局签名聚类/农场画像/价格）
  price_trace.py          逐日价格轨迹 + early(20-23)/late(26-29) 对比
  waste_audit.py          空转人工 / 棚满 / 收成变草 / 终局存货
  seed_probe.py           给定 seed 跑一局并打印商店解锁序列
  panel_shop_keys.py      面板 seed 实际走到的 route key 分布（评估 route 替换的检验力）
  harvest_routes.py       回放 → 720 步磁带 → 按 (前两家店) 建候选 route 表
results/                分析结论与决策文档
  PLAN_tape_route.md      改用磁带路线的决策依据
  top_notebooks_findings.md  头部实现解剖 + 全部实验（含负面结果）
  ladder_top_meta.md      **天梯头部 meta 分析**（克隆天花板、头部家族、三项负面结果、方法论）
  ladder_top_meta_data.md 上文的自动生成数据附录
  reports/TEMPLATE.md     版本报告模板（每个版本一份报告）
  submissions.md          提交记录（scripts/submit.py 自动追加，含 sha256）
  SESSION_STATE.md        会话交接文档
  loss_analysis_20260920.md  77 局败局集中分析
  notes_pending_issues.md    待修问题清单
  score_history.md        线上分数快照
env/                    官方环境源码与文档（kaggle-environments 1.32.7）
```

**仅在本地保留、不入库**（`.gitignore` 已排除）：`opponents/`（6 个公开头部模型，
由 `extract_opponents.py` 解出）、`experiments/`（实验变体）、`tournament_results/`（对局记录）、
以及体积较大的回放目录。这些是本地验证材料，不是交付物。

## 本地对战面板（v23_c7 的验收依据）

从公开 notebook 解出 6 个头部 agent 组成面板，用 `scripts/tournament.py` 做配对巡回：

```bash
.venv/Scripts/python scripts/extract_opponents.py          # 解出 opponents/（本地）
.venv/Scripts/python scripts/tournament.py --candidate main.py --seeds 2000-2009
```

- 每对手固定种子块 × 双座位（环境座位对称，实测镜像对局恒为 $0 平局，所以结果无噪声）
- 报 **平均边际 + 最差边际**：只看胜率会被运气骗，最差边际能识别"靠运气赢的改动"
- 实测并行效率：模拟器是纯 Python 串行逻辑（单局 7-8 秒 CPU），**GPU 无用**；
  20 进程并行后 120 局约 113 秒

## 关键结论（详见 `results/top_notebooks_findings.md`）

**1. 头部实现 100% 是"磁带"。** 解码核实了 10 个公开高分 agent：全部是 720 步动作
回放表 + 反射修补层，没有一个是规则引擎；且只有两个半磁带族（thomastschinkel 的
`Chassis` + shop-router，boatlee/salem 的单表，tetsutani 的自建变体）。它们之间的差距
不在策略搜索，而在三件事：**选哪条磁带**（按对手揭示的店铺组合/首日开局签名）、
**卖单时机微调**（sell_lead / RACE / ORDERPRI）、**执行修补**（杂草/仓库/手数）。

**2. 价格由市场库存决定，不由卖出时机决定。** 因此渠道分三类：
小镇消耗 > 产量（小麦/胡萝卜/草莓/蛋）→ 价格整季上涨，**捂仓是真钱**（我们实测小麦
1.61×、草莓 1.79× 基准价）；无消耗（肥料/甜瓜）→ 价格随累计销量单调下跌，择时无意义
（肥料 0.55× 基准价是产量问题）；双方共抛（奶/毛）→ 贴基准震荡，**卖单槽位优先级**
比择时重要得多。

**3. 规则引擎的瓶颈是执行效率，不是参数。** 规则版迭代到 v15 后，v16-v20 六个变体
（番茄线、按计划雇工、畜群人力上限、解除 NE 预留、限制小麦、分块种植、单纯加人）
**全部未能超越 v15**。诊断：对手 1 个工人管 ~8 棵作物，我们只有 4-5 棵；手工优化的
磁带每个动作都是"站定即做"，规则式打不过。

**4. 过程中的负面结果同样记录在案**（避免重复踩坑）：第 0 天买饲料"保险"反而害了自己
（现金在第 0 天会连锁复利）、羊优先开局更差、草莓缩到 5-7 棵更差、解除 NE 预留会丢掉
甜瓜第二波。

## 复现

```bash
# 环境
python -m venv .venv && .venv/Scripts/pip install -U kaggle-environments==1.32.7 kaggle

# 冒烟测试（改任何东西之前先跑这个：9 种子 × 双座位对真人对手）
.venv/Scripts/python scripts/smoke.py main.py legacy/main_rule_v15.py

# 对手面板巡回赛（本分支的验收标准；先解出对手，见上一节）
.venv/Scripts/python scripts/tournament.py --candidate main.py --seeds 2000-2009

# 与规则版头对头；单局经济诊断
.venv/Scripts/python scripts/evaluate.py --opp legacy/main_rule_v15.py --episodes 20 --seed0 8000
.venv/Scripts/python scripts/diagnose.py 1000 pass

# 打包提交（需要 Kaggle API token：~/.kaggle/access_token）
tar -czf submission.tar.gz main.py
kaggle competitions submit kaggriculture -f submission.tar.gz -m "msg"
```

## 参考材料（未随仓库分发）

这些公开 notebook 是本研究的主要参考，均为 Apache-2.0 派生，请从 Kaggle 原文获取：

- [Kaggriculture: Getting Started](https://www.kaggle.com/code/bovard/kaggriculture-getting-started) — 官方 agent 接口
- [The 2945 Farm](https://www.kaggle.com/code/thomastschinkel/the-2945-farm-96-vs-the-top-10-public-bots) — 磁带底盘血统来源（`main.py` 即其 v9/3 血缘）
- [Findings from Zero to Top Meta](https://www.kaggle.com/code/raykkretzschmar/kaggriculture-findings-from-zero-to-top-meta) — 顶级玩家的迭代方法论
- [V16-RC5](https://www.kaggle.com/code/boatlee/v16-rc5-high-score-8c-4s-premium-market-lead) — 单表磁带实现
- [A Smaller Market Shock](https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-a-smaller-market-shock) / [More Wheat, Smarter Sales](https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-more-wheat-smarter-sales) — 开局冲击与售单槽位整理

## 归属与许可

`main.py`（磁带底盘 + 后续层）基于公开工作二次开发，**文件头部完整保留上游归属声明与
Apache-2.0 许可**（thomastschinkel / yhay81 / tetsutani / prvsiyan / Dmitrii Gluzdov /
Ahmed Berat Özer 等）。`legacy/`、`versions/`、`scripts/`、`results/` 为本项目自研内容。
本仓库不含任何 Kaggle 凭证（token 存放于 `~/.kaggle/access_token`，在仓库之外）。
