"use client";

import Link from "next/link";
import { signInWithGoogle, signOut, useUser } from "@/lib/auth";
import { motion } from "framer-motion";

const links = [
  { href: "/priorities", label: "Priorities" },
  { href: "/insights", label: "Insights" },
  { href: "/subjects", label: "Subjects" },
  { href: "/overlaps", label: "Overlaps" },
  { href: "/drift", label: "Drift" },
  { href: "/explore", label: "Explore" },
  { href: "/packs", label: "Packs" },
];

export function SiteHeader() {
  const { user, loading, configured } = useUser();

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[rgba(7,21,26,0.85)] backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="font-display text-lg font-semibold tracking-tight">
          <span className="text-[var(--accent)]">NEET PG</span> Priorities
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="rounded-md px-2.5 py-1.5 text-sm text-[var(--muted)] transition hover:bg-white/5 hover:text-[var(--ink)]"
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {!configured ? (
            <span className="text-xs text-[var(--muted)]">Local mode</span>
          ) : loading ? (
            <span className="text-xs text-[var(--muted)]">…</span>
          ) : user ? (
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={() => signOut()}
              className="rounded-md border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--muted)] hover:text-[var(--ink)]"
            >
              Sign out
            </motion.button>
          ) : (
            <motion.button
              whileTap={{ scale: 0.97 }}
              onClick={() => signInWithGoogle()}
              className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-semibold text-[#042f2e]"
            >
              Google sign-in
            </motion.button>
          )}
        </div>
      </div>
      <div className="flex gap-2 overflow-x-auto border-t border-[var(--line)] px-4 py-2 md:hidden">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="whitespace-nowrap rounded-md bg-white/5 px-2.5 py-1 text-xs text-[var(--muted)]"
          >
            {l.label}
          </Link>
        ))}
      </div>
    </header>
  );
}
