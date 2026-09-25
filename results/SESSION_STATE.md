# 会话交接（新对话从这里开始读）

> 最后更新：2026-09-25 22:45。**这份文档的目的是让一个全新的会话在 5 分钟内接手。**
> 记忆不要依赖聊天记录——聊天会被摘要、细节会丢。仓库里的东西不会。

---

## 一、一句话现状

**v44（`_ADV_LOOK` 4→6）刚提交（ref 56552481），窗口锚是 v41 的 2486.2。v44 早期 5 胜 1 负（n=6，太小）。**
本地面板已饱和（27 个对手里只有 `tetsutani_cha22` 是同级），**而且指纹分析证明那个家族占天梯对局的 71%**。

## 二、天梯状态与提交规则（**最容易搞错的地方**）

```
ref 56552481  v44  PENDING      ← 挑战者（_ADV_LOOK=6）
ref 56539741  v41  2486.2       ← 锚
ref 56537565  v40  2476.2       ← 被挤出
```

- **窗口 = 最近两次提交，取较高分。窗口按「最近」淘汰，不按分数淘汰。**
  ⇒ 提交新的挤掉的是**较旧**那一格。只有当**较新那格 ≥ 较旧那格**时提交才是免费的。
- **新提交从低初始分起步、爬升几小时**（v40：1925 → 2495）。**别用首投分判断版本好坏。**
- 标定：v36 四次抽签 2472/2517/2499/2373；v40 2495；v41 2490；v37 首投 1679.7→重投 2289.2。
- 截止 **2026-09-30**。**最后名次由最后一个窗口格决定**（09-29 起要连投两次）。
- 每日额度约 3–5 次；`kaggle competitions submission-limits kaggriculture` 查。

## 三、正在跑 / 刚跑完的活

- 后台：`review_versions.py --all-versions` 正在为**每个历史版本**抓 24 局天梯对局，
  写 `tmp_replays/ref-<ref>.json`（索引）与 `tmp_replays/ep-<eid>-summary.json`（数据）。
  已有 11 个 ref 索引、291 局摘要。**重跑不会重复下载**（两层缓存）。
- 巡检 cron：`a0535d4b`（durable，每 2 小时 :23）。另一条重复的旧 cron 已删。

## 四、下一步待办（按价值排序）

1. **等 v44 出分**（几小时后）。若 ≥ v41，它就是新锚；若低，按规则替换掉较弱那格。
2. **step-1 挤压**（`goodpjw2008`《The Melon Threshold and the Step-1 Squeeze》，8 票）：
   **目前唯一的新机制**，而且是**零和**的——在 step 1 用 `[BUY WHEAT 90, SELL WHEAT 90, BUY WHEAT 5, …]`
   吃空对手 slot 0 的买单、抬价，再按恢复价买回自己 5 单位饲料；目标是**打对手 d17 的现金**
   （镜像局里对手带 ~$212 想买 2 颗瓜种，被抽 ~$54 后只买 1 颗 ≈ 终局 $1.3k）。
   证据：闭环 336 局 1.000（V45 对照 0.853）。**但守卫写死 V45 的 tape（`market[0]==['SELL','WHEAT',13]`），
   我们的 step-1 tape 是 `[BUY 13, BUY 30, SELL 30]`，必须重写守卫。** 作者自己警告"挤压会互相赛跑"。
   代码已抽出在 `tmp_forum/out_goodpjw2008_.../cell7_writefile_main_1f5c7a18.py` 第 3503–3516 行。
3. **`_ADV_LOOK` 继续定位**：6 是两块同向（+6pp），但 ghazaros 报告 9/10 会 live 反转。可测 5/8 + 留一。
4. **按 64 个商店世界切天梯局**：`zhincez` 发现**只有 `YARN_STORE` 是双倍权重的高价值单店**（~2,400/天 vs
   `PET_CAFE` 的 ~420），羊毛专精只在 yarn 城 137/200 vs 全商店 56/200 ⇒ **是匹配问题不是路线强弱**。
   我们 25–33% 收入来自羊毛，正对口。
5. 攻略：`georgymamarin` 两篇（指南）+ `kaggriculture-episodes` 数据集（25GB，每日更新，
   `episode_features.csv` 含 peak_crew / first_land_day / elbow_day）。

## 五、今天定下的关键结论（细节见 `insights/`）

