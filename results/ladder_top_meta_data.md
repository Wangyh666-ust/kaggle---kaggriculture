# 天梯头部对手分析（由 scripts/ladder_meta_report.py 生成）

语料：**15 局头部对局**（replays_ladder/）+ **24 局我们自己的对局**。
数据来源：`scripts/fetch_ladder_replays.py` 抓取的公开天梯回放；每条回放含 `info.seed`
与双方 720 步完整动作。**本文件全部数字可由脚本重跑复现**。

## 1. 语料

| episode | seed | 双方 | 比分 | 分差 |
|---|---|---|---|---|
| 112048727 | 8823651 | Majkel1337 vs Vadim Vasilenko | $105,066 : $114,179 | -9,113 |
| 112055591 | 1063836866 | Vadim Vasilenko vs THIRD FARM CLUB | $102,485 : $98,097 | +4,388 |
| 112062458 | 381415834 | mtmr_s1 vs Vadim Vasilenko | $108,049 : $107,398 | +651 |
| 112060059 | 250617489 | KawattaTaido vs 🐚seek inspiration🐚 | $105,662 : $104,165 | +1,497 |
| 112060903 | 973927580 | 吃白饭的大肥鱼 vs Vadim Vasilenko | $101,713 : $107,627 | -5,914 |
| 112061237 | 1736337329 | TheEggman vs ymg_aq | $103,650 : $102,601 | +1,049 |
| 112061264 | 24113471 | Kaggledew Valley 🏆 vs THIRD FARM CLUB | $174,206 : $171,164 | +3,042 |
| 112062012 | 1231344584 | THIRD FARM CLUB vs 吃白饭的大肥鱼 | $121,756 : $113,898 | +7,858 |
| 112062053 | 20086444 | mtmr_s1 vs Unknown Mother-Goose | $103,527 : $102,535 | +992 |
| 112062179 | 1838511592 | SpaTaro vs offhand | $83,261 : $79,965 | +3,296 |
| 112062199 | 1408744938 | ymg_aq vs Majkel1337 | $73,195 : $77,536 | -4,341 |
| 112063183 | 742113079 | 吃白饭的大肥鱼 vs ymg_aq | $103,823 : $104,623 | -800 |
| 112063769 | 1424861355 | dqvide vs DECEM | $99,306 : $129,622 | -30,316 |
| 112064036 | 1356606082 | xxxx0314 vs Unknown Mother-Goose | $106,339 : $116,618 | -10,279 |
| 112064324 | 2067712753 | mtmr_s1 vs 吃白饭的大肥鱼 | $79,986 : $83,267 | -3,281 |

## 2. 开局签名聚类（前 3 步市场单）

同一签名 = 同一 agent（或同一份共享代码）。

**家族 1** — 24 seats, 1 teams: ReD_MooN_rise

