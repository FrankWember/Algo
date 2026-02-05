'use client';

import React from 'react';
import { motion } from 'framer-motion';
import type { PathResponse, ComparisonResponse } from '@/types';

interface ResultsPanelProps {
  result: PathResponse | null;
  comparison: ComparisonResponse | null;
  isLoading: boolean;
}

export default function ResultsPanel({ result, comparison, isLoading }: ResultsPanelProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner" />
      </div>
    );
  }

  if (comparison) {
    return <ComparisonView comparison={comparison} />;
  }

  if (result) {
    return <SingleResultView result={result} />;
  }

  return (
    <div className="text-center py-12 text-gray-500">
      <p className="text-sm">No results yet. Select locations and find a path to see analysis.</p>
    </div>
  );
}

function SingleResultView({ result }: { result: PathResponse }) {
  if (!result.success) {
    return (
      <div className="bg-gray-100 border border-gray-300 rounded-lg p-4">
        <div className="text-gray-900 font-semibold">No Path Found</div>
        <div className="text-gray-600 text-sm mt-1">{result.errorMessage}</div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Algorithm Header */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 mb-1">{result.algorithm}</h4>
        <p className="text-sm text-gray-600">Optimal path found successfully</p>
      </div>

      {/* Key Metrics */}
      <div className="bg-white border border-gray-300 rounded-lg p-4 space-y-3">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Performance Metrics</h5>

        <MetricRow
          label="Total Distance"
          value={`${result.totalDistance.toFixed(1)} meters`}
          description="Length of the shortest path"
        />
        <div className="border-t border-gray-200"></div>

        <MetricRow
          label="Execution Time"
          value={`${result.executionTimeMs.toFixed(3)} ms`}
          description="Algorithm processing time"
        />
        <div className="border-t border-gray-200"></div>

        <MetricRow
          label="Nodes Visited"
          value={result.nodesVisited.toString()}
          description="Buildings explored during search"
        />
        <div className="border-t border-gray-200"></div>

        <MetricRow
          label="Edges Relaxed"
          value={result.edgesRelaxed.toString()}
          description="Path connections evaluated"
        />
      </div>

      {/* Route Path */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Route ({result.pathNames.length} stops)</h5>
        <div className="space-y-2">
          {result.pathNames.map((name, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-900 text-white flex items-center justify-center text-xs font-medium">
                {i + 1}
              </div>
              <div className="text-sm text-gray-700">{name}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ComparisonView({ comparison }: { comparison: ComparisonResponse }) {
  const algorithms = [
    { key: 'dijkstra', data: comparison.dijkstra, name: "Dijkstra's Algorithm" },
    { key: 'astar', data: comparison.astar, name: 'A* Search' },
    { key: 'bellmanFord', data: comparison.bellmanFord, name: 'Bellman-Ford' },
  ];

  // Find max values for bar scaling
  const maxTime = Math.max(...algorithms.map(a => a.data.executionTimeMs));
  const maxNodes = Math.max(...algorithms.map(a => a.data.nodesVisited));

  const winnerName = algorithms.find(a => a.key === comparison.winner)?.name || 'Unknown';

  return (
    <div className="space-y-5">
      {/* Summary */}
      <div className="bg-gray-900 text-white rounded-lg p-4">
        <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">Most Efficient</div>
        <div className="text-lg font-semibold">{winnerName}</div>
        <div className="text-xs text-gray-300 mt-2 leading-relaxed">
          {comparison.summary.analysis}
        </div>
      </div>

      {/* Path Distance */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-2">Shortest Path Distance</h5>
        <div className="text-2xl font-bold text-gray-900 mb-1">
          {comparison.dijkstra.totalDistance.toFixed(1)} meters
        </div>
        {comparison.summary.allPathsEqual && (
          <p className="text-xs text-gray-600">
            All algorithms found the same optimal path
          </p>
        )}
      </div>

      {/* Execution Time Comparison */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Execution Time Comparison</h5>
        <p className="text-xs text-gray-600 mb-4">Lower is faster</p>
        <div className="space-y-4">
          {algorithms.map(({ key, data, name }) => (
            <div key={key}>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-gray-700">{name}</span>
                <span className="text-gray-900 font-mono">{data.executionTimeMs.toFixed(3)} ms</span>
              </div>
              <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(data.executionTimeMs / maxTime) * 100}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                  className="h-full bg-gray-700 rounded-full"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Nodes Visited Comparison */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Search Efficiency</h5>
        <p className="text-xs text-gray-600 mb-4">Number of buildings explored (lower is more efficient)</p>
        <div className="space-y-4">
          {algorithms.map(({ key, data, name }) => (
            <div key={key}>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-gray-700">{name}</span>
                <span className="text-gray-900 font-mono">{data.nodesVisited} buildings</span>
              </div>
              <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(data.nodesVisited / maxNodes) * 100}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
                  className="h-full bg-gray-700 rounded-full"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Algorithm Stats */}
      <div className="space-y-3">
        <h5 className="text-sm font-semibold text-gray-700">Detailed Statistics</h5>
        {algorithms.map(({ key, data, name }) => (
          <details key={key} className="bg-white border border-gray-300 rounded-lg">
            <summary className="p-3 cursor-pointer hover:bg-gray-50 flex items-center justify-between font-medium text-sm text-gray-700">
              <span>{name}</span>
              <span className="text-gray-500 font-normal">
                {data.success ? `${data.totalDistance.toFixed(1)}m` : 'Failed'}
              </span>
            </summary>
            <div className="px-4 pb-4 pt-2 border-t border-gray-200 space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-gray-500 text-xs mb-1">Algorithm Steps</div>
                  <div className="font-mono text-gray-900">{data.steps.length}</div>
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-1">Edges Evaluated</div>
                  <div className="font-mono text-gray-900">{data.edgesRelaxed}</div>
                </div>
              </div>
              <div>
                <div className="text-gray-500 text-xs mb-2">Complete Route</div>
                <div className="space-y-1.5">
                  {data.pathNames.map((buildingName, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-medium text-gray-700">
                        {i + 1}
                      </div>
                      <span className="text-gray-700">{buildingName}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function MetricRow({ label, value, description }: { label: string; value: string; description: string }) {
  return (
    <div>
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-base font-semibold text-gray-900 font-mono">{value}</span>
      </div>
      <div className="text-xs text-gray-500">{description}</div>
    </div>
  );
}
