"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ScoreMethodology } from "@/components/ScoreMethodology";

const AXIS = "#c5d9de";
const GRID = "rgba(45,212,191,0.1)";

const tipStyle = {
  background: "#0c2229",
  border: "1px solid rgba(45,212,191,0.35)",
  borderRadius: 8,
  fontSize: 12,
  color: "#e8f2f4",
};

const tipLabelStyle = { color: "#e8f2f4", fontWeight: 600 as const };
const tipItemStyle = { color: "#c5d9de" };

const BAND: Record<string, string> = {
  Must: "#f07178",
  High: "#f0b429",
  Medium: "#2dd4bf",
  Low: "#5a7a82",
};

const ASK_COLORS = [
  "#2dd4bf",
  "#f0b429",
  "#60a5fa",
  "#f07178",
  "#a78bfa",
  "#34d399",
  "#fb923c",
  "#94a3b8",
  "#e879f9",
  "#38bdf8",
];

function pctTick(v: number) {
  return `${Math.round(Number(v))}%`;
}

function ChartShell({
  title,
  subtitle,
  children,
  tall = false,
  extraTall = false,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  tall?: boolean;
  extraTall?: boolean;
}) {
  const height = extraTall ? "h-[34rem]" : tall ? "h-96" : "h-72";
  return (
    <div className="rounded-xl surface p-4">
      {title && (
        <div className="mb-3">
          <h3 className="font-display text-base font-semibold text-[var(--ink)]">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs chart-sub">{subtitle}</p>
          )}
        </div>
      )}
      <div className={`${height} w-full`}>{children}</div>
    </div>
  );
}

