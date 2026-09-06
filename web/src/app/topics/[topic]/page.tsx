import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { FadeIn } from "@/components/Motion";
import { ScoreMethodology } from "@/components/ScoreMethodology";
import { ShareCardButton } from "@/components/ShareCardButton";
import { TopicSparkline } from "@/components/TopicSparkline";
import { TopicYearBars } from "@/components/TopicYearBars";
import { WatchlistButton } from "@/components/WatchlistButton";
import {
  getTopicYearSeries,
  loadCleanConcepts,
  loadTopicStats,
  questionsForTopic,
} from "@/lib/data";
import { subjectToSlug } from "@/lib/types";

type Props = { params: Promise<{ topic: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const topic = decodeURIComponent((await params).topic);
  const row = loadTopicStats().find((t) => t.topic === topic);
  const subject = row?.primary_subject || "MBBS";
  const score = row?.importance_score ?? 0;
  const n = row?.question_count ?? 0;
  const band = row?.priority_band || "";
  const q = new URLSearchParams({
    topic,
    subject,
    score: String(score),
    n: String(n),
    band,
  });
  return {
    title: `${topic} — NEET PG Priorities`,
    description: `${topic} (${subject}): importance ${score.toFixed(1)}, n=${n}. Frequency × recurrence × recency from memory-based past papers.`,
    openGraph: {
      title: `${topic} — ${subject}`,
      description: `Importance ${score.toFixed(1)} · n=${n} · ${band}`,
      images: [{ url: `/api/og/topic?${q.toString()}`, width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      images: [`/api/og/topic?${q.toString()}`],
    },
  };
}

export function generateStaticParams() {
  return loadTopicStats()
    .filter((t) => t.priority_band === "Must" || t.priority_band === "High")
    .slice(0, 80)
    .map((t) => ({ topic: t.topic }));
}

export default async function TopicPage({ params }: Props) {
  const topic = decodeURIComponent((await params).topic);
  const row = loadTopicStats().find((t) => t.topic === topic);
  if (!row) notFound();

  const series = getTopicYearSeries(topic);
  const concepts = loadCleanConcepts()
    .filter((c) => c.topic === topic)
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);
  const sampleQs = questionsForTopic(topic, 10);
  const slug = subjectToSlug(row.primary_subject);

  return (
    <div className="space-y-8">
      <FadeIn>
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          <Link href="/priorities" className="hover:text-[var(--accent)]">
            Priorities
          </Link>
          {" / "}
          <Link href={`/subjects/${slug}`} className="hover:text-[var(--accent)]">
            {row.primary_subject}
          </Link>
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold md:text-4xl">{topic}</h1>
        <div className="mt-3 flex flex-wrap items-end gap-4">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-4xl tabular-nums text-[var(--accent2)]">
                {row.importance_score.toFixed(1)}
              </span>
              <span className="text-sm chart-sub">importance</span>
            </div>
            <div className="mt-1">
              <ScoreMethodology compact />
            </div>
          </div>
          <div className="text-sm chart-sub">
            <div>
              n={row.question_count} · {row.priority_band}
              {row.due_for_return ? ` · gap ${row.years_since_last}y` : ""}
            </div>
            <div className="mt-0.5 max-w-md truncate">{row.year_list || "—"}</div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <ShareCardButton
            kind="topic"
            topic={topic}
            subject={row.primary_subject}
            score={row.importance_score}
            count={row.question_count}
            band={row.priority_band}
          />
          <WatchlistButton topic={topic} primarySubject={row.primary_subject} />
          <Link
            href={`/explore?topic=${encodeURIComponent(topic)}&subject=${encodeURIComponent(row.primary_subject)}`}
            className="text-sm text-[var(--accent)] hover:underline"
          >
            Explore questions →
          </Link>
        </div>
      </FadeIn>

      {series && (
        <section className="rounded-xl surface p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-display text-lg font-semibold">Questions per year</h2>
              <p className="text-xs chart-sub">
                Makes due-for-return gaps visible — quiet years after steady appearance.
              </p>
            </div>
            <TopicSparkline
              years={series.years}
              values={series.values}
              dueGap={row.years_since_last}
            />
          </div>
          <TopicYearBars years={series.years} values={series.values} />
        </section>
      )}

      {concepts.length > 0 && (
        <section>
          <h2 className="font-display mb-3 text-lg font-semibold">High-yield concepts</h2>
          <ul className="flex flex-wrap gap-2">
            {concepts.map((c) => (
              <li
                key={c.concept}
                className="rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm"
              >
                {c.concept}
                <span className="ml-2 text-xs chart-sub">{c.count}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {sampleQs.length > 0 && (
        <section>
          <h2 className="font-display mb-3 text-lg font-semibold">Sample questions</h2>
          <ul className="space-y-2">
            {sampleQs.map((q) => (
              <li key={q.qid} className="surface rounded-lg px-4 py-3 text-sm">
                <div className="flex flex-wrap items-center gap-2 text-xs chart-sub">
                  <span>{q.year}</span>
                  {q.images && q.images.length > 0 ? (
                    <span className="badge">Has image</span>
                  ) : (
                    q.has_image_ref && <span className="badge badge-missing">Image missing</span>
                  )}
                </div>
                <p className="mt-1 line-clamp-2">{q.question_text}</p>
                <Link
                  href={`/explore/${q.qid}`}
                  className="mt-2 inline-block text-xs text-[var(--accent)] hover:underline"
                >
                  Open explorer →
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
