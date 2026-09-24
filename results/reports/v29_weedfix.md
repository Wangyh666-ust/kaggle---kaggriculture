# v29 — 杂草修复（M1）：机制**已经在 main.py 里**，剩下的缺口被引擎规则封死

- **日期**：2026-09-23
- **分支**：`fix/early-death`（未提交，未 push）
- **基线**：`main.py`（= v28，`sha256 1ffa8782555cfa08…`，7374 行，**本次未改动**）
- **候选**：`experiments/weedfix/main.py`（`sha256 caedf5327678b4ed…`，7503 行，+129 行）
- **附加控件**：`experiments/weedfix/ablate_weed_repair.py`（`sha256 e9474884bf7a78e2…`，7388 行）

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 改动 | ❌ **否决**（噪声，且方向为负） |
| 预登记门槛 | **未达标**：v55 mean `+$362 → +$362`（需 ≥ +$450）；总胜 `115/120 → 115/120`（需 ≥ 117）；worst `−$405`（≥ −$405 ✅） |
| 逐局对比 | 120 局中 **6 局**变化，**每局恰好 −$10**，**0 局胜负改变** |
| 判定规则 | 合计 mean 提升 `−$0.5`（< +$80）→ 按预登记规则判为**噪声** |
| 冒烟 | ✅ `smoke OK`（9 种子 × 双座位，全部 DONE） |
| 回调耗时 | mean `1.912 → 1.979 ms`，p95 `4.329 → 4.356 ms`，max `103.3 → 105.9 ms`（预算内，见 §5） |
| **附带发现** | 消融测得：**现有的 `weed_repair` 层价值 +10 胜 / +$110 mean**（`115/120 → 105/120`）。M1 的收益**已经落袋**，不在本次改动里 |

## 1. 动机（数据）

规格：`reverse/beating_the_mainstream.md` §3「M1（最高置信度）杂草修复」。原始证据：

- 我方杂草 **71%（74/104）被挖掉后再没补种**，对手 47%（62/133），n=160；
- 每株随机杂草 **−$401**（OLS，t=−3.27，n=160）；
- 逐格追踪 seed 12：一株草让某格空了 16 天，**−$1,264**（= 该局全部分差）。

**我在当前 `main.py` 上先复现，确认这个亏损仍然活着**（自对弈，本机）：

```
.venv/Scripts/python scripts/weed_trace.py --seed 12
final  A $91,254  B $92,518  gap -1,264      # 与规格里的数字一字不差
格 (y=1, x=8)：seat0  d7 WEED → d8..d24 EMPTY（17 天），d25 才种 CARROT
              seat1  d7 PLANT STRAWBERRY → d8..d24 持续收获
```

引擎机制（`.venv/Lib/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`）：

| 行号 | 事实 |
|---|---|
| `_spawn_weeds` :836-839 | 随机草只在 `farm["tiles"][y][x] is None` 上生成 |
| `_apply_unit_action` :417-429 / :493-503 | `PLANT` / `BUILD_COOP` / `BUILD_PASTURE` 都要求 `tile is None`，否则**静默 no-op** |
| :484-491 | `DIG` 在空格上是 no-op；对 WEED / 已枯植物 / 空 COOP·PASTURE 有效 |
| **`_new_plant` :215-226** | **`"consecutive_unwatered": 1  # planting day counts as unwatered`** |
| **`_daily_refresh_plants` :783-785** | **日切时 `consecutive_unwatered >= 2` → 格子变回 `{"kind": "WEED"}`** |

最后两条是本次实验的关键，见 §6。

## 2. 排查结论：规格里的机制**已经实现**在 main.py 的底盘里

`main.py` 的 `Chassis` 自带 `weed_repair` 层（定义 :514-560，开关 `DEFAULT_SETTINGS["weed_repair"]=True` :263，
调用点 :476-477），三个分支：

