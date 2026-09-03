"use client";

/** Yearly question counts as compact bars for topic detail. */
export function TopicYearBars({
  years,
  values,
}: {
  years: number[];
  values: number[];
}) {
  if (!years.length || values.length !== years.length) return null;
  const max = Math.max(...values, 1);

  return (
    <div className="flex items-end gap-0.5 sm:gap-1" style={{ height: 96 }}>
      {years.map((y, i) => {
        const v = values[i];
        const h = Math.max(v > 0 ? 8 : 2, (v / max) * 88);
        return (
          <div key={y} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1">
            <span className="text-[9px] tabular-nums chart-sub sm:text-[10px]">
              {v || ""}
            </span>
            <div
              className="w-full max-w-[18px] rounded-t-sm"
              style={{
                height: h,
                background: v > 0 ? "#2dd4bf" : "rgba(255,255,255,0.06)",
              }}
              title={`${y}: ${v}`}
            />
            <span className="text-[8px] chart-sub sm:text-[9px]">{String(y).slice(2)}</span>
          </div>
        );
      })}
    </div>
  );
}
