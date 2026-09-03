"use client";

import Link from "next/link";
import { ShareCardButton } from "@/components/ShareCardButton";
import { TopicSparkline } from "@/components/TopicSparkline";
import { subjectToSlug } from "@/lib/types";

export type PriorityRow = {
  topic: string;
  primary_subject: string;
  importance_score?: number;
  question_count?: number;
  year_list?: string;
  years_since_last?: number;
  priority_band?: string;
  due_for_return?: boolean;
  recurrence?: number;
  sparkYears?: number[];
  sparkValues?: number[];
};

/** Desktop table + mobile cards for priority lists. */
export function PriorityList({ rows }: { rows: PriorityRow[] }) {
  return (
    <>
      {/* Mobile cards */}
      <ul className="space-y-3 md:hidden">
        {rows.map((r) => (
          <li key={`${r.topic}-${r.primary_subject}`} className="surface rounded-xl p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <Link
                  href={`/topics/${encodeURIComponent(r.topic)}`}
                  className="font-medium text-[var(--ink)] hover:text-[var(--accent)]"
                >
                  {r.topic}
                </Link>
                <div className="mt-1 text-xs chart-sub">
                  <Link
                    href={`/subjects/${subjectToSlug(r.primary_subject)}`}
                    className="text-[var(--accent)]"
                  >
                    {r.primary_subject}
                  </Link>
                  {r.priority_band ? ` · ${r.priority_band}` : ""}
                  {r.years_since_last != null && r.years_since_last > 0
                    ? ` · gap ${r.years_since_last}y`
                    : ""}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-display text-lg tabular-nums text-[var(--accent2)]">
                  {r.importance_score?.toFixed?.(1) ?? "—"}
                </div>
                <div className="text-[10px] chart-sub">n={r.question_count ?? "—"}</div>
              </div>
            </div>
            {r.sparkYears && r.sparkValues ? (
              <div className="mt-3 flex items-center justify-between gap-2">
                <TopicSparkline
                  years={r.sparkYears}
                  values={r.sparkValues}
                  dueGap={r.years_since_last}
                />
                <ShareCardButton
                  kind="topic"
                  topic={r.topic}
                  subject={r.primary_subject}
                  score={r.importance_score ?? 0}
                  count={r.question_count ?? 0}
                  band={r.priority_band || "Must"}
                  compact
                />
              </div>
            ) : (
              <div className="mt-3">
                <ShareCardButton
                  kind="topic"
                  topic={r.topic}
                  subject={r.primary_subject}
                  score={r.importance_score ?? 0}
                  count={r.question_count ?? 0}
                  band={r.priority_band || "Must"}
                  compact
                />
              </div>
            )}
          </li>
        ))}
      </ul>

      {/* Desktop table */}
      <div className="hidden overflow-x-auto rounded-xl surface md:block">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-[var(--line)] text-xs uppercase tracking-wide chart-sub">
            <tr>
              <th className="px-4 py-3">Topic</th>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Count</th>
              <th className="px-4 py-3">Trend</th>
              <th className="px-4 py-3">Years / gap</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={`${r.topic}-${r.primary_subject}`}
                className="border-b border-[var(--line)]/60"
              >
                <td className="px-4 py-2.5 font-medium">
                  <Link
                    href={`/topics/${encodeURIComponent(r.topic)}`}
                    className="hover:text-[var(--accent)]"
                  >
                    {r.topic}
                  </Link>
                </td>
                <td className="px-4 py-2.5">
                  <Link
                    className="text-[var(--accent)] hover:underline"
                    href={`/subjects/${subjectToSlug(r.primary_subject)}`}
                  >
                    {r.primary_subject}
                  </Link>
                </td>
                <td className="px-4 py-2.5 tabular-nums">
                  {r.importance_score?.toFixed?.(1) ?? "—"}
                </td>
                <td className="px-4 py-2.5 tabular-nums">{r.question_count ?? "—"}</td>
                <td className="px-4 py-2.5">
                  {r.sparkYears && r.sparkValues ? (
                    <TopicSparkline
                      years={r.sparkYears}
                      values={r.sparkValues}
                      dueGap={r.years_since_last}
                    />
                  ) : (
                    <span className="chart-sub">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-xs chart-sub max-w-[14rem] truncate">
                  {r.years_since_last != null && r.years_since_last > 0
                    ? `gap ${r.years_since_last}y`
                    : null}{" "}
                  {r.year_list || "—"}
                </td>
                <td className="px-4 py-2.5">
                  <ShareCardButton
                    kind="topic"
                    topic={r.topic}
                    subject={r.primary_subject}
                    score={r.importance_score ?? 0}
                    count={r.question_count ?? 0}
                    band={r.priority_band || "Must"}
                    compact
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
