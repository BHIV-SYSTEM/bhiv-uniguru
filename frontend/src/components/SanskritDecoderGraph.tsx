import React, { useRef, useMemo, useState } from "react";
import type { GraphNode, GraphEdge } from "../types/sanskrit";

// ── Node colour palette by type ───────────────────────────────────────────────
const NODE_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  sanskrit_concept: { fill: "#7c3aed", stroke: "#a78bfa", text: "#fff" },
  kosha:            { fill: "#0d9488", stroke: "#5eead4", text: "#fff" },
  chakra:           { fill: "#dc2626", stroke: "#f87171", text: "#fff" },
  bija:             { fill: "#d97706", stroke: "#fbbf24", text: "#fff" },
  loka:             { fill: "#1d4ed8", stroke: "#60a5fa", text: "#fff" },
  deity:            { fill: "#be185d", stroke: "#f472b6", text: "#fff" },
  shastra:          { fill: "#065f46", stroke: "#34d399", text: "#fff" },
  yantra:           { fill: "#92400e", stroke: "#f59e0b", text: "#fff" },
  vidya:            { fill: "#1e3a5f", stroke: "#38bdf8", text: "#fff" },
  knowledge_record: { fill: "#374151", stroke: "#6b7280", text: "#d1d5db" },
};
const DEFAULT_COLOR = { fill: "#1f2937", stroke: "#4b5563", text: "#e5e7eb" };

const EDGE_COLORS: Record<string, string> = {
  canonical_cross_reference: "#a78bfa",
  related_deity:             "#f472b6",
  related_loka:              "#60a5fa",
  related_kosha:             "#5eead4",
  related_chakra:            "#f87171",
  related_yantra:            "#fbbf24",
  related_vidya:             "#38bdf8",
  related_bija:              "#d97706",
  referenced_in_shastra:     "#34d399",
  retrieved_evidence:        "#6b7280",
};
const DEFAULT_EDGE = "#4b5563";

interface LayoutNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width?: number;
  height?: number;
}

// ── Simple force simulation ───────────────────────────────────────────────────
function forceLayout(
  nodes: LayoutNode[],
  edges: GraphEdge[],
  iters = 180
): LayoutNode[] {
  const cx = 0;
  const cy = 0;
  const k = Math.sqrt((600 * 400) / Math.max(nodes.length, 1));

  for (let iter = 0; iter < iters; iter++) {
    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x || 0.1;
        const dy = nodes[j].y - nodes[i].y || 0.1;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.1;
        const force = (k * k) / dist;
        const fx = (dx / dist) * force * 0.5;
        const fy = (dy / dist) * force * 0.5;
        nodes[i].vx -= fx;
        nodes[i].vy -= fy;
        nodes[j].vx += fx;
        nodes[j].vy += fy;
      }
    }
    // Attraction along edges
    for (const edge of edges) {
      const src = nodes.find((n) => n.id === edge.from);
      const tgt = nodes.find((n) => n.id === edge.to);
      if (!src || !tgt) continue;
      const dx = tgt.x - src.x;
      const dy = tgt.y - src.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.1;
      const force = (dist * dist) / k;
      const fx = (dx / dist) * force * 0.15;
      const fy = (dy / dist) * force * 0.15;
      src.vx += fx;
      src.vy += fy;
      tgt.vx -= fx;
      tgt.vy -= fy;
    }
    // Gravity to center
    for (const n of nodes) {
      n.vx += (cx - n.x) * 0.005;
      n.vy += (cy - n.y) * 0.005;
    }
    // Apply velocities with damping
    const damp = 0.82;
    for (const n of nodes) {
      n.x += n.vx;
      n.y += n.vy;
      n.vx *= damp;
      n.vy *= damp;
    }
  }
  return nodes;
}

