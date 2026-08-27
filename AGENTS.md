# AGENTS.md — NEET PG Analyzer

> Multi-agent orchestration guide for the NEET PG medical exam analysis project.

## Project Overview

**What**: Extract NEET PG / AIPGMEE past papers from PDFs → classify by 19 taught MBBS subjects / topics / concepts → frequency + importance + subject revision packs.

**Goal**: High-yield revision priorities for PG aspirants (memory-based sources only).

**Workspace**: `/Users/hrusheekeshsawarkar/Projects/side-projects/neetpg-analyser`

## Current state (Aug 2026)

- **~17.3k** unique questions, years **2010–2025**
- **~90%** LLM-labeled (`label_source=llm`); residual unlabeled ~100–150
- Subjects remapped to taught list via `mbbs_taxonomy.py` (Medicine / Surgery / OBG / …)
- Reports: `next_exam_priorities.md`, `subjects/*.md`, drift / due / overlaps
- Plots under `analysis/plots/`
- Active LLM: set `LLM_PROVIDER` in `.env` (`bht` recommended for bulk; OpenAI `gpt-5.6-luna` for speed/cost; OpenRouter free is slow)

## Agent roles

| Agent | Use for |
|-------|---------|
| **Sisyphus** (default) | Orchestration, pipeline, implementation |
| **explore** | Grep / data patterns |
| **librarian** | New PDF sources, syllabus validation |
| **oracle** | Extraction failures, API choice |
| **visual-engineering** | Plot / UI polish |
| **deep** | Full re-extract of a bad year |

## Pipeline

```
extract_* → clean_merge → classify_topics → classify_llm
  → remap_subjects → consolidate_topics
  → predict_priority → analyze → analyze_extra → generate_subject_packs
```

### Key scripts

| Script | Role |
|--------|------|
| `extract_remaining.py --gaps` | Nishant AIPGMEE 2017–18, NEETPG 2019–20, fmge 2024–25 |
| `extract_bulk.py` | CollegeDunia + fmgeplans yearwise |
| `classify_llm.py --workers N --batch-size 2–4` | Concurrent labeling; SIGTERM saves checkpoint+merged |
| `mbbs_taxonomy.py` | Canonical subjects + syllabus topics |
| `analyze_extra.py` | Drift, ask-type, overlaps, due brief |

## Extraction gaps

Authoritative list: **`analysis/reports/extraction_gaps.md`**.

High-value not yet in merge (until `--gaps` run):

- Nishant `AIPGMEE-2017.pdf`, `AIPGMEE-2018.pdf`
- Nishant `NEETPG-2019.pdf`, `NEETPG-2020.pdf`
- fmgeplans `NEETPG-2024.pdf`, `NEETPG-2025.pdf` (may be thin)
- CollegeDunia 2021 / 2023 (not in bulk)
- CollegeHai PDFs (overlap; low priority)
- 2024 Shift 2: **partial only** (~27 Qs)

## Conventions

### Subjects (exact)

```
Anatomy, Biochemistry, Physiology, Pharmacology, Microbiology, Pathology,
Community Medicine, Forensic Medicine, Ophthalmology, ENT, Medicine, Surgery,
OBG, Pediatrics, Anaesthesia, Orthopedics, Radiology, Psychiatry, Dermatology
```

### Files

- Scripts: `analysis/*.py`
- Data: `analysis/data/*.json`
- Plots: `analysis/plots/*`
- Reports: `analysis/reports/*`
- Secrets: `.env` only (gitignored)

### Topics

- Prefer syllabus topics from `SUBJECT_TOPICS` in `mbbs_taxonomy.py`
- Never invent topic `"General"` — empty = unlabeled
- After LLM: always `remap_subjects` + `consolidate_topics`

## LLM notes

- Prefer **small batches (2–4)** + many workers for BHT / OpenAI
- Don’t trust raw JSON — use `extract_json` / try-except
- `LLM_PROVIDER` is exclusive (no silent Gemini fallback unless re-enabled)
- Checkpoint every few batches to `llm_classify_checkpoint.json` **and** `merged_questions.json`

## Quality targets

| Metric | Approx now | Target |
|--------|------------|--------|
| Questions | 17k+ | keep growing via gaps |
| LLM label rate | ~90% | >95% |
| Unknown subject | ~1% | <1% |
| Unique topics | ~4k (noisy) | <500 via consolidation |
| Subject packs | 19/19 | 19/19 |

## Next actions for agents

1. Run `extract_remaining.py --gaps` → merge → classify new rows  
2. Finish residual `needs_label` (~100–150)  
3. Tighten topic consolidation (force syllabus-only where safe)  
4. Keep reports regenerated after any merge  
5. Do **not** commit `.env` or API keys  
