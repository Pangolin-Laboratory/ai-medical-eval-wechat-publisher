# Data contract and source authority

## Authority order

Use the first applicable source for each field:

1. Explicit instructions in the current user request.
2. Approved expert-review outputs or the named final report.
3. Structured analysis JSON generated from approved outputs.
4. Source workbooks and technical reports.
5. Existing charts, only as a cross-check.

Do not infer a model version from another specialty when the source is uncertain. Record the naming source and use the track the user designated as authoritative.

## Normalized 2D input

The reference renderer expects two UTF-8 JSON files.

### Analysis summary

Required top-level objects:

- `population`: `products`, `departments`, `runs_per_product_per_department`, `clinical_outputs`, `technical_outputs`.
- `products`: one row per product with `product`, `model`, `label`, `clinical`, `technical`, `total`, `overall_rank`, `clinical_rank`, `technical_rank`, `dim_means`, specialty scores, stability, ability, duration, and gate counts.
- `gates`: total `n`, `pass_a`, `pass_b`, plus `by_department` counts.
- `clinical_specialty_means` and `technical_specialty_means`.
- `correlations`, `technical_quadrant_means`, `duration`, and `largest_rank_gaps`.
- `rank_evolution`: ordered months, pool sizes, scope notes, correlations, product rows, and missing ranks as null.
- `clinical_dimension_labels`.

For every product, verify `clinical + technical = total` within rounding tolerance and ranks are unique and sequential.

### Radar data

Required fields:

- `scope`, `source`, `selection`, and `dimension_denominators`.
- `rows`, sorted by `composite_pct`, with `label`, `composite_raw`, `composite_pct`, `dimension_means`, and `dimension_pct`.

Recalculate `dimension_pct = dimension_means × 100` when normalized means are 0–1. If raw dimension means use heterogeneous denominators, divide by the matching denominator before multiplying by 100.

## Safety math

- Unit defaults to product × specialty × run output sample.
- Pass rate = passed outputs / total outputs.
- Multiple red-line triggers in the same output count once at the same gate level.
- Never display missing safety data as 100% pass; show “暂无数据”.
- Product-level failure claims require an explicit rule such as “any run failed”.

## Historical comparison

- Store missing participation as null and display “—”; never impute zero or connect nonexistent points.
- Record each month's specialty scope and score construction.
- If methods changed, compare rank evolution only and place the method-break note on the card.
- Recalculate reported Spearman values on the intersection of products observed in both months.

## Audit note

The validation note should list source files, extraction date, product count, full ranking, gate n/N, specialty means, radar selection, correlations, historical pool sizes, and image checks. Mark uncertainties instead of resolving them by guesswork.
