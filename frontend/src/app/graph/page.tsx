"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Network, RefreshCw, Search } from "lucide-react";
import { fetchDomains, fetchKnowledgeGraph } from "@/lib/api";

interface Domain {
  id: string;
  name: string;
}

type NodeType = "domain" | "topic" | "paper" | "material" | "method" | "problem" | "property";

interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  size: number;
  domain_id?: string | null;
  paper_id?: string;
  meta?: Record<string, string | number | null | undefined>;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
}

const viewBox = { width: 1120, height: 760 };
const center = { x: viewBox.width / 2, y: viewBox.height / 2 };

const nodeColors: Record<NodeType, string> = {
  domain: "#f59e0b",
  topic: "#2563eb",
  paper: "#06b6d4",
  material: "#8b5cf6",
  method: "#10b981",
  problem: "#ef4444",
  property: "#f97316",
};

const nodeLabels: Record<NodeType, string> = {
  domain: "领域",
  topic: "主题簇",
  paper: "论文",
  material: "材料",
  method: "方法",
  problem: "问题",
  property: "性质",
};

const driftByType: Record<NodeType, { radius: number; speed: number }> = {
  domain: { radius: 4, speed: 0.0006 },
  topic: { radius: 9, speed: 0.0011 },
  paper: { radius: 7, speed: 0.0014 },
  material: { radius: 11, speed: 0.0012 },
  method: { radius: 11, speed: 0.0011 },
  problem: { radius: 13, speed: 0.0013 },
  property: { radius: 10, speed: 0.00115 },
};

function polar(angle: number, radius: number) {
  return {
    x: center.x + Math.cos(angle) * radius,
    y: center.y + Math.sin(angle) * radius,
  };
}

function hashString(value: string) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash);
}

function shorten(label: string, max = 34) {
  if (label.length <= max) return label;
  return `${label.slice(0, max - 1)}…`;
}

function buildGraphLayout(nodes: GraphNode[], edges: GraphEdge[]) {
  const domainNodes = nodes.filter((node) => node.type === "domain");
  const topicNodes = nodes.filter((node) => node.type === "topic");
  const paperNodes = nodes.filter((node) => node.type === "paper");
  const signalNodes = nodes.filter((node) => !["domain", "topic", "paper"].includes(node.type));

  const positions = new Map<string, PositionedNode>();

  domainNodes.forEach((node, index) => {
    const angle = -Math.PI / 2 + (index / Math.max(1, domainNodes.length)) * Math.PI * 2;
    const point = domainNodes.length === 1 ? center : polar(angle, 80);
    positions.set(node.id, { ...node, ...point });
  });

  const topicsByDomain = new Map<string, GraphNode[]>();
  topicNodes.forEach((node) => {
    const key = node.domain_id || "unclassified";
    topicsByDomain.set(key, [...(topicsByDomain.get(key) || []), node]);
  });

  topicsByDomain.forEach((group, domainId) => {
    const domainNode = positions.get(`domain:${domainId}`) || positions.get(domainId);
    const anchor = domainNode || center;
    group.forEach((node, index) => {
      const angle = -Math.PI / 2 + (index / Math.max(1, group.length)) * Math.PI * 2;
      const point = polar(angle, 185);
      positions.set(node.id, {
        ...node,
        x: anchor.x + (point.x - center.x) * 0.72,
        y: anchor.y + (point.y - center.y) * 0.72,
      });
    });
  });

  const papersByTopic = new Map<string, GraphNode[]>();
  edges
    .filter((edge) => edge.type === "topic_paper")
    .forEach((edge) => {
      const paperNode = paperNodes.find((node) => node.id === edge.target);
      if (!paperNode) return;
      papersByTopic.set(edge.source, [...(papersByTopic.get(edge.source) || []), paperNode]);
    });

  papersByTopic.forEach((group, topicId) => {
    const anchor = positions.get(topicId) || center;
    group.forEach((node, index) => {
      const angle = -Math.PI / 2 + (index / Math.max(1, group.length)) * Math.PI * 2;
      const radius = 88 + Math.floor(index / 8) * 34;
      const point = polar(angle, radius);
      positions.set(node.id, {
        ...node,
        x: anchor.x + (point.x - center.x),
        y: anchor.y + (point.y - center.y),
      });
    });
  });

  const signalBuckets: Record<string, GraphNode[]> = {
    material: [],
    method: [],
    problem: [],
    property: [],
  };
  signalNodes.forEach((node) => {
    signalBuckets[node.type].push(node);
  });

  const sectors: Record<string, [number, number]> = {
    problem: [-Math.PI + 0.25, -Math.PI / 2 - 0.2],
    method: [-Math.PI / 2 + 0.1, -0.2],
    material: [0.15, Math.PI / 2 - 0.1],
    property: [Math.PI / 2 + 0.2, Math.PI - 0.25],
  };

  Object.entries(signalBuckets).forEach(([type, group]) => {
    const [start, end] = sectors[type];
    group.forEach((node, index) => {
      const count = Math.max(1, group.length);
      const angle = start + ((index + 0.5) / count) * (end - start);
      const radius = 305 + (index % 3) * 22;
      const point = polar(angle, radius);
      positions.set(node.id, { ...node, ...point });
    });
  });

  nodes.forEach((node) => {
    if (!positions.has(node.id)) {
      positions.set(node.id, { ...node, ...center });
    }
  });

  return Array.from(positions.values());
}

