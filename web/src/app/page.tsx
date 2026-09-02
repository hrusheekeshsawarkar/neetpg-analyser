import Link from "next/link";
import { FadeIn } from "@/components/Motion";
import {
  SubjectShareChart,
  TopicScoreChart,
} from "@/components/viz/Charts";
import {
  loadPriorities,
  loadSubjectTotals,
  loadTopicStats,
} from "@/lib/data";
import { MBBS_SUBJECTS, subjectToSlug } from "@/lib/types";

export default function HomePage() {
  const priorities = loadPriorities();
  const stats = loadTopicStats();
  const totals = loadSubjectTotals();
  const due = stats.filter((t) => t.due_for_return).length;
  const must = priorities.must_study_topics?.length ?? 0;
  const mustTopics = (priorities.must_study_topics || []).slice(0, 15);

  return (
    <div className="space-y-14">
      <FadeIn className="relative overflow-hidden rounded-2xl surface px-6 py-14 md:px-12">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 30%, rgba(45,212,191,0.25), transparent 35%), radial-gradient(circle at 80% 60%, rgba(240,180,41,0.18), transparent 40%)",
          }}
        />
        <p className="font-display text-sm font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
          NEET PG Priorities
        </p>
        <h1 className="font-display mt-3 max-w-2xl text-4xl font-semibold leading-tight md:text-5xl">
          High-yield topics from fifteen years of past papers — ranked for the next exam.
        </h1>
        <p className="mt-4 max-w-xl text-[var(--muted)]">
          Frequency, recurrence, and due-for-return signals across ~18k memory-based questions.
          Start with the priority list or explore interactive infographics.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/priorities"
            className="rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-[#042f2e]"
          >
            Next-exam priority list
          </Link>
          <Link
            href="/insights"
            className="rounded-md border border-[var(--line)] px-5 py-2.5 text-sm text-[var(--ink)]"
          >
            Infographics
          </Link>
          <Link
            href="/subjects"
            className="rounded-md border border-[var(--line)] px-5 py-2.5 text-sm text-[var(--ink)]"
          >
            Browse subjects
          </Link>
        </div>
        <div className="mt-10 grid max-w-lg grid-cols-3 gap-4 text-sm">
          <div>
            <div className="font-display text-2xl text-[var(--accent)]">18k+</div>
            <div className="text-[var(--muted)]">Questions</div>
          </div>
          <div>
            <div className="font-display text-2xl text-[var(--accent2)]">{must}</div>
            <div className="text-[var(--muted)]">Must-study</div>
          </div>
          <div>
            <div className="font-display text-2xl text-[var(--ink)]">{due}</div>
            <div className="text-[var(--muted)]">Due topics</div>
          </div>
        </div>
      </FadeIn>

      <FadeIn delay={0.05} className="grid gap-6 lg:grid-cols-2">
        <TopicScoreChart data={mustTopics} title="Must-study snapshot" />
        <SubjectShareChart data={totals} compact />
      </FadeIn>

      <FadeIn delay={0.1}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="font-display text-xl font-semibold">19 taught subjects</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Open a subject for frequency-ranked topics and due watchlists.
            </p>
          </div>
          <Link href="/insights" className="text-sm text-[var(--accent)] hover:underline">
            Full insights →
          </Link>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {MBBS_SUBJECTS.map((s) => {
            const n = totals.find((t) => t.subject === s)?.question_count;
            return (
              <Link
                key={s}
                href={`/subjects/${subjectToSlug(s)}`}
                className="surface rounded-lg px-3 py-3 text-sm transition hover:border-[var(--accent)]/40"
              >
                <div>{s}</div>
                {n != null && (
                  <div className="mt-1 text-xs text-[var(--muted)]">{n.toLocaleString()} Qs</div>
                )}
              </Link>
            );
          })}
        </div>
      </FadeIn>
    </div>
  );
}
