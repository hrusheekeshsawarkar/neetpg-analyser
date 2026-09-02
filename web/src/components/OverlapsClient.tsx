"use client";

import { FadeIn } from "@/components/Motion";
import { OverlapGraph } from "@/components/viz/OverlapGraph";
import type { OverlapRow } from "@/lib/types";

export function OverlapsClient({ rows }: { rows: OverlapRow[] }) {
  return (
    <div className="space-y-6">
      <FadeIn>
        <h1 className="font-display text-3xl font-semibold">Topic & subject overlaps</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Co-occurrence when multiple topics or secondary subjects appear on the same question —
          useful for integrated revision. Hover a node to highlight its links.
        </p>
      </FadeIn>
      <OverlapGraph rows={rows} />
      <div className="overflow-x-auto rounded-xl surface">
        <table className="w-full min-w-[480px] text-left text-sm">
          <thead className="border-b border-[var(--line)] text-xs uppercase text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3">A</th>
              <th className="px-4 py-3">B</th>
              <th className="px-4 py-3">Co-occurrence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.item_a}-${r.item_b}`} className="border-b border-[var(--line)]/50">
                <td className="px-4 py-2">{r.item_a}</td>
                <td className="px-4 py-2">{r.item_b}</td>
                <td className="px-4 py-2 tabular-nums">{r.co_occurrence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