const SanskritDecoderGraph: React.FC<Props> = ({
  nodes: rawNodes,
  edges: rawEdges,
  width = 700,
  height = 420,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    node: LayoutNode;
  } | null>(null);

  const layoutNodes = useMemo<LayoutNode[]>(() => {
    // Seed positions radially so force converges faster
    return rawNodes.map((n, i) => {
      const angle = (i / Math.max(rawNodes.length, 1)) * 2 * Math.PI;
      const radius = rawNodes.length > 1 ? 120 : 0;
      return {
        ...n,
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        r: n.type === "sanskrit_concept" ? 28 : 20,
      };
    });
  }, [rawNodes]);

  const solved = useMemo(
    () => forceLayout([...layoutNodes], rawEdges),
    [layoutNodes, rawEdges]
  );

  // Centre + scale to fit SVG
  const placed = useMemo(() => {
    if (!solved.length)
      return [];
    const xs = solved.map((n) => n.x);
    const ys = solved.map((n) => n.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const padded = 60;
    const scaleX = (width - padded * 2) / (maxX - minX || 1);
    const scaleY = (height - padded * 2) / (maxY - minY || 1);
    const s = Math.min(scaleX, scaleY, 1.4);
    const ox = width / 2 - ((maxX + minX) / 2) * s;
    const oy = height / 2 - ((maxY + minY) / 2) * s;
    const placed = solved.map((n) => ({
      ...n,
      px: n.x * s + ox,
      py: n.y * s + oy,
    }));
    return placed;
  }, [solved, width, height]);

  const placedById = useMemo(
    () =>
      new Map(
        (placed as Array<LayoutNode & { px: number; py: number }>).map((n) => [
          n.id,
          n,
        ])
      ),
    [placed]
  );

  return (
    <div className="relative select-none">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="w-full rounded-xl"
        style={{ background: "linear-gradient(135deg,#0d0d1a 0%,#0f172a 100%)" }}
        viewBox={`0 0 ${width} ${height}`}
      >
        <defs>
          <marker
            id="arrow"
            markerWidth="6"
            markerHeight="6"
            refX="5"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L0,6 L6,3 z" fill="#6b7280" />
          </marker>
          {/* Glow filters per colour */}
          <filter id="glow-purple">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Edges */}
        {rawEdges.map((edge, idx) => {
          const src = placedById.get(edge.from) as
            | (LayoutNode & { px: number; py: number })
            | undefined;
          const tgt = placedById.get(edge.to) as
            | (LayoutNode & { px: number; py: number })
            | undefined;
          if (!src || !tgt) return null;
          const color = EDGE_COLORS[edge.type] ?? DEFAULT_EDGE;
          const dx = tgt.px - src.px;
          const dy = tgt.py - src.py;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const ex = tgt.px - (dx / dist) * (tgt.r + 4);
          const ey = tgt.py - (dy / dist) * (tgt.r + 4);
          return (
            <line
              key={idx}
              x1={src.px}
              y1={src.py}
              x2={ex}
              y2={ey}
              stroke={color}
              strokeWidth={1.2}
              strokeOpacity={0.55}
              markerEnd="url(#arrow)"
            />
          );
        })}

        {/* Nodes */}
        {(placed as Array<LayoutNode & { px: number; py: number }>).map(
          (node) => {
            const palette = NODE_COLORS[node.type] ?? DEFAULT_COLOR;
            const isHovered = hovered === node.id;
            const label =
              node.label.length > 14
                ? node.label.slice(0, 13) + "…"
                : node.label;
            return (
              <g
                key={node.id}
                transform={`translate(${node.px},${node.py})`}
                style={{ cursor: "pointer" }}
                onMouseEnter={(e) => {
                  setHovered(node.id);
                  const svgRect = svgRef.current?.getBoundingClientRect();
                  setTooltip({
                    x: e.clientX - (svgRect?.left ?? 0),
                    y: e.clientY - (svgRect?.top ?? 0),
                    node,
                  });
                }}
                onMouseLeave={() => {
                  setHovered(null);
                  setTooltip(null);
                }}
              >
                <circle
                  r={isHovered ? node.r + 3 : node.r}
                  fill={palette.fill}
                  stroke={palette.stroke}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  style={{ transition: "all 0.15s ease" }}
                  filter={isHovered ? "url(#glow-purple)" : undefined}
                />
                <text
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={node.type === "sanskrit_concept" ? 9 : 8}
                  fontFamily="'Inter', sans-serif"
                  fontWeight={node.type === "sanskrit_concept" ? "700" : "400"}
                  fill={palette.text}
                  style={{ pointerEvents: "none" }}
                >
                  {label}
                </text>
              </g>
            );
          }
        )}
      </svg>

      {/* Hover tooltip */}
      {tooltip && (
        <div
          className="absolute z-50 bg-gray-900 border border-purple-700/60 rounded-lg px-3 py-2 text-xs text-white shadow-xl pointer-events-none"
          style={{
            left: Math.min(tooltip.x + 10, width - 180),
            top: Math.max(tooltip.y - 60, 0),
            maxWidth: 200,
          }}
        >
          <div className="font-bold text-purple-300">{tooltip.node.label}</div>
          <div className="text-gray-400 mt-0.5 capitalize">
            {tooltip.node.type.replace(/_/g, " ")}
          </div>
          <div className="text-gray-500 mt-0.5 text-xs truncate">
            {typeof tooltip.node.provenance === "string"
              ? tooltip.node.provenance
              : JSON.stringify(tooltip.node.provenance)}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-2 mt-2 px-1">
        {Object.entries(NODE_COLORS)
          .filter(([type]) =>
            rawNodes.some((n) => n.type === type)
          )
          .map(([type, palette]) => (
            <div key={type} className="flex items-center gap-1">
              <div
                className="w-2.5 h-2.5 rounded-full border"
                style={{
                  background: palette.fill,
                  borderColor: palette.stroke,
                }}
              />
              <span className="text-gray-400 text-xs capitalize">
                {type.replace(/_/g, " ")}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
};

export default SanskritDecoderGraph;
