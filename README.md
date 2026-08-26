# NEET PG Analyzer

Analyze NEET PG past papers (2021–2025) — extract questions, classify by subject/topic/year, and generate frequency analysis visualizations.

## 📁 Project Structure

```
neetpg-analyser/
├── neet-pg-papers/          # Source PDFs from coaching sites
│   ├── nishant-bhushan/     # Dr. Nishant Bhushan compilations (best format)
│   ├── collegedunia/         # CollegeDunia PDFs
│   ├── neetfmgeplans/        # neetfmgeplans.com compilations
│   └── collegehai/           # CollegeHai references & Google Drive links
├── analysis/
│   ├── extract_papers.py     # PDF text extraction
│   ├── extract_llm.py        # LLM-assisted extraction (2021-2023)
│   ├── extract_2024_25.py    # 2024-2025 extraction
│   ├── topic_rules.py        # Subject → topic keyword mapping (1300+ keywords)
│   ├── classify_topics.py    # Apply keyword rules to classify topics
│   ├── clean_merge.py        # Normalize subjects, deduplicate, merge
│   ├── analyze.py            # Frequency analysis + all visualizations
│   └── data/
│       ├── merged_questions.json   # Final dataset (842 questions)
│       ├── analysis_ready.csv      # CSV for analysis
│       └── *.json                  # Per-year extracted questions
└── analysis/plots/
    ├── neetpg_analysis.png   # 4-panel: bar chart, grouped bar, heatmap, Pareto
    ├── neetpg_trends.png     # Topic frequency trend lines by year
    ├── neetpg_pie.png        # Subject distribution pie chart
    ├── year_subject_matrix.csv
    └── topic_frequency.csv   # All 156 topics ranked
```

## 📰 Paper Sources

Papers are **memory-based compilations** from coaching institutes. NBE does not officially release papers.

| Source | Years | Notes |
|--------|-------|-------|
| Dr. Nishant Bhushan | 2012–2025 | Best structured format (Subject/Topic/Sub-Topic/Question/Options/Answer) |
| CollegeDunia | 2010–2025 | Numbered format, subject headers, less structured |
| neetfmgeplans.com | 2018–2025 | Chapterwise (23MB) and Yearwise (23MB) compilations |
| CollegeHai | Various | Google Drive links in `collegehai/google-drive-links.txt` |

**Disclaimer**: These are recalled memory-based papers. Questions may not be 100% accurate. Use for practice and pattern analysis, not as a substitute for official answer keys.

## 🧪 Setup

```bash
# Create venv
python3 -m venv venv && source venv/bin/activate

# Install dependencies
pip install pdfplumber matplotlib seaborn pandas numpy

# Paper PDFs already downloaded in neet-pg-papers/
```

## 🚀 Extraction Pipeline

Run in order — each step builds on the previous:

```bash
# Step 1: Extract 2021-2023 (Nishant Bhushan structured format)
python3 analysis/extract_llm.py

# Step 2: Extract 2024-2025
python3 analysis/extract_2024_25.py

# Step 3: Clean, normalize subjects, deduplicate
python3 analysis/clean_merge.py

# Step 4: Classify topics using keyword rules (1300+ keywords)
python3 analysis/classify_topics.py

# Step 5: Generate all visualizations
python3 analysis/analyze.py
```

## 📊 What Gets Generated

| Plot | Description |
|------|-------------|
| `neetpg_analysis.png` | 4-panel: questions per subject, subject by year, topic heatmap, Pareto chart |
| `neetpg_trends.png` | Line chart of top 10 topic frequencies over years |
| `neetpg_pie.png` | Subject distribution pie chart |
| `year_subject_matrix.csv` | Raw count matrix: year × subject |
| `topic_frequency.csv` | All topics ranked by frequency |

## 📈 Current Dataset Stats

- **842 questions** across 2021–2025
- **21 subjects** classified
- **156 unique topics** (after keyword classification)
- **Note**: 2021, 2024, 2025 papers use image/case-based question formats that required keyword-based topic inference rather than structured metadata

## ⚠️ Known Limitations

1. **2024 Shift 2 not extracted** — LLM parsing repeatedly timed out on that PDF format
2. **2021/2024/2025 topic coverage is partial** — These PDFs have image-based/case-presentation formats that don't extract clean question metadata. Topic classification relies on keyword matching from question text. Expect ~46% of questions still tagged "General" (image-based/case scenarios without disease-specific keywords)
3. **Year coverage is incomplete** — Oldest papers (2010–2020) were downloaded but extraction quality was poor. Focus is on 2021–2025 (current exam pattern)
4. **No official papers** — All sources are memory-based compilations. Answer keys may differ between sources.

## 🔧 Improving Accuracy

### To get more questions classified:
Edit `analysis/topic_rules.py` — add disease/drug/topic-specific keywords to the `TOPIC_RULES` dictionary. The format is simple:

```python
"Subject Name": {
    "Topic Name": ["keyword1", "keyword2", "disease name", "drug name"],
}
```

Then re-run:
```bash
python3 analysis/classify_topics.py
python3 analysis/analyze.py
```

### To re-extract 2024 Shift 2:
Try directly with pdfplumber or use Gemini 2.5 Flash API (best for PDF OCR per benchmarks).

## 🧪 API Keys Used

Set keys via environment variables (never commit real keys):

| API | Used For | Env var |
|-----|----------|---------|
| BHT LLM | Question classification, extraction | `BHT_LLM_KEY` |
| OpenAI | (optional) Extraction if BHT fails | `OPENAI_API_KEY` |
| Gemini | (optional) Vision-based PDF parsing | `GEMINI_API_KEY` |

## 📊 Key Findings (2021-2025)

| Subject | Count | % |
|---------|-------|---|
| General Surgery | 137 | 18.8% |
| General Medicine | 97 | 13.3% |
| Microbiology | 82 | 11.3% |
| Pharmacology | 48 | 6.6% |
| O&G (Obstetrics + Gynaecology) | 42 | 5.8% |
| Pathology | 40 | 5.5% |
| Anatomy | 38 | 5.2% |
| Physiology | 35 | 4.8% |

**Clinical subjects (Surgery + Medicine + O&G) = 38%** of all questions — the high-yield core.

**Pareto**: ~49 topics cover 80% of questions (from 156 total topics).

## 📄 License

For educational and practice purposes only. Question accuracy depends on the source compilation.