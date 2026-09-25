# Demand-Preserving Turn Sale Timing（tetsutani）

- **链接**：https://www.kaggle.com/code/tetsutani/demand-preserving-turn-sale-timing
- **票数**：**88**（2026-09-24）——作者 `tetsu2131`，本站粉丝基数大（历史 notebook 100–290 票）
- **产物**：`submission_cha22.tar.gz` → `main.py` **501,543 B / 7,483 行**，sha256 `127ed3e62988c047…`
  （我们自己的 `main.py` 是 1,059,397 B / 7,666 行）
  （我们抽出为 `opponents/tetsutani_cha22/main.py`）
- **Kaggle 入口（`get_last_callable` 实测）**：**`ig_agent`**，不是 `agent`

## 一、它的底座就是**我们的底座（v36）**

```
_R42_OPENING      = [['BUY_PRODUCT','WHEAT',13], ['BUY_PRODUCT','WHEAT',30], ['SELL','WHEAT',30]]
V9_OPENING_STEP0  = (("BUY_PRODUCT","WHEAT",20), ("SELL","WHEAT",15))
```

`20/15` 正是我们 **v37 之前的取值**（v37 改成 `10/5` 修早死 bug）。
且它含 `_R108_SHOP_ROUTES` / `_V92_TABLE` / `_v219_qualifies` / `make_agent` / `chassis`
——与 `opponents/v53`、`v52`、`v51`、`v50` 的相似度都在 **0.9907**。

⇒ **它是一个与我们同源、但比我们多叠了很多层的复合体。**

## 二、它主打的机制：**executable SELL 队列空洞闭合**

> "最终生产层投影**可执行的棚内库存**，把**可证明零执行**的现金品 `SELL` 变成队列空洞，
> 并把**后面的可执行 SELL 提前填进那些空洞**，同时不动非 SELL 指令。"

四层结构（它自己的图）：

```
ig_agent（继承的农场控制器）
  -> 市场护栏（有界排序、施肥、晚季种子需求控制）
  -> 同项压缩（合并重复的 SELL / BUY_PRODUCT / BUY_SEED 数量）
  -> 投影库存通行证（把执行 0 单位的现金品 SELL 标成空洞）
  -> 队列空洞闭合（把后面的可执行现金品 SELL 提前到最早的洞）
  -> 输出修改后的市场列表；末层任何异常都退回继承的 action
```

我核对了它的自检断言（notebook cell 25）：

```python
assert "# ==== IG (bundled): queue hole-closure ====" in text
assert "def _ig_close_queue" in text
assert "projected = dict(projected_shed(action, FarmView(observation)))" in text
assert "if executed <= 0:" in text
assert "target = holes.pop(0)" in text
assert "cha20_entry_agent = ig_agent" in text
assert "kaggle_agent = cha20_entry_agent" in text
```

**这一族与我们的 B2（RACE 抢跑）同宗但更保守**：它**不新造**任何市场意图，
只在**同一回合内**重排 SELL 的槽位。我们的 `_V92_P_EVERY=2` / `_OR2_SLOT_MARGIN=8`
也属于"槽位排序"这一族。

## 三、它的完整层栈（点名可查）

```
cha20 链：_FX, _DP, _MP, _BD, _MPX, _SM   （作者自己的实验层）
F4: Layer D - exact best-response ordering      (_CXD，来自 elo_2615 order-book)
F5: EXP410 fertilizer guard                     (pipe18 的 e410_agent)
F6: EXP402 late seed cap                        (pipe18 的 e402_agent)
MERGE: same-item SELL 压缩                      (port of 2695 的 E334)
IG: queue hole-closure
```

**注意 F5/F6 的原始出处是 pipe18，而 `e402_agent`/`e410_agent` 我们的 `main.py` 里已经有了。**

## 四、我们测到的（这是本文件最硬的部分）

| 条件 | 战果 | 样本 |
|---|---|---|
| `--loader kaggle`（**真·Kaggle 行为**，跑 `ig_agent`） | **我们 12胜48负**，均差 −$605，最差 −$3,222 | **60 局**（种子 1000-1029），主口径 |
| 上一条的子集（更早一次） | 我们 6胜34负，均差 −$697 | 40 局（种子 1000-1019，**与上行重叠，不算独立样本**） |
| `--loader agent`（跑 `agent`，**错的入口**） | **我们 60胜0负**，均差 +$2,064 | 60 局 |

**保真口径**：**60 局 12胜48负 = 我们输 80%**。（两块种子块正在跑第二块以按 L3 纪律复核。）

⇒ 两个结论：
1. **这个复合体确实稳定压制我们**（这是本次会话最重要的实测结果）。
2. **我们的测试台此前一直跑错入口点**，而这恰好把"复合体"这一整类对手变成了"我们能 40-0"的假象。

## 五、待办

1. **层消融**：F4/F5/F6/MERGE/IG 与 cha20 链逐条叠到我们的 v37 上单独测——
   找出**到底是哪几层**造成 80% 的差距。这是把"我们被打败"变成"我们知道为什么"的唯一路径。
2. 它没做**评分审计**（notebook 全是打包与行为审计，第 14 节自己写"单次自对弈是行为与打包审计，
   不是强度估计"）。它的强度声张完全来自打包正确，**强度证据只有我们的测量**。
3. `market-smart-farming`（105 票，2026-09-17）的产物 sha256 `f6a756cfb900b9d5…`
   **就是我们已有的 `opponents/tetsu_market/main.py`**（333,999 B）——已测。
