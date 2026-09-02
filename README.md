# NEET PG Analyzer

Extract NEET PG / AIPGMEE past-paper questions from coaching PDFs → classify by **19 taught MBBS subjects** + topics/concepts → frequency analysis, importance scoring, and subject-wise revision packs.

> Memory-based sources only. Not official NBE papers.

## Dataset (current)

| Metric | Value |
|--------|------:|
| Unique questions | ~17,300+ (2010–2025) |
| LLM-labeled | ~90% |
| Subjects | 19 (Medicine, Surgery, OBG, …) |
| Subject packs | `analysis/reports/subjects/` |

See `analysis/reports/extraction_gaps.md` for PDFs still not extracted.

## Project layout

```
neetpg-analyser/
├── .env.example                 # API keys (copy → .env, never commit)
├── docs/PRODUCT.md              # Live product spec
├── docs/RAG.md                  # Hybrid retrieval design
├── web/                         # Next.js + Supabase front end
├── neet-pg-papers/              # Source PDFs
└── analysis/
    ├── sync/                    # schema.sql, seed + embed → Supabase
    ├── extract_*.py
    ├── … pipeline scripts …
    ├── data/merged_questions.json
    ├── plots/
    └── reports/
```

### Live product (web)

See [`docs/PRODUCT.md`](docs/PRODUCT.md) and [`web/README.md`](web/README.md).

```bash
python3 analysis/sync/seed_supabase.py --local-only
cd web && npm install && npm run dev
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip pdfplumber pandas matplotlib seaborn numpy
cp .env.example .env   # set BHT_LLM_KEY and/or OPENAI / OPENROUTER / GEMINI
```

`LLM_PROVIDER` in `.env` is **exclusive** (`bht` | `openai` | `openrouter`).

## Pipeline

```bash
# Extract (as needed)
python3 analysis/extract_llm.py
python3 analysis/extract_bulk.py
python3 analysis/extract_2024_25.py
python3 analysis/extract_remaining.py --gaps   # 2017–20 Nishant + fmge 24/25

# Merge + classify
python3 analysis/clean_merge.py
python3 analysis/classify_topics.py
python3 analysis/classify_llm.py --workers 12 --batch-size 3
python3 analysis/remap_subjects.py
python3 analysis/consolidate_topics.py

# Reports + plots
python3 analysis/predict_priority.py
python3 analysis/analyze.py
python3 analysis/analyze_extra.py
python3 analysis/generate_subject_packs.py
```

## Outputs

| Path | Description |
|------|-------------|
| `reports/next_exam_priorities.md` | Must / High / due topics |
| `reports/subject_revision_packs.md` | Index of 19 subject packs |
| `reports/topic_year_drift.md` | Rising vs falling topics |
| `reports/topics_due_for_return.md` | High-recurrence gaps |
| `reports/topic_overlaps.md` | Co-occurring topics |
| `reports/extraction_gaps.md` | Unextracted local PDFs |
| `plots/neetpg_analysis.png` | Subjects, heatmap, Pareto |
| `plots/topic_importance.png` | Importance ranking |
| `plots/ask_type_by_subject.png` | Diagnosis / DOC / etc. |
| `plots/topic_year_drift.png` | Share change recent vs older |

## Taught MBBS subjects

Anatomy, Biochemistry, Physiology, Pharmacology, Microbiology, Pathology, Community Medicine, Forensic Medicine, Ophthalmology, ENT, **Medicine**, **Surgery**, **OBG**, Pediatrics, Anaesthesia, Orthopedics, Radiology, Psychiatry, Dermatology.

## Known limits

1. **2024 Shift 2** — only ~27 public recall questions (full paper not available as text)
2. **Topic spellings** — LLM free-text still creates many variants; `consolidate_topics.py` helps but is not perfect
3. **AIPGMEE year counts** can over-extract explanations — filtered but still heavy for 2013–2016
4. No official papers — memory compilations only

## License

Educational / practice use only.
