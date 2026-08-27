# Extraction gaps — local PDFs vs dataset

Generated from inventory of `neet-pg-papers/` vs `analysis/data/q_*.json`.

## Still to extract (high value)

| PDF | Why | Suggested command |
|-----|-----|-------------------|
| `nishant-bhushan/AIPGMEE-2017.pdf` | Not in merge; text OK (`Question N` format) | `python3 analysis/extract_remaining.py --aipgmee-gap` |
| `nishant-bhushan/AIPGMEE-2018.pdf` | Not in merge; same format as 2012–16 | same |
| `nishant-bhushan/NEETPG-2019.pdf` | Not in merge; numbered MCQs | `python3 analysis/extract_remaining.py --nishant-2019-2020` |
| `nishant-bhushan/NEETPG-2020.pdf` | Not in merge; numbered MCQs | same |
| `neetfmgeplans/NEETPG-2024.pdf` | Standalone year PDF not parsed (thin / image-heavy) | `python3 analysis/extract_remaining.py --fmge-2024-2025` |
| `neetfmgeplans/NEETPG-2025.pdf` | Same | same |
| `collegedunia/neetpg-2021.pdf` | Not in bulk extract | extend `extract_bulk.py` |
| `collegedunia/neetpg-2023.pdf` | Not in bulk extract | extend `extract_bulk.py` |
| `collegedunia/neetpg-2025.pdf` | Tiny / stub (~38KB) | skip or replace source |
| `collegehai/*.pdf` | Downloaded but no dedicated JSON | low priority (overlap with Nishant) |
| `aglasem/NEETPG-2021.pdf` | 27KB stub | skip |

## Partial

| PDF | Status |
|-----|--------|
| Nishant / CollegeHai **2024 Shift 2** | Only ~27 public recall Qs in `q_2024_shift2.json` — full paper not available as text |
| CollegeDunia **2015** | PDF not present in folder |

## Already covered

Nishant 2021–2023 + 2024 Shift 1 + 2025; AIPGMEE 2012–2016; CollegeDunia bulk 2010–2014/2016–2020/2022 + 2024; fmgeplans yearwise + chapterwise + 2022/2023 year PDFs.

## Gap extract results (latest run)

| Source | Extracted |
|--------|----------:|
| AIPGMEE 2017–2018 | 454 |
| Nishant NEETPG 2019–2020 | 718 |
| fmgeplans standalone 2024/2025 | 0 (parser found no `Ques No` blocks — image-heavy / different layout) |

After merge: **~18.4k** unique questions (was ~17.3k).

```bash
python3 analysis/extract_remaining.py --gaps
python3 analysis/clean_merge.py
python3 analysis/classify_topics.py
python3 analysis/classify_llm.py --workers 12 --batch-size 3
python3 analysis/remap_subjects.py
python3 analysis/consolidate_topics.py
python3 analysis/predict_priority.py
python3 analysis/analyze.py
python3 analysis/analyze_extra.py
python3 analysis/generate_subject_packs.py
```
