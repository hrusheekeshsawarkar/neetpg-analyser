import { notFound } from "next/navigation";
import { FadeIn } from "@/components/Motion";
import { PackDownload } from "@/components/PackDownload";
import { loadPackMarkdown } from "@/lib/data";
import { MBBS_SUBJECTS, slugToSubject, subjectToSlug } from "@/lib/types";

export function generateStaticParams() {
  return MBBS_SUBJECTS.map((s) => ({ subject: subjectToSlug(s) }));
}

export default async function PackPage({
  params,
}: {
  params: Promise<{ subject: string }>;
}) {
  const { subject: slug } = await params;
  const name = slugToSubject(slug);
  if (!MBBS_SUBJECTS.includes(name as (typeof MBBS_SUBJECTS)[number])) {
    notFound();
  }
  const md = loadPackMarkdown(slug);
  if (!md) notFound();

  return (
    <div className="space-y-6">
      <FadeIn>
        <h1 className="font-display text-3xl font-semibold">{name} revision pack</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Generated from past-paper frequency and syllabus map. Memory-based sources only.
        </p>
        <div className="mt-4">
          <PackDownload slug={slug} />
        </div>
      </FadeIn>
      <article className="prose-pack surface rounded-xl p-6 whitespace-pre-wrap text-sm">
        {md}
      </article>
    </div>
  );
}
