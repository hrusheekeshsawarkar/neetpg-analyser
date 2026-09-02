import Link from "next/link";
import { FadeIn } from "@/components/Motion";
import { loadTopicStats } from "@/lib/data";
import { MBBS_SUBJECTS, subjectToSlug } from "@/lib/types";

export default function SubjectsIndexPage() {
  const stats = loadTopicStats();
  const bySubject = Object.fromEntries(
    MBBS_SUBJECTS.map((s) => [
      s,
      stats.filter((t) => t.primary_subject === s).length,
    ]),
  );

  return (
    <div className="space-y-6">
      <FadeIn>
        <h1 className="font-display text-3xl font-semibold">Subjects</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Frequency-ranked topics, due-for-return strips, and ask-type mix per taught subject.
        </p>
      </FadeIn>
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        {MBBS_SUBJECTS.map((s) => (
          <Link
            key={s}
            href={`/subjects/${subjectToSlug(s)}`}
            className="surface rounded-xl p-4 transition hover:border-[var(--accent)]/40"
          >
            <div className="font-display text-lg font-semibold">{s}</div>
            <div className="mt-1 text-sm text-[var(--muted)]">
              {bySubject[s] || 0} scored topics
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