| # | 结论 | 证据 |
|---|---|---|
| 1 | **我们的 `main.py` 是 ahmed v56 的严格超集**（v56 只多 1 个标识符），且赢它 96% | 标识符 diff + `e410_agent` 逐字节相同 |
| 2 | **天梯占 71% 的对手家族 = `opponents/tetsutani_cha22` 那套代码** | 开局指纹（磁带 step 0–143 固定 ⇒ 开局指令是**代码指纹**） |
| 3 | **本地改进确实迁移到了天梯**：v40/v41 比上一代高 170–200 分 | v41 2490 / v40 2495 vs v36 2321 / v37 2289 |
| 4 | **胜负是被几百块决定的**：v41 的局 \|差距\| 中位 $353，73% < $600，**双方终局资金只差 0.36%** | 56 局样本 |
| 5 | **差的全是成交价，不是数量**（羊毛 +4.08%、草莓 +8.64%） | 挂钩引擎 `_commit_unit` 逐笔对照 |
| 6 | **开局改动是 no-op**：v43 对齐天梯主家族开局，800 局**逐格与 v41 完全相同**，一次 W/L 都没翻 | 两块种子 |
| 7 | **`_ADV_LOOK` 4→6 有效**：对 tetsutani 55%→61%，两块同向（+6pp/+6pp） | 400 局 |
| 8 | **`_BD`（BUYDIP）被否证**：两块种子方向相反 + 最差单局恶化到 −$10.3k | 800 局 |

## 六、陷阱清单（每条都真踩过）

| 陷阱 | 表现 | 处置 |
|---|---|---|
| **Kaggle CLI 上传走 googleapis，本机间歇不通** | 进度条卡在 `0.00/624k`，CLI 打印 `Could not submit`，**但返回码仍是 0** | `submit.py` 已改成只在明确成功时记 submitted。挂代理或重试 |
| **GBK 控制台** | 打印对手名（含 `ı` 等）崩溃；`print` 在提交**之后**会让成功看起来像失败 | 用 `sys.stdout.reconfigure(errors="replace")`；`submit.py` 有 `say()` |
| **JSON 往返把整数键变字符串** | 读缓存摘要后整行为 None，静默给出错值 | `field_ledger.denormalise()` 在 IO 边界归一 |
| **双引号字符串里写直角引号** | JS 语法错误 → **整页白屏**。今晚犯了 3 次 | 改 JS 后必跑 `node --check` |
| **DOM 桩测不出"写进了隐藏容器"** | 总览页空白 | 只能靠人眼；改完 UI 要真的打开看 |
| **`experiments/` 是 gitignored** | `make_v*.py` 构建器不会被提交 | 用 `git add -f` |
| **cron 重复触发** | 旧 session-only cron + 新 durable cron 同时在 :23 跑 | 已删旧的那条 |

## 七、目录地图

```
main.py                      当前提交基线（v37 系）；experiments/v44/adv6.py 是现在的候选
scripts/
  tournament.py              成批对局（--loader kaggle 才是真行为）
  build_ladder.py            把栈式 agent 冻在任意一层做前缀消融 ← 定位"哪一层值钱"的唯一工具
  opponent_fingerprint.py    开局指纹 → 判断对手是哪份代码；--ours 对比我们的版本
  review_versions.py         ★ 生成多版本复盘页（读 API 拿全部提交，本地有就复用、没有就抓）
  ledger_app.py              复盘页的 UI 与图表（JS，手写 SVG，无依赖）
  review_losses.py           单版本/本地模式；提供 compact() 等被上面复用
  field_ledger.py            数据提取与指标口径（revenue_mix / denormalise / collect）
  world_split.py             按商店世界切胜率
  submit.py                  构建+校验入口点+记录 sha256 与 ref
results/
  SESSION_STATE.md           ← 本文件
  submissions.md             提交审计（**只有 status=submitted 且有 ref 的行可信**）
  reports/                   每版一份报告
  ledger/ladder_review.html  ★ 多版本复盘页（唯一入口，双击打开）
insights/                    claims.md（A–G 共 ~60 条）+ local_findings.md（M1–M36、L1–L15）+ sources/
tmp_replays/                 两层缓存：ref-<ref>.json（索引）+ ep-<eid>-summary.json（数据）
```

## 八、新会话的启动提示词（直接复制）

> 读 `results/SESSION_STATE.md` 和 `insights/claims.md`、`insights/local_findings.md`，然后按里面的
> 「下一步待办」继续。约束：①每个决策要有数据与原理支撑 ②每个版本要有报告 ③A/B 验收要求两块独立
> 种子方向一致 ④结论必须标样本量。长任务用 run_in_background，不要用 nohup。
> 我（用户）负责观察，你负责从数据和逻辑上判断，发现我的观察有误要指正。

---

## 九、给新会话的补充（2026-09-25 深夜，最后一轮）

### 9.1 开工自检（三条命令，10 秒，确认工具链还活着）

