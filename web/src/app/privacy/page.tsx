import { FadeIn } from "@/components/Motion";
import { DISCLAIMER } from "@/lib/types";

export default function PrivacyPage() {
  return (
    <FadeIn className="prose-pack space-y-4">
      <h1 className="font-display text-3xl font-semibold">Privacy</h1>
      <p>
        If you sign in with Google, we store your account id, email, and display name in
        Supabase Auth / <code>profiles</code> so we can gate pack downloads, similar-question
        search, and watchlists, and measure product usage (downloads, explore events).
      </p>
      <p>
        We do not sell personal data. Usage events are for product validation only.
      </p>
      <p className="text-sm text-[var(--muted)]">{DISCLAIMER}</p>
    </FadeIn>
  );
}
