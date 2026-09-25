# Grandmaster Agent v8（anhadmahajan06）—— 又一份"同栈拼装"

- **链接**：https://www.kaggle.com/code/anhadmahajan06/kaggriculture-autonomous-ai-farming-agent
- **产物**：`main.py` **1,067,635 B**，sha256 `2993cf92…`，**Kaggle 入口 `_cxd_agent`**

## 一、它的配方 = 我们正在走的路

> "**Competitive Edge: V56 Base + EarlyCycle Open + E402 Late Seed Capping +
> E410 Fertilizer Conservation + Layer D Order Book Lockstep Settlement**"

| 层 | 它的说法 | 与我们对照 |
|---|---|---|
| **V56 核心** | `_ALT_MODE = 'EarlyCycle'`：**"Direct 5-wheat opening eliminates 12 coins opening friction"** | 又一次独立的"开局买 5 麦"（nathanjacob 的 C9 是同一主张）。注意它自报的收益是 **12 币**——**和我们测到的"整个开局改动值 +$26"同一量级**，第三份独立证据说明**开局这条线本来就很小** |
| **E402 Seed Capping** | 第 25–27 天（612–648 步）停止买无法成熟的胡萝卜/小麦种子 | 我们 `main.py` 里**已有** `e402_agent` |
| **E410 Fertilizer Conservation** | 600–718 步停止给"已施肥/已到产量上限"的地块施肥料，"preserving ~1,000 fertilizer units and **liquidating them for +2,000 to +3,000 coins**" | 我们**已有** `e410_agent`。**这条是唯一给了具体金额、且我们能本地验证的** → 见待办 |
| **Layer D Order Book**（`_cxd_agent`） | "Treats market actions as an order book, reordering transactions into **lockstep micro-batches**. Secures front-running advantage in market clearance, gaining **+180 coins net edge**" | **这就是我们 v41 移植的 `_CXD`**。它的自报收益只有 **+$180/局**；我们实测 v41 相对 v40 在 tetsutani 上是 50%→55%（+5pp）——**量级对得上**（都是"小但真实"） |

## 二、证据强度：**n = 4**

> "**Deterministic Win Rate: 100% across all tested seeds (42, 100) and reversed seat positions**"

两个种子 × 两个座位 = **4 局**，声称"100% 胜率"。

这和另外两家是同一模式：

| 作者 | 声称 | 实际样本 |
|---|---|---|
| anhadmahajan06 | "100% deterministic win rate" | **4 局**（2 种子 × 2 座位） |
| dmitriigluzdov | `LOCAL_GAMES` 全部 `outcome: 1.0` | 5 个 demo 种子，**实际差额 $3–$212**（在 $60k–120k 量级上 = 0.005%–0.3%） |
| leoprovorov | lead-1 六局全胜、lead-2 六局全胜 | **6 局**（3 世界 × 2 座位） |
| nathanjacob | pipe18 vs 14 个对手 88.9% Elo | 650 局（**这一家的样本量是认真的**） |

⇒ **公开前线的高调声称，证据量普遍是 n=4~6。** 我们的 L3 纪律（两独立种子块、每臂 ≥500 局）
在这个赛场上属于**远高于社区平均**的严格度。这既是我们的优势（不容易被噪声骗），
也提醒我们：**别人 notebook 里的"大幅提升"基本不可信，必须自己测**。

## 三、为什么这份 notebook 对我们仍然有用

1. **它独立确认了 `_CXD`（Layer D）是真实有效的**，且量级是"+$180/局"这种小数目——
   与我们 v41 的实测（+5pp on tetsutani）一致。**两次独立测量的量级吻合，是好信号**。
2. **它给出了 E410（肥料守恒）的唯一具体金额**：+$2,000–$3,000/局。这是我们可以本地验的第一条。
3. 它的层命名 `_ALT_MODE = 'EarlyCycle'` 提示：**开局模式是一个可切换的开关**，
   而不是硬编码——如果我们以后要再动开局，这比改常量更干净。

## 四、待办

1. **验 E410 肥料守恒**：我们 `main.py` 已有 `e410_agent`，但**它是否包含"第 600–718 步停止施肥"这一条**？
   用 `scripts/waste_audit.py` 查我方在 600–718 步的施肥次数与肥料消耗。
   若有浪费，这条是**明确有金额、且独立可测**的改动。
2. 核对 `_ALT_MODE` 式的"开局开关"是否存在（一次性判断，低成本）。
