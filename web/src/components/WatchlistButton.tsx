"use client";

import { signInWithGoogle, useUser } from "@/lib/auth";
import { useState } from "react";

export function WatchlistButton({
  topic,
  primarySubject,
}: {
  topic: string;
  primarySubject: string;
}) {
  const { user, configured } = useUser();
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onClick() {
    if (!configured) {
      alert("Connect Supabase + Google sign-in to save a watchlist.");
      return;
    }
    if (!user) {
      await signInWithGoogle();
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, primary_subject: primarySubject }),
      });
      if (res.ok) setSaved(true);
      else {
        const j = await res.json().catch(() => ({}));
        alert(j.error || "Could not save");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      disabled={busy || saved}
      onClick={onClick}
      className="text-[10px] uppercase tracking-wide text-[var(--accent)] hover:underline disabled:opacity-50"
    >
      {saved ? "Saved" : "Watch"}
    </button>
  );
}
