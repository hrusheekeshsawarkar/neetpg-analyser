import type { Metadata } from "next";
import Link from "next/link";
import { FadeIn, StaggerItem, StaggerList } from "@/components/Motion";
import { ImportanceBandBars } from "@/components/viz/Charts";
import { loadPriorities } from "@/lib/data";
import { subjectToSlug } from "@/lib/types";

export const metadata: Metadata = {
  title: "Next exam priorities — NEET PG Priorities",
  description:
    "Dated must-study and due-for-return topic list from memory-based NEET PG / AIPGMEE past papers.",
};

function TopicTable({
  rows,
}: {
  rows: Array<{
    topic: string;
    primary_subject: string;
    importance_score?: number;
    question_count?: number;
    year_list?: string;
    years_since_last?: number;
  }>;
}) {
  return (
    <div className="overflow-x-auto rounded-xl surface">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--muted)]">
          <tr>
            <th className="px-4 py-3">Topic</th>
            <th className="px-4 py-3">Subject</th>
            <th className="px-4 py-3">Score</th>
            <th className="px-4 py-3">Count</th>
            <th className="px-4 py-3">Years</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.topic}-${r.primary_subject}`} className="border-b border-[var(--line)]/60">
              <td className="px-4 py-2.5 font-medium">{r.topic}</td>
              <td className="px-4 py-2.5">
                <Link
                  className="text-[var(--accent)] hover:underline"
                  href={`/subjects/${subjectToSlug(r.primary_subject)}`}
                >
                  {r.primary_subject}
                </Link>
              </td>
              <td className="px-4 py-2.5 tabular-nums">{r.importance_score?.toFixed?.(1) ?? "—"}</td>
              <td className="px-4 py-2.5 tabular-nums">{r.question_count ?? "—"}</td>
              <td className="px-4 py-2.5 text-xs text-[var(--muted)]">
                {r.year_list || (r.years_since_last != null ? `gap ${r.years_since_last}y` : "—")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PrioritiesPage() {
  const data = loadPriorities();
  const asOf = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-10">
      <FadeIn>
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent2)]">Shareable brief · {asOf}</p>
        <h1 className="font-display mt-2 text-3xl font-semibold md:text-4xl">
          Priority list for the next exam
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">{data.disclaimer}</p>
        <p className="mt-2 text-sm">
          <Link href="/insights" className="text-[var(--accent)] hover:underline">
            Open interactive insights →
          </Link>
        </p>
      </FadeIn>

      <FadeIn delay={0.05}>
        <ImportanceBandBars
          data={[
            ...(data.must_study_topics || []),
            ...(data.high_priority_topics || []),
          ].map((t) => ({
            topic: t.topic,
            primary_subject: t.primary_subject,
            importance_score: t.importance_score ?? 0,
            priority_band: t.priority_band || "Must",
            question_count: t.question_count ?? 0,
          }))}
        />
      </FadeIn>

      <StaggerList className="space-y-10">
        <StaggerItem>
          <h2 className="font-display mb-3 text-xl font-semibold text-[var(--accent)]">Must-study topics</h2>
          <TopicTable rows={data.must_study_topics || []} />
        </StaggerItem>

        <StaggerItem>
          <h2 className="font-display mb-3 text-xl font-semibold">High priority</h2>
          <TopicTable rows={data.high_priority_topics || []} />
        </StaggerItem>

        <StaggerItem>
          <h2 className="font-display mb-3 text-xl font-semibold text-[var(--accent2)]">
            Possibly due for return
          </h2>
          <p className="mb-3 text-sm text-[var(--muted)]">
            High-recurrence topics quiet recently — revision candidates, not predictions.
          </p>
          <TopicTable
            rows={(data.due_for_return || []).map((d) => ({
              topic: d.topic,
              primary_subject: String(d.primary_subject || "—"),
              year_list: d.year_list,
              years_since_last: d.years_since_last as number | undefined,
              importance_score: d.importance_score as number | undefined,
              question_count: d.question_count as number | undefined,
            }))}
          />
        </StaggerItem>
      </StaggerList>
    </div>
  );
}
