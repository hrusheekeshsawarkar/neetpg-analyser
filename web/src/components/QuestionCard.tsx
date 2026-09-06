import Link from "next/link";
import type { ReactNode } from "react";
import type { QuestionRow } from "@/lib/types";

const OPTION_KEYS = ["1", "2", "3", "4"] as const;

export function QuestionCard({
  q,
  showAnswers = true,
  href,
  meta,
}: {
  q: QuestionRow;
  showAnswers?: boolean;
  href?: string;
  meta?: ReactNode;
}) {
  const options = [
    { key: "1", text: q.option_1 },
    { key: "2", text: q.option_2 },
    { key: "3", text: q.option_3 },
    { key: "4", text: q.option_4 },
  ].filter((o) => o.text);

  const answer = (q.answer_key || "").trim();

  const body = (
    <article className="surface rounded-xl p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
        <span>{q.year}</span>
        {q.exam && (
          <>
            <span>·</span>
            <span>{q.exam}</span>
          </>
        )}
        {q.subject_clean && (
          <>
            <span>·</span>
            <span>{q.subject_clean}</span>
          </>
        )}
        {q.topic_clean && (
          <>
            <span>·</span>
            <span>{q.topic_clean}</span>
          </>
        )}
        {q.ask_type && (
          <>
            <span>·</span>
            <span>{q.ask_type.replace(/_/g, " ")}</span>
          </>
        )}
        {q.has_image_ref && <span className="badge badge-missing">Image missing</span>}
        {meta}
      </div>
      <p className="mt-2 text-sm leading-relaxed">{q.question_text}</p>
      {options.length > 0 && (
        <ul className="mt-3 space-y-1.5 text-sm">
          {options.map((o) => {
            const correct =
              showAnswers &&
              answer &&
              (answer === o.key ||
                answer === OPTION_KEYS[Number(o.key) - 1] ||
                answer.toLowerCase() === (o.text || "").toLowerCase());
            return (
              <li
                key={o.key}
                className={`rounded-md border px-3 py-1.5 ${
                  correct
                    ? "border-[var(--accent)]/50 bg-[rgba(45,212,191,0.12)]"
                    : "border-[var(--line)]"
                }`}
              >
                <span className="mr-2 font-semibold text-[var(--muted)]">
                  {String.fromCharCode(64 + Number(o.key))}.
                </span>
                {o.text}
                {correct && (
                  <span className="ml-2 text-xs font-semibold text-[var(--accent)]">
                    Correct
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {showAnswers && !answer && options.length > 0 && (
        <p className="mt-2 text-xs text-[var(--muted)]">Answer key not available for this stem.</p>
      )}
      {showAnswers && q.answer_note && (
        <p className="mt-3 text-xs leading-relaxed text-[var(--muted)]">
          <span className="font-semibold text-[var(--fg)]">Explanation. </span>
          {q.answer_note}
        </p>
      )}
    </article>
  );

  if (href) {
    return (
      <Link href={href} className="block transition hover:opacity-95">
        {body}
      </Link>
    );
  }
  return body;
}
