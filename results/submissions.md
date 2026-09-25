# 提交记录（scripts/submit.py 自动追加）

| 时间 | 版本 | 状态 | sha256(前16位) | 行数 | 说明 |
|---|---|---|---|---|---|
| 2026-09-22 23:44 | v25 | built | `d40d0619aca482ca` | 7016 | dry-run smoke of the new submit path (early-death fix already submitted as 56462261) |
| 2026-09-23 00:26 | v26 | built | `8d52c0f76eb3e290` | 7016 | V55 parity: V9_RACE_DEFAULT 40->41, _SR_MARGIN 4->8, _SR_HOURS (22,23)->(21,22,23); local H2H 75-25, panel 594->626/680 |
| 2026-09-23 00:53 | v26 | submitted | `8d52c0f76eb3e290` | 7016 | V55 parity: V9_RACE_DEFAULT 40->41, _SR_MARGIN 4->8, _SR_HOURS (22,23)->(21,22,23); local H2H 75-25, panel 594->626/680 |
| 2026-09-23 01:25 | v27 | built | `4af6b0bad0155bea` | 7123 | port public V56 layers EXP402 + EXP410; H2H 82W-6L-12T vs v26, panel 626->632/680 with margin gains |
| 2026-09-23 01:45 | v27 | submitted | `4af6b0bad0155bea` | 7123 | port public V56 layers EXP402 (cap late seed buys) + EXP410 (skip no-op fertilizer); H2H 82W-6L-12T vs v26, panel 626->632/680 |
| 2026-09-23 10:20 | v28 | built | `1ffa8782555cfa08` | 7374 | port public V57 counter-D mirror best-response + seedfloat + funding-order invariant; H2H 98W-2L vs v27, 151/160 vs our own past versions, panel 632->634/680 with margin gains; callback max 40.6->46.5ms |
| 2026-09-23 10:28 | v28 | submitted | `1ffa8782555cfa08` | 7374 | port public V57 counter-D mirror best-response + seedfloat + funding-order invariant; H2H 98W-2L vs v27, 151/160 vs our own past versions, panel 632->634/680, callback max 40.6->46.5ms |
| 2026-09-23 18:51 | v34 | submitted | `178ae0f727641cf4` | 7333 | adopt prvsiyan/kaggriculture-frontier (105v, re-run 09-23): 17-opponent panel 680/680 vs v28 634/680, worst margin +11 vs -1533; H2H vs v28 38-2 |
| 2026-09-24 12:37 | v35 | submitted | `946732c88a6485ad` | 7333 | 3 tuned constants from public LB-2700 agent on the same e410 base (_CA_MARGIN -5->-15, _OR2_SLOT_MARGIN 20->8, _V92_P_EVERY 3->2); n=500 H2H vs v34: 69.3% decided, z=+8.5 |
| 2026-09-24 13:40 | v36 | submitted | `29197d1404700684` | 7333 | market-race horizon 41->44 (the public LB-2700 agent's own round-2 value); vs v34 n=500 70.9% decided, vs herdsafe n=320 87.8->94.7% (CIs disjoint) |
| 2026-09-24 18:22 | v37 | submitted | `33ae48c1301ecedb` | 7665 | restore the early-death fix dropped when adopting the frontier: opening 20/15->10/5 keeps step-24 cash at $12-18 instead of $1. On v36's ladder replays 5/62 games (8.1%) hit the trigger and they are the 5 largest losses (-$30k to -$8k, $108,831 total); local v37-vs-v36 281W-19L=93.7%, vs herdsafe 303-17 unchanged (no regression) |
| 2026-09-24 20:28 | v37 | submitted | `33ae48c1301ecedb` | 7665 | re-roll of the identical v37 code: the previous run drew a 1301-mean field so it never entered the bracket where the early-death trigger fires, making the fix unverifiable; this is an independent draw |
| 2026-09-24 23:23 | v36 | submitted | `29197d1404700684` | 7333 | re-submit v36 (race44) on a fresh draw: window is 2 and the evicted slot held 1679.7, so the floor stays at v37b's 2256.2; this measures v36's draw variance against v37's |
