'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { Node, Edge } from '@/types';

interface CampusMapProps {
  nodes: Node[];
  edges: Edge[];
  path: string[];
  visitedNodes: string[];
  currentNode: string | null;
  selectedStart: string | null;
  selectedEnd: string | null;
  onNodeClick: (nodeId: string) => void;
  highlightedEdges?: Array<{ source: string; target: string }>;
  showAllNodes?: boolean;
}

const NODE_COLORS: Record<string, string> = {
  academic: '#dc2626',      // red
  residential: '#2563eb',   // blue
  recreation: '#16a34a',    // green
  parking: '#9333ea',       // purple
  research: '#d97706',      // amber
  other: '#64748b',         // slate
};

export default function CampusMap({
  nodes,
  edges,
  path,
  visitedNodes,
  currentNode,
  selectedStart,
  selectedEnd,
  onNodeClick,
  highlightedEdges = [],
  showAllNodes = true,
}: CampusMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: Node } | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // ─── Zoom / pan state (drives re-renders / visual output) ───────────────
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  // isPanning is ONLY used to change the cursor; all drag logic uses refs below.
  const [isPanning, setIsPanning] = useState(false);

  // ─── Refs mirror the latest state values so event handlers always have
  //     up-to-date data without stale closures or re-creation on every render.
  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const isDraggingRef = useRef(false);
  const lastPointerRef = useRef({ x: 0, y: 0 }); // last mouse/touch position
  const lastTouchDistRef = useRef(0);             // for pinch-to-zoom distance

  // Keep refs in sync whenever state changes (state is the source of truth for rendering).
  useEffect(() => { panRef.current = pan; }, [pan]);
  useEffect(() => { zoomRef.current = zoom; }, [zoom]);

  // ─── Helpers that update both the ref (instant) and state (schedules render) ──

  /** Pan to a new absolute offset. */
  const applyPan = useCallback((newPan: { x: number; y: number }) => {
    panRef.current = newPan;
    setPan(newPan);
  }, []);

  /**
   * Zoom to `newZoom` while keeping the screen point (pivotX, pivotY) fixed.
   *
   * Derivation:
   *   screen_x = baseX * zoom + pan.x   →   baseX = (screen_x − pan.x) / zoom
   *   We want baseX * newZoom + newPan.x = screen_x (same physical point stays put)
   *   ∴  newPan.x = screen_x − baseX * newZoom
   */
  const applyZoom = useCallback((newZoom: number, pivotX: number, pivotY: number) => {
    const originX = (pivotX - panRef.current.x) / zoomRef.current;
    const originY = (pivotY - panRef.current.y) / zoomRef.current;
    const newPan = {
      x: pivotX - originX * newZoom,
      y: pivotY - originY * newZoom,
    };
    panRef.current = newPan;
    zoomRef.current = newZoom;
    setPan(newPan);
    setZoom(newZoom);
  }, []); // stable — closes only over refs

  // ─── Resize observer ────────────────────────────────────────────────────
  useEffect(() => {
    const update = () => {
      if (svgRef.current) {
        const r = svgRef.current.getBoundingClientRect();
        setDimensions({ width: r.width, height: r.height });
      }
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  // ─── All pointer / wheel event handling (mounted once) ──────────────────
  //
  // Why imperative listeners instead of React props?
  //
  // 1. `wheel` — React attaches wheel listeners as passive in some builds,
  //    preventing e.preventDefault() (needed to stop page scroll while zooming).
  //    Attaching natively with { passive: false } guarantees it works.
  //
  // 2. `mousemove` / `mouseup` on *window* — attaching these at window level
  //    means the drag continues even when the cursor leaves the SVG boundary.
  //    The old onMouseLeave={handleMouseUp} caused panning to abort on fast drags.
  //
  // 3. Refs instead of state for drag flags — state updates are batched and
  //    scheduled; a mousemove event arriving before the re-render would see the
  //    old isPanning=false and silently do nothing. Refs are always current.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    // ── Wheel zoom ──────────────────────────────────────────────────────
    const onWheel = (e: WheelEvent) => {
      e.preventDefault(); // stop the page from scrolling
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      const newZoom = Math.max(0.5, Math.min(3, zoomRef.current + delta));
      if (newZoom === zoomRef.current) return;

      const rect = svg.getBoundingClientRect();
      applyZoom(newZoom, e.clientX - rect.left, e.clientY - rect.top);
    };

    // ── Mouse drag ──────────────────────────────────────────────────────
    const onMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return; // left button only

      // Let clicks on building nodes fall through to their React onClick handler.
      // We detect this by checking whether the target is inside a .node-group <g>.
      if ((e.target as SVGElement).closest('.node-group')) return;

      e.preventDefault(); // prevent text selection while dragging
      isDraggingRef.current = true;
      lastPointerRef.current = { x: e.clientX, y: e.clientY };
      setIsPanning(true);
    };

    // Attached to window so panning continues if the cursor leaves the SVG.
    const onMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const dx = e.clientX - lastPointerRef.current.x;
      const dy = e.clientY - lastPointerRef.current.y;
      lastPointerRef.current = { x: e.clientX, y: e.clientY };
      applyPan({ x: panRef.current.x + dx, y: panRef.current.y + dy });
    };

    const onMouseUp = () => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      setIsPanning(false);
    };

    // ── Touch drag + pinch-to-zoom ───────────────────────────────────────
    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        e.preventDefault();
        isDraggingRef.current = true;
        lastTouchDistRef.current = 0;
        lastPointerRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        setIsPanning(true);
      } else if (e.touches.length === 2) {
        e.preventDefault();
        isDraggingRef.current = true;
        lastTouchDistRef.current = Math.hypot(
          e.touches[1].clientX - e.touches[0].clientX,
          e.touches[1].clientY - e.touches[0].clientY,
        );
        // Track midpoint for panning during pinch
        lastPointerRef.current = {
          x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
          y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
        };
      }
    };

    const onTouchMove = (e: TouchEvent) => {
      if (!isDraggingRef.current) return;
      e.preventDefault();

      if (e.touches.length === 1) {
        // Single-finger pan
        const dx = e.touches[0].clientX - lastPointerRef.current.x;
        const dy = e.touches[0].clientY - lastPointerRef.current.y;
        lastPointerRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        applyPan({ x: panRef.current.x + dx, y: panRef.current.y + dy });
      } else if (e.touches.length === 2) {
        // Two-finger pinch zoom + pan
        const dist = Math.hypot(
          e.touches[1].clientX - e.touches[0].clientX,
          e.touches[1].clientY - e.touches[0].clientY,
        );
        const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
        const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        const rect = svg.getBoundingClientRect();

        if (lastTouchDistRef.current > 0) {
          const scale = dist / lastTouchDistRef.current;
          const newZoom = Math.max(0.5, Math.min(3, zoomRef.current * scale));
          applyZoom(newZoom, midX - rect.left, midY - rect.top);
        }
        lastTouchDistRef.current = dist;
        lastPointerRef.current = { x: midX, y: midY };
      }
    };

    const onTouchEnd = () => {
      isDraggingRef.current = false;
      lastTouchDistRef.current = 0;
      setIsPanning(false);
    };

    // ── Register listeners ───────────────────────────────────────────────
    svg.addEventListener('wheel', onWheel, { passive: false });
    svg.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    svg.addEventListener('touchstart', onTouchStart, { passive: false });
    svg.addEventListener('touchmove', onTouchMove, { passive: false });
    svg.addEventListener('touchend', onTouchEnd);

    return () => {
      svg.removeEventListener('wheel', onWheel);
      svg.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      svg.removeEventListener('touchstart', onTouchStart);
      svg.removeEventListener('touchmove', onTouchMove);
      svg.removeEventListener('touchend', onTouchEnd);
    };
  }, [applyPan, applyZoom]); // applyPan / applyZoom are stable (empty-dep useCallbacks)

  // ─── Zoom button controls ────────────────────────────────────────────────
  const handleZoomIn = () => {
    const newZoom = Math.min(zoomRef.current + 0.2, 3);
    applyZoom(newZoom, dimensions.width / 2, dimensions.height / 2);
  };

  const handleZoomOut = () => {
    const newZoom = Math.max(zoomRef.current - 0.2, 0.5);
    applyZoom(newZoom, dimensions.width / 2, dimensions.height / 2);
  };

  const handleResetView = () => {
    panRef.current = { x: 0, y: 0 };
    zoomRef.current = 1;
    setPan({ x: 0, y: 0 });
    setZoom(1);
  };

  // ─── Coordinate scaling (called during render, so uses state values) ────
  const scaleX = (x: number) => {
    const baseX = (x / 100) * dimensions.width * 0.9 + dimensions.width * 0.05;
    return baseX * zoom + pan.x;
  };
  const scaleY = (y: number) => {
    const baseY = (y / 100) * dimensions.height * 0.9 + dimensions.height * 0.05;
    return baseY * zoom + pan.y;
  };

  // ─── Edge / node helpers ────────────────────────────────────────────────
  const isEdgeInPath = useCallback((source: string, target: string) => {
    for (let i = 0; i < path.length - 1; i++) {
      if (
        (path[i] === source && path[i + 1] === target) ||
        (path[i] === target && path[i + 1] === source)
      ) return true;
    }
    return false;
  }, [path]);

  const isEdgeHighlighted = useCallback((source: string, target: string) =>
    highlightedEdges.some(
      e => (e.source === source && e.target === target) ||
           (e.source === target && e.target === source),
    ), [highlightedEdges]);

  const getNodeState = useCallback((nodeId: string) => {
    if (nodeId === selectedStart) return 'start';
    if (nodeId === selectedEnd) return 'end';
    if (nodeId === currentNode) return 'current';
    if (path.includes(nodeId)) return 'path';
    if (visitedNodes.includes(nodeId)) return 'visited';
    return 'default';
  }, [selectedStart, selectedEnd, currentNode, path, visitedNodes]);

  const getNodeRadius = (state: string) => {
    switch (state) {
      case 'start': case 'end': return 12;
      case 'current': return 10;
      case 'path': return 9;
      case 'visited': return 7;
      default: return 6;
    }
  };

  const getNodeColor = (node: Node, state: string) => {
    switch (state) {
      case 'start':   return '#22c55e';
      case 'end':     return '#ef4444';
      case 'current': return '#f59e0b';
      case 'path':    return '#3b82f6';
      case 'visited': return '#a855f7';
      default: return NODE_COLORS[node.type] || '#64748b';
    }
  };

  const handleNodeHover = (e: React.MouseEvent, node: Node) => {
    if (!isDraggingRef.current) {
      const rect = svgRef.current?.getBoundingClientRect();
      if (rect) {
        setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top - 40, node });
      }
    }
  };

  const shouldShowLabels = zoom > 1.2;

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-white rounded-lg shadow-inner overflow-hidden"
    >
      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 z-20 map-controls">
        <button
          onClick={handleZoomIn}
          disabled={zoom >= 3}
          className="bg-white/90 backdrop-blur-sm px-3 py-2 md:px-4 md:py-3 rounded-lg shadow-md hover:bg-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-gray-700 text-sm"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          disabled={zoom <= 0.5}
          className="bg-white/90 backdrop-blur-sm px-3 py-2 md:px-4 md:py-3 rounded-lg shadow-md hover:bg-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-gray-700 text-sm"
          title="Zoom Out"
        >
          −
        </button>
        <button
          onClick={handleResetView}
          className="bg-white/90 backdrop-blur-sm px-3 py-2 md:px-4 md:py-3 rounded-lg shadow-md hover:bg-white transition-colors text-gray-700 text-xs font-medium"
          title="Reset View"
        >
          Reset
        </button>

        {/* Zoom level indicator */}
        <div className="bg-white/90 backdrop-blur-sm px-2 py-1 rounded-lg shadow-md text-xs text-center font-medium text-gray-600">
          {Math.round(zoom * 100)}%
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 md:top-4 bg-white/90 backdrop-blur-sm p-2 md:p-3 rounded-lg shadow-md z-10 text-xs max-w-xs">
        <div className="font-semibold mb-1 md:mb-2 text-gray-700 text-xs md:text-sm">Legend</div>
        <div className="grid grid-cols-2 gap-x-2 md:gap-x-3 gap-y-1 mb-2">
          <div className="flex items-center gap-1 md:gap-2">
            <div className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-green-500 flex-shrink-0" />
            <span className="text-[10px] md:text-xs">Start</span>
          </div>
          <div className="flex items-center gap-1 md:gap-2">
            <div className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-red-500 flex-shrink-0" />
            <span className="text-[10px] md:text-xs">End</span>
          </div>
          <div className="flex items-center gap-1 md:gap-2">
            <div className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-amber-500 flex-shrink-0" />
            <span className="text-[10px] md:text-xs">Current</span>
          </div>
          <div className="flex items-center gap-1 md:gap-2">
            <div className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-purple-500 flex-shrink-0" />
            <span className="text-[10px] md:text-xs">Visited</span>
          </div>
          <div className="flex items-center gap-1 md:gap-2 col-span-2">
            <div className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-blue-500 flex-shrink-0" />
            <span className="text-[10px] md:text-xs">Path</span>
          </div>
        </div>
        <div className="border-t border-gray-200 pt-1 md:pt-2 grid grid-cols-2 gap-x-2 gap-y-1">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#dc2626' }} />
            <span className="text-[9px] md:text-[10px] text-gray-600">Academic</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#2563eb' }} />
            <span className="text-[9px] md:text-[10px] text-gray-600">Residential</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#16a34a' }} />
            <span className="text-[9px] md:text-[10px] text-gray-600">Recreation</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#d97706' }} />
            <span className="text-[9px] md:text-[10px] text-gray-600">Research</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#9333ea' }} />
            <span className="text-[9px] md:text-[10px] text-gray-600">Parking</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#64748b' }} />
            <span className="text-[9px] md:text-[10px] text-gray-600">Other</span>
          </div>
        </div>
        <div className="hidden md:block mt-2 pt-2 border-t border-gray-200 text-[10px] text-gray-500">
          Scroll to zoom · drag to pan
        </div>
        <div className="md:hidden mt-1 pt-1 border-t border-gray-200 text-[9px] text-gray-500">
          Pinch to zoom · drag to pan
        </div>
      </div>

      {/*
        The SVG has NO onWheel / onMouseDown / onMouseMove / onMouseUp / onMouseLeave
        props — all interaction is wired imperatively in the useEffect above.
        This avoids React's passive-listener default (which breaks preventDefault)
        and eliminates stale-closure bugs from handler recreation.
      */}
      <svg
        ref={svgRef}
        className="w-full h-full"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
      >
        {/* Grid background */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e5e7eb" strokeWidth="0.5" />
          </pattern>
        </defs>
        {/* This rect covers the entire SVG and is the most common drag target.
            Previously the mousedown guard checked e.target === svg (the SVG root),
            which this rect always intercepted — panning never started. */}
        <rect width="100%" height="100%" fill="url(#grid)" />

        {/* Edges */}
        <g className="edges">
          {edges.map((edge, index) => {
            const sourceNode = nodes.find(n => n.id === edge.source);
            const targetNode = nodes.find(n => n.id === edge.target);
            if (!sourceNode || !targetNode) return null;

            const inPath = isEdgeInPath(edge.source, edge.target);
            const highlighted = isEdgeHighlighted(edge.source, edge.target);

            return (
              <line
                key={`edge-${index}`}
                x1={scaleX(sourceNode.x)}
                y1={scaleY(sourceNode.y)}
                x2={scaleX(targetNode.x)}
                y2={scaleY(targetNode.y)}
                stroke={inPath ? '#3b82f6' : highlighted ? '#f59e0b' : '#d1d5db'}
                strokeWidth={inPath ? 4 : highlighted ? 3 : 1.5}
                strokeLinecap="round"
                className={inPath ? 'path-animated' : ''}
                style={{ transition: 'stroke 0.3s, stroke-width 0.3s' }}
              />
            );
          })}
        </g>

        {/* Nodes — each node group has the "node-group" class so the drag handler
            can identify node clicks and skip starting a pan for them. */}
        <g className="nodes">
          {nodes.map(node => {
            const state = getNodeState(node.id);
            const radius = getNodeRadius(state);
            const color = getNodeColor(node, state);

            if (!showAllNodes && node.type === 'parking' && state === 'default') {
              return null;
            }

            return (
              <g
                key={node.id}
                // "node-group" lets the drag handler exempt clicks on nodes
                className={`node-group cursor-pointer ${state === 'current' ? 'node-visiting' : ''}`}
                onClick={() => onNodeClick(node.id)}
                onMouseEnter={(e) => handleNodeHover(e, node)}
                onMouseLeave={() => setTooltip(null)}
              >
                {/* Pulsing outer ring for start / end nodes */}
                {(state === 'start' || state === 'end') && (
                  <circle
                    cx={scaleX(node.x)}
                    cy={scaleY(node.y)}
                    r={radius + 4}
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    strokeDasharray="4 2"
                    className="animate-pulse"
                  />
                )}

                {/* Main node circle */}
                <circle
                  cx={scaleX(node.x)}
                  cy={scaleY(node.y)}
                  r={radius}
                  fill={color}
                  stroke="white"
                  strokeWidth="2"
                  style={{
                    filter: state !== 'default' ? 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' : 'none',
                    transition: 'r 0.3s, fill 0.3s',
                  }}
                />

                {/* Label — shown for highlighted nodes or when zoomed in */}
                {(state !== 'default' || (shouldShowLabels && node.type !== 'parking')) && (
                  <text
                    x={scaleX(node.x)}
                    y={scaleY(node.y) + radius + 14}
                    textAnchor="middle"
                    fontSize={zoom > 1.5 ? '11' : '10'}
                    fill="#374151"
                    fontWeight={state !== 'default' ? 'bold' : 'normal'}
                    style={{ pointerEvents: 'none', userSelect: 'none' }}
                  >
                    {node.shortName}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Hover tooltip */}
      {tooltip && (
        <div
          className="node-tooltip"
          style={{ left: tooltip.x, top: tooltip.y, transform: 'translateX(-50%)' }}
        >
          <div className="font-semibold">{tooltip.node.name}</div>
          <div className="text-gray-500 text-xs capitalize">{tooltip.node.type}</div>
        </div>
      )}
    </div>
  );
}
