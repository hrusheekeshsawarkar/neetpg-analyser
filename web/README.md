# NEET PG Priorities (web)

Next.js App Router front end for the analysis pipeline.

## Setup

```bash
cd web
cp .env.example .env.local
# Optional: fill Supabase + OpenAI for Google auth and pgvector hybrid RAG
npm install
npm run dev
```

Without Supabase, the app runs in **local mode**: public viz from `public/data/*`, and similar-question search uses the on-disk BM25-ish index over `../analysis/data/web_mirror/questions.json`.

Refresh mirror data:

```bash
python ../analysis/sync/seed_supabase.py --local-only
# then re-copy CSVs/JSON into public/data if needed, or re-run the cp steps from the product plan
```

## Supabase

1. Create a project; enable Google Auth.
2. Run [`../analysis/sync/schema.sql`](../analysis/sync/schema.sql) in the SQL editor.
3. Set `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in the repo root `.env`.
4. `python ../analysis/sync/seed_supabase.py`
5. `python ../analysis/sync/embed_questions.py`
6. Set `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `.env.local`.

## Routes

| Path | Access |
|------|--------|
| `/`, `/priorities`, `/subjects`, `/overlaps`, `/drift` | Public |
| `/explore`, `/explore/[qid]` | Browse public; similar retrieval gated when Auth configured |
| `/packs/[subject]` | View public; download gated when Auth configured |
