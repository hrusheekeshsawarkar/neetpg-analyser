import { ImageResponse } from "next/og";

export const runtime = "edge";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const topic = searchParams.get("topic") || "Topic";
  const subject = searchParams.get("subject") || "MBBS";
  const scoreNum = Number(searchParams.get("score") || 0);
  const count = searchParams.get("n") || "";
  const band = searchParams.get("band") || "";

  const bandColor =
    band === "Must" ? "#f07178" : band === "High" ? "#f0b429" : "#2dd4bf";

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "linear-gradient(145deg, #07151a 0%, #0c2229 55%, #123038 100%)",
          padding: 56,
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          color: "#e8f2f4",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div
            style={{
              display: "flex",
              fontSize: 22,
              color: "#2dd4bf",
              letterSpacing: 4,
              textTransform: "uppercase",
              fontWeight: 600,
            }}
          >
            NEET PG Priorities
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 54,
              fontWeight: 700,
              lineHeight: 1.15,
              maxWidth: 960,
            }}
          >
            {topic.slice(0, 80)}
          </div>
          <div style={{ display: "flex", fontSize: 28, color: "#b8d0d6" }}>{subject}</div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
              <span style={{ fontSize: 72, fontWeight: 700, color: bandColor }}>
                {scoreNum ? scoreNum.toFixed(1) : "—"}
              </span>
              <span style={{ fontSize: 28, color: "#b8d0d6" }}>importance</span>
            </div>
            <div style={{ display: "flex", gap: 16, fontSize: 24, color: "#c5d9de" }}>
              {count ? <span>n = {count}</span> : null}
              {band ? (
                <span
                  style={{
                    background: "rgba(255,255,255,0.08)",
                    padding: "4px 14px",
                    borderRadius: 8,
                    color: bandColor,
                    fontWeight: 600,
                  }}
                >
                  {band}
                </span>
              ) : null}
            </div>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              fontSize: 18,
              color: "#8aa8b0",
              maxWidth: 320,
              textAlign: "right",
            }}
          >
            Frequency × recurrence × recency
            <span style={{ marginTop: 6 }}>Memory-based · not official NBE</span>
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
