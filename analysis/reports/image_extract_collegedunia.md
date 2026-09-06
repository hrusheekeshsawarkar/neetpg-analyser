# CollegeDunia image extraction — pilot results

Script: `analysis/extract_images_collegedunia.py`  
Run: `python analysis/extract_images_collegedunia.py --years 2016-2024`

## Totals (2016–2024)

| Metric | Count |
|--------|------:|
| Clinical images found in PDFs | 453 |
| Questions linked to ≥1 image | **415** |
| Of which matched `merged_questions` (source=collegedunia) | 301 |
| Linked but no merge row (mostly 2021/2023 not in merge) | 114 |
| Image-cue stems with no recoverable figure | 52 |
| Orphan clinical images (unassigned) | 32 |
| Image files on disk | 421 (~42 MB) |

Per year (linked / cue-unlinked / clinical):

| Year | Linked | Cue unlinked | Clinical imgs |
|------|-------:|-------------:|--------------:|
| 2016 | 23 | 6 | 30 |
| 2017 | 23 | 6 | 30 |
| 2018 | 30 | 5 | 31 |
| 2019 | 52 | 1 | 53 |
| 2020 | 67 | 8 | 70 |
| 2021 | 43 | 7 | 49 |
| 2022 | 68 | 7 | 76 |
| 2023 | 46 | 9 | 49 |
| 2024 | 63 | 3 | 65 |

## Outputs

- Images: `analysis/data/question_images/collegedunia/{year}/qNNN_pNNN_*.{jpg,png}`
- Manifest: `analysis/data/image_extract_collegedunia.json`
- Visual QA: `analysis/reports/image_extract_collegedunia_review.html` (cue-unlinked first)

```bash
# open review (needs relative paths to ../data/...)
open analysis/reports/image_extract_collegedunia_review.html
```

## Spot-check (manual)

Correct pairings observed:

- 2022 Q1 — embryology diagram with marker **A**
- 2022 Q3 — histology (islet / pancreas)
- 2022 Q4 — oxygen / non-rebreather mask
- 2024 Q1 — knee X-ray (fracture question)
- 2024 Q10 — UGIE endoscopic image
- 2018 Q209 — pectoralis major muscle figure

## Known gaps / false cues

- Some “cue unlinked” are **false cues** (e.g. option text contains `X-ray`, or “given below” for refraction prescriptions) — figure never existed in the PDF.
- Some real image stems still miss figures that the coaching PDF never embedded.
- Cross-page figures (stem at page bottom → image at next page top) are handled via carry-forward; a few edge cases remain in the orphan count.
- `merged_questions` currently lacks CollegeDunia **2021** and **2023** rows, so those links are `linked_no_merge_row` until those years are merged.

## Next (after you QA the HTML)

1. Optionally: `python analysis/extract_images_collegedunia.py --years 2016-2024 --patch-merged` to write `images[]` onto merge rows.
2. Mirror images into `web/public/` (or Supabase storage) and show them in `QuestionCard` instead of “Image missing”.
3. Extend the same extractor to Nishant / fmgeplans.
