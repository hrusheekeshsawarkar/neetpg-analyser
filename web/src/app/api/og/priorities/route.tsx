import { ImageResponse } from "next/og";

export const runtime = "edge";

/** Branded OG card for the priorities brief — query params optional overrides. */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const asOf = searchParams.get("asOf") || new Date().toISOString().slice(0, 10);
  const must = searchParams.get("must") || "Must-study topics from 15+ years of papers";
  const due = searchParams.get("due") || "Due-for-return watchlist included";

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "linear-gradient(160deg, #07151a 0%, #0e2a32 50%, #1a3d2f 100%)",
          padding: 56,
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          color: "#e8f2f4",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "flex",
              fontSize: 22,
              color: "#f0b429",
              letterSpacing: 3,
              textTransform: "uppercase",
              fontWeight: 600,
            }}
          >
            Shareable brief · {asOf}
          </div>
          <div style={{ display: "flex", fontSize: 58, fontWeight: 700, lineHeight: 1.1, maxWidth: 980 }}>
            Priority list for the next NEET PG
          </div>
          <div style={{ display: "flex", fontSize: 26, color: "#b8d0d6", maxWidth: 900 }}>
            {must}
          </div>
          <div style={{ display: "flex", fontSize: 24, color: "#2dd4bf" }}>{due}</div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ display: "flex", fontSize: 28, fontWeight: 600, color: "#2dd4bf" }}>
            NEET PG Priorities
          </div>
          <div style={{ display: "flex", fontSize: 18, color: "#8aa8b0", maxWidth: 420, textAlign: "right" }}>
            Memory-based sources only. Not official NBE papers. Forecasts, not guarantees.
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