function animateNodes(nodes: PositionedNode[], tick: number) {
  return nodes.map((node) => {
    const drift = driftByType[node.type];
    const phase = hashString(node.id) * 0.0002;
    const secondary = hashString(`${node.id}:secondary`) * 0.00017;
    return {
      ...node,
      x: node.x + Math.cos(tick * drift.speed + phase) * drift.radius,
      y: node.y + Math.sin(tick * (drift.speed * 0.92) + secondary) * drift.radius,
    };
  });
}

export default function GraphPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [domainId, setDomainId] = useState("");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(90);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchKnowledgeGraph({
        domain_id: domainId || undefined,
        limit,
      });
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
      setSelectedNode(null);
    } finally {
      setLoading(false);
    }
  }, [domainId, limit]);

  useEffect(() => {
    fetchDomains().then((data) => setDomains(data || [])).catch(() => setDomains([]));
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    const onFocus = () => {
      loadGraph();
    };
    window.addEventListener("focus", onFocus);
    const timer = window.setInterval(() => {
      loadGraph();
    }, 15000);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.clearInterval(timer);
    };
  }, [loadGraph]);

  useEffect(() => {
    let frame = 0;
    let raf = 0;
    const loop = () => {
      frame += 1;
      setTick(frame);
      raf = window.requestAnimationFrame(loop);
    };
    raf = window.requestAnimationFrame(loop);
    return () => window.cancelAnimationFrame(raf);
  }, []);

  const visibleNodes = useMemo(() => {
    if (!query.trim()) return nodes;
    const term = query.trim().toLowerCase();
    return nodes.filter((node) => node.label.toLowerCase().includes(term));
  }, [nodes, query]);

  const visibleIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);
  const visibleEdges = useMemo(
    () => edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    [edges, visibleIds]
  );

  const positionedNodes = useMemo(() => buildGraphLayout(visibleNodes, visibleEdges), [visibleNodes, visibleEdges]);
  const animatedNodes = useMemo(() => animateNodes(positionedNodes, tick), [positionedNodes, tick]);
  const nodeMap = useMemo(() => new Map(animatedNodes.map((node) => [node.id, node])), [animatedNodes]);

  const stats = useMemo(() => {
    const counts: Record<NodeType, number> = {
      domain: 0,
      topic: 0,
      paper: 0,
      material: 0,
      method: 0,
      problem: 0,
      property: 0,
    };
    visibleNodes.forEach((node) => {
      counts[node.type] += 1;
    });
    return counts;
  }, [visibleNodes]);

  const connected = useMemo(() => {
    if (!selectedNode) return new Set<string>();
    const ids = new Set<string>([selectedNode.id]);
    visibleEdges.forEach((edge) => {
      if (edge.source === selectedNode.id || edge.target === selectedNode.id) {
        ids.add(edge.source);
        ids.add(edge.target);
      }
    });
    return ids;
  }, [selectedNode, visibleEdges]);

  return (
    <div className="h-full overflow-hidden bg-[#05070b] text-white">
      <div className="flex h-full">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="border-b border-white/10 bg-black/30 px-5 py-4 backdrop-blur">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-300/40 bg-cyan-300/10 text-cyan-200">
                  <Network className="h-5 w-5" />
                </div>
                <div>
                  <h1 className="font-heading text-xl text-white">主题图谱</h1>
                  <p className="text-xs text-cyan-100/60">
                    从论文主题簇出发，连接问题、方法、材料与关键性质。
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-cyan-100/40" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="搜索节点"
                    className="h-9 w-52 rounded-md border border-white/10 bg-white/5 pl-9 pr-3 text-sm text-white placeholder:text-cyan-100/40 focus:border-cyan-300/70 focus:outline-none"
                  />
                </div>
                <select
                  value={domainId}
                  onChange={(event) => setDomainId(event.target.value)}
                  className="h-9 rounded-md border border-white/10 bg-[#0d1220] px-3 text-sm text-white focus:border-cyan-300/70 focus:outline-none"
                >
                  <option value="">全部领域</option>
                  {domains.map((domain) => (
                    <option key={domain.id} value={domain.id}>
                      {domain.name}
                    </option>
                  ))}
                </select>
                <select
                  value={limit}
                  onChange={(event) => setLimit(Number(event.target.value))}
                  className="h-9 rounded-md border border-white/10 bg-[#0d1220] px-3 text-sm text-white focus:border-cyan-300/70 focus:outline-none"
                >
                  <option value={70}>70 节点</option>
                  <option value={90}>90 节点</option>
                  <option value={120}>120 节点</option>
                </select>
                <button
                  onClick={loadGraph}
                  disabled={loading}
                  className="inline-flex h-9 items-center gap-2 rounded-md border border-cyan-300/40 px-3 text-sm font-medium text-cyan-100 hover:bg-cyan-300/10 disabled:opacity-50"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                  刷新
                </button>
              </div>
            </div>
          </div>

          <div className="relative min-h-0 flex-1">
            <svg viewBox={`0 0 ${viewBox.width} ${viewBox.height}`} className="h-full w-full">
              <defs>
                <radialGradient id="graphGlow" cx="50%" cy="50%" r="55%">
                  <stop offset="0%" stopColor="rgba(56,189,248,0.18)" />
                  <stop offset="100%" stopColor="rgba(5,7,11,0)" />
                </radialGradient>
              </defs>
              <rect width={viewBox.width} height={viewBox.height} fill="#05070b" />
              <circle cx={center.x} cy={center.y} r="320" fill="url(#graphGlow)" />

              {visibleEdges.map((edge, index) => {
                const source = nodeMap.get(edge.source);
                const target = nodeMap.get(edge.target);
                if (!source || !target) return null;
                const isActive = !selectedNode || connected.has(edge.source) || connected.has(edge.target);
                const shimmer = 0.22 + ((Math.sin(tick * 0.03 + index * 0.8) + 1) / 2) * 0.18;
                return (
                  <line
                    key={edge.id}
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke={edge.type === "topic_paper" ? "#38bdf8" : "#94a3b8"}
                    strokeOpacity={isActive ? shimmer : 0.08}
                    strokeWidth={edge.type === "topic_paper" ? 1.7 : 1.15}
                  />
                );
              })}

              {animatedNodes.map((node) => {
                const active = !selectedNode || connected.has(node.id);
                const baseRadius = Math.max(8, Math.min(24, node.size));
                const pulse = 1 + Math.sin(tick * 0.05 + hashString(node.id) * 0.0003) * 0.08;
                const radius = baseRadius * pulse;
                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={() => setSelectedNode(node)}
                    className="cursor-pointer"
                  >
                    <circle
                      r={radius + 8}
                      fill={nodeColors[node.type]}
                      fillOpacity={active ? 0.1 : 0.03}
                    />
                    <circle
                      r={radius}
                      fill={nodeColors[node.type]}
                      fillOpacity={active ? 0.94 : 0.3}
                      stroke={selectedNode?.id === node.id ? "#ffffff" : "rgba(255,255,255,0.16)"}
                      strokeWidth={selectedNode?.id === node.id ? 2.5 : 1}
                    />
                    <text
                      y={radius + 16}
                      textAnchor="middle"
                      fill={active ? "#e2e8f0" : "rgba(226,232,240,0.35)"}
                      fontSize={11}
                    >
                      {shorten(node.label, node.type === "paper" ? 28 : 20)}
                    </text>
                  </g>
                );
              })}
            </svg>

            <div className="pointer-events-none absolute left-5 top-5 flex flex-wrap gap-3 text-xs text-cyan-100/70">
              <span>主题簇 {stats.topic}</span>
              <span>论文 {stats.paper}</span>
              <span>问题 {stats.problem}</span>
              <span>方法 {stats.method}</span>
              <span>材料 {stats.material}</span>
              <span>性质 {stats.property}</span>
            </div>
          </div>
        </div>

        <aside className="w-80 shrink-0 border-l border-white/10 bg-black/40 p-5 backdrop-blur">
          <h2 className="text-sm font-semibold text-cyan-100">节点信息</h2>
          {selectedNode ? (
            <div className="mt-4 space-y-4">
              <div>
                <div className="text-xs uppercase tracking-wider text-cyan-100/40">
                  {nodeLabels[selectedNode.type]}
                </div>
                <div className="mt-2 text-base font-semibold leading-6 text-white">{selectedNode.label}</div>
              </div>
              <div className="space-y-2 text-xs text-cyan-100/65">
                <div>ID: {selectedNode.id}</div>
                {selectedNode.domain_id && <div>领域: {selectedNode.domain_id}</div>}
                {selectedNode.paper_id && <div>论文 ID: {selectedNode.paper_id}</div>}
                {selectedNode.meta?.year && <div>年份: {selectedNode.meta.year}</div>}
                {selectedNode.meta?.journal && <div>期刊: {selectedNode.meta.journal}</div>}
                {selectedNode.meta?.paper_count && <div>主题内论文: {selectedNode.meta.paper_count}</div>}
                {selectedNode.meta?.count && <div>信号强度: {selectedNode.meta.count}</div>}
              </div>
            </div>
          ) : (
            <div className="mt-4 text-sm leading-6 text-cyan-100/55">
              先从主题簇节点看全局，再顺着问题、方法、材料和性质节点定位相关文献。
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
