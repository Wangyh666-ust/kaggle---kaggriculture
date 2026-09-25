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