1. **分支 A**：单位脚下的目标格是 WEED，而 tape 动作是 `PLANT/BUILD_*` → 改写成 `DIG`，并把**意图动作入队**；
2. **分支 B**：队列里的动作在后续「tape 动作是 no-op」的回合重放（并把被顶掉的 no-op 排到队尾，从而让 PLANT→WATER 链不散）；
3. **分支 D**：站在 WEED 上、tape 动作本来是 no-op 的回合 → 改成 `DIG`。

也就是说「挖草 + 把中断的计划重新入队」这条 M1 主机制**在跑**。我对分支做了逐次普查
（`Chassis._weed_repair` 打桩；40 局 = seeds 2000-2039 vs v55，seat 0）：

| 分支 | 次数 / 40 局 |
|---|---|
| A 被草挡住的 `PLANT/BUILD` → `DIG` + 入队 | **5** |
| D 站在草上的 no-op 回合 → `DIG` | **40** |
| C 队列被丢弃（3×`PLANT` + 2×`WATER`） | **5** |

**候选只补分支 C 的口子**：父层在「下一步 tape 动作是移动」时会把已入队的 PLANT 丢掉
（:547-548 `if replay[0] == "PLANT" and next_op in MOVES: pending.pop(i, None)`，注释写的是「怕错过当天的 WATER，所以留着种子」）。

## 3. 改动内容

`experiments/weedfix/main.py` = `main.py` **原样复制** + 文件末尾追加一层（129 行），遵循仓库既有约定
（`_MY_PARENT = agent` / `del agent` / 重定义 `agent`，已验证 `agent True`）。

```python
# 1) 把底盘的分支 C 补上：父层丢掉的 PLANT，如果单位还站在目标格上、
#    格子已经空了、且本回合 tape 动作是 no-op，就把 PLANT 重放回去
_WF_PARENT_REPAIR = Chassis._weed_repair
def _wf_repair_queue(self, action, view, st, route, step):
    before = {i: list(q) for i, q in st["pending"].items()}
    _WF_PARENT_REPAIR(self, action, view, st, route, step)   # 先跑父层
    for i, q in before.items():
        if not q or i in st["pending"]:            # 父层没丢 → 不动
            continue
        pos, intended = q[0]
        if intended[0] != "PLANT":                 # 只管 PLANT
            continue
        # 四道闸：单位还在目标格 / 格子已空 / tape 动作确实是 no-op / 种子还在
        ...
        units[i] = list(intended)                  # 重放被丢掉的那次种植
    ...
Chassis._weed_repair = _wf_repair_queue

# 2) 最外层兜底：任何单位把 PLANT/BUILD_* 瞄在 WEED 上都是引擎会忽略的 no-op，
#    换成 DIG 零成本（规格里的"安全洞察"）
del agent
def agent(observation, configuration=None):
    return _wf_safety_dig(_MY_PARENT(observation, configuration), observation)
```

选择「调用父层 + 事后修复」而不是整体重写 `_weed_repair`，是为了**父层的其它行为（分支 A/B/D）逐位不变**，
只改动被识别出来的那一次丢弃。

## 4. 实验方法

- 面板：`--seeds 2000-2039 --seats 0`，对手 `v55 / prvsiyan / guru`，120 局（与规格 §3 的验收基线同一条命令）。
- 指标：胜/负/平 + mean margin + worst margin，**并逐局 diff 两个 JSON**（只看均值会被四舍五入骗过去）。
- **预登记门槛（在看到候选结果之前固定）**：① v55 mean ≥ **+$450**；② 合计胜 ≥ **117/120**；③ worst ≥ **−$405**；
  ④ 若合计 mean 提升 < **+$80** 或 v55 输 2 场以上 → 判噪声、放弃。
- 基线在**同一台机器、同一时段**重跑（`wall 71s`），数字与规格里的实测基线**完全一致**，说明面板没有漂移。

## 5. 结果

### 5.1 面板

