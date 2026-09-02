import Link from "next/link";
import { notFound } from "next/navigation";
import { FadeIn } from "@/components/Motion";
import { QuestionCard } from "@/components/QuestionCard";
import { SimilarPanel } from "@/components/SimilarPanel";
import { getQuestion } from "@/lib/data";

export default async function ExploreQuestionPage({
  params,
}: {
  params: Promise<{ qid: string }>;
}) {
  const { qid } = await params;
  const q = getQuestion(qid);
  if (!q) notFound();

  return (
    <div className="space-y-8">
      <FadeIn>
        <p className="text-xs text-[var(--muted)]">
          <Link href="/explore" className="hover:text-[var(--accent)]">
            Explore
          </Link>{" "}
          / {qid.slice(0, 10)}…
        </p>
        <h1 className="font-display mt-2 text-2xl font-semibold">Question detail</h1>
      </FadeIn>
      <QuestionCard q={q} showAnswers />
      <SimilarPanel qid={qid} />
    </div>
  );
}
