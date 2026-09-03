import type { Metadata } from "next";
import Link from "next/link";
import { FadeIn, StaggerItem, StaggerList } from "@/components/Motion";
import { PriorityList, type PriorityRow } from "@/components/PriorityList";
import { ScoreMethodology } from "@/components/ScoreMethodology";
import { ShareCardButton } from "@/components/ShareCardButton";
import { ImportanceBandBars } from "@/components/viz/Charts";
import { getTopicYearSeries, loadPriorities } from "@/lib/data";

export const metadata: Metadata = {
  title: "Next exam priorities — NEET PG Priorities",
  description:
    "Dated must-study and due-for-return topic list from memory-based NEET PG / AIPGMEE past papers.",
  openGraph: {
    title: "Priority list for the next NEET PG",
    description:
      "Must-study and due-for-return topics from ~18k memory-based past questions.",
    images: [{ url: "/api/og/priorities", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    images: ["/api/og/priorities"],
  },
};

function withSparks(rows: PriorityRow[]): PriorityRow[] {
  return rows.map((r) => {
    const series = getTopicYearSeries(r.topic);
    return series
      ? { ...r, sparkYears: series.years, sparkValues: series.values }
      : r;
  });
}

export default function PrioritiesPage() {
  const data = loadPriorities();
  const asOf = new Date().toISOString().slice(0, 10);
  const must = withSparks(data.must_study_topics || []);
  const high = withSparks(data.high_priority_topics || []);
  const due = withSparks(
    (data.due_for_return || []).map((d) => ({
      topic: d.topic,
      primary_subject: String(d.primary_subject || "—"),
      year_list: d.year_list,
      years_since_last: d.years_since_last as number | undefined,
      importance_score: d.importance_score as number | undefined,
      question_count: d.question_count as number | undefined,
      priority_band: "Due",
      due_for_return: true,
    })),
  );

  return (
    <div className="space-y-10">
      <FadeIn>
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent2)]">
          Shareable brief · {asOf}
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold md:text-4xl">
          Priority list for the next exam
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">{data.disclaimer}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <ScoreMethodology />
          <ShareCardButton kind="priorities" />
          <Link href="/insights" className="text-sm text-[var(--accent)] hover:underline">
            Open interactive insights →
          </Link>
        </div>
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
          <h2 className="font-display mb-3 text-xl font-semibold text-[var(--accent)]">
            Must-study topics
          </h2>
          <PriorityList rows={must} />
        </StaggerItem>

        <StaggerItem>
          <h2 className="font-display mb-3 text-xl font-semibold">High priority</h2>
          <PriorityList rows={high} />
        </StaggerItem>

        <StaggerItem>
          <h2 className="font-display mb-3 text-xl font-semibold text-[var(--accent2)]">
            Possibly due for return
          </h2>
          <p className="mb-3 text-sm text-[var(--muted)]">
            High-recurrence topics quiet recently — revision candidates, not predictions. Sparklines
            show yearly volume so the gap is visible.
          </p>
          <PriorityList rows={due} />
        </StaggerItem>
      </StaggerList>
    </div>
  );
}
