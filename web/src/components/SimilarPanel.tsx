"use client";

import { useEffect, useState } from "react";
import { QuestionCard } from "@/components/QuestionCard";
import { SignInGate } from "@/components/SignInGate";
import { useUser } from "@/lib/auth";
import type { QuestionRow } from "@/lib/types";

type SimilarRow = QuestionRow & {
  rrf_score?: number;
  same_topic?: boolean;
  dense_rank?: number | null;
  sparse_rank?: number | null;
};

export function SimilarPanel({ qid }: { qid: string }) {
  const { user, configured } = useUser();
  const [rows, setRows] = useState<SimilarRow[]>([]);
  const [meta, setMeta] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const allowLocal =
      !configured || process.env.NEXT_PUBLIC_ALLOW_LOCAL_EXPLORE === "1";
    if (configured && !user && !allowLocal) return;

    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const res = await fetch("/api/similar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ qid, k: 8 }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Similar search failed");
        if (!cancelled) {
          setRows(data.results || []);
          setMeta(data.mode || "");
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [qid, user, configured]);

  return (
    <SignInGate soft={false} message="Sign in to retrieve similar past questions for this stem.">
      <div className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="font-display text-lg font-semibold">Similar past questions</h2>
          {meta && <span className="text-xs text-[var(--muted)]">mode: {meta}</span>}
        </div>
        {loading && <p className="text-sm text-[var(--muted)]">Retrieving…</p>}
        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
        <ul className="space-y-3">
          {rows.map((r) => (
            <li key={r.qid}>
              <QuestionCard
                q={r}
                showAnswers
                href={`/explore/${r.qid}`}
                meta={
                  <>
                    {r.same_topic ? (
                      <span className="badge badge-same">Same topic</span>
                    ) : (
                      <span className="badge badge-cross">Cross-topic</span>
                    )}
                    {r.rrf_score != null && (
                      <span className="text-[10px] text-[var(--muted)]">
                        score {Number(r.rrf_score).toFixed(3)}
                      </span>
                    )}
                  </>
                }
              />
            </li>
          ))}
        </ul>
      </div>
    </SignInGate>
  );
}
