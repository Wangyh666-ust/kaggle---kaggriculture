# 会话交接文档（2026-09-22）——压缩/新会话从此恢复

> 本文件是唯一的状态交接点。对话历史可能丢失，**本文件 + git 历史 + results/ 才是真相**。

## 一、当前线上状态（提交 refs 与分数）

| 提交 ref | 版本 | 线上 Elo | 状态 |
|---|---|---|---|
| 56447879 | **v24 重跑**（全新评分） | 爬分中（PENDING） | 监控中，首跑被早期拖累 |
| 56439769 | v24 首次 | 2258.5（89 局） | 已收敛 |
| 56428515 | **v23_c7（当前主力）** | **2452.2 ~ 2459** | 已收敛，= `main` 分支的 `main.py` |
| 56410548 | v21 磁带底盘 | 2148.4 | 历史 |
| — | v15（规则版最好） | 565.8 | 规则路线终点 `legacy/main_rule_v15.py` |

**榜单参照**：榜首约 2900。

## 二、Git 分支结构

```
main       ← 主力：main.py = v23_c7（已合并、已收敛 2452+）
exp/v24-v55← main.py = v24（V55 等价体：race41 + _SR_*）→ 也是两次线上提交的版本
master     ← 规则路线冻结点
```

- 仓库：https://github.com/Wangyh666-ust/kaggle---kaggriculture（分支均带 README）
- 标签：`submit-v11 / submit-v15 / submit-v21 / v21-tape-base / v23-c7`
- **本地保留、不上传**：`opponents/`（对手模型）、`experiments/`（实验变体）、
  `tournament_results/`（对局记录）、`replays*/`（回放）、`kernels/`（参考 notebook）

## 三、agent 形态（现在是磁带路线）

- `main.py` ≈ 6662 行、纯标准库、720 步动作磁带 + ~40 层反射修补（thomastschinkel/prvsiyan 血统，Apache-2.0 文件内保留归属）
- 家族树（逐行 diff 得出）：我们 ⊂ guru（+707 行）⊂ prvsiyan（+186 行）
- **核心支柱层：`_V92_P`（对手成交流预测库）**——消融实验证明摘掉它对 guru 30-10 → 4-36，必须保护

## 四、已验证的结论（别再重复试）

**有效**：
1. 追迭代链拿层（v21→v23_c7 +289 Elo；追公开 V55 再 +11 胜/180 局）
2. `_V92_P_BLOB/_INDEX` 换 guru 版（决定性，+6 镜像胜场）
3. 保留我们的 `_SR_MARGIN=4`/`_SR_HOURS=(22,23)`（抄这两个会退 4 胜）

**无效/有害（负面结果）**：
- 自录卖单流库：语料只有旧库 1/10（232 vs 2398 流），180 局 p=0.86 无差异 → 不采用
- 对手渠道反制（减种对手泛滥作物）：价格照样崩，白让份额
- 分块种植 v20：8/20；按计划雇工 v17/畜群上限 v17b/小麦限额 v18/单纯加人 v19：全部 ≤ v15
- 第 0 天饲料"保险"：现金在第 0 天连锁复利，seed 1000 -$26k
- 羊优先开局：牛日产 1.5 > 羊 1.33，且第 0 天砍牛连锁延误
- 草莓缩到 5-7 棵：-36k/5 局；草莓 28+ 棵：渠道太浅价格崩

## 五、评分机制发现（影响提交策略）

**早期对局权重远大于后期**（实测：早期 +11 分/局、中期 +3、收敛后 +0.36）。
- 前 30-50 局的胜率基本决定上限
- 每次提交都是**全新评分** → 早期翻车就"重开一局"（重交同代码）
- 74% 胜率 = 分数远未收敛（水平处胜率应接近 50%）
- 教训：v24 首跑 14 局只有 1716.8，被早期拖累收敛到 2258；v23_c7 早期顺，到 2452

## 六、基础设施（都已就位）

- `scripts/tournament.py`：对手面板配对巡回赛（16 workers 默认、`--seats 0/1` 单座位；
  **协议建议：20 种子 × 1 座位 = 同样墙钟、独立样本翻倍**，环境座位对称有硬证据）
- `scripts/smoke.py`：改任何东西之前先跑（9 种子 × 双座位，断言 DONE + 资金 >$10k）
- `scripts/record_v92_library.py` + `verify_v92_library.py` + `v92_fire_probe.py`：数据类改动的验证链（drop-in 解码、防泄漏留一评估）
- 对手面板（12 个，`opponents/`）：6 个区分力对手（v55 自我镜像/prvsiyan/guru/v49branch/v51/v52）
  + 6 个护栏对手（beatv48/ourv21/rule_v15/tetsutani/reyhan|pilkwang/salem）。
  当前基线：**262/320（81.9%），平均边际 +$11,443，最差 -$792**
- 监控 cron：`01M33B4DBWBS5TMJV18V99FWHX`（v24 重跑，每小时）

## 七、kimi-code 架构配置（已完成）

- 主 agent = `kimi-code/k3`（max 强度）
- 子代理 = `deepseek/deepseek-flash`（high），池里含 k3（可临时指定做硬子任务）
- 生效方式：会话内执行 **`/model` 选 K3**（`default_model` 只在会话启动时读，`/reload` 不重绑当前会话模型）

## 八、立即下一步（按优先级）

1. **等 v24 重跑轨迹**（前 20 局决定上限；若 15 局时 >2000 有机会冲 2450+）
2. **验证破局线索**：保留我们原 `_SR` 参数可对 V55 用户群 8-10-2 ——
   用新协议（20 种子 × `--seats 0`）跑一次 `main_v24_race41.py`（在 experiments/v23/）确认，
   再决定是否占一次提交额度（今天剩 ~3-4 次）
3. 若 v24 重跑收敛 > 2452：`git checkout main && git merge exp/v24-v55` 提升 `main`
4. 过程纪律：**改任何东西之前先跑 `scripts/smoke.py`**（已有两次隐藏 NameError 的教训）

## 九、复现要点

```bash
# 环境
.venv/Scripts/pip install -U kaggle-environments==1.32.7 kaggle
# 对手解出（本地）
.venv/Scripts/python scripts/extract_opponents.py
# 面板巡回赛（验收标准）
.venv/Scripts/python scripts/tournament.py --candidate main.py --seeds 2000-2019 --seats 0
# 提交
tar -czf submission.tar.gz main.py && kaggle competitions submit kaggriculture -f submission.tar.gz -m "msg"
```
