"use client";

import { signInWithGoogle, useUser } from "@/lib/auth";
import type { ReactNode } from "react";

/** Soft gate: shows children always, plus a sign-in nudge when logged out. */
export function SignInGate({
  children,
  soft = false,
  message = "Sign in with Google to run similar-question retrieval and download packs.",
}: {
  children?: ReactNode;
  soft?: boolean;
  message?: string;
}) {
  const { user, loading, configured } = useUser();

  if (!configured) {
    return (
      <div className="space-y-3">
        <div className="rounded-lg border border-[var(--line)] bg-white/5 px-3 py-2 text-xs text-[var(--muted)]">
          Local mode (Supabase not configured). Explore uses on-device sparse similarity; pack
          downloads and watchlists need Google Auth.
        </div>
        {children}
      </div>
    );
  }

  if (loading) {
    return <p className="text-sm text-[var(--muted)]">Checking session…</p>;
  }

  if (!user) {
    return (
      <div className="space-y-4">
        <div className="surface rounded-xl p-5">
          <p className="text-sm text-[var(--muted)]">{message}</p>
          <button
            type="button"
            onClick={() => signInWithGoogle()}
            className="mt-3 rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[#042f2e]"
          >
            Google sign-in
          </button>
        </div>
        {soft ? children : null}
      </div>
    );
  }

  return <>{children}</>;
}
