"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DriftRow } from "@/lib/types";

export function DriftChart({
  rising,
  falling,
}: {
  rising: DriftRow[];
  falling: DriftRow[];
}) {
  const data = [
    ...rising.slice(0, 10).map((r) => ({
      name: r.topic.length > 16 ? r.topic.slice(0, 14) + "…" : r.topic,
      full: r.topic,
      delta: +(r.delta_share * 100).toFixed(2),
    })),
    ...falling
      .slice(0, 10)
      .reverse()
      .map((r) => ({
        name: r.topic.length > 16 ? r.topic.slice(0, 14) + "…" : r.topic,
        full: r.topic,
        delta: +(r.delta_share * 100).toFixed(2),
      })),
  ];

  return (
    <div className="h-96 w-full rounded-xl surface p-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ bottom: 48 }}>
          <CartesianGrid stroke="rgba(45,212,191,0.08)" vertical={false} />
          <XAxis
            dataKey="name"
            stroke="#8aa8b0"
            tick={{ fontSize: 10 }}
            interval={0}
            angle={-28}
            textAnchor="end"
            height={70}
          />
          <YAxis stroke="#8aa8b0" tick={{ fontSize: 11 }} unit="pp" />
          <ReferenceLine y={0} stroke="#8aa8b0" />
          <Tooltip
            contentStyle={{
              background: "#0c2229",
              border: "1px solid rgba(45,212,191,0.25)",
              borderRadius: 8,
            }}
            formatter={(value, _n, item) => [
              `${value} pp`,
              (item?.payload as { full?: string })?.full || "Δ share",
            ]}
          />
          <Bar dataKey="delta" radius={[4, 4, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.full} fill={d.delta >= 0 ? "#2dd4bf" : "#f07178"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
