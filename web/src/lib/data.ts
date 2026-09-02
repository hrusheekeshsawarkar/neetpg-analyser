import { readFileSync, existsSync, realpathSync } from "fs";
import path from "path";
import type {
  DriftRow,
  OverlapRow,
  PriorityPayload,
  QuestionRow,
  TopicStat,
} from "@/lib/types";

const publicData = (...parts: string[]) =>
  path.join(process.cwd(), "public", "data", ...parts);

function parseCsv(text: string): Record<string, string>[] {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = splitCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cols = splitCsvLine(line);
    const row: Record<string, string> = {};
    headers.forEach((h, i) => {
      row[h] = cols[i] ?? "";
    });
    return row;
  });
}

function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQ && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQ = !inQ;
      }
    } else if (ch === "," && !inQ) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

export function loadPriorities(): PriorityPayload {
  const raw = readFileSync(publicData("priorities.json"), "utf8");
  return JSON.parse(raw) as PriorityPayload;
}

export function loadTopicStats(): TopicStat[] {
  const rows = parseCsv(readFileSync(publicData("topic_importance.csv"), "utf8"));
  return rows.map((r) => ({
    topic: r.topic,
    primary_subject: r.primary_subject,
    question_count: Number(r.question_count),
    years_seen: Number(r.years_seen),
    year_list: r.year_list,
    recurrence: Number(r.recurrence),
    recent_count: Number(r.recent_count),
    years_since_last: Number(r.years_since_last),
    due_for_return: String(r.due_for_return).toLowerCase() === "true",
    importance_score: Number(r.importance_score),
    priority_band: r.priority_band,
  }));
}

export function loadOverlaps(): OverlapRow[] {
  const rows = parseCsv(readFileSync(publicData("overlaps.csv"), "utf8"));
  return rows.map((r) => ({
    item_a: r.item_a,
    item_b: r.item_b,
    co_occurrence: Number(r.co_occurrence),
  }));
}

export function loadDrift(): DriftRow[] {
  const rows = parseCsv(readFileSync(publicData("drift.csv"), "utf8"));
  return rows.map((r) => ({
    topic: r.topic,
    recent_count: Number(r.recent_count),
    older_count: Number(r.older_count),
    recent_share: Number(r.recent_share),
    older_share: Number(r.older_share),
    delta_share: Number(r.delta_share),
  }));
}

export function loadAskTypeBySubject(): Array<{
  subject: string;
  ask_type: string;
  count: number;
}> {
  const rows = parseCsv(
    readFileSync(publicData("ask_type_by_subject.csv"), "utf8"),
  );
  return rows.map((r) => ({
    subject: r.subject,
    ask_type: r.ask_type,
    count: Number(r.count),
  }));
}

export function loadPackMarkdown(slug: string): string | null {
  const p = publicData("packs", `${slug}.md`);
  if (!existsSync(p)) return null;
  return readFileSync(p, "utf8");
}

function questionsMirrorPath(): string | null {
  if (process.env.QUESTIONS_MIRROR_PATH) {
    try {
      return realpathSync(process.env.QUESTIONS_MIRROR_PATH);
    } catch {
      return null;
    }
  }
  const candidates = [
    // Prefer a real file under web/ (works on Vercel when Root Directory = web)
    path.join(process.cwd(), "data", "questions.json"),
    path.join(process.cwd(), "..", "analysis", "data", "web_mirror", "questions.json"),
    path.join(process.cwd(), "public", "data", "questions.json"),
  ];
  for (const c of candidates) {
    try {
      // realpathSync fails on dangling symlinks (e.g. gitignored web_mirror on Vercel)
      if (!existsSync(c)) continue;
      return realpathSync(c);
    } catch {
      continue;
    }
  }
  return null;
}

let questionsCache: QuestionRow[] | null = null;
let questionsById: Map<string, QuestionRow> | null = null;

export function loadQuestions(): QuestionRow[] {
  if (questionsCache) return questionsCache;
  const p = questionsMirrorPath();
  if (!p) {
    questionsCache = [];
    questionsById = new Map();
    return questionsCache;
  }
  questionsCache = JSON.parse(readFileSync(p, "utf8")) as QuestionRow[];
  questionsById = new Map(questionsCache.map((q) => [q.qid, q]));
  return questionsCache;
}

export function getQuestion(qid: string): QuestionRow | null {
  loadQuestions();
  return questionsById?.get(qid) ?? null;
}

export function questionsForSubject(subject: string, limit = 40): QuestionRow[] {
  return loadQuestions()
    .filter((q) => q.subject_clean === subject)
    .slice(0, limit);
}

export function questionsForTopic(topic: string, limit = 40): QuestionRow[] {
  return loadQuestions()
    .filter((q) => q.topic_clean === topic)
    .slice(0, limit);
}
