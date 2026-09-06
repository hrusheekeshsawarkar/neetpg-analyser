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

Without Supabase, the app runs in **local mode**: public viz from `public/data/*`, and similar-question search uses `data/questions.json` (copied by the seed script — do not symlink into gitignored `analysis/data/web_mirror/`).

Refresh mirror data:

```bash
python ../analysis/sync/seed_supabase.py --local-only
# writes analysis/data/web_mirror/* and copies into web/public/data + web/data/questions.json
```

**Vercel:** Root Directory = `web`, leave Output Directory empty. Commit:

- `web/data/questions.json` (~11MB) so explore works without Supabase
- `web/public/question_images/` (compressed JPEGs of linked figures, ~13MB) so images render in production

Regenerate both via `python ../analysis/sync/seed_supabase.py --local-only`. Full-res extracts stay gitignored under `analysis/data/question_images/`.

Optional CDN override: set `NEXT_PUBLIC_QUESTION_IMAGES_BASE_URL` if figures are hosted on Blob / Supabase Storage instead of `public/`.

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
