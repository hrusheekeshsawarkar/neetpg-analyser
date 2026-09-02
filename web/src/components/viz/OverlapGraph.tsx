"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { OverlapRow } from "@/lib/types";

type SimNode = {
  id: string;
  label: string;
  isSubject: boolean;
  w: number;
  hx: number;
  hy: number;
  phase: number;
  angle: number;
};

type Edge = { a: string; b: string; w: number };

function shortLabel(id: string) {
  const raw = id.replace(/^SUBJ:/, "");
  if (raw.length <= 15) return raw;
  return raw.slice(0, 13) + "…";
}

function edgeKey(a: string, b: string) {
  return a < b ? `${a}||${b}` : `${b}||${a}`;
}

function easeOutCubic(t: number) {
  return 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);
}

function buildGraph(rows: OverlapRow[], W: number, H: number) {
  const undirected = new Map<string, Edge>();
  for (const r of rows) {
    if (r.item_a === r.item_b) continue;
    const key = edgeKey(r.item_a, r.item_b);
    const prev = undirected.get(key);
    if (!prev || r.co_occurrence > prev.w) {
      undirected.set(key, { a: r.item_a, b: r.item_b, w: r.co_occurrence });
    }
  }

  const ranked = [...undirected.values()].sort((a, b) => b.w - a.w);
  const subjectEdges = ranked.filter(
    (e) => e.a.startsWith("SUBJ:") && e.b.startsWith("SUBJ:"),
  );
  const otherEdges = ranked.filter(
    (e) => !(e.a.startsWith("SUBJ:") && e.b.startsWith("SUBJ:")),
  );
  // Clean constellation: mostly subjects + a few hot topic pairs
  const edges = [...subjectEdges.slice(0, 16), ...otherEdges.slice(0, 6)];

  const weights = new Map<string, number>();
  for (const e of edges) {
    weights.set(e.a, (weights.get(e.a) || 0) + e.w);
    weights.set(e.b, (weights.get(e.b) || 0) + e.w);
  }

  const subjects = [...weights.keys()]
    .filter((id) => id.startsWith("SUBJ:"))
    .sort((a, b) => weights.get(b)! - weights.get(a)!);
  const topics = [...weights.keys()]
    .filter((id) => !id.startsWith("SUBJ:"))
    .sort((a, b) => weights.get(b)! - weights.get(a)!);

  const cx = W / 2;
  const cy = H / 2 - 12;
  const nodes: SimNode[] = [];

  // Inner ring — subjects (even spacing)
  subjects.forEach((id, i) => {
    const angle = -Math.PI / 2 + (i / Math.max(subjects.length, 1)) * Math.PI * 2;
    const radius = 128;
    nodes.push({
      id,
      label: shortLabel(id),
      isSubject: true,
      w: weights.get(id) || 1,
      hx: cx + Math.cos(angle) * radius,
      hy: cy + Math.sin(angle) * radius,
      phase: i * 0.9,
      angle,
    });
  });

  // Outer ring — topics (offset so labels don't stack on subjects)
  topics.forEach((id, i) => {
    const angle =
      -Math.PI / 2 +
      Math.PI / Math.max(topics.length, 1) +
      (i / Math.max(topics.length, 1)) * Math.PI * 2;
    const radius = 205;
    nodes.push({
      id,
      label: shortLabel(id),
      isSubject: false,
      w: weights.get(id) || 1,
      hx: cx + Math.cos(angle) * radius,
      hy: cy + Math.sin(angle) * radius,
      phase: i * 1.3 + 2,
      angle,
    });
  });

  return { nodes, edges, cx, cy };
}

function neighborsOf(id: string, edges: Edge[]) {
  const set = new Set<string>();
  for (const e of edges) {
    if (e.a === id) set.add(e.b);
    if (e.b === id) set.add(e.a);
  }
  return set;
}

