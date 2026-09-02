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

export function TopicScoreChart({
  data,
}: {
  data: Array<{ topic: string; importance_score: number; question_count: number }>;
}) {
  const chartData = data.slice(0, 15).map((d) => ({
    name: d.topic.length > 18 ? d.topic.slice(0, 16) + "…" : d.topic,
    score: d.importance_score,
    count: d.question_count,
  }));

  return (
    <div className="h-72 w-full rounded-xl surface p-3">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 12 }}>
          <CartesianGrid stroke="rgba(45,212,191,0.08)" horizontal={false} />
          <XAxis type="number" stroke="#8aa8b0" tick={{ fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="name"
            width={110}
            stroke="#8aa8b0"
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              background: "#0c2229",
              border: "1px solid rgba(45,212,191,0.25)",
              borderRadius: 8,
            }}
          />
          <Bar dataKey="score" fill="#2dd4bf" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function AskTypeChart({
  data,
}: {
  data: Array<{ ask_type: string; count: number }>;
}) {
  const chartData = [...data]
    .sort((a, b) => b.count - a.count)
    .slice(0, 8)
    .map((d) => ({
      name: d.ask_type.replace(/_/g, " "),
      count: d.count,
    }));

  return (
    <div className="h-64 w-full rounded-xl surface p-3">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid stroke="rgba(45,212,191,0.08)" vertical={false} />
          <XAxis dataKey="name" stroke="#8aa8b0" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} />
          <YAxis stroke="#8aa8b0" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: "#0c2229",
              border: "1px solid rgba(45,212,191,0.25)",
              borderRadius: 8,
            }}
          />
          <Bar dataKey="count" fill="#f0b429" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
