import type { QuestionRow } from "@/lib/types";
import { getQuestion, loadQuestions } from "@/lib/data";

function tokenize(text: string): string[] {
  return (text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 2);
}

function buildDocText(q: QuestionRow): string {
  return [
    q.subject_clean,
    q.topic_clean,
    q.concept,
    q.ask_type,
    q.question_text,
    q.option_1,
    q.option_2,
    q.option_3,
    q.option_4,
    ...(q.topics || []),
  ]
    .filter(Boolean)
    .join(" ");
}

type Index = {
  N: number;
  df: Map<string, number>;
  docs: Array<{ q: QuestionRow; tokens: string[]; tf: Map<string, number> }>;
};

let indexCache: Index | null = null;

function getIndex(): Index {
  if (indexCache) return indexCache;
  const all = loadQuestions();
  const df = new Map<string, number>();
  const docs: Index["docs"] = [];
  for (const row of all) {
    const tokens = tokenize(buildDocText(row));
    const tf = new Map<string, number>();
    const seen = new Set<string>();
    for (const t of tokens) {
      tf.set(t, (tf.get(t) || 0) + 1);
      seen.add(t);
    }
    for (const t of seen) df.set(t, (df.get(t) || 0) + 1);
    docs.push({ q: row, tokens, tf });
  }
  indexCache = { N: all.length || 1, df, docs };
  return indexCache;
}

/** Local sparse fallback (BM25-ish) when pgvector is unavailable. */
export function localSimilar(opts: {
  qid?: string;
  text?: string;
  k?: number;
  subject?: string | null;
  topic?: string | null;
  year_min?: number | null;
  year_max?: number | null;
}): Array<QuestionRow & { rrf_score: number; same_topic: boolean }> {
  const k = opts.k ?? 10;
  const seed = opts.qid ? getQuestion(opts.qid) : null;
  const queryText =
    opts.text ||
    (seed
      ? `${seed.topic_clean || ""} ${seed.concept || ""} ${seed.question_text}`
      : "");
  const qTokens = tokenize(queryText);
  if (!qTokens.length) return [];

  const qSet = new Set(qTokens);
  const { N, df, docs } = getIndex();
  const scored: Array<QuestionRow & { rrf_score: number; same_topic: boolean }> =
    [];

  for (const { q: row, tf } of docs) {
    if (opts.qid && row.qid === opts.qid) continue;
    if (opts.subject && row.subject_clean !== opts.subject) continue;
    if (opts.topic && row.topic_clean !== opts.topic) continue;
    if (opts.year_min != null && (row.year ?? 0) < opts.year_min) continue;
    if (opts.year_max != null && (row.year ?? 9999) > opts.year_max) continue;

    let score = 0;
    for (const t of qSet) {
      const f = tf.get(t) || 0;
      if (!f) continue;
      const idf = Math.log(1 + N / ((df.get(t) || 0) + 1));
      score += ((f * (1.5 + 1)) / (f + 1.5)) * idf;
    }
    if (seed?.topic_clean && row.topic_clean === seed.topic_clean) score *= 1.35;
    if (seed?.concept && row.concept && row.concept === seed.concept) score *= 1.25;
    if (score <= 0) continue;

    scored.push({
      ...row,
      rrf_score: score,
      same_topic: Boolean(
        (opts.topic && row.topic_clean === opts.topic) ||
          (seed?.topic_clean && row.topic_clean === seed.topic_clean),
      ),
    });
  }

  scored.sort((a, b) => b.rrf_score - a.rrf_score);
  return scored.slice(0, k);
}
