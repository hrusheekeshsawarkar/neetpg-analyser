# FirstRanker image extraction — QA brief

Script: `analysis/extract_images_firstranker.py`  
Review: `analysis/reports/image_extract_firstranker_review.html`

```bash
open analysis/reports/image_extract_firstranker_review.html
```

## Results

| Metric | Count |
|--------|------:|
| Linked | **252** |
| Cue unlinked | 40 |
| Matched merge | 72 |
| Clinical images seen | 326 |

| PDF | Linked |
|-----|-------:|
| 2018 | 45 |
| 2020 | 60 |
| 2022 | 64 |
| 2023 | 36 |
| 2024 s1 | 37 |
| 2024 s2 | 10 |

## Scope

- 2018, 2020, 2022–2024 (shift 1 & 2)
- **2021 skipped** (full-page scans; no selectable stems)
- Watermark strips (`www.FirstRanker.com`, 240×34) filtered

## After you confirm

```bash
python analysis/extract_images_firstranker.py --years 2018,2020,2022-2024 --patch-merged
python analysis/sync/seed_supabase.py --local-only
```
