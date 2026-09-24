# 逆向工程：把头部策略拆解出来

**目标**：把榜首几支队伍的策略，从公开回放里**还原成我们可以直接使用/对打的工件**，
而不是停在"他们很强"这种结论上。

## 为什么可行

每条公开天梯回放都带：

- `info.seed` —— 这一局的世界种子
- `info.TeamNames` / `rewards` —— 双方与比分
- **双方各自 720 步的完整动作流**（`steps[t][seat].action` = `{farmer, hands, market}`）
- **双方各自的 private 状态**（`steps[t][seat].observation.private` = `shed`/`seeds`/`inventories`）

也就是说：**头部 agent 的行为是完全可观测的**——它的开局、它在每个商店组合下选的路线、
它的雇佣与买卖节奏、它的畜群与作物计划，全都逐回合可见。拿不到源码，但拿得到行为。

## 目录

```
reverse/
  README.md              本文件：目标、方法、如何复现
  targets.md             目标队伍清单（teamId / 分数 / 名次 / 已知血统线索）
  profiles/              每支队伍的拆解报告（一支一份）
  replays/               抓下来的回放（git-ignored）
```

## 方法（可复现）

```bash
# 1. 抓语料（按 teamId；脚本会按 429 退避并断点续跑）
.venv/Scripts/python scripts/fetch_ladder_replays.py \
    --teams 16732748,16730612,16770421 --episodes 10 --out reverse/replays

# 2. 通用画像（开局签名聚类 / 农场画像 / 购买 / 价格轨迹）
.venv/Scripts/python scripts/ladder_meta_report.py --top reverse/replays --out reverse/profiles/_data.md

# 3. 与我们的逐回合差分（同一商店组合下他们在哪些回合做了什么）
.venv/Scripts/python scripts/harvest_routes.py --replays reverse/replays --coverage-only
.venv/Scripts/python scripts/harvest_routes.py --replays reverse/replays \
    --prefer "<target team>" --out reverse/routes_<team>.json
```

## 已知的坑（先记住，别浪费时间）

1. **同 seed ≠ 同世界。** `_spawn_weeds` 只在空格子消耗 rng，商店抽取用同一台 rng，
   所以商店序列取决于双方打法。**不能**把我们的 agent 放到他们的 seed 上比钱。
   他们的回放只能用于**观测**，不能用于**重放对局**。
   （见 `results/ladder_top_meta.md` §7）
2. **"2900+ 公开 notebook"不可信。** haideptry / thomastschinkel 公开 notebook 里内嵌的
   agent 我们实测 40-0 赢它，自报的 2850–2945 复现不出来。
3. **验证集局要剔除。** `EPISODE_TYPE_VALIDATION` 是自己打自己，不是天梯局，
   而且不保证 $0 平局（座位不对称）。
4. **别只看分数。** 榜单分主要由"抽到多强的对手"决定，不是实力。
   （见 `results/score_is_opponent_draw.md`）

## 交付标准

一支队伍的拆解算"完成"，要能回答：

- [ ] 它的**开局签名**（前 3 步市场单）是什么？和已知公开血统（我们/guru/prvsiyan/V49-V57）是否同源？
- [ ] 它在**每个商店组合**下走什么路线？（能建出 route 表吗？）
- [ ] 它的**农场计划**：d12/d16/d20 的畜群构成、作物构成、空地块、雇工数
- [ ] 它的**市场节奏**：什么时机卖、卖哪些渠道、订单槽位怎么排
- [ ] **和我们相比，它在哪些回合做了不同的事**（逐回合 diff，不是画像）
- [ ] 这些差异里，哪些是**可以移植到我们 agent 上的**（且不依赖它特有的层）