export function OverlapGraph({ rows }: { rows: OverlapRow[] }) {
  const W = 960;
  const H = 500;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hoverRef = useRef<string | null>(null);
  const hoverBlend = useRef(0);
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

    const { nodes, edges, cx, cy } = graph;
    const maxW = Math.max(...nodes.map((n) => n.w), 1);
    const maxE = Math.max(...edges.map((e) => e.w), 1);
    const pos = new Map(nodes.map((n) => [n.id, { x: n.hx, y: n.hy }]));
    const start = performance.now();
    let raf = 0;

    const radiusOf = (w: number) => 9 + 13 * Math.sqrt(w / maxW);

    const draw = (now: number) => {
      const elapsed = (now - start) / 1000;
      const intro = easeOutCubic(elapsed / 1.0);
      const t = elapsed;

      const target = hoverRef.current ? 1 : 0;
      hoverBlend.current += (target - hoverBlend.current) * 0.14;
      const hA = hoverBlend.current;
      const hover = hoverRef.current;
      const neigh = hover ? neighborsOf(hover, edges) : null;

      // Background
      const bg = ctx.createRadialGradient(cx, cy, 30, cx, cy, 460);
      bg.addColorStop(0, "#1a4550");
      bg.addColorStop(0.45, "#0e2a32");
      bg.addColorStop(1, "#07151a");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);

      // Decorative rings
      for (const [rad, alpha] of [
        [128, 0.1],
        [205, 0.07],
      ] as const) {
        ctx.beginPath();
        ctx.arc(cx, cy, rad, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(45,212,191,${alpha})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Slow orbital drift of the whole constellation + per-node float
      const orbit = t * 0.12;
      for (const n of nodes) {
        const rot = n.angle + orbit;
        const baseR = Math.hypot(n.hx - cx, n.hy - cy);
        const amp = n.isSubject ? 2.2 : 3.5;
        const breathe = Math.sin(t * 0.7 + n.phase) * amp;
        const x = cx + Math.cos(rot) * (baseR + breathe * 0.15);
        const y = cy + Math.sin(rot) * (baseR + breathe * 0.15);
        // tiny tangential sway
        const tx = -Math.sin(rot) * Math.cos(t * 0.55 + n.phase) * amp;
        const ty = Math.cos(rot) * Math.sin(t * 0.5 + n.phase) * amp * 0.85;
        pos.set(n.id, { x: x + tx * 0.35, y: y + ty * 0.35 });
      }

      // Edges — draw under nodes
      for (const e of edges) {
        const a = pos.get(e.a);
        const b = pos.get(e.b);
        if (!a || !b) continue;

        const onPath =
          !!hover &&
          ((e.a === hover && neigh?.has(e.b)) || (e.b === hover && neigh?.has(e.a)));

        let alpha = (0.22 + 0.55 * (e.w / maxE)) * intro;
        if (hA > 0.02) {
          alpha = onPath ? 0.25 + 0.7 * hA : alpha * (1 - 0.88 * hA);
        }

        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const cxOff = -dy * 0.05;
        const cyOff = dx * 0.05;

        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo(mx + cxOff, my + cyOff, b.x, b.y);
        ctx.strokeStyle = onPath ? "#f0b429" : "#5eead4";
        ctx.globalAlpha = alpha;
        ctx.lineWidth = onPath ? 3 : 1.2 + 2.4 * (e.w / maxE);
        ctx.lineCap = "round";
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      // Nodes — stagger from center outward
      const ordered = [...nodes].sort((a, b) => {
        if (a.isSubject !== b.isSubject) return a.isSubject ? -1 : 1;
        return b.w - a.w;
      });

      ordered.forEach((n, i) => {
        const delay = 0.06 + i * 0.035;
        const appear = easeOutCubic((elapsed - delay) / 0.6);
        if (appear <= 0.01) return;

        const p = pos.get(n.id)!;
        const x = cx + (p.x - cx) * appear;
        const y = cy + (p.y - cy) * appear;
        const r = radiusOf(n.w) * (0.4 + 0.6 * appear);

        const isHover = hover === n.id;
        const isNeigh = Boolean(neigh?.has(n.id));
        let nodeAlpha = intro;
        if (hA > 0.02) {
          nodeAlpha = isHover || isNeigh ? 1 : 1 - 0.8 * hA;
        }

        const pulse = 1 + Math.sin(t * 2.4 + n.phase) * 0.05;
        const liveAngle = n.angle + orbit;

        // Glow
        ctx.globalAlpha = nodeAlpha * (isHover ? 0.6 : 0.32);
        ctx.beginPath();
        ctx.arc(x, y, r * pulse + (isHover ? 14 : 8), 0, Math.PI * 2);
        ctx.fillStyle = n.isSubject ? "rgba(240,180,41,0.55)" : "rgba(45,212,191,0.5)";
        ctx.fill();

        // Core with highlight
        ctx.globalAlpha = nodeAlpha;
        const core = ctx.createRadialGradient(
          x - r * 0.35,
          y - r * 0.4,
          0.5,
          x,
          y,
          r,
        );
        core.addColorStop(0, n.isSubject ? "#fff3c4" : "#b8fff4");
        core.addColorStop(0.45, n.isSubject ? "#f0b429" : "#2dd4bf");
        core.addColorStop(1, n.isSubject ? "#c48410" : "#0f766e");
        ctx.beginPath();
        ctx.arc(x, y, r * pulse, 0, Math.PI * 2);
        ctx.fillStyle = core;
        ctx.fill();
        ctx.strokeStyle = "rgba(255,255,255,0.4)";
        ctx.lineWidth = 1.25;
        ctx.stroke();

        // Label outside along radial
        const labelR = r * pulse + 16;
        const lx = x + Math.cos(liveAngle) * labelR;
        const ly = y + Math.sin(liveAngle) * labelR;
        const cos = Math.cos(liveAngle);
        ctx.globalAlpha = nodeAlpha * appear;
        ctx.fillStyle = isHover || isNeigh ? "#ffffff" : "#d8ecef";
        ctx.font = `${isHover ? 600 : 500} ${isHover ? 13 : 11.5}px ui-sans-serif, system-ui, sans-serif`;
        ctx.textAlign = cos > 0.25 ? "left" : cos < -0.25 ? "right" : "center";
        ctx.textBaseline = "middle";
        ctx.fillText(n.label, lx, ly);
        ctx.globalAlpha = 1;
      });

      raf = requestAnimationFrame(draw);
    };

    const onMove = (ev: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = ((ev.clientX - rect.left) / rect.width) * W;
      const y = ((ev.clientY - rect.top) / rect.height) * H;
      let hit: (typeof nodes)[0] | null = null;
      let best = Infinity;
      for (const n of nodes) {
        const p = pos.get(n.id);
        if (!p) continue;
        const r = radiusOf(n.w) + 8;
        const d = Math.hypot(p.x - x, p.y - y);
        if (d <= r && d < best) {
          best = d;
          hit = n;
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
      <div className="flex h-[500px] items-center justify-center rounded-xl surface text-sm text-[var(--muted)]">
        No overlap data loaded.
      </div>
    );
  }

  if (!mounted) {
    return (
      <div className="flex h-[500px] items-center justify-center rounded-xl surface text-sm text-[var(--muted)]">
        Loading overlap graph…
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl surface bg-[#07151a]">
      <canvas
        ref={canvasRef}
        className="h-[500px] w-full"
        style={{ display: "block" }}
        aria-label="Topic and subject co-occurrence graph"
      />
      <div className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap items-center gap-3 text-[10px] text-[var(--muted)]">
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[var(--accent2)]" />
          Subject
        </span>
        <span>
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[var(--accent)]" />
          Topic
        </span>
        <span>Hover to focus links</span>
        {hoverLabel && (
          <span className="rounded-md bg-white/10 px-2 py-0.5 text-[var(--ink)]">
            {hoverLabel}
          </span>
        )}
      </div>
    </div>
  );
}
