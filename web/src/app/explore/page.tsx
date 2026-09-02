import Link from "next/link";
import { FadeIn } from "@/components/Motion";
import { QuestionCard } from "@/components/QuestionCard";
import { SignInGate } from "@/components/SignInGate";
import { questionsForSubject, questionsForTopic, loadQuestions } from "@/lib/data";

export default async function ExploreIndexPage({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string; subject?: string; q?: string }>;
}) {
  const sp = await searchParams;
  let list = loadQuestions().slice(0, 24);
  if (sp.topic) list = questionsForTopic(sp.topic, 40);
  else if (sp.subject) list = questionsForSubject(sp.subject, 40);
  if (sp.q) {
    const needle = sp.q.toLowerCase();
    list = loadQuestions()
      .filter((x) => (x.question_text || "").toLowerCase().includes(needle))
      .slice(0, 40);
  }

  return (
    <div className="space-y-6">
      <FadeIn>
        <h1 className="font-display text-3xl font-semibold">Explore questions</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Browse stems by subject or topic. Opening a question runs hybrid similar-question
          retrieval (sign-in required when Supabase Auth is configured).
        </p>
        {(sp.topic || sp.subject) && (
          <p className="mt-2 text-sm text-[var(--accent)]">
            Filter: {sp.subject || ""} {sp.topic ? `· ${sp.topic}` : ""}
          </p>
        )}
      </FadeIn>

      <SignInGate soft>
        <form className="flex flex-wrap gap-2" action="/explore" method="get">
          <input
            name="q"
            defaultValue={sp.q}
            placeholder="Filter by keyword…"
            className="min-w-[220px] flex-1 rounded-md border border-[var(--line)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
          />
          <button
            type="submit"
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[#042f2e]"
          >
            Search
          </button>
        </form>
      </SignInGate>

      <ul className="space-y-3">
        {list.map((q) => (
          <li key={q.qid}>
            <QuestionCard q={q} showAnswers={false} href={`/explore/${q.qid}`} />
          </li>
        ))}
      </ul>
      {list.length === 0 && (
        <p className="text-sm text-[var(--muted)]">
          No questions loaded. Run{" "}
          <code className="text-[var(--accent)]">python analysis/sync/seed_supabase.py --local-only</code>{" "}
          so the mirror exists.
        </p>
      )}
      <p className="text-xs text-[var(--muted)]">
        <Link href="/subjects" className="text-[var(--accent)] hover:underline">
          Back to subjects
        </Link>
      </p>
    </div>
  );
}