```
[] | [["BUY_PRODUCT","WHEAT",10],["SELL","WHEAT",5],["BUY_SEED","WHEAT",1]] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 2** — 11 seats, 5 teams: DECEM, Unknown Mother-Goose, Vadim Vasilenko, Zain96, mtmr_s1

```
[] | [["BUY_ANIMAL","COW",1],["BUY_PRODUCT","WHEAT",5]] | [["SELL","WHEAT",1],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",3]]
```

**家族 3** — 3 seats, 1 teams: THIRD FARM CLUB

```
[] | [["BUY_PRODUCT","WHEAT",3],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","SHEEP",2],["BUY_ANIMAL","COW",3],["BUY_SEED","MELON",7],["BUY_SEED","WHEAT",13]] | []
```

**家族 4** — 3 seats, 1 teams: 吃白饭的大肥鱼

```
[] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_PRODUCT","WHEAT",4],["BUY_ANIMAL","COW",2],["BUY_SEED","MELON",6],["BUY_ANIMAL","SHEEP",3],["BUY_SEED","WHEAT",9]] | [["BUY_SEED","WHEAT",1]]
```

**家族 5** — 3 seats, 1 teams: ymg_aq

```
[] | [["BUY_PRODUCT","WHEAT",20],["BUY_PRODUCT","WHEAT",18],["SELL","WHEAT",36],["BUY_PRODUCT","WHEAT",91],["BUY_PRODUCT","WHEAT",40],["SELL","WHEAT",63],["SELL","WHEAT",11],["SELL","WHEAT",85],["BUY_ANIMAL","COW",1],["BUY_PRODUCT","WHEAT",5]] | [["SELL","WHEAT",1],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",3]]
```

**家族 6** — 3 seats, 3 teams: Auto Fermers, Dinesh Makireddy 7389, chandora

```
[] | [["BUY_PRODUCT","WHEAT",20],["SELL","WHEAT",15],["BUY_SEED","WHEAT",1]] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 7** — 2 seats, 2 teams: JZ, dqvide

```
[] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2],["BUY_SEED","WHEAT",7],["BUY_SEED","MELON",12],["BUY_PRODUCT","WHEAT",6]] | [["SELL","WHEAT",3]]
```

**家族 8** — 2 seats, 2 teams: Adil Munawar, Sahaj Deep Singh

```
[] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",4],["BUY_SEED","WHEAT",5],["BUY_SEED","MELON",5],["BUY_PRODUCT","WHEAT",5]] | []
```

**家族 9** — 2 seats, 2 teams: Pardheev Krishna, coke lu

```
[] | [["BUY_PRODUCT","WHEAT",13],["BUY_PRODUCT","WHEAT",30],["SELL","WHEAT",30]] | [["SELL","WHEAT",13],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 10** — 1 seats, 1 teams: Majkel1337

```
[] | [["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2],["BUY_PRODUCT","WHEAT",6]] | [["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",1]]
```

**家族 11** — 1 seats, 1 teams: KawattaTaido

```
[] | [["BUY_PRODUCT","WHEAT",14]] | [["SELL","WHEAT",9],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2],["BUY_SEED","WHEAT",7],["BUY_SEED","MELON",12]]
```

**家族 12** — 1 seats, 1 teams: 🐚seek inspiration🐚

```
[] | [["BUY_PRODUCT","WHEAT",5]] | [["SELL","WHEAT",5],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 13** — 1 seats, 1 teams: TheEggman

```
[] | [["BUY_PRODUCT","WHEAT",5],["BUY_ANIMAL","COW",1]] | [["SELL","WHEAT",1],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",3]]
```

**家族 14** — 1 seats, 1 teams: Kaggledew Valley 🏆

```
[] | [["BUY_PRODUCT","WHEAT",5],["BUY_ANIMAL","COW",3],["BUY_ANIMAL","SHEEP",2],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","MELON",4],["BUY_SEED","WHEAT",4]] | [["BUY_SEED","MELON",1]]
```

**家族 15** — 1 seats, 1 teams: SpaTaro

```
[] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","MELON",7],["BUY_SEED","WHEAT",7],["BUY_PRODUCT","WHEAT",14],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]] | [["SELL","WHEAT",3],["HIRE"],["HIRE"],["BUY_PRODUCT","CARROT",16],["BUY_PRODUCT","EGG",5],["BUY_PRODUCT","STRAWBERRY",16],["BUY_PRODUCT","TOMATO",14],["BUY_PRODUCT","WHEAT",3]]
```

**家族 16** — 1 seats, 1 teams: offhand

```
[] | [["BUY_PRODUCT","WHEAT",10],["SELL","WHEAT",10],["BUY_SEED","WHEAT",1]] | [["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 17** — 1 seats, 1 teams: Majkel1337

```
[] | [["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",2],["BUY_PRODUCT","WHEAT",2]] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",1]]
```

**家族 18** — 1 seats, 1 teams: 吃白饭的大肥鱼

```
[] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_PRODUCT","WHEAT",4],["BUY_ANIMAL","COW",2],["BUY_SEED","MELON",6],["BUY_ANIMAL","SHEEP",3],["BUY_SEED","WHEAT",9]] | []
```

**家族 19** — 1 seats, 1 teams: xxxx0314

```
[] | [["BUY_PRODUCT","WHEAT",20],["SELL","WHEAT",15]] | [["BUY_PRODUCT","WHEAT",30],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 20** — 1 seats, 1 teams: Orange

```
[] | [["BUY_ANIMAL","GOOSE",3],["BUY_PRODUCT","WHEAT",3],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","MELON",8]] | [["HIRE"]]
```

**家族 21** — 1 seats, 1 teams: ayutin tin

```
[] | [["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2],["BUY_SEED","MELON",12],["BUY_SEED","WHEAT",7],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"]] | [["BUY_PRODUCT","WHEAT",2]]
```

**家族 22** — 1 seats, 1 teams: lmq

```
[] | [["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_SEED","MELON",6],["BUY_SEED","WHEAT",6],["SELL","WHEAT",1],["SELL","WHEAT",3],["SELL","WHEAT",1]] | [["BUY_PRODUCT","WHEAT",6],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_SEED","WHEAT",5]]
```

**家族 23** — 1 seats, 1 teams: Veeranuch Leelalai

```
[] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"]] | []
```

**家族 24** — 1 seats, 1 teams: Wiz

```
[] | [["BUY_PRODUCT","WHEAT",4],["HIRE"],["HIRE"],["BUY_SEED","MELON",7],["BUY_SEED","WHEAT",5],["BUY_ANIMAL","SHEEP",4]] | []
```

**家族 25** — 1 seats, 1 teams: R3ddrag0n

```
[] | [["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",4],["BUY_SEED","WHEAT",5],["BUY_SEED","MELON",5]] | []
```

**家族 26** — 1 seats, 1 teams: hikarinosenshi

```
[] | [["BUY_PRODUCT","WHEAT",13]] | [["SELL","WHEAT",8],["BUY_SEED","WHEAT",7],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 27** — 1 seats, 1 teams: Pat

```
[] | [["BUY_PRODUCT","WHEAT",5],["BUY_PRODUCT","WHEAT",10],["SELL","WHEAT",60]] | [["SELL","WHEAT",13],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 28** — 1 seats, 1 teams: democatXamer

```
[] | [["BUY_PRODUCT","WHEAT",69],["SELL","WHEAT",69]] | [["SELL","WHEAT",13],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 29** — 1 seats, 1 teams: rishavsaigal

```
[] | [["BUY_PRODUCT","WHEAT",60],["SELL","WHEAT",60]] | [["SELL","WHEAT",13],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 30** — 1 seats, 1 teams: John Gates

```
[] | [["BUY_PRODUCT","WHEAT",7],["SELL","WHEAT",2]] | [["BUY_PRODUCT","WHEAT",30],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 31** — 1 seats, 1 teams: Dzmitry Pihulski

```
[] | [["BUY_PRODUCT","WHEAT",13]] | [["SELL","WHEAT",13],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 32** — 1 seats, 1 teams: Odyssey

```
[] | [["BUY_PRODUCT","WHEAT",50],["SELL","WHEAT",50]] | [["SELL","WHEAT",13],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 33** — 1 seats, 1 teams: liu bo

```
[] | [["BUY_PRODUCT","WHEAT",70],["SELL","WHEAT",70]] | [["SELL","WHEAT",13],["BUY_PRODUCT","WHEAT",5],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

**家族 34** — 1 seats, 1 teams: Georgi Kanev

```
[] | [["BUY_PRODUCT","WHEAT",20],["SELL","WHEAT",15]] | [["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]]
```

## 3. 头部座位的农场画像

| 队伍 | 座位 | d12 金钱/畜群/作物/空地块/雇工 | d16 金钱/畜群/作物/空地块/雇工 | d20 金钱/畜群/作物/空地块/雇工 | d29 金钱/畜群/作物/空地块/雇工 |
|---|---|---|---|---|---|
| Majkel1337 | s0 | $11k / C4+G7+S11 / MELO1+STRA25+WHEA27 / 25 / 12 | $33k / C4+G7+S12 / STRA25+TOMA2+WHEA24 / 26 / 12 | $57k / C4+G7+S12 / STRA20+TOMA3+WHEA28 / 26 / 11 | $105k / C4+G7+S3 / CARR2+WHEA1 / 66 / 10 |
| Vadim Vasilenko | s1 | $12k / C6+G6+S14 / STRA20+TOMA1+WHEA27 / 26 / 11 | $37k / C6+G6+S14 / STRA20+TOMA8+WHEA21 / 25 / 12 | $62k / C6+G6+S14 / STRA10+TOMA12+WHEA26 / 25 / 11 | $114k / C2+G4+S7 / TOMA3 / 72 / 10 |
| Vadim Vasilenko | s0 | $19k / C10+G3+S11 / STRA22+TOMA1+WHEA28 / 25 / 11 | $50k / C10+G3+S11 / CARR3+STRA22+TOMA7+WHEA18 / 26 / 11 | $70k / C10+G3+S11 / CARR12+STRA12+TOMA10+WHEA17 / 25 / 11 | $102k / C4+G1+S1 / TOMA3 / 84 / 10 |
| THIRD FARM CLUB | s1 | $17k / C6+G2+S12 / CARR6+MELO6+STRA29+TOMA5+WHEA9 / 25 / 9 | $36k / C7+G2+S12 / CARR4+MELO6+STRA22+TOMA7+WHEA15 / 25 / 11 | $52k / C7+G2+S7 / CARR9+MELO6+STRA14+TOMA12+WHEA18 / 25 / 11 | $98k / C3+G2+S4 / STRA6+TOMA3 / 76 / 10 |
| mtmr_s1 | s0 | $6k / C13+S10 / MELO2+STRA18+TOMA5+WHEA48 / 4 / 11 | $32k / C13+S10 / CARR19+MELO5+STRA24+TOMA17+WHEA9 / 3 / 13 | $59k / C13+S10 / CARR11+MELO9+STRA14+TOMA16+WHEA26 / 0 / 12 | $108k / C5+S4 / STRA6 / 58 / 10 |
| Vadim Vasilenko | s1 | $21k / C10+G2+S10 / STRA21+TOMA5+WHEA27 / 25 / 11 | $48k / C10+G2+S10 / STRA21+TOMA10+WHEA22 / 25 / 11 | $69k / C10+G2+S10 / CARR5+STRA11+TOMA13+WHEA24 / 25 / 11 | $107k / C3+G1+S3 / STRA1+TOMA3 / 76 / 10 |
| KawattaTaido | s0 | $19k / C10+G2+S2 / MELO1+STRA37+WHEA21 / 27 / 10 | $36k / C10+G2+S2 / MELO1+STRA37+TOMA8+WHEA15 / 25 / 11 | $63k / C10+G2+S2 / STRA37+TOMA13+WHEA11 / 25 / 12 | $106k / C9+G2 / TOMA5 / 75 / 11 |
| 🐚seek inspiration🐚 | s1 | $20k / C11+G2+S2 / MELO1+STRA34+WHEA25 / 25 / 10 | $37k / C11+G2+S2 / MELO1+STRA34+TOMA8+WHEA17 / 25 / 12 | $62k / C11+G2+S2 / STRA34+TOMA15+WHEA11 / 25 / 12 | $104k / C7+G2 / TOMA6 / 72 / 11 |
| 吃白饭的大肥鱼 | s0 | $12k / C8+G6+S4 / MELO6+STRA16+TOMA6+WHEA29 / 25 / 9 | $30k / C8+G6+S4 / MELO6+STRA34+TOMA8+WHEA9 / 25 / 9 | $42k / C8+G6+S4 / CARR4+MELO5+STRA24+TOMA8+WHEA16 / 25 / 10 | $102k / C8+G1+S1 / CARR1+STRA17+WHEA4 / 60 / 12 |
| Vadim Vasilenko | s1 | $15k / C10+G9+S3 / STRA22+TOMA5+WHEA26 / 25 / 11 | $39k / C10+G9+S3 / STRA25+TOMA9+WHEA19 / 25 / 11 | $58k / C10+G9+S3 / STRA16+TOMA12+WHEA25 / 25 / 11 | $108k / C10+G7 / STRA3+TOMA3+WHEA2 / 62 / 10 |
| TheEggman | s0 | $15k / C7+G8+S3 / CARR6+STRA29+TOMA1+WHEA21 / 25 / 10 | $37k / C7+G8+S3 / CARR13+STRA29+TOMA6+WHEA9 / 25 / 11 | $58k / C7+G7+S3 / CARR7+STRA21+TOMA10+WHEA20 / 25 / 11 | $104k / C7+G4 / TOMA3+WHEA3 / 71 / 9 |
| ymg_aq | s1 | $14k / C8+G4+S3 / CARR10+STRA32+TOMA2+WHEA14 / 27 / 11 | $31k / C8+G4+S3 / CARR9+STRA35+TOMA3+WHEA12 / 26 / 11 | $58k / C9+G4+S3 / CARR12+STRA27+TOMA9+WHEA11 / 25 / 11 | $103k / C9+G4+S3 / STRA3+TOMA3+WHEA3 / 68 / 10 |
| Kaggledew Valley 🏆 | s0 | $16k / C13+G2+S2 / MELO8+STRA38+TOMA5+WHEA7 / 25 / 9 | $38k / C13+G2+S2 / MELO8+STRA43+TOMA5+WHEA1 / 26 / 8 | $82k / C14+G2+S2 / MELO2+STRA39+TOMA5+WHEA4 / 32 / 12 | $174k / C12+G2+S1 / STRA6 / 77 / 11 |
| THIRD FARM CLUB | s1 | $15k / C13+G3+S3 / CARR2+MELO4+STRA39+TOMA3+WHEA8 / 25 / 8 | $25k / C13+G3+S3 / MELO3+STRA39+TOMA4+WHEA10 / 25 / 9 | $87k / C14+G3+S2 / CARR1+MELO3+STRA36+TOMA5+WHEA11 / 25 / 10 | $171k / C14+G2 / STRA1+TOMA1+WHEA1 / 78 / 11 |
| THIRD FARM CLUB | s0 | $14k / C6+G9+S3 / CARR4+MELO4+STRA29+TOMA2+WHEA18 / 25 / 10 | $29k / C6+G9+S3 / CARR5+MELO4+STRA31+TOMA5+WHEA12 / 25 / 11 | $55k / C6+G9+S3 / CARR5+MELO2+STRA27+TOMA8+WHEA15 / 25 / 10 | $122k / C6+G8 / STRA7+TOMA3 / 71 / 11 |
| 吃白饭的大肥鱼 | s1 | $14k / C13+G5+S3 / MELO5+STRA22+TOMA6+WHEA21 / 25 / 9 | $30k / C13+G5+S4 / MELO5+STRA27+TOMA15+WHEA6 / 25 / 9 | $57k / C13+G5+S4 / CARR8+MELO5+STRA17+TOMA20+WHEA3 / 25 / 10 | $114k / C12 / CARR1+STRA5+TOMA2+WHEA1 / 73 / 13 |
| mtmr_s1 | s0 | $8k / C15+G3+S3 / MELO2+STRA21+TOMA24+WHEA24 / 8 / 12 | $33k / C15+G4+S3 / CARR2+MELO2+STRA21+TOMA24+WHEA26 / 2 / 11 | $54k / C15+G4+S3 / MELO5+STRA12+TOMA38+WHEA18 / 4 / 12 | $104k / C15+G4 / CARR4+TOMA14 / 46 / 11 |
| Unknown Mother-Goo | s1 | $17k / C15+S3 / STRA12+TOMA16+WHEA29 / 25 / 12 | $46k / C15+S3 / STRA12+TOMA21+WHEA24 / 25 / 11 | $69k / C15+S3 / STRA4+TOMA22+WHEA29 / 27 / 11 | $103k / C15 / TOMA1 / 80 / 10 |
| SpaTaro | s0 | $19k / C9+S3 / CARR9+STRA32+WHEA22 / 25 / 10 | $36k / C9+S3 / CARR13+STRA36+WHEA14 / 25 / 10 | $57k / C9+S3 / CARR16+STRA31+WHEA15 / 26 / 10 | $83k / C8+S2 / STRA4 / 78 / 9 |
| offhand | s1 | $20k / C8+G3+S6 / STRA33+WHEA24 / 25 / 9 | $34k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $52k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $80k / C8+G3+S6 / - / 82 / 8 |
| ymg_aq | s0 | $17k / C9+G3+S3 / CARR10+STRA17+TOMA6+WHEA25 / 27 / 11 | $36k / C9+G4+S3 / CARR13+STRA20+TOMA11+WHEA15 / 25 / 11 | $45k / C9+G4+S3 / CARR17+STRA12+TOMA16+WHEA14 / 25 / 10 | $73k / C9+G4+S3 / CARR2+STRA3+TOMA5 / 68 / 11 |
| Majkel1337 | s1 | $20k / C9+G4+S3 / CARR11+MELO1+STRA15+TOMA5+WHEA26 / 25 / 11 | $39k / C9+G4+S3 / CARR16+STRA14+TOMA13+WHEA16 / 25 / 11 | $47k / C9+G4+S3 / CARR15+STRA5+TOMA24+WHEA15 / 25 / 11 | $78k / C7+G4 / TOMA10+WHEA6 / 62 / 10 |
| 吃白饭的大肥鱼 | s0 | $13k / C9+G1+S12 / MELO6+STRA22+TOMA2+WHEA23 / 25 / 10 | $41k / C9+G1+S13 / CARR2+MELO6+STRA26+TOMA4+WHEA14 / 25 / 12 | $68k / C9+G1+S13 / CARR11+MELO5+STRA16+TOMA4+WHEA16 / 25 / 10 | $104k / C3+G1+S4 / CARR1+STRA4+WHEA3 / 75 / 12 |
| ymg_aq | s1 | $15k / C10+G1+S11 / CARR2+MELO1+STRA27+TOMA1+WHEA21 / 26 / 11 | $48k / C10+G1+S11 / CARR8+STRA27+TOMA2+WHEA15 / 26 / 11 | $73k / C10+G1+S11 / CARR12+STRA19+TOMA4+WHEA17 / 25 / 11 | $105k / C8+G1+S3 / - / 76 / 10 |
| dqvide | s0 | $13k / C10+S3 / MELO8+STRA34+WHEA15 / 29 / 10 | $24k / C10+S3 / MELO6+STRA33+WHEA18 / 29 / 9 | $39k / C10+S3 / STRA33+WHEA24 / 29 / 12 | $99k / C10+S3 / WHEA1 / 67 / 8 |
| DECEM | s1 | $14k / C8+G9+S3 / STRA32+TOMA3+WHEA20 / 25 / 11 | $40k / C8+G9+S3 / STRA35+TOMA5+WHEA15 / 25 / 11 | $66k / C8+G9+S3 / STRA25+TOMA12+WHEA18 / 25 / 11 | $130k / C8+G8 / STRA3+TOMA4+WHEA1 / 63 / 10 |
| xxxx0314 | s0 | $20k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $40k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $61k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $106k / C9+G3+S5 / - / 82 / 11 |
| Unknown Mother-Goo | s1 | $13k / C12+G2+S3 / STRA32+TOMA1+WHEA25 / 25 / 11 | $41k / C12+G2+S3 / STRA40+TOMA3+WHEA14 / 26 / 11 | $70k / C12+G2+S3 / STRA31+TOMA3+WHEA24 / 25 / 11 | $117k / C10+G2 / STRA8 / 75 / 11 |
| mtmr_s1 | s0 | $8k / C5+G9+S3 / CARR51+MELO4+STRA21+WHEA4 / 3 / 12 | $24k / C5+G9+S3 / CARR12+MELO8+STRA11+TOMA19+WHEA33 / 0 / 11 | $31k / C5+G9+S5 / CARR4+MELO8+STRA5+TOMA19+WHEA42 / 1 / 12 | $80k / C5+G9+S2 / CARR4+WHEA2 / 62 / 12 |
| 吃白饭的大肥鱼 | s1 | $14k / C8+G7+S4 / CARR23+MELO1+STRA10+TOMA7+WHEA15 / 25 / 10 | $28k / C8+G7+S4 / CARR11+MELO1+STRA5+TOMA13+WHEA26 / 25 / 10 | $33k / C7+G7+S11 / CARR19+STRA3+TOMA13+WHEA13 / 26 / 11 | $83k / C3+G7+S11 / CARR2+STRA2 / 66 / 11 |

## 4. 我们自己的农场画像

| 队伍 | 座位 | d12 金钱/畜群/作物/空地块/雇工 | d16 金钱/畜群/作物/空地块/雇工 | d20 金钱/畜群/作物/空地块/雇工 | d29 金钱/畜群/作物/空地块/雇工 |
|---|---|---|---|---|---|
| ReD_MooN_rise | s0 | $14k / C6+S17 / STRA33+WHEA24 / 19 / 11 | $36k / C6+S17 / STRA33+WHEA25 / 19 / 12 | $82k / C6+S17 / STRA33+WHEA25 / 18 / 14 | $178k / C6+S17 / - / 74 / 12 |
| Orange | s1 | $18k / G3 / CARR20+STRA4+WHEA12 / 61 / 9 | $24k / G3 / STRA4+WHEA9 / 84 / 9 | $28k / G3 / CARR10+STRA2+WHEA10 / 75 / 9 | $42k / G3 / STRA2+WHEA2 / 93 / 9 |
| ReD_MooN_rise | s0 | $21k / C8+G3+S6 / STRA33+WHEA24 / 25 / 9 | $37k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $55k / C8+G3+S6 / STRA33+TOMA10+WHEA25 / 14 / 12 | $150k / C8+G3+S6 / TOMA10 / 70 / 13 |
| ayutin tin | s1 | $8k / C8+S6 / MELO12+STRA39+WHEA7 / 28 / 12 | $14k / C8+S6 / MELO12+STRA39 / 35 / 12 | $21k / C8+S6 / MELO12+STRA39+WHEA2 / 32 / 12 | $55k / C8+S6 / WHEA1 / 84 / 12 |
| ReD_MooN_rise | s0 | $14k / C6+S17 / STRA33+WHEA24 / 19 / 11 | $32k / C6+S17 / STRA33+WHEA25 / 19 / 12 | $67k / C6+S17 / STRA33+WHEA25 / 18 / 14 | $128k / C6+S17 / - / 74 / 12 |
| lmq | s1 | $9k / C8+S6 / MELO6+STRA32+WHEA4 / 44 / 12 | $16k / C8+S6 / MELO10+STRA39+WHEA4 / 33 / 12 | $27k / C8+S6 / MELO9+STRA39+WHEA1 / 36 / 12 | $52k / C8+S5 / STRA6+WHEA1 / 57 / 12 |
| Veeranuch Leelalai | s0 | $2k / C10+S5 / MELO13+STRA39+WHEA2 / 31 / 12 | $9k / C10+S5 / CARR1+MELO13+STRA39+WHEA3 / 29 / 12 | $19k / C8+S5 / CARR11+MELO4+STRA39+WHEA1 / 30 / 11 | $52k / S5 / - / 49 / 3 |
| ReD_MooN_rise | s1 | $20k / C6+G5+S6 / STRA33+WHEA24 / 25 / 9 | $35k / C6+G5+S6 / STRA33+WHEA25 / 25 / 11 | $59k / C6+G5+S6 / STRA33+WHEA25 / 25 / 11 | $118k / C6+G4+S6 / - / 82 / 11 |
| Sahaj Deep Singh | s0 | $6k / C8+S4 / MELO14+STRA35+WHEA13 / 26 / 10 | $11k / C8+S4 / MELO14+STRA35+WHEA13 / 26 / 13 | $20k / C8+S4 / MELO2+STRA32+WHEA26 / 28 / 14 | $31k / C9+S4 / WHEA1 / 81 / 10 |
| ReD_MooN_rise | s1 | $20k / C6+G5+S6 / STRA33+WHEA24 / 25 / 9 | $29k / C6+G5+S6 / STRA33+WHEA25 / 25 / 11 | $37k / C6+G5+S6 / CARR2+STRA33+WHEA23 / 25 / 11 | $67k / C6+G4+S6 / - / 82 / 11 |
| ReD_MooN_rise | s0 | $20k / C6+G2+S9 / STRA33+WHEA24 / 25 / 9 | $37k / C6+G2+S9 / STRA33+WHEA25 / 25 / 11 | $53k / C6+G2+S9 / CARR3+STRA33+WHEA22 / 25 / 11 | $83k / C6+G2+S8 / - / 81 / 11 |
| Adil Munawar | s1 | $6k / C8+S4 / MELO14+STRA35+WHEA13 / 26 / 10 | $19k / C8+S4 / MELO14+STRA35+WHEA13 / 26 / 13 | $32k / C8+S4 / MELO2+STRA32+WHEA26 / 28 / 14 | $45k / C9+S4 / WHEA1 / 81 / 10 |
| Wiz | s0 | $8k / C5+S9 / MELO4+STRA31+WHEA12 / 37 / 9 | $14k / C5+S9 / MELO4+STRA31+WHEA20 / 29 / 11 | $21k / C5+S9 / MELO4+STRA29+WHEA20 / 29 / 11 | $44k / C5+S9 / WHEA8 / 59 / 6 |
| ReD_MooN_rise | s1 | $19k / C6+G5+S6 / STRA33+WHEA24 / 25 / 9 | $29k / C6+G5+S6 / STRA33+WHEA25 / 25 / 11 | $40k / C6+G5+S6 / STRA33+WHEA25 / 25 / 11 | $70k / C6+G5+S6 / - / 81 / 11 |
| ReD_MooN_rise | s0 | $20k / C6+G2+S9 / STRA33+WHEA24 / 25 / 9 | $38k / C6+G2+S9 / STRA33+WHEA25 / 25 / 11 | $60k / C6+G2+S9 / STRA33+TOMA10+WHEA25 / 15 / 12 | $132k / C6+G2+S9 / TOMA10 / 71 / 13 |
| R3ddrag0n | s1 | $9k / C8+S4 / MELO14+STRA36+WHEA13 / 25 / 10 | $21k / C8+S4 / MELO14+STRA36+WHEA13 / 25 / 13 | $47k / C8+S4 / MELO2+STRA33+WHEA26 / 27 / 14 | $98k / C8+S5 / CARR1 / 81 / 10 |
| JZ | s0 | $14k / C8+S6 / STRA42+WHEA19 / 25 / 11 | $23k / C8+S6 / STRA42+WHEA19 / 25 / 11 | $41k / C8+S6 / STRA42+WHEA17 / 27 / 11 | $82k / C8+S6 / WHEA1 / 74 / 8 |
| ReD_MooN_rise | s1 | $21k / C8+G3+S6 / STRA33+WHEA24 / 25 / 9 | $37k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $57k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $99k / C8+G2+S6 / - / 82 / 11 |
| hikarinosenshi | s0 | $14k / C6+G3+S4 / STRA31+WHEA24 / 27 / 9 | $26k / C6+G3+S4 / STRA31+WHEA25 / 27 / 11 | $45k / C6+G3+S4 / STRA31+WHEA25 / 27 / 12 | $88k / C6+G3+S2 / - / 79 / 9 |
| ReD_MooN_rise | s1 | $20k / C8+G3+S6 / STRA33+WHEA24 / 25 / 9 | $39k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $62k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $118k / C8+G3+S6 / - / 82 / 11 |
| coke lu | s0 | $14k / C8+G3+S6 / STRA33+WHEA24 / 25 / 9 | $24k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $40k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $65k / C8+G3+S6 / - / 81 / 11 |
| ReD_MooN_rise | s1 | $17k / C6+G5+S6 / STRA33+WHEA24 / 25 / 9 | $26k / C6+G5+S6 / CARR3+STRA33+WHEA22 / 25 / 11 | $43k / C6+G5+S6 / CARR2+STRA33+WHEA23 / 25 / 11 | $78k / C6+G4+S6 / - / 81 / 11 |
| Pardheev Krishna | s0 | $19k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $44k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $64k / C9+G3+S5 / STRA33+TOMA10+WHEA25 / 15 / 12 | $121k / C9+G3+S5 / TOMA10 / 71 / 13 |
| ReD_MooN_rise | s1 | $20k / C12+S5 / STRA33+WHEA24 / 25 / 9 | $44k / C12+S5 / STRA33+WHEA25 / 25 / 11 | $67k / C12+S5 / STRA33+TOMA10+WHEA25 / 15 / 12 | $129k / C12+S5 / TOMA10 / 72 / 13 |
| Pat | s0 | $19k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $41k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $64k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $109k / C9+G3+S5 / - / 81 / 11 |
| ReD_MooN_rise | s1 | $20k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $41k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $66k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $110k / C9+G3+S5 / - / 80 / 11 |
| democatXamer | s0 | $19k / C8+G3+S6 / STRA33+WHEA23 / 26 / 9 | $39k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $53k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $78k / C8+G3+S6 / - / 82 / 11 |
| ReD_MooN_rise | s1 | $20k / C8+S9 / STRA33+WHEA24 / 25 / 9 | $38k / C8+S9 / STRA33+WHEA25 / 25 / 11 | $56k / C8+S9 / STRA33+WHEA25 / 25 / 11 | $81k / C8+S9 / - / 82 / 11 |
| ReD_MooN_rise | s0 | $19k / C6+S11 / STRA33+WHEA24 / 25 / 9 | $36k / C6+S11 / STRA33+WHEA25 / 25 / 11 | $56k / C6+S11 / CARR11+STRA33+WHEA14 / 25 / 12 | $103k / C6+S11 / - / 82 / 11 |
| rishavsaigal | s1 | $16k / C6+S10 / STRA33+WHEA21 / 28 / 9 | $34k / C6+S10 / STRA33+WHEA25 / 25 / 12 | $52k / C6+S10 / STRA33+WHEA25 / 25 / 12 | $94k / C6+S10 / - / 81 / 11 |
| John Gates | s0 | $19k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $39k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $59k / C9+G3+S5 / STRA33+TOMA10+WHEA25 / 15 / 12 | $127k / C9+G3+S5 / TOMA10 / 72 / 13 |
| ReD_MooN_rise | s1 | $20k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $39k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $59k / C9+G3+S5 / STRA33+TOMA10+WHEA25 / 15 / 12 | $128k / C9+G3+S5 / TOMA10 / 71 / 13 |
| ReD_MooN_rise | s0 | $17k / C6+G5+S6 / STRA33+WHEA24 / 25 / 9 | $26k / C6+G5+S6 / CARR6+STRA33+WHEA19 / 25 / 11 | $41k / C6+G5+S6 / CARR2+STRA33+WHEA23 / 25 / 11 | $78k / C6+G4+S6 / - / 80 / 11 |
| Dinesh Makireddy 7 | s1 | $17k / C6+G5+S6 / STRA33+WHEA24 / 25 / 9 | $26k / C6+G5+S6 / CARR6+STRA33+WHEA19 / 25 / 11 | $41k / C6+G5+S6 / CARR2+STRA33+WHEA23 / 25 / 11 | $78k / C6+G4+S6 / - / 82 / 11 |
| ReD_MooN_rise | s0 | $20k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $39k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $56k / C9+G3+S5 / STRA33+TOMA10+WHEA25 / 15 / 12 | $110k / C9+G3+S5 / TOMA10 / 72 / 13 |
| Auto Fermers | s1 | $20k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $39k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $56k / C9+G3+S5 / STRA33+TOMA10+WHEA25 / 15 / 12 | $112k / C9+G3+S5 / TOMA10 / 71 / 13 |
| Dzmitry Pihulski | s0 | $19k / C10+G3+S4 / STRA33+WHEA24 / 25 / 9 | $39k / C10+G3+S4 / STRA33+WHEA25 / 25 / 11 | $67k / C10+G3+S4 / STRA33+WHEA25 / 25 / 11 | $131k / C10+G3+S4 / - / 82 / 11 |
| ReD_MooN_rise | s1 | $20k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $39k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $67k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $128k / C9+G3+S5 / - / 82 / 11 |
| Odyssey | s0 | $18k / C8+G3+S6 / STRA33+WHEA24 / 25 / 9 | $32k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $46k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $77k / C8+G3+S6 / - / 82 / 11 |
| ReD_MooN_rise | s1 | $19k / C8+G3+S6 / STRA33+WHEA24 / 25 / 9 | $32k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $48k / C8+G3+S6 / STRA33+WHEA25 / 25 / 11 | $78k / C8+G3+S6 / - / 82 / 11 |
| liu bo | s0 | $19k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $38k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $57k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $100k / C9+G3+S5 / - / 82 / 11 |
| ReD_MooN_rise | s1 | $20k / C9+G3+S5 / STRA33+WHEA24 / 25 / 9 | $39k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $58k / C9+G3+S5 / STRA33+WHEA25 / 25 / 11 | $102k / C9+G3+S5 / - / 82 / 11 |
| ReD_MooN_rise | s0 | $18k / C6+S11 / STRA33+WHEA24 / 25 / 9 | $38k / C6+S11 / STRA33+WHEA25 / 25 / 11 | $61k / C6+S11 / STRA33+WHEA25 / 25 / 12 | $86k / C6+S11 / - / 81 / 11 |
| chandora | s1 | $18k / C6+S11 / STRA33+WHEA23 / 26 / 9 | $38k / C6+S11 / STRA33+WHEA25 / 25 / 11 | $60k / C6+S11 / STRA33+WHEA25 / 25 / 12 | $86k / C6+S11 / - / 82 / 11 |
| ReD_MooN_rise | s0 | $18k / C6+G2+S9 / STRA33+WHEA24 / 25 / 9 | $34k / C6+G2+S9 / STRA33+WHEA25 / 25 / 11 | $59k / C6+G2+S9 / STRA33+WHEA25 / 25 / 11 | $112k / C6+G2+S9 / - / 80 / 11 |
| Zain96 | s1 | $14k / C5+G4+S9 / CARR4+STRA19+WHEA31 / 27 / 11 | $33k / C4+G4+S9 / STRA20+WHEA32 / 27 / 11 | $57k / C3+G4+S8 / STRA10+TOMA4+WHEA41 / 28 / 12 | $102k / C2+G4+S4 / STRA2+TOMA4+WHEA4 / 71 / 10 |
| ReD_MooN_rise | s0 | $12k / C8+S15 / STRA33+WHEA24 / 19 / 11 | $30k / C8+S15 / STRA33+WHEA25 / 19 / 12 | $59k / C8+S15 / STRA33+WHEA25 / 17 / 12 | $82k / C8+S15 / - / 72 / 11 |
| Georgi Kanev | s1 | $12k / C8+S15 / STRA33+WHEA24 / 19 / 11 | $30k / C8+S15 / STRA33+WHEA25 / 18 / 12 | $59k / C8+S15 / STRA33+WHEA25 / 18 / 12 | $82k / C8+S15 / - / 74 / 11 |

## 5. 种子/牲畜购买与雇工（整局累计）

| 队伍 | 座位 | BUY_SEED | BUY_ANIMAL | HIRE 次数 |
|---|---|---|---|---|
| Majkel1337 | s0 | WHEAT 182, CARROT 33, STRAWBERRY 29, MELON 15, TOMATO 7 | SHEEP 13, GOOSE 7, COW 5 | 295 |
| Vadim Vasilenko | s1 | WHEAT 180, STRAWBERRY 42, MELON 31, CARROT 18, TOMATO 12 | SHEEP 15, COW 9, GOOSE 6 | 310 |
| Vadim Vasilenko | s0 | WHEAT 145, CARROT 90, STRAWBERRY 40, MELON 25, TOMATO 10 | COW 17, SHEEP 17, GOOSE 4 | 305 |
| THIRD FARM CLUB | s1 | WHEAT 140, CARROT 70, STRAWBERRY 35, MELON 18, TOMATO 12 | SHEEP 12, COW 7, GOOSE 2 | 263 |
| mtmr_s1 | s0 | WHEAT 179, CARROT 71, STRAWBERRY 26, MELON 25, TOMATO 17 | COW 16, SHEEP 14 | 314 |
| Vadim Vasilenko | s1 | WHEAT 175, CARROT 48, STRAWBERRY 37, MELON 25, TOMATO 15 | COW 20, SHEEP 17, GOOSE 2 | 306 |
| KawattaTaido | s0 | WHEAT 125, CARROT 50, STRAWBERRY 39, MELON 13, TOMATO 13 | COW 10, SHEEP 2, GOOSE 2 | 286 |
| 🐚seek inspiration🐚 | s1 | WHEAT 129, CARROT 52, STRAWBERRY 34, TOMATO 15, MELON 13 | COW 11, SHEEP 2, GOOSE 2 | 286 |
| 吃白饭的大肥鱼 | s0 | WHEAT 130, STRAWBERRY 45, CARROT 20, MELON 16, TOMATO 8 | COW 9, GOOSE 6, SHEEP 4 | 286 |
| Vadim Vasilenko | s1 | WHEAT 179, STRAWBERRY 38, MELON 30, TOMATO 15, CARROT 12 | COW 13, GOOSE 9, SHEEP 3 | 306 |
| TheEggman | s0 | WHEAT 160, CARROT 76, STRAWBERRY 30, TOMATO 13, MELON 10 | GOOSE 8, COW 7, SHEEP 3 | 282 |
| ymg_aq | s1 | WHEAT 140, CARROT 67, STRAWBERRY 46, MELON 21, TOMATO 11 | COW 9, GOOSE 4, SHEEP 3 | 288 |
| Kaggledew Valley 🏆 | s0 | WHEAT 92, STRAWBERRY 44, MELON 16, TOMATO 6, CARROT 3 | COW 14, SHEEP 2, GOOSE 2 | 267 |
| THIRD FARM CLUB | s1 | WHEAT 140, STRAWBERRY 43, MELON 13, CARROT 11, TOMATO 5 | COW 14, SHEEP 3, GOOSE 3 | 268 |
| THIRD FARM CLUB | s0 | WHEAT 150, CARROT 58, STRAWBERRY 42, MELON 14, TOMATO 8 | GOOSE 9, COW 6, SHEEP 3 | 263 |
| 吃白饭的大肥鱼 | s1 | WHEAT 101, CARROT 60, STRAWBERRY 28, TOMATO 20, MELON 15 | COW 13, GOOSE 5, SHEEP 4 | 285 |
| mtmr_s1 | s0 | WHEAT 163, CARROT 60, TOMATO 38, STRAWBERRY 22, MELON 21 | COW 15, GOOSE 4, SHEEP 3 | 315 |
| Unknown Mother-Goo | s1 | WHEAT 226, TOMATO 24, CARROT 14, MELON 13, STRAWBERRY 13 | COW 19, SHEEP 3 | 293 |
| SpaTaro | s0 | WHEAT 186, CARROT 71, STRAWBERRY 39, MELON 18 | COW 13, SHEEP 3 | 270 |
| offhand | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | COW 8, SHEEP 6, GOOSE 3 | 260 |
| ymg_aq | s0 | WHEAT 150, CARROT 98, STRAWBERRY 35, MELON 21, TOMATO 20 | COW 9, GOOSE 5, SHEEP 3 | 280 |
| Majkel1337 | s1 | WHEAT 162, CARROT 97, TOMATO 27, MELON 25, STRAWBERRY 18 | COW 13, SHEEP 7, GOOSE 4 | 302 |
| 吃白饭的大肥鱼 | s0 | WHEAT 139, CARROT 71, STRAWBERRY 27, MELON 15, TOMATO 4 | SHEEP 13, COW 9, GOOSE 1 | 297 |
| ymg_aq | s1 | WHEAT 134, CARROT 64, STRAWBERRY 38, MELON 21, TOMATO 6 | SHEEP 11, COW 10, GOOSE 1 | 286 |
| dqvide | s0 | WHEAT 135, STRAWBERRY 34, MELON 20, CARROT 14 | COW 10, SHEEP 4 | 277 |
| DECEM | s1 | WHEAT 170, STRAWBERRY 54, MELON 26, TOMATO 12, CARROT 9 | COW 11, GOOSE 9, SHEEP 3 | 294 |
| xxxx0314 | s0 | WHEAT 163, STRAWBERRY 33, CARROT 31, MELON 12 | COW 9, SHEEP 5, GOOSE 3 | 265 |
| Unknown Mother-Goo | s1 | WHEAT 176, STRAWBERRY 54, CARROT 14, MELON 11, TOMATO 3 | COW 13, SHEEP 3, GOOSE 2 | 291 |
| mtmr_s1 | s0 | WHEAT 208, CARROT 143, MELON 21, STRAWBERRY 21, TOMATO 19 | GOOSE 12, COW 7, SHEEP 5 | 305 |
| 吃白饭的大肥鱼 | s1 | WHEAT 140, CARROT 95, STRAWBERRY 25, TOMATO 13, MELON 11 | SHEEP 18, COW 8, GOOSE 7 | 293 |
| ReD_MooN_rise | s0 | WHEAT 166, STRAWBERRY 33, CARROT 28, MELON 12 | SHEEP 17, COW 6 | 301 |
| Orange | s1 | CARROT 100, WHEAT 70, MELON 17, STRAWBERRY 6 | GOOSE 3 | 235 |
| ReD_MooN_rise | s0 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12, TOMATO 10 | COW 8, SHEEP 6, GOOSE 3 | 283 |
| ayutin tin | s1 | WHEAT 61, STRAWBERRY 39, MELON 24 | COW 8, SHEEP 6 | 307 |
| ReD_MooN_rise | s0 | WHEAT 166, STRAWBERRY 33, CARROT 28, MELON 12 | SHEEP 17, COW 6 | 304 |
| lmq | s1 | WHEAT 66, STRAWBERRY 44, MELON 21 | COW 8, SHEEP 6 | 306 |
| Veeranuch Leelalai | s0 | CARROT 47, STRAWBERRY 41, MELON 20, WHEAT 18 | COW 24, SHEEP 5 | 285 |
| ReD_MooN_rise | s1 | WHEAT 146, CARROT 60, STRAWBERRY 33, MELON 12 | COW 6, SHEEP 6, GOOSE 5 | 265 |
| Sahaj Deep Singh | s0 | WHEAT 148, STRAWBERRY 37, MELON 19 | COW 9, SHEEP 4 | 262 |
| ReD_MooN_rise | s1 | WHEAT 138, CARROT 68, STRAWBERRY 33, MELON 12 | COW 6, SHEEP 6, GOOSE 5 | 266 |
| ReD_MooN_rise | s0 | WHEAT 140, CARROT 66, STRAWBERRY 33, MELON 12 | SHEEP 9, COW 6, GOOSE 2 | 265 |
| Adil Munawar | s1 | WHEAT 148, STRAWBERRY 37, MELON 19 | COW 9, SHEEP 4 | 262 |
| Wiz | s0 | WHEAT 133, STRAWBERRY 32, MELON 11 | SHEEP 10, COW 6 | 247 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | COW 6, SHEEP 6, GOOSE 5 | 267 |
| ReD_MooN_rise | s0 | WHEAT 159, CARROT 48, STRAWBERRY 33, MELON 12, TOMATO 10 | SHEEP 9, COW 6, GOOSE 2 | 284 |
| R3ddrag0n | s1 | WHEAT 143, STRAWBERRY 37, MELON 20, CARROT 14 | COW 8, SHEEP 5 | 262 |
| JZ | s0 | WHEAT 103, CARROT 50, STRAWBERRY 44, MELON 12 | COW 8, SHEEP 7 | 277 |
| ReD_MooN_rise | s1 | WHEAT 145, CARROT 56, STRAWBERRY 33, MELON 12 | COW 8, SHEEP 6, GOOSE 3 | 266 |
| hikarinosenshi | s0 | WHEAT 197, STRAWBERRY 33, MELON 12, CARROT 9 | COW 9, SHEEP 5, GOOSE 4 | 280 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | COW 8, SHEEP 6, GOOSE 3 | 265 |
| coke lu | s0 | WHEAT 163, STRAWBERRY 33, CARROT 31, MELON 12 | COW 8, SHEEP 6, GOOSE 3 | 265 |
| ReD_MooN_rise | s1 | WHEAT 135, CARROT 71, STRAWBERRY 33, MELON 12 | COW 6, SHEEP 6, GOOSE 5 | 268 |
| Pardheev Krishna | s0 | WHEAT 163, STRAWBERRY 33, CARROT 31, MELON 12, TOMATO 10 | COW 9, SHEEP 5, GOOSE 3 | 282 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12, TOMATO 10 | COW 12, SHEEP 5 | 284 |
| Pat | s0 | WHEAT 163, STRAWBERRY 33, CARROT 31, MELON 12 | COW 9, SHEEP 5, GOOSE 3 | 267 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | COW 9, SHEEP 5, GOOSE 3 | 267 |
| democatXamer | s0 | WHEAT 162, STRAWBERRY 33, CARROT 31, MELON 12 | COW 8, SHEEP 6, GOOSE 3 | 267 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | SHEEP 9, COW 8 | 267 |
| ReD_MooN_rise | s0 | WHEAT 135, CARROT 71, STRAWBERRY 33, MELON 12 | SHEEP 11, COW 6 | 281 |
| rishavsaigal | s1 | WHEAT 160, STRAWBERRY 34, CARROT 31, MELON 12 | SHEEP 11, COW 6 | 283 |
| John Gates | s0 | WHEAT 163, STRAWBERRY 33, CARROT 31, MELON 12, TOMATO 10 | COW 9, SHEEP 5, GOOSE 3 | 286 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12, TOMATO 10 | COW 9, SHEEP 5, GOOSE 3 | 284 |
| ReD_MooN_rise | s0 | WHEAT 135, CARROT 71, STRAWBERRY 33, MELON 12 | COW 6, SHEEP 6, GOOSE 5 | 267 |
| Dinesh Makireddy 7 | s1 | WHEAT 135, CARROT 71, STRAWBERRY 33, MELON 12 | COW 6, SHEEP 6, GOOSE 5 | 267 |
| ReD_MooN_rise | s0 | WHEAT 160, CARROT 47, STRAWBERRY 33, MELON 12, TOMATO 10 | COW 9, SHEEP 5, GOOSE 3 | 283 |
| Auto Fermers | s1 | WHEAT 159, CARROT 40, STRAWBERRY 33, MELON 12, TOMATO 10 | COW 9, SHEEP 5, GOOSE 3 | 283 |
| Dzmitry Pihulski | s0 | WHEAT 163, STRAWBERRY 33, CARROT 31, MELON 12 | COW 10, SHEEP 4, GOOSE 3 | 268 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | COW 9, SHEEP 5, GOOSE 3 | 268 |
| Odyssey | s0 | WHEAT 162, STRAWBERRY 33, CARROT 31, MELON 12 | COW 8, SHEEP 6, GOOSE 3 | 268 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | COW 8, SHEEP 6, GOOSE 3 | 268 |
| liu bo | s0 | WHEAT 162, STRAWBERRY 33, CARROT 31, MELON 12 | COW 9, SHEEP 5, GOOSE 3 | 267 |
| ReD_MooN_rise | s1 | WHEAT 164, STRAWBERRY 33, CARROT 31, MELON 12 | COW 9, SHEEP 5, GOOSE 3 | 267 |
| ReD_MooN_rise | s0 | WHEAT 166, STRAWBERRY 33, CARROT 28, MELON 12 | SHEEP 11, COW 6 | 282 |
| chandora | s1 | WHEAT 166, STRAWBERRY 33, CARROT 28, MELON 12 | SHEEP 11, COW 6 | 282 |
| ReD_MooN_rise | s0 | WHEAT 159, CARROT 48, STRAWBERRY 33, MELON 12 | SHEEP 9, COW 6, GOOSE 2 | 265 |
| Zain96 | s1 | WHEAT 277, STRAWBERRY 29, MELON 12, CARROT 4, TOMATO 4 | SHEEP 9, COW 5, GOOSE 4 | 286 |
| ReD_MooN_rise | s0 | WHEAT 159, CARROT 48, STRAWBERRY 33, MELON 12 | SHEEP 15, COW 8 | 291 |
| Georgi Kanev | s1 | WHEAT 158, CARROT 48, STRAWBERRY 33, MELON 12 | SHEEP 15, COW 8 | 291 |

## 6. 价格轨迹（每局该座位看到的报价，按天取均值）

`early` = 第 20-23 天，`late` = 第 26-29 天。

### 全体座位

| product | d8 | d12 | d16 | d20 | d22 | d24 | d26 | d27 | d28 | d29 | early 20-23 | late 26-29 | late-early |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TOMATO | 63 | 65 | 69 | 73 | 78 | 86 | 97 | 100 | 97 | 98 | 76 | 98 | +22 |
| CARROT | 37 | 39 | 42 | 45 | 47 | 49 | 50 | 51 | 51 | 50 | 46 | 50 | +5 |
| STRAWBERRY | 162 | 183 | 195 | 135 | 91 | 72 | 84 | 82 | 94 | 88 | 113 | 87 | -26 |
| MELON | 269 | 122 | 113 | 115 | 96 | 87 | 89 | 89 | 90 | 91 | 105 | 90 | -15 |
| WHEAT | 33 | 39 | 40 | 41 | 41 | 41 | 41 | 40 | 38 | 36 | 41 | 39 | -2 |
| EGG | 50 | 52 | 52 | 51 | 51 | 51 | 52 | 52 | 53 | 53 | 51 | 52 | +1 |
| MILK | 200 | 160 | 100 | 57 | 56 | 56 | 62 | 67 | 58 | 55 | 57 | 61 | +4 |
| WOOL | 184 | 159 | 98 | 85 | 82 | 83 | 85 | 91 | 85 | 78 | 83 | 85 | +2 |

### 仅我们（ReD_MooN_rise 所在局）

| product | d8 | d12 | d16 | d20 | d22 | d24 | d26 | d27 | d28 | d29 | early 20-23 | late 26-29 | late-early |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TOMATO | 63 | 65 | 69 | 74 | 82 | 96 | 116 | 120 | 117 | 120 | 78 | 118 | +40 |
| CARROT | 37 | 39 | 42 | 47 | 49 | 52 | 55 | 56 | 57 | 56 | 48 | 56 | +8 |
| STRAWBERRY | 162 | 182 | 199 | 137 | 80 | 63 | 69 | 58 | 72 | 63 | 109 | 65 | -43 |
| MELON | 269 | 98 | 102 | 108 | 87 | 84 | 87 | 88 | 90 | 92 | 97 | 89 | -8 |
| WHEAT | 32 | 39 | 41 | 42 | 42 | 42 | 41 | 41 | 39 | 38 | 42 | 40 | -2 |
| EGG | 51 | 52 | 53 | 53 | 53 | 53 | 53 | 54 | 54 | 55 | 53 | 54 | +1 |
| MILK | 198 | 142 | 69 | 50 | 58 | 58 | 61 | 70 | 63 | 58 | 54 | 63 | +10 |
| WOOL | 188 | 172 | 121 | 116 | 108 | 112 | 107 | 117 | 108 | 93 | 112 | 106 | -6 |

### 仅头部对局

| product | d8 | d12 | d16 | d20 | d22 | d24 | d26 | d27 | d28 | d29 | early 20-23 | late 26-29 | late-early |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TOMATO | 62 | 65 | 68 | 72 | 72 | 70 | 68 | 67 | 65 | 64 | 72 | 66 | -6 |
| CARROT | 37 | 39 | 41 | 42 | 43 | 44 | 43 | 42 | 42 | 40 | 43 | 42 | -1 |
| STRAWBERRY | 163 | 184 | 188 | 132 | 109 | 87 | 110 | 121 | 130 | 128 | 120 | 122 | +2 |
| MELON | 269 | 160 | 132 | 126 | 109 | 92 | 92 | 91 | 90 | 90 | 118 | 91 | -27 |
| WHEAT | 34 | 40 | 39 | 40 | 40 | 41 | 40 | 39 | 37 | 33 | 40 | 37 | -3 |
| EGG | 50 | 51 | 50 | 49 | 49 | 48 | 49 | 49 | 49 | 49 | 49 | 49 | +1 |
| MILK | 204 | 188 | 149 | 69 | 54 | 52 | 65 | 62 | 51 | 50 | 62 | 57 | -4 |
| WOOL | 178 | 139 | 60 | 34 | 41 | 38 | 51 | 51 | 48 | 54 | 37 | 51 | +14 |

