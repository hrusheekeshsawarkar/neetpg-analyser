import Link from "next/link";
import { FadeIn } from "@/components/Motion";
import { MBBS_SUBJECTS, subjectToSlug } from "@/lib/types";

export default function PacksIndexPage() {
  return (
    <div className="space-y-6">
      <FadeIn>
        <h1 className="font-display text-3xl font-semibold">Revision packs</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Per-subject markdown packs generated from the analysis pipeline. Download is gated
          behind Google sign-in when Supabase Auth is configured.
        </p>
      </FadeIn>
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        {MBBS_SUBJECTS.map((s) => (
          <Link
            key={s}
            href={`/packs/${subjectToSlug(s)}`}
            className="surface rounded-xl p-4 transition hover:border-[var(--accent)]/40"
          >
            <div className="font-display font-semibold">{s}</div>
            <div className="mt-1 text-xs text-[var(--muted)]">View & download</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
