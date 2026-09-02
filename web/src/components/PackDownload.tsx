"use client";

import { signInWithGoogle, useUser } from "@/lib/auth";

export function PackDownload({ slug }: { slug: string }) {
  const { user, configured } = useUser();

  async function download() {
    if (configured && !user) {
      await signInWithGoogle();
      return;
    }
    const res = await fetch(`/api/packs/${slug}`);
    if (res.status === 401) {
      await signInWithGoogle();
      return;
    }
    if (!res.ok) {
      alert("Download failed");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}-revision-pack.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      type="button"
      onClick={download}
      className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[#042f2e]"
    >
      {configured && !user ? "Sign in to download" : "Download markdown"}
    </button>
  );
}
