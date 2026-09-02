# Hybrid RAG Design

## Goal (v1)

Similar-question explorer: given a seed question or free-text query, return the nearest past exam stems with year, subject, topics, options, and correct answer — not a medical chatbot.

## Architecture

```
query (qid or text)
  ├─► dense: embedding cosine (pgvector)
  ├─► sparse: Postgres FTS (tsvector / ts_rank_cd)
  └─► RRF fusion → filters → top-K
```

Optional later: one-line LLM “why these match”. v1 ships scores + shared topic/concept without LLM.

## Embedding text template

Concatenate (skip empty parts):

```text
Subject: {subject_clean}
Topic: {topic_clean}
Concept: {concept}
Ask type: {ask_type}
Question: {question_text}
Options: A) {option_1} B) {option_2} C) {option_3} D) {option_4}
```

- Model (default): `text-embedding-3-small` (1536 dims) via OpenAI.
- Store in `questions.embedding vector(1536)`.
- Re-embed only rows where `embedding IS NULL` (or force `--all`).

## Sparse index

Generated column / trigger maintains `search_tsv`:

```sql
setweight(to_tsvector('english', coalesce(topic_clean,'')), 'A') ||
setweight(to_tsvector('english', coalesce(concept,'')), 'A') ||
setweight(to_tsvector('english', coalesce(question_text,'')), 'B') ||
setweight(to_tsvector('english', coalesce(option_1,'') || ' ' || ...), 'C')
```

Query with `plainto_tsquery('english', $q)` and `ts_rank_cd`.

## Hybrid fusion (RRF)

For each candidate from dense top-N and sparse top-N:

```
score = 1/(60 + rank_dense) + 1/(60 + rank_sparse)
```

- Exclude self `qid`.
- Hard filters (optional): `subject_clean`, `topic_clean`, `year`, `ask_type`.
- Soft signal in UI: badge **same topic** vs **cross-topic**.

Exposed as Supabase RPC `match_questions_hybrid(...)`.

## API

`POST /api/similar` (auth required)

```json
{ "qid": "...", "text": null, "k": 10, "filters": { "subject": null, "year_min": null } }
```

- If `qid`: use that row’s embedding + stem text for FTS.
- If `text` only: embed on the fly (server) + FTS on text.
- Rate-limit by `auth.uid()`.

## Failure modes

| Case | Behavior |
|------|----------|
| Image stem, no asset | `has_image_ref`; UI **Image missing** |
| Empty `answer` | Show options, no correct highlight |
| No embedding yet | Fall back to FTS-only; warn in API meta |
| Medical abbreviation mismatch | Acceptable v1 gap; Python synonym module later |

## Eval (lightweight)

1. Hand-pick 20 seed `qid`s across subjects.
2. Judge top-5: same concept? (Y/N)
3. Track % sharing `topic_clean` or token overlap on `concept`.
4. Re-run after reindex or analyzer changes.

## Index refresh

```bash
python analysis/sync/seed_supabase.py          # upsert questions + stats
python analysis/sync/embed_questions.py        # fill missing embeddings
# Optional: python analysis/sync/embed_questions.py --all
```

After pipeline adds years: seed → embed → spot-check `/explore/[qid]`.

## v1.5+ Python retrieval

Same HTTP contract; swap RPC for a service that does custom BM25 + medical synonyms + optional rerank. Next.js stays the product edge.