| 对手 | 基线 W/L/T | 候选 W/L/T | 基线 mean / worst | 候选 mean / worst |
|---|---|---|---|---|
| guru | 39-1-0 | 39-1-0 | +$510 / −$131 | +$510 / −$131 |
| prvsiyan | 38-2-0 | 38-2-0 | +$430 / −$205 | +$430 / −$205 |
| **v55** | **38-2-0** | **38-2-0** | **+$362 / −$405** | **+$362 / −$405** |
| **合计** | **115/120 (95.8%)** | **115/120 (95.8%)** | **+$434 / −$405** | **+$434 / −$405** |

### 5.2 逐局 diff（关键证据）

120 局里**只有 6 局**的 margin 变了，**每一局恰好 −$10**，**没有任何一局的胜负翻转**：

| 对手-种子 | 基线 margin | 候选 margin | Δ |
|---|---:|---:|---:|
| guru-2011 / guru-2036 | 291 / 655 | 281 / 645 | −10 / −10 |
| prvsiyan-2011 / prvsiyan-2036 | 215 / 576 | 205 / 566 | −10 / −10 |
| v55-2011 / v55-2036 | 225 / 576 | 215 / 566 | −10 / −10 |

（合计 −$60 → mean −$0.5，四舍五入后仍显示 +$434，所以§5.1 的表看着一样；逐局 diff 才是真相。）

两边的负局集合完全相同：`(guru,2021,−131) (prvsiyan,2006,−56) (prvsiyan,2021,−205) (v55,2006,−66) (v55,2021,−405)`。
**这 5 局没有一局是被草或本次改动决定的。**

### 5.3 时间

| | mean | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| 基线 `main.py` | 1.912 ms | 1.232 | 4.329 | 9.555 | 103.287 ms |
| 候选 | 1.979 ms | 1.303 | 4.356 | 9.510 | 105.865 ms |

（`scripts/callback_timing.py --seeds 2000,2001,2002`，各 2157 次回调；max 由终局规划器首次调用主导，
与本次改动无关。开销 +0.07 ms/次，远低于 60 ms 预算。）

## 6. 为什么这个口子补不了（负面结果的机制解释）

**重放下去的计划在当天就会死，$10 的种子白花。** 逐格验证（seed 2011 vs v55，候选）：

```
候选在 step 186 于格 (9,0) 重放 PLANT WHEAT
格 (9,0)  : step 187..  PLANT:WHEAT  →  日切(step 192)后  WEED
```

原因就是 §1 表里那两行引擎规则：`_new_plant` 让新植物带着 `consecutive_unwatered = 1` 出生
（"planting day counts as unwatered"），如果当天没被浇到水，日切时 `>= 2` → **整棵植物变回 WEED**。
所以「种下去但当天浇不到水」是**确定性亏损**（种子 + 格子双重损失），
父层 `next_op in MOVES → pending.pop` 的那道闸**是对的**，我这次是把它拆了，于是 6 局各亏 $10。

而 seed 12 那个值 $1,264 的格子之所以修不了，是因为**固定 tape 下动作槽位不够**：

| step | tape（unit 3） | 恢复所需 |
|---|---|---|
| 185 | `PLANT STRAWBERRY`（被 WEED 挡掉） | ①`DIG`（父层已做） |
| 186 | `WATER`（格子已空 → no-op） | ②`PLANT` |
| 187 | `NORTH`（走人） | ③`WATER` ← **没有槽位** |

DIG + PLANT + WATER 三个动作要挤进 185/186 两个槽位。唯一可行的补救是"借一步"：把 187 的 `NORTH`
改成 `WATER`，让这个单位此后**整条路线晚一步**（公开血统的 weedlag 描述的正是这种"晚一步"，
但它的前提是 tape 后面有空转槽位可以吸收，这里没有）。那属于**另一种机制**（改移动、可能连累该单位后续所有
浇水/收获），不在本次改动范围内，也不是本次预登记的对象。

**量化上限**：分支 C 的 PLANT 丢弃在 v55 面板上是 **3 次 / 40 局**，其中 2 次（seeds 2011/2036）实测价值 **$10/次**；
即便"借一步"100% 成功，也到不了 +$88 的门槛。门槛本身是先于数据设定的，这里如实记为**未达标**。