```bash
# ① 环境与引擎能跑（顺便确认入口点规则没变）
.venv/Scripts/python -c "from kaggle_environments import make; e=make('kaggriculture',configuration={'seed':1},debug=False); e.run(['opponents/v56/main.py']*2); print('engine ok', e.steps[-1][0].reward)"

# ② 提交审计是否可信（只信 status=submitted 且有 ref 的行）
tail -5 results/submissions.md

# ③ 复盘页能生成（会复用缓存，不联网）
.venv/Scripts/python scripts/review_versions.py --versions v44,v41,v40
```
改过 `ledger_app.py` / `field_ledger.py` 的 JS 后**必须**跑：
`.venv/Scripts/python -c "t=open('results/ledger/ladder_review.html',encoding='utf-8').read();open('tmp_v39/c.js','w',encoding='utf-8').write(t[t.index('<script>')+8:t.rindex('</script>')])" && node --check tmp_v39/c.js`
（今晚有一个未转义的中文引号把整页变成白屏，就是这个检查抓到的。）

### 9.2 ❌ **已经关掉的线索——不要重做**（细节见 `insights/claims.md` 的状态列）

| 线索 | 状态 | 一句话原因 |
|---|---|---|
| RACE 跨回合抢跑抢先卖（含"补还"） | ❌ | v30/v31/v32 三次失败；补还贡献为零；伤害随前视长度缩放 |
| boatlee 克隆距离门控 | ❌ | `_clone_distance` 对全部 8 个对手恒为 0，彻底 no-op |
| 番茄扩张（放宽 V219 门槛/填满 17 格/买第 4 象限） | ❌ | 引擎上每株恰好产 4 次（与种植日无关）；放宽门槛 **435→415→357 单调剂量-反应**；买第 4 象限 0胜80负 |
| `_CXTB` 番茄收益门控 | ❌ | 实际是 no-op（被基础门控先拒） |
| 开局改动（买 5 麦 / 最小开局 / C9） | ❌ | **v43 对齐天梯主家族开局，800 局逐格与 v41 完全相同**，一次 W/L 都没翻 |
| `_BD` BUYDIP | ❌ | 两块种子方向相反 + 最差单局从 −$3.3k 恶化到 −$10.3k |
| ca25 常量（`_CA_MARGIN=-25`） | ❌ | 镜像两块方向矛盾（58.7% / 39.8%） |
| 毛线店晚开 = 劣势 | ❌ | 被"别的店也晚开"这个对照打掉（38.5% → 50.0%） |
| "本地 20 局/对手"级别的结论 | ❌ 方法上禁止 | `_SR_*` 假阴性代价几百 Elo |
| `pipe7`/`tetsu_market`/`guruv4`/`v55`/`v56`/`v57` 作为"强对手" | ⚪ | 我们 100% / 93–100%。**只有 `tetsutani_cha22`(55%)、`fieldcraft`(86.7%)、`hybrid2965`(90%) 值得当验收对手** |

### 9.3 正在飞的三条线（接手时先看它们）

1. **v44 出分**（ref 56552481）。出分后按 §二 的规则决定是否换格。
2. **"41 条路线 = 13 经典 + 28 商店特化"**（来自 `master-engine-v4` 的自述）：我们的 41 条磁带是否也这么分组？**有没有商店对落进了错的组？** 低成本、可核实。
3. **step-1 挤压**（`goodpjw2008`，代码已抽在 `tmp_forum/out_goodpjw2008_*/cell7_writefile_main_1f5c7a18.py` 第 3503–3516 行）：唯一的新机制，零和，正对"几百块级"胜负。**守卫必须按我们的 tape（`[BUY 13, BUY 30, SELL 30]`）重写**。

### 9.4 报告纪律（今晚用血换的两条）

1. **胜率必须配最差 margin**。`guruv4` 我们 60-0，**最差只赢 $2**；`hybrid2965` 90% 但最差 −$622。只报胜率会说成"碾压"。
2. **凡是"我们大胜"，先怀疑加载再相信它**。今晚两个最严重的测量错误（跑错入口点、对手目录没进 `sys.path`）**都让对手变弱**，而且**都不报错**——因为"我们赢"不会引起警觉。

### 9.5 一句话回答"现在到底在什么位置"

**我们不在公开 meta 后面。** 四篇最新的公开 agent（`master-engine-v3` 我们 40-0、`v4` 60-0、`2965-hybrid` 90%、`fieldcraft` 86.7%）
**没有一篇含有我们没有的机制**；我们是 ahmed v56 的严格超集并赢它 96%；天梯占 71% 的那个家族就是我们本地唯一同级
`tetsutani_cha22` 的代码。**剩下的差距是"几百块"，不是"一套策略"。**
