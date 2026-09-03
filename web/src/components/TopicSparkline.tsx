"use client";

/** Tiny year-count sparkline (SVG). */
export function TopicSparkline({
  years,
  values,
  dueGap,
  className = "",
}: {
  years: number[];
  values: number[];
  dueGap?: number;
  className?: string;
}) {
  if (!years.length || values.length !== years.length) return null;
  const w = 120;
  const h = 28;
  const max = Math.max(...values, 1);
  const step = years.length > 1 ? w / (years.length - 1) : w;
  const points = values
    .map((v, i) => {
      const x = i * step;
      const y = h - 2 - (v / max) * (h - 6);
      return `${x},${y}`;
    })
    .join(" ");

  const lastIdx = values.length - 1;
  // highlight last non-zero / gap visually
  const quiet = dueGap != null && dueGap >= 1;

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width={w}
      height={h}
      className={className}
      role="img"
      aria-label={`Yearly question counts ${years[0]}–${years[years.length - 1]}`}
    >
      <polyline
        fill="none"
        stroke={quiet ? "#f0b429" : "#2dd4bf"}
        strokeWidth="1.75"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
      {values.map((v, i) =>
        v > 0 ? (
          <circle
            key={years[i]}
            cx={i * step}
            cy={h - 2 - (v / max) * (h - 6)}
            r={i === lastIdx ? 2.4 : 1.4}
            fill={quiet && i === lastIdx ? "#f0b429" : "#e8f2f4"}
          />
        ) : null,
      )}
    </svg>
  );
}
