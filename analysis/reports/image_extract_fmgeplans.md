# fmgeplans image extraction — QA brief

Script: `analysis/extract_images_fmgeplans.py`  
Review: `analysis/reports/image_extract_fmgeplans_review.html`

```bash
open analysis/reports/image_extract_fmgeplans_review.html
```

## Results (this run — column-aware fix)

Yearwise previously mixed **left/right columns** (wrong stem + wrong figure). Fixed by:
- column-scoped text extraction
- image cues only from the stem (not Ans explanations)
- orphans only attach to same-column stems that already cue an image

| Metric | Count |
|--------|------:|
| Linked | **632** |
| Cue unlinked | **131** (was ~737) |
| In merge | 233 |

| PDF | Linked |
|-----|-------:|
| NEETPG-2022 | 63 |
| NEETPG-2023 | 36 |
| NEETPG-2024 | 18 |
| NEETPG-2025 | 110 |
| NEETPG-yearwise | 405 |

Verified fixes for reported mismatches:
- 2019 Q13 p556 → mandible / foramen stem (not hand/nerve bleed)
- 2019 Q161 p568 → Epley maneuver stem (not landfill bleed)

**QA tip:** Reload the review HTML and spot-check yearwise again; per-year PrepLadder cards were already mostly fine.

## Scope

- Per-year PrepLadder PDFs: `NEETPG-2022` … `NEETPG-2025`
- MEDINK compilation: `NEETPG-yearwise.pdf` (2-column, year headers)

Chapterwise skipped for this pass (weaker layout signal).

## After you confirm

```bash
python analysis/extract_images_fmgeplans.py --all --patch-merged
python analysis/sync/seed_supabase.py --local-only
```
