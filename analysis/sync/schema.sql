-- NEET PG Priorities — Supabase schema
-- Run in Supabase SQL editor (or psql). Requires pgvector.

create extension if not exists vector;
create extension if not exists pg_trgm;

-- ---------------------------------------------------------------------------
-- Questions (RAG corpus)
-- ---------------------------------------------------------------------------
create table if not exists public.questions (
  qid text primary key,
  question_number text,
  year int,
  exam text,
  shift text,
  source text,
  subject text,
  subject_clean text,
  topic text,
  topic_clean text,
  topics text[] default '{}',
  secondary_subjects text[] default '{}',
  subtopic text,
  concept text,
  ask_type text,
  label_source text,
  question_text text not null default '',
  option_1 text,
  option_2 text,
  option_3 text,
  option_4 text,
  answer_key text,
  answer_note text,
  has_image_ref boolean not null default false,
  embedding vector(1536),
  search_tsv tsvector,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists questions_subject_clean_idx on public.questions (subject_clean);
create index if not exists questions_topic_clean_idx on public.questions (topic_clean);
create index if not exists questions_year_idx on public.questions (year);
create index if not exists questions_ask_type_idx on public.questions (ask_type);
create index if not exists questions_embedding_null_idx on public.questions (qid) where embedding is null;

-- IVFFlat / HNSW after data load; create once embeddings exist:
-- create index questions_embedding_idx on public.questions
--   using hnsw (embedding vector_cosine_ops);

create or replace function public.questions_search_tsv_update()
returns trigger
language plpgsql
as $$
begin
  new.search_tsv :=
    setweight(to_tsvector('english', coalesce(new.topic_clean, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.concept, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.subject_clean, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.question_text, '')), 'B') ||
    setweight(
      to_tsvector(
        'english',
        coalesce(new.option_1, '') || ' ' ||
        coalesce(new.option_2, '') || ' ' ||
        coalesce(new.option_3, '') || ' ' ||
        coalesce(new.option_4, '')
      ),
      'C'
    );
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists questions_search_tsv_trg on public.questions;
create trigger questions_search_tsv_trg
  before insert or update of topic_clean, concept, subject_clean, question_text,
    option_1, option_2, option_3, option_4
  on public.questions
  for each row
  execute function public.questions_search_tsv_update();

create index if not exists questions_search_tsv_idx on public.questions using gin (search_tsv);

-- ---------------------------------------------------------------------------
-- Topic / viz stats
-- ---------------------------------------------------------------------------
create table if not exists public.topic_stats (
  topic text not null,
  primary_subject text not null,
  question_count int,
  years_seen int,
  year_list text,
  recurrence float,
  recent_count int,
  years_since_last int,
  due_for_return boolean,
  importance_score float,
  priority_band text,
  primary key (topic, primary_subject)
);

create table if not exists public.topic_overlaps (
  id bigserial primary key,
  item_a text not null,
  item_b text not null,
  co_occurrence int not null,
  unique (item_a, item_b)
);

create table if not exists public.topic_drift (
  topic text primary key,
  recent_count float,
  older_count float,
  recent_share float,
  older_share float,
  delta_share float
);

create table if not exists public.ask_type_stats (
  id bigserial primary key,
  subject text not null,
  ask_type text not null,
  count int not null,
  unique (subject, ask_type)
);

create table if not exists public.priority_snapshots (
  id bigserial primary key,
  as_of_date date not null default current_date,
  disclaimer text,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create unique index if not exists priority_snapshots_as_of_uniq
  on public.priority_snapshots (as_of_date);

create table if not exists public.subject_packs (
  subject_slug text primary key,
  subject_name text not null,
  markdown text not null,
  question_count int,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Users / analytics
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists public.saved_topics (
  id bigserial primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  topic text not null,
  primary_subject text not null,
  created_at timestamptz not null default now(),
  unique (user_id, topic, primary_subject)
);

create table if not exists public.pack_downloads (
  id bigserial primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  subject_slug text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.explore_events (
  id bigserial primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  qid text,
  query_text text,
  result_count int,
  created_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', new.email)
  )
  on conflict (id) do update
    set email = excluded.email,
        display_name = coalesce(excluded.display_name, public.profiles.display_name);
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- Hybrid match RPC
-- ---------------------------------------------------------------------------
create or replace function public.match_questions_hybrid(
  query_embedding vector(1536),
  query_text text,
  match_count int default 10,
  exclude_qid text default null,
  filter_subject text default null,
  filter_topic text default null,
  year_min int default null,
  year_max int default null,
  rrf_k int default 60,
  candidate_n int default 40
)
returns table (
  qid text,
  year int,
  exam text,
  subject_clean text,
  topic_clean text,
  concept text,
  ask_type text,
  question_text text,
  option_1 text,
  option_2 text,
  option_3 text,
  option_4 text,
  answer_key text,
  has_image_ref boolean,
  topics text[],
  rrf_score float,
  dense_rank int,
  sparse_rank int,
  same_topic boolean
)
language sql
stable
as $$
  with dense as (
    select
      q.qid,
      row_number() over (order by q.embedding <=> query_embedding) as rnk
    from public.questions q
    where query_embedding is not null
      and q.embedding is not null
      and (exclude_qid is null or q.qid <> exclude_qid)
      and (filter_subject is null or q.subject_clean = filter_subject)
      and (filter_topic is null or q.topic_clean = filter_topic)
      and (year_min is null or q.year >= year_min)
      and (year_max is null or q.year <= year_max)
    order by q.embedding <=> query_embedding
    limit greatest(candidate_n, match_count)
  ),
  sparse as (
    select
      q.qid,
      row_number() over (
        order by ts_rank_cd(q.search_tsv, plainto_tsquery('english', coalesce(query_text, ''))) desc
      ) as rnk
    from public.questions q
    where coalesce(query_text, '') <> ''
      and q.search_tsv @@ plainto_tsquery('english', query_text)
      and (exclude_qid is null or q.qid <> exclude_qid)
      and (filter_subject is null or q.subject_clean = filter_subject)
      and (filter_topic is null or q.topic_clean = filter_topic)
      and (year_min is null or q.year >= year_min)
      and (year_max is null or q.year <= year_max)
    order by ts_rank_cd(q.search_tsv, plainto_tsquery('english', query_text)) desc
    limit greatest(candidate_n, match_count)
  ),
  fused as (
    select
      coalesce(d.qid, s.qid) as qid,
      coalesce(1.0 / (rrf_k + d.rnk), 0.0) + coalesce(1.0 / (rrf_k + s.rnk), 0.0) as score,
      d.rnk as dense_rank,
      s.rnk as sparse_rank
    from dense d
    full outer join sparse s on d.qid = s.qid
  )
  select
    q.qid,
    q.year,
    q.exam,
    q.subject_clean,
    q.topic_clean,
    q.concept,
    q.ask_type,
    q.question_text,
    q.option_1,
    q.option_2,
    q.option_3,
    q.option_4,
    q.answer_key,
    q.has_image_ref,
    q.topics,
    f.score::float as rrf_score,
    f.dense_rank::int,
    f.sparse_rank::int,
    (
      filter_topic is not null and q.topic_clean = filter_topic
    ) as same_topic
  from fused f
  join public.questions q on q.qid = f.qid
  order by f.score desc
  limit match_count;
$$;

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------
alter table public.questions enable row level security;
alter table public.topic_stats enable row level security;
alter table public.topic_overlaps enable row level security;
alter table public.topic_drift enable row level security;
alter table public.ask_type_stats enable row level security;
alter table public.priority_snapshots enable row level security;
alter table public.subject_packs enable row level security;
alter table public.profiles enable row level security;
alter table public.saved_topics enable row level security;
alter table public.pack_downloads enable row level security;
alter table public.explore_events enable row level security;

-- Public read for analytics tables + questions metadata (explore UI still gated in app)
drop policy if exists "Public read questions" on public.questions;
create policy "Public read questions" on public.questions for select using (true);

drop policy if exists "Public read topic_stats" on public.topic_stats;
create policy "Public read topic_stats" on public.topic_stats for select using (true);

drop policy if exists "Public read topic_overlaps" on public.topic_overlaps;
create policy "Public read topic_overlaps" on public.topic_overlaps for select using (true);

drop policy if exists "Public read topic_drift" on public.topic_drift;
create policy "Public read topic_drift" on public.topic_drift for select using (true);

drop policy if exists "Public read ask_type_stats" on public.ask_type_stats;
create policy "Public read ask_type_stats" on public.ask_type_stats for select using (true);

drop policy if exists "Public read priority_snapshots" on public.priority_snapshots;
create policy "Public read priority_snapshots" on public.priority_snapshots for select using (true);

drop policy if exists "Public read subject_packs" on public.subject_packs;
create policy "Public read subject_packs" on public.subject_packs for select using (true);

drop policy if exists "Users read own profile" on public.profiles;
create policy "Users read own profile" on public.profiles
  for select using (auth.uid() = id);

drop policy if exists "Users update own profile" on public.profiles;
create policy "Users update own profile" on public.profiles
  for update using (auth.uid() = id);

drop policy if exists "Users manage saved_topics" on public.saved_topics;
create policy "Users manage saved_topics" on public.saved_topics
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users insert pack_downloads" on public.pack_downloads;
create policy "Users insert pack_downloads" on public.pack_downloads
  for insert with check (auth.uid() = user_id);

drop policy if exists "Users read own pack_downloads" on public.pack_downloads;
create policy "Users read own pack_downloads" on public.pack_downloads
  for select using (auth.uid() = user_id);

drop policy if exists "Users insert explore_events" on public.explore_events;
create policy "Users insert explore_events" on public.explore_events
  for insert with check (auth.uid() = user_id);

drop policy if exists "Users read own explore_events" on public.explore_events;
create policy "Users read own explore_events" on public.explore_events
  for select using (auth.uid() = user_id);

-- Service role bypasses RLS for seed/embed scripts.