export function TopicScoreChart({
  data,
  title = "Topic importance",
}: {
  data: Array<{
    topic: string;
    importance_score: number;
    question_count: number;
    priority_band?: string;
  }>;
  title?: string;
}) {
  const chartData = data.slice(0, 18).map((d) => ({
    name: d.topic.length > 20 ? d.topic.slice(0, 18) + "..." : d.topic,
    full: d.topic,
    score: d.importance_score,
    count: d.question_count,
    band: d.priority_band || "Medium",
  }));

  return (
    <ChartShell title={title} subtitle="Frequency × recurrence × recency" tall>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 4, right: 12 }}>
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis
            type="number"
            stroke={AXIS}
            tick={{ fill: AXIS, fontSize: 11 }}
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={118}
            stroke={AXIS}
            tick={{ fill: AXIS, fontSize: 10 }}
            interval={0}
          />
          <Tooltip
            contentStyle={tipStyle}
            labelStyle={tipLabelStyle}
            itemStyle={tipItemStyle}
            formatter={(value, _n, item) => {
              const p = item?.payload as { count?: number; band?: string; full?: string };
              return [
                `${Number(value).toFixed(1)} · n=${p?.count ?? "—"} · ${p?.band ?? ""}`,
                p?.full || "Score",
              ];
            }}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {chartData.map((d) => (
              <Cell key={d.full} fill={BAND[d.band] || BAND.Medium} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
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
    <ChartShell title="Ask-type mix" subtitle="How this subject is tested">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            dataKey="name"
            stroke={AXIS}
            tick={{ fill: AXIS, fontSize: 10 }}
            interval={0}
            angle={-18}
            textAnchor="end"
            height={58}
          />
          <YAxis stroke={AXIS} tick={{ fill: AXIS, fontSize: 11 }} />
          <Tooltip
            contentStyle={tipStyle}
            labelStyle={tipLabelStyle}
            itemStyle={tipItemStyle}
          />
          <Bar dataKey="count" fill="#f0b429" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function SubjectShareChart({
  data,
  compact = false,
}: {
  data: Array<{ subject: string; question_count: number; share: number }>;
  compact?: boolean;
}) {
  const chartData = [...data]
    .filter((d) => d.question_count > 0)
    .sort((a, b) => a.question_count - b.question_count)
    .map((d) => ({
      name: d.subject,
      count: d.question_count,
      pct: +(d.share * 100).toFixed(1),
    }));

  const shown = compact ? chartData.slice(-12) : chartData;
  const n = shown.length;

  return (
    <ChartShell
      title="Questions by subject"
      subtitle={
        compact
          ? `Top ${n} subjects by volume`
          : `All ${n} taught MBBS subjects`
      }
      tall={compact}
      extraTall={!compact}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={shown}
          layout="vertical"
          margin={{ left: 8, right: 16, top: 4, bottom: 4 }}
        >
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis
            type="number"
            stroke={AXIS}
            tick={{ fill: AXIS, fontSize: 11 }}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={128}
            stroke={AXIS}
            tick={{ fill: AXIS, fontSize: 11 }}
            interval={0}
          />
          <Tooltip
            contentStyle={tipStyle}
            labelStyle={tipLabelStyle}
            itemStyle={tipItemStyle}
            formatter={(value, _n, item) => {
              const p = item?.payload as { pct?: number };
              return [`${value} (${p?.pct ?? 0}%)`, "Questions"];
            }}
          />
          <Bar dataKey="count" fill="#2dd4bf" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function YearSubjectHeatmap({
  years,
  subjects,
  matrix,
}: {
  years: number[];
  subjects: string[];
  matrix: Record<string, Record<number, number>>;
}) {
  const ranked = [...subjects]
    .map((s) => ({
      s,
      total: years.reduce((a, y) => a + (matrix[s]?.[y] || 0), 0),
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 12)
    .map((x) => x.s);

  const yearTotals: Record<number, number> = {};
  for (const y of years) {
    yearTotals[y] = subjects.reduce((a, s) => a + (matrix[s]?.[y] || 0), 0) || 1;
  }

  return (
    <div className="rounded-xl surface p-3 sm:p-4">
      <h3 className="font-display text-base font-semibold text-[var(--ink)]">
        Subject mix across years
      </h3>
      <p className="mt-0.5 mb-2 text-xs chart-sub">
        Cell color = share of that year&apos;s questions (top 12 subjects)
      </p>
      <p className="mb-2 text-[10px] chart-sub sm:hidden">Swipe sideways for years →</p>
      <div className="-mx-1 overflow-x-auto overscroll-x-contain pb-1">
        <table className="w-full min-w-[540px] border-separate border-spacing-0.5 text-[9px] sm:min-w-[720px] sm:text-[10px]">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-[#0c2229] px-1.5 py-1 text-left chart-sub sm:px-2">
                Subject
              </th>
              {years.map((y) => (
                <th key={y} className="px-0.5 py-1 font-normal chart-sub sm:px-1">
                  {String(y).slice(2)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ranked.map((s) => (
              <tr key={s}>
                <td className="sticky left-0 z-10 max-w-[5.5rem] truncate bg-[#0c2229] px-1.5 py-0.5 text-[var(--ink)] sm:max-w-none sm:whitespace-nowrap sm:px-2">
                  {s}
                </td>
                {years.map((y) => {
                  const n = matrix[s]?.[y] || 0;
                  const share = n / yearTotals[y];
                  const alpha = 0.12 + share * 3.2;
                  return (
                    <td
                      key={y}
                      title={`${s} ${y}: ${n} Qs (${(share * 100).toFixed(1)}%)`}
                      className="px-0.5 py-0.5 text-center tabular-nums"
                      style={{
                        background: `rgba(45, 212, 191, ${Math.min(alpha, 0.92)})`,
                        color: share > 0.12 ? "#042f2e" : "#9bb8c0",
                        minWidth: 22,
                      }}
                    >
                      {n || "·"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StackedAskTypeChart({
  data,
}: {
  data: Array<{ subject: string; ask_type: string; count: number; share?: number }>;
}) {
  const bySub = new Map<string, Record<string, number>>();
  const askTypes = new Set<string>();
  for (const r of data) {
    if (!bySub.has(r.subject)) bySub.set(r.subject, {});
    bySub.get(r.subject)![r.ask_type] = (bySub.get(r.subject)![r.ask_type] || 0) + r.count;
    askTypes.add(r.ask_type);
  }
  // Show all subjects with data (up to 19), sorted by volume
  const totals = [...bySub.entries()]
    .map(([subject, counts]) => ({
      subject,
      total: Object.values(counts).reduce((a, b) => a + b, 0),
      counts,
    }))
    .sort((a, b) => b.total - a.total);

  const types = [...askTypes]
    .map((t) => ({
      t,
      n: data.filter((d) => d.ask_type === t).reduce((a, d) => a + d.count, 0),
    }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 7)
    .map((x) => x.t);

  const chartData = totals.map((row) => {
    const out: Record<string, string | number> = {
      name: row.subject.length > 16 ? row.subject.slice(0, 14) + "..." : row.subject,
      full: row.subject,
    };
    const sum = types.reduce((a, t) => a + (row.counts[t] || 0), 0) || 1;
    let running = 0;
    types.forEach((t, i) => {
      let pct = +(((row.counts[t] || 0) / sum) * 100).toFixed(1);
      // Last segment absorbs rounding so stack hits exactly 100
      if (i === types.length - 1) {
        pct = Math.max(0, +(100 - running).toFixed(1));
      } else {
        running += pct;
      }
      out[t] = pct;
    });
    return out;
  });

  return (
    <ChartShell
      title="Ask-type mix by subject"
      subtitle={`% within subject (${totals.length} subjects × top ask types)`}
      extraTall
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ left: 4, right: 8, top: 4, bottom: 4 }}
        >
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tickFormatter={pctTick}
            stroke={AXIS}
            tick={{ fill: AXIS, fontSize: 11 }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={110}
            stroke={AXIS}
            tick={{ fill: AXIS, fontSize: 10 }}
            interval={0}
          />
          <Tooltip
            contentStyle={tipStyle}
            labelStyle={tipLabelStyle}
            itemStyle={tipItemStyle}
            formatter={(value, name) => [`${Number(value).toFixed(1)}%`, String(name)]}
            labelFormatter={(_, payload) => {
              const p = payload?.[0]?.payload as { full?: string } | undefined;
              return p?.full || "";
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: AXIS }}
            formatter={(value) => (
              <span style={{ color: AXIS }}>{value}</span>
            )}
          />
          {types.map((t, i) => (
            <Bar
              key={t}
              dataKey={t}
              stackId="a"
              fill={ASK_COLORS[i % ASK_COLORS.length]}
              name={t.replace(/_/g, " ")}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function ConceptBars({
  groups,
}: {
  groups: Array<{ topic: string; concepts: Array<{ concept: string; count: number }> }>;
}) {
  return (
    <div className="rounded-xl surface p-4">
      <h3 className="font-display text-base font-semibold text-[var(--ink)]">
        High-yield concepts
      </h3>
      <p className="mt-0.5 mb-4 text-xs chart-sub">
        Cleaned labels (vignette stems filtered) within top topics
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {groups.map((g) => {
          const max = Math.max(...g.concepts.map((c) => c.count), 1);
          return (
            <div key={g.topic}>
              <div className="mb-2 text-sm font-medium text-[var(--accent)]">{g.topic}</div>
              <ul className="space-y-1.5">
                {g.concepts.map((c) => (
                  <li key={c.concept} className="text-xs">
                    <div className="mb-0.5 flex justify-between gap-2">
                      <span className="truncate text-[var(--ink)]">{c.concept}</span>
                      <span className="tabular-nums chart-sub">{c.count}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
                      <div
                        className="h-full rounded-full bg-[var(--accent)]"
                        style={{ width: `${(100 * c.count) / max}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ImportanceBandBars({
  data,
}: {
  data: Array<{
    topic: string;
    primary_subject: string;
    importance_score: number;
    priority_band: string;
    question_count: number;
  }>;
}) {
  return (
    <div className="rounded-xl surface p-4">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-base font-semibold text-[var(--ink)]">
          Must & high priority
        </h3>
        <ScoreMethodology />
      </div>
      <p className="mb-4 text-xs chart-sub">
        Shareable score bars — tap a score to see the weighting
      </p>
      <ul className="space-y-2.5">
        {data.slice(0, 20).map((d) => (
          <li key={`${d.topic}-${d.primary_subject}`} className="text-sm">
            <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
              <span className="min-w-0">
                <Link
                  href={`/topics/${encodeURIComponent(d.topic)}`}
                  className="font-medium text-[var(--ink)] hover:text-[var(--accent)]"
                >
                  {d.topic}
                </Link>
                <span className="ml-2 text-xs chart-sub">{d.primary_subject}</span>
              </span>
              <span
                className="shrink-0 tabular-nums text-xs font-semibold"
                style={{ color: BAND[d.priority_band] || BAND.Medium }}
                title="Importance score — open methodology above"
              >
                {d.importance_score.toFixed(1)}
                <span className="ml-1 font-normal chart-sub">n={d.question_count}</span>
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(100, d.importance_score)}%`,
                  background: BAND[d.priority_band] || BAND.Medium,
                }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
