import Link from "next/link";
import { notFound } from "next/navigation";
import { FadeIn } from "@/components/Motion";
import { ScoreMethodology } from "@/components/ScoreMethodology";
import { TopicSparkline } from "@/components/TopicSparkline";
import { AskTypeChart, ConceptBars, TopicScoreChart } from "@/components/viz/Charts";
import { WatchlistButton } from "@/components/WatchlistButton";
import {
  getTopicYearSeries,
  loadAskTypeBySubject,
  loadCleanConcepts,
  loadTopicStats,
  questionsForSubject,
} from "@/lib/data";
import { MBBS_SUBJECTS, slugToSubject, subjectToSlug } from "@/lib/types";

export function generateStaticParams() {
  return MBBS_SUBJECTS.map((s) => ({ subject: subjectToSlug(s) }));
}

export default async function SubjectPage({
  params,
}: {
  params: Promise<{ subject: string }>;
}) {
  const { subject: slug } = await params;
  const subject = slugToSubject(slug);
  if (!MBBS_SUBJECTS.includes(subject as (typeof MBBS_SUBJECTS)[number])) {
    notFound();
  }

  const topics = loadTopicStats()
    .filter((t) => t.primary_subject === subject)
    .sort((a, b) => b.importance_score - a.importance_score);
  const due = topics.filter((t) => t.due_for_return);
  const askTypes = loadAskTypeBySubject().filter((a) => a.subject === subject);
  const sampleQs = questionsForSubject(subject, 12);
  const topTopicNames = topics.slice(0, 6).map((t) => t.topic);
  const allConcepts = loadCleanConcepts();
  const conceptGroups = topTopicNames
    .map((topic) => ({
      topic,
      concepts: allConcepts
        .filter((c) => c.topic === topic)
        .sort((a, b) => b.count - a.count)
        .slice(0, 5),
    }))
    .filter((g) => g.concepts.length > 0)
    .slice(0, 4);

  return (
    <div className="space-y-8">
      <FadeIn>
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          <Link href="/subjects" className="hover:text-[var(--accent)]">
            Subjects
          </Link>{" "}
          / {subject}
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold">{subject}</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          {topics.length} scored topics · {due.length} due for return
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <ScoreMethodology compact />
          <Link
            href={`/packs/${slug}`}
            className="text-sm text-[var(--accent)] hover:underline"
          >
            Download revision pack →
          </Link>
        </div>
      </FadeIn>

      {due.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-lg font-semibold text-[var(--accent2)]">
            Due for return
          </h2>
          <div className="flex flex-wrap gap-2">
            {due.slice(0, 12).map((t) => {
              const series = getTopicYearSeries(t.topic);
              return (
                <div
                  key={t.topic}
                  className="surface flex max-w-full flex-wrap items-center gap-2 rounded-lg px-3 py-2 text-sm"
                >
                  <Link
                    href={`/topics/${encodeURIComponent(t.topic)}`}
                    className="hover:text-[var(--accent)]"
                  >
                    {t.topic}
                  </Link>
                  <span className="text-xs text-[var(--muted)]">gap {t.years_since_last}y</span>
                  {series && (
                    <TopicSparkline
                      years={series.years}
                      values={series.values}
                      dueGap={t.years_since_last}
                    />
                  )}
                  <WatchlistButton topic={t.topic} primarySubject={subject} />
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section className="grid gap-6 md:grid-cols-2">
        <TopicScoreChart data={topics} />
        <AskTypeChart data={askTypes} />
      </section>

      {conceptGroups.length > 0 && <ConceptBars groups={conceptGroups} />}

      <section>
        <h2 className="font-display mb-3 text-lg font-semibold">Frequency-ranked topics</h2>

        {/* Mobile cards */}
        <ul className="space-y-3 md:hidden">
          {topics.map((t) => {
            const series = getTopicYearSeries(t.topic);
            return (
              <li key={t.topic} className="surface rounded-xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      href={`/topics/${encodeURIComponent(t.topic)}`}
                      className="font-medium hover:text-[var(--accent)]"
                    >
                      {t.topic}
                    </Link>
                    <div className="mt-1 text-xs chart-sub">
                      {t.priority_band}
                      {t.due_for_return ? ` · gap ${t.years_since_last}y` : ""}
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="font-display text-lg tabular-nums text-[var(--accent2)]">
                      {t.importance_score.toFixed(1)}
                    </div>
                    <div className="text-[10px] chart-sub">n={t.question_count}</div>
                  </div>
                </div>
                {series && (
                  <div className="mt-3">
                    <TopicSparkline
                      years={series.years}
                      values={series.values}
                      dueGap={t.years_since_last}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        {/* Desktop table */}
        <div className="hidden overflow-x-auto rounded-xl surface md:block">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-[var(--line)] text-xs uppercase text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Topic</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Count</th>
                <th className="px-4 py-3">Trend</th>
                <th className="px-4 py-3">Band</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {topics.map((t) => {
                const series = getTopicYearSeries(t.topic);
                return (
                  <tr key={t.topic} className="border-b border-[var(--line)]/50">
                    <td className="px-4 py-2.5 font-medium">
                      <Link
                        href={`/topics/${encodeURIComponent(t.topic)}`}
                        className="hover:text-[var(--accent)]"
                      >
                        {t.topic}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 tabular-nums">
                      {t.importance_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums">{t.question_count}</td>
                    <td className="px-4 py-2.5">
                      {series ? (
                        <TopicSparkline
                          years={series.years}
                          values={series.values}
                          dueGap={t.years_since_last}
                        />
                      ) : (
                        <span className="chart-sub">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--muted)]">{t.priority_band}</td>
                    <td className="px-4 py-2.5">
                      <Link
                        href={`/explore?topic=${encodeURIComponent(t.topic)}&subject=${encodeURIComponent(subject)}`}
                        className="text-xs text-[var(--accent)] hover:underline"
                      >
                        Explore Qs
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="font-display mb-3 text-lg font-semibold">Sample questions</h2>
        <p className="mb-3 text-sm text-[var(--muted)]">
          Sign in to open similar-question retrieval for any stem.
        </p>
        <ul className="space-y-2">
          {sampleQs.map((q) => (
            <li key={q.qid} className="surface rounded-lg px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
                <span>{q.year}</span>
                <span>·</span>
                <span>{q.topic_clean}</span>
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
    </div>
  );
}
