import Link from "next/link";
import { notFound } from "next/navigation";
import { FadeIn } from "@/components/Motion";
import { AskTypeChart, TopicScoreChart } from "@/components/viz/Charts";
import { WatchlistButton } from "@/components/WatchlistButton";
import {
  loadAskTypeBySubject,
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
        <div className="mt-4">
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
            {due.slice(0, 12).map((t) => (
              <div
                key={t.topic}
                className="surface flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
              >
                <span>{t.topic}</span>
                <span className="text-xs text-[var(--muted)]">
                  gap {t.years_since_last}y
                </span>
                <WatchlistButton topic={t.topic} primarySubject={subject} />
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="grid gap-6 md:grid-cols-2">
        <div>
          <h2 className="font-display mb-3 text-lg font-semibold">Topic importance</h2>
          <TopicScoreChart data={topics} />
        </div>
        <div>
          <h2 className="font-display mb-3 text-lg font-semibold">Ask-type mix</h2>
          <AskTypeChart data={askTypes} />
        </div>
      </section>

      <section>
        <h2 className="font-display mb-3 text-lg font-semibold">Frequency-ranked topics</h2>
        <div className="overflow-x-auto rounded-xl surface">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="border-b border-[var(--line)] text-xs uppercase text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Topic</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Count</th>
                <th className="px-4 py-3">Band</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {topics.map((t) => (
                <tr key={t.topic} className="border-b border-[var(--line)]/50">
                  <td className="px-4 py-2.5 font-medium">{t.topic}</td>
                  <td className="px-4 py-2.5 tabular-nums">{t.importance_score.toFixed(1)}</td>
                  <td className="px-4 py-2.5 tabular-nums">{t.question_count}</td>
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
              ))}
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
                {q.has_image_ref && <span className="badge badge-missing">Image missing</span>}
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