## 7. 被否决的变体 / 负面结果

| 变体 | 结果（seeds 2000-2039, seat 0, 120 局） | 否决理由 |
|---|---|---|
| **候选（本次）**：补分支 C 的 PLANT 重放 + 外层 WEED 兜底 DIG | 115/120，mean +$434，**6 局各 −$10**，0 胜负翻转 | 噪声且方向为负；重放的植物当天必死（§6） |
| **消融控件**：关掉现有 `weed_repair`（`_IMPL.chassis.cfg["weed_repair"]=False`） | **105/120（87.5%）**，mean **+$324**，worst **−$854**；guru 35-5 +$400 / prvsiyan 35-5 +$317 / v55 35-5 +$254 | 反向证明：**M1 的机制已经在 main.py 里并且值 +10 胜 / +$110**，本次候选拿不到它 |

## 8. 决策与后续

- **不改 `main.py`**（本次全程未编辑，hash 仍是 v28 的 `1ffa8782…`）；候选留在 `experiments/weedfix/` 供复核。
- M1 这条线按规格的说法"最高置信度"，但**它的收益已经在血统里**：本次消融测得其价值为 +10 胜 / +$110 mean，
  真正的残余缺口（分支 C）只有 3 次 / 40 局、每次 $10 量级，**结构性不可能达到 +$88 的门槛**。
- 后续若要继续做杂草方向，只有两条有实际量级的路：
  1. **M2（把日终空格清零）**：随机草只长在空格上，把空格数从 ~4.5 压到 0/1 才能动抽签分布本身；
  2. **"借一步"式修复**：允许单位为一株值钱的作物晚一步（并接受路线整体错位的风险），
     只有当目标作物是 STRAWBERRY/MELON 这类高价持产作物时才值得——需要单独设计、单独 A/B。

## 9. 复现

```bash
# 入口点约定校验（必须打印 agent True）
.venv/Scripts/python -c "import importlib.util;s=importlib.util.spec_from_file_location('x','experiments/weedfix/main.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);c=[(k,v) for k,v in vars(m).items() if callable(v) and not k.startswith('__')];print(c[-1][0], m.agent is c[-1][1])"

# 冒烟
.venv/Scripts/python scripts/smoke.py experiments/weedfix/main.py

# 预登记面板：基线 / 候选 / 消融控件（同机、同seed块）
.venv/Scripts/python scripts/tournament.py --candidate main.py \
  --opponents opponents/v55/main.py opponents/prvsiyan/main.py opponents/guru/main.py \
  --seeds 2000-2039 --seats 0
.venv/Scripts/python scripts/tournament.py --candidate experiments/weedfix/main.py \
  --opponents opponents/v55/main.py opponents/prvsiyan/main.py opponents/guru/main.py \
  --seeds 2000-2039 --seats 0
.venv/Scripts/python scripts/tournament.py --candidate experiments/weedfix/ablate_weed_repair.py \
  --opponents opponents/v55/main.py opponents/prvsiyan/main.py opponents/guru/main.py \
  --seeds 2000-2039 --seats 0

# 逐局 diff（§5.2 的证据）
#   tournament_results/agent-20260923-133819.json   （基线）
#   tournament_results/weedfix-20260923-134307.json （候选）

# 耗时
.venv/Scripts/python scripts/callback_timing.py --cand main.py --seeds 2000,2001,2002
.venv/Scripts/python scripts/callback_timing.py --cand experiments/weedfix/main.py --seeds 2000,2001,2002

# 逐格追踪（§1 / §6）
.venv/Scripts/python scripts/weed_trace.py --seed 12

# 分支普查打桩脚本（本次新写，未纳入 scripts/）：.scratch_ed/probe_branches.py
#   .venv/Scripts/python .scratch_ed/probe_branches.py --seeds 2000-2039 --opp opponents/v55/main.py
#   .venv/Scripts/python .scratch_ed/check_replay_fate.py 2011
```
