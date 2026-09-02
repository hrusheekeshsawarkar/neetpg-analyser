import { DISCLAIMER } from "@/lib/types";

export function DisclaimerBanner({ extra }: { extra?: string }) {
  return (
    <div className="disclaimer-bar px-4 py-2 text-center">
      <strong className="font-semibold">Disclaimer:</strong> {extra || DISCLAIMER}
    </div>
  );
}

export function DisclaimerFooter() {
  return (
    <footer className="mt-16 border-t border-[var(--line)] px-4 py-8 text-center text-xs text-[var(--muted)]">
      <p className="mx-auto max-w-3xl">{DISCLAIMER}</p>
      <p className="mt-2">Educational / practice use only. ~18k memory-based questions, 2010–2025.</p>
      <p className="mt-2">
        <a href="/privacy" className="text-[var(--accent)] hover:underline">
          Privacy
        </a>
      </p>
    </footer>
  );
}
