# Nishant image extraction — QA brief

Script: `analysis/extract_images_nishant.py`  
Review: `analysis/reports/image_extract_nishant_review.html`

```bash
open analysis/reports/image_extract_nishant_review.html
```

## Results (this run)

| Metric | Count |
|--------|------:|
| Linked questions | **239** |
| Cue unlinked | 34 |
| Clinical images seen | 326 |
| Matched into merge (mostly AIPGMEE 2018) | 31 |
| Orphan images | 85 |

Per PDF: see console / `image_extract_nishant.json` summary.

## How to judge

1. Open the HTML — **cue-unlinked** cards first (red).
2. Spot-check green **linked** cards: does the figure match the stem?
3. Watch for footer logos / banners wrongly kept (should be rare after filter).

After you confirm, we can `--patch-merged` (for rows that exist) and continue to fmgeplans / FirstRanker.
