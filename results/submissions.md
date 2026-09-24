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
