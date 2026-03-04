'use client';

import React from 'react';
import { motion } from 'framer-motion';
import type { AlgorithmType } from '@/types';

interface AlgorithmSelectorProps {
  selectedAlgorithm: AlgorithmType | 'compare';
  onSelect: (algorithm: AlgorithmType | 'compare') => void;
}

const ALGORITHMS = [
  {
    id: 'dijkstra' as const,
    name: "Dijkstra's",
    description: 'Classic greedy shortest path',
    complexity: 'O((V+E) log V)',
    color: 'bg-blue-500',
    icon: '🎯',
  },
  {
    id: 'floydWarshall' as const,
    name: 'Floyd-Warshall',
    description: 'All-pairs dynamic programming',
    complexity: 'O(V³)',
    color: 'bg-purple-500',
    icon: '🔄',
  },
  {
    id: 'compare' as const,
    name: 'Compare All',
    description: 'Run all algorithms and compare',
    complexity: 'Side by side',
    color: 'bg-siue-red',
    icon: '📊',
  },
];

export default function AlgorithmSelector({
  selectedAlgorithm,
  onSelect,
}: AlgorithmSelectorProps) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-gray-700 text-sm">Select Algorithm</h3>
      <div className="grid grid-cols-2 gap-3">
        {ALGORITHMS.map((algo) => (
          <motion.button
            key={algo.id}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSelect(algo.id)}
            className={`
              algorithm-card p-3 rounded-lg border-2 text-left transition-all
              ${selectedAlgorithm === algo.id
                ? 'border-siue-red bg-red-50'
                : 'border-gray-200 bg-white hover:border-gray-300'
              }
            `}
          >
            <div className="flex items-start gap-2">
              <span className="text-xl">{algo.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 text-sm leading-snug">
                  {algo.name}
                </div>
                <div className="text-xs text-gray-500 leading-snug">
                  {algo.description}
                </div>
                <div className="mt-1">
                  <span className={`
                    inline-block px-1.5 py-0.5 rounded text-xs font-mono
                    ${selectedAlgorithm === algo.id
                      ? 'bg-siue-red text-white'
                      : 'bg-gray-100 text-gray-600'
                    }
                  `}>
                    {algo.complexity}
                  </span>
                </div>
              </div>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
