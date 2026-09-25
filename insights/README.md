# 洞见知识库

**用途**：把公开文章里的洞见、我们自己的本地结论，统一登记成一张**带状态的总表**，
并区分清楚三类东西——**已可用 / 待确认 / 本地已否证**。

这个目录的规则只有一条：**每条洞见都必须有状态和证据指针**。
没有状态的想法不写进来；状态是"待确认"就说明白缺什么才能确认。

## 状态图例

| 标记 | 含义 | 什么时候可以升级/降级 |
|---|---|---|
| ✅ **可用** | 已采纳进 `main.py`，或本地验证过且可复现 | 只能被"两个独立种子块的反例"降级 |
| 🔶 **待确认** | 有道理、有出处，但我们**没验证过**，或样本不足以定论 | 补上缺失的实验即可升级或降级 |
| ❌ **已否证** | 我们本地测过、是负结果 | 除非有新证据推翻那次测量，否则不再重复投入 |
| ⚪ **不适用** | 针对我们没有的场景（如克制某个我们打不到的公开 agent） | —— |

## 文件

```
insights/
  README.md              本文件：用途、图例、怎么维护
  claims.md              ★ 总表：每条洞见 + 来源 + 状态 + 证据指针（最重要的一张表）
  local_findings.md      我们自己验证过的可复用结论（不来自外部文章）
  sources/               每份公开文章一份，保留原始表述与出处
    metav4.md            thomastschinkel《The Metav4 Farm v13》——§6 交接 / §7 负面清单 / §8 评测课
    the_2945_farm.md     thomastschinkel《The 2945 Farm》v9/4——0-36 与番茄缺口
    kaitofukami_v27.md   Kaito《25/27 Strict-Future v27 Midgame Meta Reset》——开局坍缩、续带
    ice_and_fire.md      leoprovorov《A Song of Ice and Fire》——冰火诊断法（固定 vs 反应）
    shepherds_ledger.md  haideptry《The Shepherds Ledger》09-24——投机性开盘陷阱
    demystifying_2900.md haideptry《Demystifying 2900+ Meta》——RACE / day-11 羊 / 番茄主张
    herd_safe_window.md  dmitriigluzdov《Herd-Safe Sale Window》LB2700——常量与 _CXTB
    boatlee_clone_preemption.md  boatlee《V14 Clone Preemption》《V16-RC5 8C/4S》
```

## 怎么用（工作流）

1. **动手之前先查 `claims.md`**。如果那条已经是 ❌，不要重做；如果是 🔶，先确认"缺的那个实验"是什么。
2. **新的外部文章**：加一个 `sources/<名字>.md`（保留原文关键句 + 链接），并在 `claims.md` 里加行。
3. **做了实验之后**：只改 `claims.md` 里的**状态**和**证据指针**，原始表述留在 `sources/` 不动——
   这样能看出"我们否证的是他的原话，还是我们自己的转述"。
4. **我们自己发现的结论**写进 `local_findings.md`，不要混进 `sources/`。

## 一条纪律（本项目最贵的一课）

**结论必须标样本量与不确定性。**
本项目已经因为"20 局/对手"级别的样本得出过假阴性（`_SR_*` 那条，代价几百 Elo），
也因为单一种子块得出过假阳性（ca25、毛线店各一次）。
**任何要写进"可用"的 A/B，每臂 ≥500 局，且两个独立种子块方向一致。**

---

## 工具索引（`scripts/`）

2026-09-25 这一轮新增/固化的工具。每个的 docstring 里都写了"它回答什么问题"。

### 评测与对手

| 工具 | 回答什么问题 |
|---|---|
| `scripts/tournament.py` | 候选 vs 对手面板，逐对手 W/L/T + 均差。**`--loader kaggle`（默认）才是 Kaggle 真行为**——取命名空间里最后一个可调用对象；`--loader agent` 是旧口径，仅用于对照（见 L7） |
| `scripts/build_ladder.py` | **把栈式 agent 冻在任意一层做入口**，做前缀消融。原理：作者逐层包裹时把父函数存成 `_XXX_PARENT`，在副本末尾追加 `_ABLATION_ENTRY = <stage>` 就能让 Kaggle 的 last-callable 规则选中它。**这是目前唯一能把"我们被打败"定位到具体层的工具** |
| `scripts/world_split.py` | 按**商店世界**切分胜率（leoprovorov 的"评测单元是路线×世界"）。用来找 L4 说的"结构性空洞" |
| `scripts/field_ledger.py` | 把**一局**渲染成自包含 HTML（内联 SVG，无依赖）：现金/闲置/地块账本/日内现金流/市场指令/终局账本。支持 `--replay` 读真实天梯回放 |

### 源码与血缘

| 工具 | 回答什么问题 |
|---|---|
| `scripts/extract_embedded.py` | 从 notebook 里抽出内嵌的 agent（支持 base64/base85/base85-of-zlib、gzip/zlib、裸 .py、tar 内含 main.py；字节字面量；`base64.b64decode('…')` 这类**被调用包裹**的写法） |
| `scripts/token_compare.py` | 两个 agent 的**标识符集合差**——"谁定义了对方没有的名字"。**不要用整体相似度**，见 L13 |
| `scripts/lineage_id.py` | 判断一个未知 agent 属于哪条已知血统（标记词 + 排序敏感 ratio） |
| `scripts/opening_trace.py` | 逐回合打印现金/价格/市场指令。**注意口径**：`env.steps[t][i]["observation"]` 里的 money 是**动作执行之后**的余额 |
| `scripts/atomic_plant_probe.py` | 量"原子播种"陷阱（同作物 PLANT 请求数 > 种子数则**全部**变 PASS）触发多少次。实测我们是 0 |

### 提交

| 工具 | 说明 |
|---|---|
| `scripts/submit.py` | 构建 + 校验入口点 + 记录 sha256 与 **ref** 到 `results/submissions.md`。⚠️ 2026-09-25 修：它曾在提交**成功之后**因 GBK 控制台编码崩溃，看起来像失败且日志写不进去 |
