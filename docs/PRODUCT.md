# NEET PG Priorities — Product Spec

Working name: **neetpg-priorities** (rename anytime).

## Vision

Turn the offline NEET PG analysis pipeline into a live product aspirants actually use:

1. **Dated priority list** for the next exam (screenshot-friendly, shareable).
2. **Subject / topic visualizations** — frequency, due-for-return, overlaps, drift.
3. **Hybrid similar-question explorer** (Google-gated) over ~18k memory-based past questions.
4. **Subject revision pack downloads** (Google-gated) for usage signal.

Audience: NEET PG / AIPGMEE aspirants. Almost no good open tooling exists beyond static PDF compilations.

## Legal / trust (site-wide)

**Memory-based sources only. Not official NBE papers. Priorities are forecasts from past-paper frequency/recurrence/recency — not a guarantee of next-exam questions.**

- Show on every page (banner + footer), not only the README.
- Mirror `disclaimer` from `analysis/reports/next_exam_priorities.json`.
- Privacy: Google email stored only for auth / usage analytics.

## Public vs gated

| Surface | Anonymous | Signed in (Google) |
|---------|-----------|--------------------|
| Landing, priorities, subjects, overlaps, drift | Full read | Full read |
| Topic frequency / due / overlap charts | Full read | Full read |
| Similar-question explorer / RAG | Soft CTA → sign in | Full access |
| Subject pack download | Soft CTA → sign in | Download + logged |
| Saved due-for-return watchlist | — | CRUD |

## Data contracts

### Question ID (`qid`)

Stable hash — never array index:

```text
qid = sha256("{year}|{exam}|{shift}|{question_number}|{normalized_stem[:200]}")
```

- `normalized_stem` = lowercase, collapse whitespace.
- Empty `shift` / `question_number` → empty string segment.
- Stored on every `questions` row; used in URLs `/explore/[qid]`.

### Source → tables

| Offline artifact | Supabase |
|------------------|----------|
| `merged_questions.json` | `questions` (+ embeddings later) |
| `next_exam_priorities.json` | `priority_snapshots` |
| `topic_importance.csv` | `topic_stats` |
| `multi_topic_overlaps*.csv` | `topic_overlaps` |
| `topic_year_drift.csv` | `topic_drift` |
| `ask_type_by_subject.csv` | `ask_type_stats` |
| `reports/subjects/*.md` | `subject_packs` |

### Image references

If stem matches image cues (`image below`, `marked A`, `x-ray`, `shown in the figure`, etc.) and no asset exists → `has_image_ref = true`. UI shows **Image missing**.
**need to find out ways to include images in the questions**
### Answers

Show correct option on explore / similar results when `answer` is present. Empty answer → show options without highlight.

## Auth

- Supabase Auth + Google OAuth.
- Anonymous browse of public routes.
- API routes for similar search / pack download / watchlist require session.

## Sync runbook

After any merge / classify / report regen:

```bash
# 1. Apply schema once (Supabase SQL editor or psql)
# 2. Seed structured data
python analysis/sync/seed_supabase.py

# 3. Embed new / missing rows (needs OPENAI_API_KEY or configured embed provider)
python analysis/sync/embed_questions.py
```

Env (see root `.env.example` + `web/.env.example`):

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (sync scripts)
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (web)
- `OPENAI_API_KEY` (embeddings)

## Success metrics

- Google signups
- Pack downloads (by subject)
- Explore sessions / similar queries
- Later: % overlap of must-study topics with the next actual exam (resume-grade validation)

## Phasing

| Phase | Ship |
|-------|------|
| v1 | Public viz + gated hybrid explorer + packs |
| v1.5 | Optional Python BM25/synonym retrieval behind same API |
| v2 | Chat tutor (cite-only), post-exam validation page |

## Infographics

Regenerate improved static plots + UI CSVs:

```bash
PYTHONPATH=analysis python3 analysis/export_viz_data.py
```

Live hub: `/insights` (subject share, year×subject heatmap, ask-type mix, importance bars, cleaned concepts). Home / Priorities / Subjects reuse the same chart components.

Share / trust UX:

- OG cards via `next/og`: `/api/og/topic`, `/api/og/priorities` (Download / Share on priority + topic pages)
- Score methodology tooltip (35/30/20/10/5 weights) on priorities, insights, subjects, topic detail
- Per-topic year sparklines + `/topics/[topic]` bars from `topic_year_series.json`
- Mobile: card layout for priority/subject topic lists; swipeable year heatmap

## Out of scope (v1)

Always-on Python RAG microservice, payments, hosting exam images, replacing the offline pipeline.

## To-Dos
1. find ways to add images
2. add a seperate section where papers are arranged according to the sources
3. add sources to the og explore questions
4. connect other remaing services to vercel
5. add o-auth
