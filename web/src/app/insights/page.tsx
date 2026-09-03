import { FadeIn } from "@/components/Motion";
import { ScoreMethodology } from "@/components/ScoreMethodology";
import { ShareCardButton } from "@/components/ShareCardButton";
import {
  ConceptBars,
  ImportanceBandBars,
  StackedAskTypeChart,
  SubjectShareChart,
  TopicScoreChart,
  YearSubjectHeatmap,
} from "@/components/viz/Charts";
import {
  loadAskTypeShare,
  loadCleanConcepts,
  loadSubjectTotals,
  loadTopicStats,
  loadYearSubjectMatrix,
} from "@/lib/data";

export const metadata = {
  title: "Insights & infographics — NEET PG Priorities",
  description:
    "Interactive charts: subject share, year mix, ask-types, topic importance, and high-yield concepts from memory-based past papers.",
};

export default function InsightsPage() {
  const totals = loadSubjectTotals();
  const yearSubj = loadYearSubjectMatrix();
  const askShare = loadAskTypeShare();
  const topics = loadTopicStats()
    .filter((t) => t.priority_band === "Must" || t.priority_band === "High")
    .sort((a, b) => b.importance_score - a.importance_score);
  const concepts = loadCleanConcepts();
  const topTopicNames = topics.slice(0, 8).map((t) => t.topic);
  const conceptGroups = topTopicNames
    .map((topic) => ({
      topic,
      concepts: concepts
        .filter((c) => c.topic === topic)
        .sort((a, b) => b.count - a.count)
        .slice(0, 5),
    }))
    .filter((g) => g.concepts.length > 0)
    .slice(0, 4);

  const nQ = totals.reduce((a, t) => a + t.question_count, 0);

  return (
    <div className="space-y-8">
      <FadeIn>
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent)]">
          Infographics
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold md:text-4xl">
          Insights from {nQ > 0 ? nQ.toLocaleString() : "18k+"} past questions
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Interactive versions of the analysis plots — subject volume, year mix, how questions
          are asked, and cleaned high-yield concepts. Memory-based sources only.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <ScoreMethodology />
          <ShareCardButton kind="priorities" />
        </div>
      </FadeIn>

      <div className="grid gap-6 lg:grid-cols-2">
        <SubjectShareChart data={totals} />
        <TopicScoreChart
          data={topics.slice(0, 18)}
          title="Highest-importance topics"
        />
      </div>

      <YearSubjectHeatmap
        years={yearSubj.years}
        subjects={yearSubj.subjects}
        matrix={yearSubj.matrix}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <StackedAskTypeChart data={askShare} />
        <ImportanceBandBars
          data={topics.slice(0, 20).map((t) => ({
            topic: t.topic,
            primary_subject: t.primary_subject,
            importance_score: t.importance_score,
            priority_band: t.priority_band,
            question_count: t.question_count,
          }))}
        />
      </div>

      {conceptGroups.length > 0 && <ConceptBars groups={conceptGroups} />}
    </div>
  );
}
