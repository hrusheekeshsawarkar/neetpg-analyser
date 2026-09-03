/** Importance score methodology (mirrors analysis/predict_priority.score_topics). */

export const SCORE_WEIGHTS = [
  {
    key: "frequency",
    label: "Frequency",
    weight: 35,
    detail: "Unique questions on this topic (capped at 20 for the score).",
  },
  {
    key: "recurrence",
    label: "Recurrence",
    weight: 30,
    detail: "Share of exam years (2010–2025) in which the topic appeared.",
  },
  {
    key: "recency_weighted",
    label: "Recency-weighted volume",
    weight: 20,
    detail: "Question counts with newer years weighted higher.",
  },
  {
    key: "recent_share",
    label: "Recent share",
    weight: 10,
    detail: "Fraction of this topic’s questions from the latest ~2 exam years.",
  },
  {
    key: "due_bonus",
    label: "Due-for-return",
    weight: 5,
    detail: "Bonus when a high-recurrence topic has been quiet recently.",
  },
] as const;

export const SCORE_BANDS = [
  { band: "Must", min: 70, color: "#f07178" },
  { band: "High", min: 45, color: "#f0b429" },
  { band: "Medium", min: 25, color: "#2dd4bf" },
  { band: "Low", min: 0, color: "#5a7a82" },
] as const;

export const SCORE_BLURB =
  "Score = 35% frequency + 30% recurrence + 20% recency-weighted volume + 10% recent share + 5% due-for-return bonus. Not a guarantee of next-exam questions.";

export function topicSharePath(topic: string, subject: string) {
  const q = new URLSearchParams({
    topic,
    subject,
  });
  return `/api/og/topic?${q.toString()}`;
}

export function prioritiesSharePath() {
  return `/api/og/priorities`;
}
