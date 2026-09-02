"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
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
    ...rising.slice(0, 8).map((r) => ({
      name: r.topic.length > 16 ? r.topic.slice(0, 14) + "…" : r.topic,
      delta: +(r.delta_share * 100).toFixed(2),
    })),
    ...falling.slice(0, 8).map((r) => ({
      name: r.topic.length > 16 ? r.topic.slice(0, 14) + "…" : r.topic,
      delta: +(r.delta_share * 100).toFixed(2),
    })),
  ];

  return (
    <div className="h-80 w-full rounded-xl surface p-3">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="rgba(45,212,191,0.08)" vertical={false} />
          <XAxis dataKey="name" stroke="#8aa8b0" tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={70} />
          <YAxis stroke="#8aa8b0" tick={{ fontSize: 11 }} unit="pp" />
          <Tooltip
            contentStyle={{
              background: "#0c2229",
              border: "1px solid rgba(45,212,191,0.25)",
              borderRadius: 8,
            }}
          />
          <Bar dataKey="delta" fill="#2dd4bf" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
