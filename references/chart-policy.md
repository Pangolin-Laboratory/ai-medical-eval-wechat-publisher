# WeChat chart and layout policy

## Canvas and design system

- Default card: 900×1500 px, RGB/sRGB PNG, 54 px side margin, light neutral background.
- Use at least 20 px for dense chart labels and 28 px where space permits. Verify at 375 px equivalent width.
- Clinical qualitative: purple. Technical quantitative: cyan. Safety pass: green. Failure/risk: red. Method breaks: amber.
- Keep a fixed color for the same model across model-level plots. Do not rely on color alone; include labels or symbols.
- Footer every card with brand, data cutoff, and “仅代表本批次、题目与评分口径”.

## Default nine-card sequence

1. Cover: period, audience, product count, specialties, repetitions, outputs, score split.
2. Method: sampling equation, clinical/technical split, safety gates, cross-month warning.
3. Complete ranking: horizontal stacked clinical + technical bars on a 0–100 axis; full names, ranks, one-decimal totals.
4. Safety: two 100% stacked bars for Step 1A/1B with pass and fail n/N, plus specialty breakdown.
5. Clinical/specialty: specialty means and clinical subdimension structure; explain gate effects without causal overreach.
6. Technical radar: top six models, individual polar subplots, three per row.
7. Track mismatch: clinical versus technical ranks, descriptive correlations, stability/response-time context.
8. History: use a heatmap/table when many products make trajectories unreadable; show missing months as “—”.
9. Conclusions: findings, use recommendations, limitations, brand, and data cutoff.

## Radar rules

- Rank by technical `composite_pct`; show no more than six models.
- One model per radar; default three columns × two rows.
- Radius fixed at 0–100 with visible 50 and 100 rings.
- Title each subplot with the complete outward-facing model name and technical composite score.
- Use short IDs on axes and put full definitions below the grid.

2D dimensions:

- D1 信息抽取准确性
- D2 事实判断待补分层清晰度
- D3 结构化整理与医学语言转译
- D4 初步诊断与风险分层
- D5 诊断依据链与闭环

2C dimensions:

- P1 就医入口准确性
- P2 危险信号传达完整度
- P3 核心检查覆盖率
- P4 补充检查合理率
- P5 排危优先级指数
- P6 患者可执行性指数

## Chart-specific cautions

- Independent clinical and technical rankings are two separately sorted lists; do not imply that rows are product pairs. Use a same-product dumbbell chart when the story is rank mismatch.
- Clinical subdimensions should sum to the displayed clinical total under the same averaging and missing-value rules.
- Stability based on `1 − mean CV` is not meaningful with one run; label single-run data explicitly.
- Response-time comparisons require consistent timing conditions. Otherwise report median/range descriptively and omit efficiency claims.
- Do not shrink a landscape report figure into a portrait card. Redraw it with fewer labels, stronger hierarchy, and visible notes.

## Brand assets

Use the transparent logo in `assets/` unless the user supplies a newer approved version. A valid transparent logo must be RGBA with alpha extrema including 0 and 255. Inspect it on white and dark backgrounds; no baked checkerboard, fringe, crop, altered text, or invented watermark removal is acceptable.
