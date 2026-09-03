"use client";

import { useState } from "react";
import { prioritiesSharePath, topicSharePath } from "@/lib/scoring";

type TopicShareProps = {
  kind: "topic";
  topic: string;
  subject: string;
  score: number;
  count: number;
  band: string;
};

type PrioritiesShareProps = {
  kind: "priorities";
};

export function ShareCardButton(
  props: (TopicShareProps | PrioritiesShareProps) & { compact?: boolean },
) {
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const compact = props.compact ?? false;

  const ogPath =
    props.kind === "priorities"
      ? prioritiesSharePath()
      : topicSharePath(props.topic, props.subject) +
        `&score=${props.score}&n=${props.count}&band=${encodeURIComponent(props.band)}`;

  async function absoluteOgUrl() {
    return `${window.location.origin}${ogPath}`;
  }

  async function download() {
    setBusy(true);
    try {
      const url = await absoluteOgUrl();
      const res = await fetch(url);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download =
        props.kind === "priorities"
          ? "neetpg-priorities.png"
          : `neetpg-${props.topic.toLowerCase().replace(/\s+/g, "-").slice(0, 40)}.png`;
      a.click();
      URL.revokeObjectURL(a.href);
    } finally {
      setBusy(false);
    }
  }

  async function copyLink() {
    const url = await absoluteOgUrl();
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }

  async function shareNative() {
    const url = await absoluteOgUrl();
    if (navigator.share) {
      try {
        await navigator.share({
          title:
            props.kind === "priorities"
              ? "NEET PG Priorities"
              : `${props.topic} — NEET PG Priorities`,
          text:
            props.kind === "priorities"
              ? "Next-exam priority list from memory-based past papers"
              : `${props.topic} (${props.subject}) — score ${props.score}`,
          url: props.kind === "priorities" ? window.location.origin + "/priorities" : url,
        });
        return;
      } catch {
        /* fall through */
      }
    }
    await copyLink();
  }

  const btn =
    "rounded-md border border-[var(--line)] px-2.5 py-1 text-[11px] text-[var(--ink)] hover:border-[var(--accent)]/40 disabled:opacity-60";

  return (
    <div className="inline-flex flex-wrap gap-1.5">
      <button
        type="button"
        disabled={busy}
        onClick={download}
        className={
          compact
            ? btn
            : "rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-semibold text-[#042f2e] disabled:opacity-60"
        }
      >
        {busy ? "…" : compact ? "PNG" : "Download card"}
      </button>
      <button type="button" onClick={shareNative} className={compact ? btn : `${btn} px-3 py-1.5 text-xs`}>
        {copied ? "Copied" : "Share"}
      </button>
      {!compact && (
        <a
          href={ogPath}
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs text-[#c5d9de] hover:text-[var(--ink)]"
        >
          Preview
        </a>
      )}
    </div>
  );
}
