"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { OverlapRow } from "@/lib/types";

type SimNode = {
  id: string;
  label: string;
  isSubject: boolean;
  w: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
};

type Edge = { a: string; b: string; w: number };

function shortLabel(id: string) {
  const raw = id.replace(/^SUBJ:/, "");
  return raw.length > 18 ? raw.slice(0, 16) + "…" : raw;
}

function buildGraph(rows: OverlapRow[], W: number, H: number) {
  const weights = new Map<string, number>();
  const edges: Edge[] = [];
  for (const r of rows.slice(0, 36)) {
    weights.set(r.item_a, (weights.get(r.item_a) || 0) + r.co_occurrence);
    weights.set(r.item_b, (weights.get(r.item_b) || 0) + r.co_occurrence);
    edges.push({ a: r.item_a, b: r.item_b, w: r.co_occurrence });
  }
  const ids = [...weights.keys()];
  const cx = W / 2;
  const cy = H / 2;
  const nodes: SimNode[] = ids.map((id, i) => {
    const angle = (i / Math.max(ids.length, 1)) * Math.PI * 2;
    const radius = 100 + (i % 5) * 30;
    return {
      id,
      label: shortLabel(id),
      isSubject: id.startsWith("SUBJ:"),
      w: weights.get(id) || 1,
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
    };
  });
  return { nodes, edges };
}

/**
 * Client-only animated overlap map (canvas 2D).
 * Mount-gated to avoid SSR hydration mismatches; no WebGL/font CDN deps.
 */
export function OverlapGraph({ rows }: { rows: OverlapRow[] }) {
  const W = 960;
  const H = 440;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hoverRef = useRef<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [hoverLabel, setHoverLabel] = useState<string | null>(null);

  const graph = useMemo(() => buildGraph(rows, W, H), [rows]);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted || !rows.length) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const nodes = graph.nodes.map((n) => ({ ...n }));
    const edges = graph.edges;
    const maxW = Math.max(...nodes.map((n) => n.w), 1);
    const maxE = Math.max(...edges.map((e) => e.w), 1);
    let frame = 0;
    let raf = 0;

    const draw = () => {
      frame += 1;
      const byId = new Map(nodes.map((n) => [n.id, n]));

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          let dx = a.x - b.x;
          let dy = a.y - b.y;
          const dist = Math.hypot(dx, dy) || 0.01;
          const force = 1100 / (dist * dist);
          dx = (dx / dist) * force;
          dy = (dy / dist) * force;
          a.vx += dx;
          a.vy += dy;
          b.vx -= dx;
          b.vy -= dy;
        }
      }

      for (const e of edges) {
        const a = byId.get(e.a);
        const b = byId.get(e.b);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 0.01;
        const ideal = 125 - 45 * (e.w / maxE);
        const force = (dist - ideal) * 0.022;
        a.vx += (dx / dist) * force;
        a.vy += (dy / dist) * force;
        b.vx -= (dx / dist) * force;
        b.vy -= (dy / dist) * force;
      }

      const cx = W / 2;
      const cy = H / 2;
      const t = frame * 0.004;
      for (const n of nodes) {
        n.vx += (cx - n.x) * 0.0045;
        n.vy += (cy - n.y) * 0.0045;
        n.vx += Math.cos(t + n.w * 0.01) * 0.02;
        n.vy += Math.sin(t * 0.85 + n.w * 0.01) * 0.02;
        n.vx *= 0.84;
        n.vy *= 0.84;
        n.x = Math.min(W - 48, Math.max(48, n.x + n.vx));
        n.y = Math.min(H - 36, Math.max(36, n.y + n.vy));
      }

      // background
      const grad = ctx.createRadialGradient(cx, cy * 0.9, 40, cx, cy, 420);
      grad.addColorStop(0, "#123038");
      grad.addColorStop(1, "#07151a");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      const hover = hoverRef.current;

      for (const e of edges) {
        const a = byId.get(e.a);
        const b = byId.get(e.b);
        if (!a || !b) continue;
        const active = hover === e.a || hover === e.b;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = active ? "#f0b429" : "#2dd4bf";
        ctx.globalAlpha = active ? 0.9 : 0.12 + 0.45 * (e.w / maxE);
        ctx.lineWidth = active ? 2.4 : 1 + 2 * (e.w / maxE);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      for (const n of nodes) {
        const r = 8 + 16 * (n.w / maxW);
        const fill = n.isSubject ? "#f0b429" : "#2dd4bf";
        const active = hover === n.id;
        if (active) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + 7, 0, Math.PI * 2);
          ctx.fillStyle = fill;
          ctx.globalAlpha = 0.2;
          ctx.fill();
          ctx.globalAlpha = 1;
        }
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = fill;
        ctx.fill();
        ctx.fillStyle = active ? "#ffffff" : "#d5e6ea";
        ctx.font = `${active ? "600" : "400"} 11px var(--font-ibm), system-ui, sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(n.label, n.x, n.y + r + 14);
      }

      raf = requestAnimationFrame(draw);
    };

    const onMove = (ev: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = ((ev.clientX - rect.left) / rect.width) * W;
      const y = ((ev.clientY - rect.top) / rect.height) * H;
      let hit: SimNode | null = null;
      for (const n of nodes) {
        const r = 10 + 16 * (n.w / maxW);
        if (Math.hypot(n.x - x, n.y - y) <= r + 4) {
          hit = n;
          break;
        }
      }
      const next = hit?.id ?? null;
      if (hoverRef.current !== next) {
        hoverRef.current = next;
        setHoverLabel(hit ? hit.id.replace(/^SUBJ:/, "") : null);
      }
    };

    const onLeave = () => {
      hoverRef.current = null;
      setHoverLabel(null);
    };

    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseleave", onLeave);
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mouseleave", onLeave);
    };
  }, [mounted, graph, rows.length]);

  if (!rows.length) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-xl surface text-sm text-[var(--muted)]">
        No overlap data loaded.
      </div>
    );
  }

  if (!mounted) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-xl surface text-sm text-[var(--muted)]">
        Loading overlap graph…
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl surface bg-[#07151a]">
      <canvas
        ref={canvasRef}
        className="h-[420px] w-full"
        style={{ display: "block" }}
        aria-label="Topic and subject co-occurrence graph"
      />
      <div className="pointer-events-none absolute bottom-2 left-3 flex flex-wrap gap-3 text-[10px] text-[var(--muted)]">
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[var(--accent2)]" />
          Subject
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[var(--accent)]" />
          Topic / pair
        </span>
        <span>Size ∝ co-occurrence · hover to highlight</span>
        {hoverLabel && (
          <span className="text-[var(--ink)]">Selected: {hoverLabel}</span>
        )}
      </div>
    </div>
  );
}
