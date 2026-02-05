'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { Node, Edge, AlgorithmStep } from '@/types';

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
  academic: '#dc2626',
  residential: '#2563eb',
  athletic: '#16a34a',
  parking: '#9333ea',
  other: '#64748b',
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

  // Zoom and pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Scale coordinates to SVG dimensions with zoom and pan
  const scaleX = (x: number) => {
    const baseX = (x / 100) * dimensions.width * 0.9 + dimensions.width * 0.05;
    return baseX * zoom + pan.x;
  };
  const scaleY = (y: number) => {
    const baseY = (y / 100) * dimensions.height * 0.9 + dimensions.height * 0.05;
    return baseY * zoom + pan.y;
  };

  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (svgRef.current) {
        const rect = svgRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Zoom controls - centered zoom
  const handleZoomIn = () => {
    const newZoom = Math.min(zoom + 0.2, 3);
    zoomToCenter(newZoom);
  };

  const handleZoomOut = () => {
    const newZoom = Math.max(zoom - 0.2, 0.5);
    zoomToCenter(newZoom);
  };

  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Zoom from center
  const zoomToCenter = (newZoom: number) => {
    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;

    // Calculate the point in the original coordinate system
    const originX = (centerX - pan.x) / zoom;
    const originY = (centerY - pan.y) / zoom;

    // Calculate new pan to keep the center point fixed
    const newPan = {
      x: centerX - originX * newZoom,
      y: centerY - originY * newZoom,
    };

    setZoom(newZoom);
    setPan(newPan);
  };

  // Mouse wheel zoom - centered
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    const newZoom = Math.max(0.5, Math.min(3, zoom + delta));

    if (newZoom !== zoom) {
      const rect = svgRef.current?.getBoundingClientRect();
      if (rect) {
        // Zoom towards mouse cursor position
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const originX = (mouseX - pan.x) / zoom;
        const originY = (mouseY - pan.y) / zoom;

        setPan({
          x: mouseX - originX * newZoom,
          y: mouseY - originY * newZoom,
        });
        setZoom(newZoom);
      }
    }
  }, [zoom, pan]);

  // Panning with mouse drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0 && e.target === svgRef.current) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    }
  }, [isPanning, panStart]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Check if an edge is part of the current path
  const isEdgeInPath = useCallback((source: string, target: string) => {
    for (let i = 0; i < path.length - 1; i++) {
      if (
        (path[i] === source && path[i + 1] === target) ||
        (path[i] === target && path[i + 1] === source)
      ) {
        return true;
      }
    }
    return false;
  }, [path]);

  // Check if edge is highlighted (being considered by algorithm)
  const isEdgeHighlighted = useCallback((source: string, target: string) => {
    return highlightedEdges.some(
      e => (e.source === source && e.target === target) ||
           (e.source === target && e.target === source)
    );
  }, [highlightedEdges]);

  // Get node state for styling
  const getNodeState = useCallback((nodeId: string) => {
    if (nodeId === selectedStart) return 'start';
    if (nodeId === selectedEnd) return 'end';
    if (nodeId === currentNode) return 'current';
    if (path.includes(nodeId)) return 'path';
    if (visitedNodes.includes(nodeId)) return 'visited';
    return 'default';
  }, [selectedStart, selectedEnd, currentNode, path, visitedNodes]);

  // Get node radius based on state
  const getNodeRadius = (state: string) => {
    switch (state) {
      case 'start':
      case 'end':
        return 12;
      case 'current':
        return 10;
      case 'path':
        return 9;
      case 'visited':
        return 7;
      default:
        return 6;
    }
  };

  // Get node color based on state and type
  const getNodeColor = (node: Node, state: string) => {
    switch (state) {
      case 'start':
        return '#22c55e'; // Green
      case 'end':
        return '#ef4444'; // Red
      case 'current':
        return '#f59e0b'; // Amber
      case 'path':
        return '#3b82f6'; // Blue
      case 'visited':
        return '#a855f7'; // Purple (lighter)
      default:
        return NODE_COLORS[node.type] || '#64748b';
    }
  };

  const handleNodeHover = (e: React.MouseEvent, node: Node) => {
    if (!isPanning) {
      const rect = svgRef.current?.getBoundingClientRect();
      if (rect) {
        setTooltip({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top - 40,
          node,
        });
      }
    }
  };

  // Determine if labels should be shown based on zoom level
  const shouldShowLabels = zoom > 1.2;

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

      {/* Legend - Bottom left on mobile, top left on desktop */}
      <div className="absolute bottom-4 left-4 md:top-4 bg-white/90 backdrop-blur-sm p-2 md:p-3 rounded-lg shadow-md z-10 text-xs max-w-xs">
        <div className="font-semibold mb-1 md:mb-2 text-gray-700 text-xs md:text-sm">Legend</div>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-x-2 md:gap-x-3 gap-y-1">
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
        <div className="hidden md:block mt-2 pt-2 border-t border-gray-200 text-[10px] text-gray-500">
          Scroll to zoom, drag to pan
        </div>
        <div className="md:hidden mt-1 pt-1 border-t border-gray-200 text-[9px] text-gray-500">
          Pinch to zoom, drag to pan
        </div>
      </div>

      <svg
        ref={svgRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        preserveAspectRatio="xMidYMid meet"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
      >
        {/* Grid background */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e5e7eb" strokeWidth="0.5" />
          </pattern>
        </defs>
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
                style={{
                  transition: 'stroke 0.3s, stroke-width 0.3s',
                }}
              />
            );
          })}
        </g>

        {/* Nodes */}
        <g className="nodes">
          {nodes.map(node => {
            const state = getNodeState(node.id);
            const radius = getNodeRadius(state);
            const color = getNodeColor(node, state);
            const isInteractive = state === 'default' || state === 'visited';

            // Filter parking lots when not showing all nodes
            if (!showAllNodes && node.type === 'parking' && state === 'default') {
              return null;
            }

            return (
              <g
                key={node.id}
                className={`cursor-pointer ${state === 'current' ? 'node-visiting' : ''}`}
                onClick={() => onNodeClick(node.id)}
                onMouseEnter={(e) => handleNodeHover(e, node)}
                onMouseLeave={() => setTooltip(null)}
              >
                {/* Outer ring for start/end */}
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

                {/* Node label - shown only for important nodes or when zoomed in */}
                {(state !== 'default' || (shouldShowLabels && node.type !== 'parking')) && (
                  <text
                    x={scaleX(node.x)}
                    y={scaleY(node.y) + radius + 14}
                    textAnchor="middle"
                    fontSize={zoom > 1.5 ? "11" : "10"}
                    fill="#374151"
                    fontWeight={state !== 'default' ? 'bold' : 'normal'}
                    style={{
                      pointerEvents: 'none',
                      userSelect: 'none',
                    }}
                  >
                    {node.shortName}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="node-tooltip"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: 'translateX(-50%)',
          }}
        >
          <div className="font-semibold">{tooltip.node.name}</div>
          <div className="text-gray-500 text-xs capitalize">{tooltip.node.type}</div>
        </div>
      )}
    </div>
  );
}
