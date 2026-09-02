export type TopicStat = {
  topic: string;
  primary_subject: string;
  question_count: number;
  years_seen: number;
  year_list: string;
  recurrence: number;
  recent_count: number;
  years_since_last: number;
  due_for_return: boolean;
  importance_score: number;
  priority_band: string;
};

export type PriorityPayload = {
  disclaimer: string;
  must_study_topics: TopicStat[];
  high_priority_topics: TopicStat[];
  due_for_return: Array<{
    topic: string;
    primary_subject?: string;
    years_since_last?: number;
    year_list?: string;
    [key: string]: unknown;
  }>;
  evergreen_topics?: TopicStat[];
  within_topic_concepts?: Record<string, Array<{ concept: string; count: number }>>;
};

export type QuestionRow = {
  qid: string;
  year: number | null;
  exam: string | null;
  shift?: string | null;
  subject_clean: string | null;
  topic_clean: string | null;
  topics: string[];
  concept: string | null;
  ask_type: string | null;
  question_text: string;
  option_1: string | null;
  option_2: string | null;
  option_3: string | null;
  option_4: string | null;
  answer_key: string | null;
  has_image_ref: boolean;
};

export type OverlapRow = {
  item_a: string;
  item_b: string;
  co_occurrence: number;
};

export type DriftRow = {
  topic: string;
  recent_count: number;
  older_count: number;
  recent_share: number;
  older_share: number;
  delta_share: number;
};

export const MBBS_SUBJECTS = [
  "Anatomy",
  "Biochemistry",
  "Physiology",
  "Pharmacology",
  "Microbiology",
  "Pathology",
  "Community Medicine",
  "Forensic Medicine",
  "Ophthalmology",
  "ENT",
  "Medicine",
  "Surgery",
  "OBG",
  "Pediatrics",
  "Anaesthesia",
  "Orthopedics",
  "Radiology",
  "Psychiatry",
  "Dermatology",
] as const;

export function subjectToSlug(name: string): string {
  return name.toLowerCase().replace(/\s+/g, "_");
}

export function slugToSubject(slug: string): string {
  const map: Record<string, string> = {
    obg: "OBG",
    ent: "ENT",
  };
  if (map[slug]) return map[slug];
  return slug
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export const DISCLAIMER =
  "Memory-based sources only. Not official NBE papers. Priorities are forecasts from past-paper frequency/recurrence/recency — not a guarantee of next-exam questions.";
