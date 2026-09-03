"use client";

import { useId, useState } from "react";
import { SCORE_BANDS, SCORE_BLURB, SCORE_WEIGHTS } from "@/lib/scoring";

export function ScoreMethodology({ compact = false }: { compact?: boolean }) {
  const id = useId();
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="inline-flex items-center gap-1 rounded-md border border-[var(--line)] bg-white/5 px-2 py-0.5 text-[11px] text-[#c5d9de] transition hover:border-[var(--accent)]/40 hover:text-[var(--ink)]"
      >
        {compact ? "How scored?" : "Frequency × recurrence × recency"}
        <span aria-hidden className="text-[var(--accent)]">
          ▾
        </span>
      </button>
      {open && (
        <div
          id={id}
          role="dialog"
          className="absolute left-0 top-full z-30 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-[var(--line)] bg-[#0c2229] p-3 text-left shadow-xl"
        >
          <p className="text-xs leading-relaxed text-[#e8f2f4]">{SCORE_BLURB}</p>
          <ul className="mt-3 space-y-2">
            {SCORE_WEIGHTS.map((w) => (
              <li key={w.key} className="text-xs">
                <div className="mb-1 flex justify-between gap-2 text-[var(--ink)]">
                  <span className="font-medium">{w.label}</span>
                  <span className="tabular-nums text-[var(--accent)]">{w.weight}%</span>
                </div>
                <div className="mb-1 h-1.5 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="h-full rounded-full bg-[var(--accent)]"
                    style={{ width: `${w.weight * 2.2}%` }}
                  />
                </div>
                <p className="chart-sub">{w.detail}</p>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex flex-wrap gap-2 border-t border-[var(--line)] pt-2">
            {SCORE_BANDS.map((b) => (
              <span
                key={b.band}
                className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
                style={{ background: `${b.color}22`, color: b.color }}
              >
                {b.band} ≥ {b.min}
              </span>
            ))}
          </div>
        </div>
      )}
    </span>
  );
}
