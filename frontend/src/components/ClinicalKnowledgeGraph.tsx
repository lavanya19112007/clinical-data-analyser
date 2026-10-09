import React, { useState, useEffect, useRef } from 'react';
import {
  Network,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  User,
  Building,
  Calendar,
  Activity,
  AlertTriangle,
  FileCheck,
  ShieldAlert,
  Layers,
  ChevronRight,
  Info,
  X,
  Sparkles,
  RefreshCw,
  Search
} from 'lucide-react';

interface GraphNode {
  id: string;
  type: 'patient' | 'site' | 'visit' | 'laboratory' | 'adverse_event' | 'doses' | 'protocol_rule' | 'safety_alert';
  label: string;
  category: string;
  status?: string;
  site?: string;
  data?: any;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  label: string;
}

interface KnowledgeGraphProps {
  subjectId?: string;
  currentCut: number;
  onSelectNode?: (node: GraphNode) => void;
}

export const ClinicalKnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  subjectId = '042-S05-003',
  currentCut,
  onSelectNode
}) => {
  const [selectedSubj, setSelectedSubj] = useState<string>(subjectId);
  const [loading, setLoading] = useState<boolean>(false);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [highlightCausalChain, setHighlightCausalChain] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  useEffect(() => {
    setSelectedSubj(subjectId);
  }, [subjectId]);

  useEffect(() => {
    fetchGraphData(selectedSubj, currentCut);
  }, [selectedSubj, currentCut]);

  const fetchGraphData = async (subjid: string, cut: number) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/knowledge-graph?subject_id=${subjid}&cut=${cut}`);
      const data = await res.json();
      setGraphData({ nodes: data.nodes || [], edges: data.edges || [] });
    } catch (err) {
      console.error('Error fetching knowledge graph:', err);
    } finally {
      setLoading(false);
    }
  };

  // Node position layout generator
  const getNodeCoordinates = (node: GraphNode, index: number, total: number) => {
    // Structured hierarchical/radial clinical layout
    const centerX = 450;
    const centerY = 300;

    switch (node.type) {
      case 'patient':
        return { x: 260, y: 280 };
      case 'site':
        return { x: 100, y: 280 };
      case 'visit': {
        const vIdx = index % 3;
        return { x: 400, y: 150 + vIdx * 110 };
      }
      case 'doses':
        return { x: 260, y: 460 };
      case 'laboratory': {
        const labIdx = index % 5;
        return { x: 580, y: 100 + labIdx * 80 };
      }
      case 'adverse_event':
        return { x: 440, y: 460 };
      case 'protocol_rule':
        return { x: 740, y: 220 };
      case 'safety_alert':
        return { x: 880, y: 260 };
      default:
        return {
          x: centerX + 220 * Math.cos((index * 2 * Math.PI) / total),
          y: centerY + 180 * Math.sin((index * 2 * Math.PI) / total)
        };
    }
  };

  // Node styling helpers
  const getNodeBadgeColor = (type: GraphNode['type'], status?: string) => {
    switch (type) {
      case 'patient':
        return { bg: 'bg-indigo-600', border: 'border-indigo-400', text: 'text-white', ring: 'ring-indigo-100' };
      case 'site':
        return { bg: 'bg-teal-600', border: 'border-teal-400', text: 'text-white', ring: 'ring-teal-100' };
      case 'visit':
        return { bg: 'bg-sky-600', border: 'border-sky-400', text: 'text-white', ring: 'ring-sky-100' };
      case 'laboratory':
        if (status === 'CRITICAL') return { bg: 'bg-rose-600', border: 'border-rose-400', text: 'text-white', ring: 'ring-rose-200' };
        if (status === 'ELEVATED') return { bg: 'bg-amber-600', border: 'border-amber-400', text: 'text-white', ring: 'ring-amber-200' };
        return { bg: 'bg-emerald-600', border: 'border-emerald-400', text: 'text-white', ring: 'ring-emerald-100' };
      case 'adverse_event':
        return { bg: 'bg-rose-700', border: 'border-rose-500', text: 'text-white', ring: 'ring-rose-200' };
      case 'doses':
        return { bg: 'bg-emerald-700', border: 'border-emerald-500', text: 'text-white', ring: 'ring-emerald-100' };
      case 'protocol_rule':
        return { bg: 'bg-purple-700', border: 'border-purple-500', text: 'text-white', ring: 'ring-purple-200' };
      case 'safety_alert':
        return { bg: 'bg-red-700', border: 'border-red-500', text: 'text-white', ring: 'ring-red-200' };
      default:
        return { bg: 'bg-slate-600', border: 'border-slate-400', text: 'text-white', ring: 'ring-slate-100' };
    }
  };

  const getNodeIcon = (type: GraphNode['type']) => {
    switch (type) {
      case 'patient': return <User className="w-3.5 h-3.5" />;
      case 'site': return <Building className="w-3.5 h-3.5" />;
      case 'visit': return <Calendar className="w-3.5 h-3.5" />;
      case 'laboratory': return <Activity className="w-3.5 h-3.5" />;
      case 'adverse_event': return <AlertTriangle className="w-3.5 h-3.5" />;
      case 'doses': return <Layers className="w-3.5 h-3.5" />;
      case 'protocol_rule': return <FileCheck className="w-3.5 h-3.5" />;
      case 'safety_alert': return <ShieldAlert className="w-3.5 h-3.5" />;
      default: return <Info className="w-3.5 h-3.5" />;
    }
  };

  const isCausalNode = (node: GraphNode) => {
    if (!highlightCausalChain) return false;
    const l = node.label.toLowerCase();
    const id = node.id.toLowerCase();
    return (
      id.includes('patient') ||
      id.includes('week4') ||
      l.includes('alt') ||
      l.includes('bilirubin') ||
      id.includes('hys_law') ||
      id.includes('safety')
    );
  };

  // Filter nodes
  const filteredNodes = (graphData?.nodes || []).filter((n) => {
    if (filterType === 'ALL') return true;
    if (filterType === 'LABS') return n.type === 'laboratory';
    if (filterType === 'AE') return n.type === 'adverse_event';
    if (filterType === 'VISITS') return n.type === 'visit';
    if (filterType === 'RULES') return n.type === 'protocol_rule' || n.type === 'safety_alert';
    return true;
  });

  const nodeMap = new Map<string, { x: number; y: number; node: GraphNode }>();
  filteredNodes.forEach((n, idx) => {
    nodeMap.set(n.id, { ...getNodeCoordinates(n, idx, filteredNodes.length), node: n });
  });

  const visibleEdges = (graphData?.edges || []).filter(
    (e) => nodeMap.has(e.source) && nodeMap.has(e.target)
  );

  return (
    <div className="bg-white border border-emerald-200/90 rounded-2xl p-6 shadow-sm flex flex-col space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-mono font-bold tracking-wide uppercase">
              Interactive Clinical Knowledge Graph
            </span>
            <span className="text-xs text-slate-500 font-mono">
              Temporal Cut {currentCut}
            </span>
          </div>
          <h2 className="text-lg font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Network className="w-5 h-5 text-emerald-600" />
            Connected Clinical Trial Knowledge Graph
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Demonstrates multi-domain clinical reasoning over entities (Patient → Visits → Labs → Rule → Alert) rather than flat SQL tables.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Subject Switcher */}
          <div className="flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5">
            <span className="text-slate-500 font-medium">Subject:</span>
            <select
              value={selectedSubj}
              onChange={(e) => setSelectedSubj(e.target.value)}
              className="font-mono font-bold text-slate-900 bg-transparent focus:outline-hidden cursor-pointer"
            >
              <option value="042-S05-003">042-S05-003 (Hy's Law Signal)</option>
              <option value="042-S07-002">042-S07-002 (Discontinued AE)</option>
              <option value="042-S01-001">042-S01-001 (Site S01 Clean)</option>
              <option value="042-S03-001">042-S03-001 (Dose Deviation)</option>
            </select>
          </div>

          {/* Causal Chain Highlight Toggle */}
          <button
            onClick={() => setHighlightCausalChain(!highlightCausalChain)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
              highlightCausalChain
                ? 'bg-amber-100 text-amber-900 border border-amber-300 shadow-xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            <span>{highlightCausalChain ? 'Causal Chain Active' : 'Highlight Causal Chain'}</span>
          </button>

          {/* Zoom Controls */}
          <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg p-0.5">
            <button
              onClick={() => setZoomLevel((z) => Math.min(1.6, z + 0.15))}
              className="p-1 hover:bg-white rounded text-slate-600 cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.15))}
              className="p-1 hover:bg-white rounded text-slate-600 cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => {
                setZoomLevel(1);
                setPanOffset({ x: 0, y: 0 });
              }}
              className="p-1 hover:bg-white rounded text-slate-600 cursor-pointer"
              title="Reset View"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Domain Filter Pills */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-400 font-medium mr-1 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Filters:
          </span>
          {[
            { id: 'ALL', label: 'All Entities' },
            { id: 'LABS', label: 'Laboratories' },
            { id: 'AE', label: 'Adverse Events' },
            { id: 'VISITS', label: 'Visits' },
            { id: 'RULES', label: 'Rules & Alerts' }
          ].map((flt) => (
            <button
              key={flt.id}
              onClick={() => setFilterType(flt.id)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition cursor-pointer ${
                filterType === flt.id
                  ? 'bg-emerald-700 text-white font-bold'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {flt.label}
            </button>
          ))}
        </div>

        <div className="text-[11px] text-slate-500 font-mono">
          Click any node to inspect raw clinical attributes
        </div>
      </div>

      {/* Graph Visual Canvas */}
      <div className="relative border border-slate-200 bg-slate-950 rounded-xl overflow-hidden min-h-[500px] flex items-center justify-center select-none shadow-inner">
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-2 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
            <span className="text-xs font-mono">Constructing cut-aware knowledge graph...</span>
          </div>
        ) : (
          <div
            className="w-full h-[540px] relative overflow-hidden cursor-grab active:cursor-grabbing"
            onMouseDown={(e) => {
              setIsDragging(true);
              setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
            }}
            onMouseMove={(e) => {
              if (isDragging) {
                setPanOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
              }
            }}
            onMouseUp={() => setIsDragging(false)}
            onMouseLeave={() => setIsDragging(false)}
          >
            {/* SVG Edges Layer */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              style={{
                transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
                transformOrigin: 'center center'
              }}
            >
              <defs>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
                </marker>
                <marker
                  id="arrow-causal"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
              </defs>

              {visibleEdges.map((edge) => {
                const s = nodeMap.get(edge.source);
                const t = nodeMap.get(edge.target);
                if (!s || !t) return null;

                const isCausalEdge =
                  highlightCausalChain && isCausalNode(s.node) && isCausalNode(t.node);

                return (
                  <g key={edge.id}>
                    <line
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke={isCausalEdge ? '#f59e0b' : '#334155'}
                      strokeWidth={isCausalEdge ? 2.5 : 1.2}
                      strokeDasharray={edge.relationship === 'EVALUATED_BY' ? '4 3' : 'none'}
                      markerEnd={isCausalEdge ? 'url(#arrow-causal)' : 'url(#arrow)'}
                      opacity={isCausalEdge ? 1 : 0.6}
                    />
                    <text
                      x={(s.x + t.x) / 2}
                      y={(s.y + t.y) / 2 - 4}
                      fill={isCausalEdge ? '#fbbf24' : '#64748b'}
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {edge.label}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Nodes DOM Layer */}
            <div
              className="absolute inset-0 w-full h-full"
              style={{
                transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
                transformOrigin: 'center center'
              }}
            >
              {Array.from(nodeMap.values()).map(({ x, y, node }) => {
                const colors = getNodeBadgeColor(node.type, node.status);
                const isCausal = isCausalNode(node);
                const isSelected = selectedNode?.id === node.id;

                return (
                  <div
                    key={node.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedNode(node);
                      if (onSelectNode) onSelectNode(node);
                    }}
                    style={{ left: `${x}px`, top: `${y}px` }}
                    className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-transform hover:scale-110 ${
                      isSelected ? 'ring-4 ring-emerald-400 z-30 scale-105' : 'z-20'
                    }`}
                  >
                    <div
                      className={`px-3 py-2 rounded-xl border flex items-center gap-2 shadow-lg ${
                        colors.bg
                      } ${colors.border} ${colors.text} ${
                        isCausal
                          ? 'ring-2 ring-amber-400 shadow-amber-500/20 shadow-md'
                          : ''
                      }`}
                    >
                      <div className="p-1 rounded bg-black/20">{getNodeIcon(node.type)}</div>
                      <div className="text-left">
                        <div className="text-[10px] font-mono opacity-80 uppercase leading-none">
                          {node.category}
                        </div>
                        <div className="text-xs font-bold leading-tight mt-0.5 truncate max-w-[170px]">
                          {node.label}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Causal Chain Highlight Banner inside Canvas */}
        {highlightCausalChain && (
          <div className="absolute top-3 left-3 bg-slate-900/90 border border-amber-500/60 rounded-lg p-2.5 text-xs text-amber-300 max-w-sm backdrop-blur-xs shadow-md">
            <div className="flex items-center gap-1.5 font-bold text-amber-400">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Hy's Law Causal Verification Pathway</span>
            </div>
            <div className="text-[11px] text-slate-300 mt-1 leading-snug font-mono">
              Subject 042-S05-003 → Visit WEEK4 → ALT (160 U/L) + Bilirubin (2.8 mg/dL) → FDA Rule (2009) → Safety Alert
            </div>
          </div>
        )}
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 animate-fadeIn">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-[11px] font-mono font-bold uppercase">
                {selectedNode.category}
              </span>
              <span className="text-xs font-mono text-slate-500">ID: {selectedNode.id}</span>
            </div>
            <h4 className="text-sm font-bold text-slate-900 mt-1">{selectedNode.label}</h4>
            <div className="text-xs text-slate-600 mt-0.5 font-mono">
              {JSON.stringify(selectedNode.data || {})}
            </div>
          </div>

          <button
            onClick={() => setSelectedNode(null)}
            className="p-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-600 text-xs font-semibold cursor-pointer self-end md:self-center"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};
