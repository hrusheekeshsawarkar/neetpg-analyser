import { FadeIn } from "@/components/Motion";
import { DriftChart } from "@/components/viz/DriftChart";
import { loadDrift } from "@/lib/data";

export default function DriftPage() {
  const rows = loadDrift();
  const rising = [...rows].sort((a, b) => b.delta_share - a.delta_share).slice(0, 20);
  const falling = [...rows].sort((a, b) => a.delta_share - b.delta_share).slice(0, 20);

  return (
    <div className="space-y-8">
      <FadeIn>
        <h1 className="font-display text-3xl font-semibold">Topic year drift</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Share of questions in recent years (≈2021–25) vs older years — rising vs cooling topics.
        </p>
      </FadeIn>

      <DriftChart rising={rising} falling={falling} />

      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-xl surface p-4">
          <h2 className="font-display text-lg font-semibold text-[var(--accent)]">Rising</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {rising.map((r) => (
              <li key={r.topic} className="flex justify-between gap-2">
                <span>{r.topic}</span>
                <span className="tabular-nums text-[var(--accent)]">
                  +{(r.delta_share * 100).toFixed(2)}pp
                </span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl surface p-4">
          <h2 className="font-display text-lg font-semibold text-[var(--danger)]">Falling</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {falling.map((r) => (
              <li key={r.topic} className="flex justify-between gap-2">
                <span>{r.topic}</span>
                <span className="tabular-nums text-[var(--danger)]">
                  {(r.delta_share * 100).toFixed(2)}pp
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
