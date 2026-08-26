# AGENTS.md — NEET PG Analyzer

> Multi-agent orchestration guide for the NEET PG medical exam analysis project.

## Project Overview

**What**: Extract NEET PG past paper questions from PDFs → classify by subject/topic/year → generate frequency analysis visualizations (bar charts, heatmaps, Pareto charts, trend lines).

**Goal**: Identify high-yield topics that repeatedly appear across years, so medical PG aspirants can prioritize their revision.

## Agent Roles

| Agent | Responsibility | When to Use |
|-------|---------------|-------------|
| **Sisyphus** (this session) | Orchestration, delegation, pipeline building, implementation | All phases — coordinates everything |
| **explore** | Find patterns in extracted question data, grep for keywords | When exploring what topics exist in the dataset |
| **librarian** | Find additional paper sources, medical NEET PG resources, best practices for medical data analysis | When finding new PDF sources or validating topic lists |
| **oracle** | Architecture decisions, debugging extraction failures, choosing LLM APIs | When extraction consistently fails, or architecture needs review |
| **visual-engineering** | Design/impl improvements to plots | If user wants richer visualizations |
| **deep** | Deep re-extraction of specific years with better prompting | When a specific year's data is poor and needs a full redo |

## Current Agent: **Sisyphus** (this session)

**Context**: `/Users/hrusheekeshsawarkar/Projects/side-projects/neetpg-analyser`

**Current state**:
- Pipeline built and running: `extract_llm.py` → `extract_2024_25.py` → `clean_merge.py` → `classify_topics.py` → `analyze.py`
- 842 questions extracted across 2021-2025
- 21 subjects classified, 156 topics identified (many still "General" for image-based questions)
- 3 visualizations generated in `analysis/plots/`
- BHT LLM API used for extraction and classification (key via env / local config)

## Pipeline Phases

### Phase 1: Paper Download (done)
- Source PDFs from 4 coaching sites (Nishant Bhushan, CollegeDunia, neetfmgeplans, CollegeHai)
- 37 PDFs downloaded (~365MB) in `neet-pg-papers/`
- **Note**: CollegeHai uses Google Drive links — not directly downloadable

### Phase 2: Extraction (partially done)
- `extract_llm.py`: Nishant Bhushan 2021-2023 → 606 questions (clean format)
- `extract_2024_25.py`: 2024-2025 → ~236 questions (format varies by shift)
- **Gap**: 2024 Shift 2 not extracted (LLM timeout on that format)
- **Gap**: CollegeDunia 2022/2023 not re-extracted (prior LLM calls timed out)

