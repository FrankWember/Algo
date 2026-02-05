'use client';

import React, { useState, useMemo } from 'react';
import { MapPin, Building2, Home, Car, Dumbbell } from 'lucide-react';
import type { Node } from '@/types';

interface BuildingSelectorProps {
  nodes: Node[];
  selectedStart: string | null;
  selectedEnd: string | null;
  onStartSelect: (id: string) => void;
  onEndSelect: (id: string) => void;
  onSwap: () => void;
}

interface LocationInputProps {
  label: string;
  value: string;
  selectedNode: Node | undefined;
  colorClass: string;
  isActive: boolean;
  onFocus: () => void;
  onBlur: () => void;
  onChange: (value: string) => void;
  onClear: () => void;
  onSelect: (id: string) => void;
  filteredNodes: Node[];
  groupedNodes: Record<string, Node[]>;
  searchQuery: string;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  academic: <Building2 size={14} />,
  residential: <Home size={14} />,
  parking: <Car size={14} />,
  athletic: <Dumbbell size={14} />,
  other: <MapPin size={14} />,
};

const TYPE_LABELS: Record<string, string> = {
  academic: 'Academic',
  residential: 'Residential',
  parking: 'Parking',
  athletic: 'Athletic',
  other: 'Other',
};

function NodeDropdown({
  nodes,
  searchQuery,
  groupedNodes,
  onSelect,
}: {
  nodes: Node[];
  searchQuery: string;
  groupedNodes: Record<string, Node[]>;
  onSelect: (id: string) => void;
}) {
  if (searchQuery) {
    return nodes.length > 0 ? (
      <>
        {nodes.map(node => (
          <NodeItem key={node.id} node={node} onSelect={onSelect} />
        ))}
      </>
    ) : (
      <div className="px-3 py-2 text-gray-500 text-sm">No results found</div>
    );
  }

  return (
    <>
      {Object.entries(groupedNodes).map(([type, typeNodes]) => (
        <NodeGroup
          key={type}
          type={type}
          nodes={typeNodes}
          onSelect={onSelect}
        />
      ))}
    </>
  );
}

function NodeGroup({
  type,
  nodes,
  onSelect,
}: {
  type: string;
  nodes: Node[];
  onSelect: (id: string) => void;
}) {
  return (
    <div>
      <div className="px-3 py-1 bg-gray-50 text-xs font-medium text-gray-500 sticky top-0">
        {TYPE_LABELS[type]}
      </div>
      {nodes.slice(0, 10).map(node => (
        <NodeItem key={node.id} node={node} onSelect={onSelect} />
      ))}
    </div>
  );
}

function NodeItem({
  node,
  onSelect,
  showShortName = false,
}: {
  node: Node;
  onSelect: (id: string) => void;
  showShortName?: boolean;
}) {
  return (
    <button
      onClick={() => onSelect(node.id)}
      className="w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center gap-2 text-sm"
    >
      {TYPE_ICONS[node.type]}
      <span>{node.name}</span>
      {showShortName && (
        <span className="text-gray-400 text-xs">({node.shortName})</span>
      )}
    </button>
  );
}

function LocationInput({
  label,
  value,
  selectedNode,
  colorClass,
  isActive,
  onFocus,
  onBlur,
  onChange,
  onClear,
  onSelect,
  filteredNodes,
  groupedNodes,
  searchQuery,
}: LocationInputProps) {
  return (
    <div className="relative">
      <label className="block text-xs font-medium text-gray-500 mb-1">
        {label}
      </label>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <div className={`w-3 h-3 rounded-full ${colorClass}`} />
        </div>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          onBlur={() => setTimeout(onBlur, 200)}
          placeholder="Search buildings..."
          className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-siue-red focus:border-transparent"
        />
        {selectedNode && !searchQuery && (
          <button
            onClick={onClear}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        )}
      </div>

      {isActive && (searchQuery || !selectedNode) && (
        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          <NodeDropdown
            nodes={filteredNodes}
            searchQuery={searchQuery}
            groupedNodes={groupedNodes}
            onSelect={(id) => {
              onSelect(id);
              onChange('');
            }}
          />
        </div>
      )}
    </div>
  );
}

export default function BuildingSelector({
  nodes,
  selectedStart,
  selectedEnd,
  onStartSelect,
  onEndSelect,
  onSwap,
}: BuildingSelectorProps) {
  const [startSearch, setStartSearch] = useState('');
  const [endSearch, setEndSearch] = useState('');
  const [activeField, setActiveField] = useState<'start' | 'end' | null>(null);

  const groupedNodes = useMemo(() => {
    const groups: Record<string, Node[]> = {};
    nodes.forEach(node => {
      if (!groups[node.type]) {
        groups[node.type] = [];
      }
      groups[node.type].push(node);
    });
    Object.values(groups).forEach(group => {
      group.sort((a, b) => a.name.localeCompare(b.name));
    });
    return groups;
  }, [nodes]);

  const filterNodes = (search: string) => {
    const searchLower = search.toLowerCase();
    return nodes.filter(
      node =>
        node.name.toLowerCase().includes(searchLower) ||
        node.shortName.toLowerCase().includes(searchLower) ||
        node.id.toLowerCase().includes(searchLower)
    );
  };

  const filteredStartNodes = startSearch ? filterNodes(startSearch) : [];
  const filteredEndNodes = endSearch ? filterNodes(endSearch) : [];

  const findNode = (id: string | null) => nodes.find(n => n.id === id);
  const startNode = findNode(selectedStart);
  const endNode = findNode(selectedEnd);

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-gray-700 text-sm">Select Route</h3>

      <LocationInput
        label="Start Location"
        value={startSearch || (startNode ? startNode.name : '')}
        selectedNode={startNode}
        colorClass="bg-green-500"
        isActive={activeField === 'start'}
        onFocus={() => setActiveField('start')}
        onBlur={() => setActiveField(null)}
        onChange={(value) => {
          setStartSearch(value);
          setActiveField('start');
        }}
        onClear={() => {
          onStartSelect('');
          setStartSearch('');
        }}
        onSelect={onStartSelect}
        filteredNodes={filteredStartNodes}
        groupedNodes={groupedNodes}
        searchQuery={startSearch}
      />

      <div className="flex justify-center">
        <button
          onClick={onSwap}
          disabled={!selectedStart && !selectedEnd}
          className="p-2 rounded-full hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Swap start and end"
        >
          <svg
            className="w-5 h-5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
            />
          </svg>
        </button>
      </div>

      <LocationInput
        label="End Location"
        value={endSearch || (endNode ? endNode.name : '')}
        selectedNode={endNode}
        colorClass="bg-red-500"
        isActive={activeField === 'end'}
        onFocus={() => setActiveField('end')}
        onBlur={() => setActiveField(null)}
        onChange={(value) => {
          setEndSearch(value);
          setActiveField('end');
        }}
        onClear={() => {
          onEndSelect('');
          setEndSearch('');
        }}
        onSelect={onEndSelect}
        filteredNodes={filteredEndNodes}
        groupedNodes={groupedNodes}
        searchQuery={endSearch}
      />
    </div>
  );
}