### Phase 3: Cleaning & Merging (done)
- `clean_merge.py`: Normalizes subject names, deduplicates across sources
- `classify_topics.py`: Keyword-based topic classification (1300+ keywords across 21 subjects, ~40 topic categories)
- **Gap**: 385/842 questions still tagged "General" (image-based/case-scenario questions from 2021, 2024, 2025 papers where question text doesn't contain disease-specific keywords)

### Phase 4: Analysis & Visualization (done)
- `analyze.py`: Generates 4-panel analysis PNG, trend lines PNG, pie chart PNG, plus CSV matrices
- Current visualizations are functional but basic

## What's Working

✅ PDF download from multiple sources  
✅ Question extraction from structured Nishant Bhushan PDFs  
✅ Subject normalization (fixes OCR noise like "Pharmacology d" → "Pharmacology")  
✅ Keyword-based topic classification across 21 subjects  
✅ Bar chart, grouped bar, heatmap, Pareto, trend lines, pie chart  
✅ CSVs for year×subject matrix and topic frequency rankings  

## What's Incomplete / Known Issues

| Issue | Impact | Fix Approach |
|-------|--------|--------------|
| 2024 Shift 2 not extracted | ~100 questions missing from 2024 | Re-extract with pdfplumber + LLM, or use Gemini 2.5 Flash (best for PDFs) |
| 385/842 questions tagged "General" | Topic analysis incomplete for 2021, 2024, 2025 | Add more keywords to `topic_rules.py`, or use LLM to classify remaining "General" questions in batch |
| CollegeDunia 2022/2023 extraction attempted but failed | ~200 questions potentially missed | Re-extract with fresh LLM calls or keyword-based parser |
| No data for 2010-2020 | Historical trends unavailable | Old papers exist but extraction quality was poor — requires dedicated effort |
| "Virology", "Parasitology", "Systemic Bacteriology" topics bleeding into subject names | Minor noise in topic distribution | The `topic_clean` field picked up topic names as if they were subjects — fix in `clean_merge.py` normalization |

## How to Continue

### If continuing the extraction gap (2024 Shift 2, CollegeDunia):
```
# Test extraction on the specific PDF first
python3 -c "
import pdfplumber
with pdfplumber.open('neet-pg-papers/nishant-bhushan/NEETPG-2024-shift2.pdf') as pdf:
    print(f'Pages: {len(pdf.pages)}')
    t = pdf.pages[0].extract_text()
    print(t[:500] if t else 'NO TEXT')
"
# If has text → use pdfplumber regex extraction
# If image-based → use LLM API (Gemini 2.5 Flash recommended per benchmarks) or OpenAI with vision
```

### If fixing "General" topic problem:
```
# See which questions are still General
python3 -c "
import json
from collections import Counter
with open('analysis/data/merged_questions.json') as f:
    qs = json.load(f)
gen = [q for q in qs if q.get('topic_clean','').lower() == 'general']
by_subj = Counter(q['subject_clean'] for q in gen)
for s, c in sorted(by_subj.items(), key=lambda x: -x[1]):
    print(f'{s}: {c}')
"
# Add disease/drug/topic keywords to topic_rules.py → re-run classify_topics.py
```

### If re-generating visualizations:
```bash
python3 analysis/analyze.py
# Outputs go to analysis/plots/
```

## Conventions

### Subject Naming (use these exact forms in `topic_rules.py` and `clean_merge.py`):
```
Anatomy, Physiology, Biochemistry, Pathology, Pharmacology, Microbiology,
Forensic Medicine, Community Medicine, General Medicine, Dermatology,
Psychiatry, General Surgery, Orthopaedics, Anaesthesia, Obstetrics,
Gynaecology, Paediatrics, ENT, Ophthalmology, Radiology, Emergency Medicine
```

### File Naming:
- `*.py` in `analysis/` — extraction, cleaning, analysis scripts
- `*.json` in `analysis/data/` — extracted question datasets
- `*.csv` in `analysis/plots/` — analysis output matrices
- `*.png` in `analysis/plots/` — visualization images

### Topic Hierarchy:
- `topic_clean` — specific topic within subject (e.g., "Cardiology", "Virology", "Fractures")
- NOT "General" or "Unknown" — those indicate unclassified questions
- `subtopic` field exists in Nishant Bhushan format but not consistently populated

## LLM API Configuration

### BHT LLM (currently used)
```python
LLM_API = "https://llmapi-key.ris.bht-berlin.de/v1/chat/completions"
LLM_KEY = os.environ["BHT_LLM_KEY"]  # do not commit real keys
MODEL = "bht/large"  # context: 196k tokens, output: 4k tokens
```

### OpenAI (available as backup)
API Key: set `OPENAI_API_KEY` in the environment (do not commit real keys)
Best for: Structured JSON extraction from extracted text

### Gemini 2.5 Flash (recommended for future PDF work)
API Key: set `GEMINI_API_KEY` in the environment (do not commit real keys)
Best for: **Native PDF parsing via vision** (per benchmarks: 87-96% accuracy on scanned docs, vs 47% with text-only extraction). Also has 1M token context window.

### Model Selection for PDF Extraction (per research):
- **Gemini 2.5 Pro/Flash** — best overall for PDF OCR + extraction (benchmarks show native image processing > Docling/text extraction)
- **Claude Sonnet 4** — best factual accuracy for text-heavy PDFs
- **BHT/large** — used currently, works for text extraction, struggles with JSON-only output
- **GPT-4o** — good but aggressive downscaling (768px) hurts accuracy on small text

## Quality Benchmarks to Hit

| Metric | Current | Target |
|--------|---------|--------|
| Questions extracted | 842 | 3000+ (5 years × 600 questions) |
| Subject coverage | 21/21 | 21/21 (all subjects present) |
| Topic classification rate | 54% | 85%+ |
| "General" topic rate | 46% | <15% |
| Years with full extraction | 2022, 2023 | 2021-2025 all complete |

## Notes for Future Sessions

- **Don't trust LLM JSON output** — always wrap in try/except, find JSON boundaries manually with `find('[')` / `find(']')`
- **Batches > ~20 questions** tend to get thinking tags inserted → break into smaller batches
- **Medical subject classification is deterministic** — keyword matching is more reliable than LLM for subject (LLM sometimes returns subject names as "topics")
- **Gemini 2.5 is the future** — for any new PDF work, use the Gemini API with PDF upload directly (no intermediate OCR step needed)
- **The Pareto principle applies** — ~49 topics cover 80% of questions. Focus keyword expansion on those first.