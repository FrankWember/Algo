'use client';

import React from 'react';
import { motion } from 'framer-motion';
import type { PathResponse, ComparisonResponse, AccessibilityInfo, RoutePreferences } from '@/types';

interface ResultsPanelProps {
  result: PathResponse | null;
  comparison: ComparisonResponse | null;
  isLoading: boolean;
  accessibilityData?: Record<string, AccessibilityInfo>;
  preferences?: RoutePreferences;
}

export default function ResultsPanel({
  result, comparison, isLoading, accessibilityData = {}, preferences,
}: ResultsPanelProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner" />
      </div>
    );
  }

  if (comparison) {
    return <ComparisonView comparison={comparison} accessibilityData={accessibilityData} preferences={preferences} />;
  }

  if (result) {
    return <SingleResultView result={result} accessibilityData={accessibilityData} preferences={preferences} />;
  }

  return (
    <div className="text-center py-12 text-gray-500">
      <p className="text-sm">No results yet. Select locations and find a path to see analysis.</p>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function computePathAccessibility(
  path: string[],
  accessibilityData: Record<string, AccessibilityInfo>
): { rating: number; wheelchairOk: boolean; totalStairs: number; hasElevator: boolean; issues: string[] } {
  if (path.length === 0) return { rating: 10, wheelchairOk: true, totalStairs: 0, hasElevator: false, issues: [] };

  let ratingSum = 0, ratingCount = 0, totalStairs = 0, hasElevator = false;
  let wheelchairOk = true;
  const issues: string[] = [];

  for (const bid of path) {
    const info = accessibilityData[bid];
    if (!info) continue;
    ratingSum += info.accessibility_rating;
    ratingCount++;
    if (!info.wheelchair_accessible) {
      wheelchairOk = false;
      issues.push(`${info.building_name}: not wheelchair accessible`);
    }
    if (info.elevators?.count > 0) hasElevator = true;
    const minStairs = Math.min(...(info.entrances || []).map(e => e.stairs_count ?? 0));
    totalStairs += minStairs;
  }

  return {
    rating: ratingCount > 0 ? Math.round(ratingSum / ratingCount) : 0,
    wheelchairOk,
    totalStairs,
    hasElevator,
    issues,
  };
}

function ratingColor(r: number) {
  if (r >= 9) return 'text-green-600';
  if (r >= 7) return 'text-yellow-600';
  if (r >= 5) return 'text-orange-500';
  return 'text-red-600';
}

function ratingLabel(r: number) {
  if (r >= 9) return 'Excellent';
  if (r >= 7) return 'Good';
  if (r >= 5) return 'Moderate';
  return 'Poor';
}

function crowdLabel(mult: number) {
  if (mult >= 1.7) return { text: 'Very busy', color: 'text-red-600', icon: '🔴' };
  if (mult >= 1.4) return { text: 'Busy', color: 'text-orange-500', icon: '🟠' };
  if (mult >= 1.1) return { text: 'Moderate', color: 'text-yellow-600', icon: '🟡' };
  return { text: 'Quiet', color: 'text-green-600', icon: '🟢' };
}

// ── Accessibility badge ───────────────────────────────────────────────────────

function AccessibilityBadge({ path, accessibilityData }: { path: string[]; accessibilityData: Record<string, AccessibilityInfo> }) {
  const info = computePathAccessibility(path, accessibilityData);
  if (!info.rating) return null;

  return (
    <div className="bg-white border border-gray-300 rounded-lg p-4 space-y-3">
      <h5 className="text-sm font-semibold text-gray-700">Accessibility Along Route</h5>
      <div className="flex items-center justify-between">
        <div>
          <span className={`text-2xl font-bold ${ratingColor(info.rating)}`}>{info.rating}</span>
          <span className="text-gray-400 text-sm">/10</span>
        </div>
        <span className={`text-sm font-medium px-2 py-1 rounded-full ${
          info.rating >= 9 ? 'bg-green-50 text-green-700' :
          info.rating >= 7 ? 'bg-yellow-50 text-yellow-700' :
          info.rating >= 5 ? 'bg-orange-50 text-orange-700' : 'bg-red-50 text-red-700'
        }`}>
          {ratingLabel(info.rating)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5">
          <span>{info.wheelchairOk ? '✅' : '⚠️'}</span>
          <span className="text-gray-600">Wheelchair {info.wheelchairOk ? 'accessible' : 'issues found'}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>{info.hasElevator ? '🛗' : '—'}</span>
          <span className="text-gray-600">{info.hasElevator ? 'Elevator available' : 'No elevator'}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>🚶</span>
          <span className="text-gray-600">{info.totalStairs} total stairs</span>
        </div>
      </div>

      {info.issues.length > 0 && (
        <div className="bg-orange-50 rounded p-2">
          {info.issues.map((issue, i) => (
            <p key={i} className="text-xs text-orange-700">⚠️ {issue}</p>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Crowd / schedule badge ────────────────────────────────────────────────────

function CrowdBadge({ crowdMultiplier, departureTime }: { crowdMultiplier: number; departureTime?: string }) {
  if (!departureTime) return null;
  const cl = crowdLabel(crowdMultiplier);

  return (
    <div className="bg-white border border-gray-300 rounded-lg p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Crowd at {departureTime}</p>
          <p className={`text-sm font-semibold ${cl.color}`}>{cl.icon} {cl.text}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Speed multiplier</p>
          <p className="text-base font-bold text-gray-900 font-mono">×{crowdMultiplier.toFixed(1)}</p>
        </div>
      </div>
      {crowdMultiplier > 1 && (
        <p className="text-xs text-gray-400 mt-1.5">
          Effective travel time ≈ {crowdMultiplier.toFixed(1)}× base distance
        </p>
      )}
    </div>
  );
}

// ── Preferences-applied notice ────────────────────────────────────────────────

function PreferencesNotice({ preferences }: { preferences?: RoutePreferences }) {
  if (!preferences) return null;
  const active = [
    preferences.wheelchair_only && 'wheelchair accessible only',
    preferences.avoid_stairs && `minimize stairs${preferences.max_stairs < 999 ? ` (max ${preferences.max_stairs})` : ''}`,
    preferences.departure_time && `departure ${preferences.departure_time}`,
  ].filter(Boolean);
  if (!active.length) return null;

  return (
    <div className="bg-siue-red/5 border border-siue-red/20 rounded-lg p-3">
      <p className="text-xs font-semibold text-siue-red mb-1">Preferences applied to this route</p>
      <ul className="text-xs text-gray-600 space-y-0.5">
        {active.map((a, i) => <li key={i}>• {a}</li>)}
      </ul>
    </div>
  );
}

// ── Single result view ────────────────────────────────────────────────────────

function SingleResultView({
  result, accessibilityData, preferences,
}: { result: PathResponse; accessibilityData: Record<string, AccessibilityInfo>; preferences?: RoutePreferences }) {
  if (!result.success) {
    return (
      <div className="bg-gray-100 border border-gray-300 rounded-lg p-4">
        <div className="text-gray-900 font-semibold">No Path Found</div>
        <div className="text-gray-600 text-sm mt-1">{result.errorMessage}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold text-gray-900 mb-1">{result.algorithm}</h4>
        <p className="text-sm text-gray-600">Optimal path found successfully</p>
      </div>

      <PreferencesNotice preferences={preferences} />

      {/* Key Metrics */}
      <div className="bg-white border border-gray-300 rounded-lg p-4 space-y-3">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Performance Metrics</h5>
        <MetricRow label="Total Distance" value={`${result.totalDistance.toFixed(1)} m`} description="Length of the shortest path" />
        <div className="border-t border-gray-200" />
        <MetricRow label="Execution Time" value={`${result.executionTimeMs.toFixed(3)} ms`} description="Algorithm processing time" />
        <div className="border-t border-gray-200" />
        <MetricRow label="Nodes Visited" value={result.nodesVisited.toString()} description="Buildings explored during search" />
        <div className="border-t border-gray-200" />
        <MetricRow label="Edges Relaxed" value={result.edgesRelaxed.toString()} description="Path connections evaluated" />
      </div>

      {/* Crowd info */}
      {result.crowdMultiplier !== undefined && preferences?.departure_time && (
        <CrowdBadge crowdMultiplier={result.crowdMultiplier} departureTime={preferences.departure_time} />
      )}

      {/* Accessibility */}
      <AccessibilityBadge path={result.path} accessibilityData={accessibilityData} />

      {/* Route Path */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Route ({result.pathNames.length} stops)</h5>
        <div className="space-y-2">
          {result.pathNames.map((name, i) => {
            const bid = result.path[i];
            const acc = accessibilityData[bid];
            return (
              <div key={i} className="flex items-center gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-900 text-white flex items-center justify-center text-xs font-medium">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-700 truncate">{name}</div>
                  {acc && (
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`text-xs ${ratingColor(acc.accessibility_rating)}`}>
                        ♿ {acc.accessibility_rating}/10
                      </span>
                      {acc.elevators?.count > 0 && <span className="text-xs text-gray-400">🛗</span>}
                      {Math.min(...(acc.entrances || []).map(e => e.stairs_count ?? 0)) > 0 && (
                        <span className="text-xs text-gray-400">
                          🚶 {Math.min(...acc.entrances.map(e => e.stairs_count ?? 0))} stairs
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Comparison view ───────────────────────────────────────────────────────────

function ComparisonView({
  comparison, accessibilityData, preferences,
}: { comparison: ComparisonResponse; accessibilityData: Record<string, AccessibilityInfo>; preferences?: RoutePreferences }) {
  const algorithms = [
    { key: 'dijkstra', data: comparison.dijkstra, name: "Dijkstra's Algorithm" },
    { key: 'astar', data: comparison.astar, name: 'A* Search' },
    { key: 'bellmanFord', data: comparison.bellmanFord, name: 'Bellman-Ford' },
  ];

  const maxTime = Math.max(...algorithms.map(a => a.data.executionTimeMs));
  const maxNodes = Math.max(...algorithms.map(a => a.data.nodesVisited));
  const winnerName = algorithms.find(a => a.key === comparison.winner)?.name || 'Unknown';

  // Use the winner path for accessibility display
  const winnerData = algorithms.find(a => a.key === comparison.winner)?.data;

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="bg-gray-900 text-white rounded-lg p-4">
        <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">Most Efficient</div>
        <div className="text-lg font-semibold">{winnerName}</div>
        <div className="text-xs text-gray-300 mt-2 leading-relaxed">
          {comparison.summary.analysis}
        </div>
      </div>

      <PreferencesNotice preferences={preferences} />

      {/* Crowd / schedule row */}
      {comparison.summary.crowdMultiplier !== undefined && preferences?.departure_time && (
        <CrowdBadge
          crowdMultiplier={comparison.summary.crowdMultiplier as number}
          departureTime={preferences.departure_time}
        />
      )}

      {/* Path Distance */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-2">Shortest Path Distance</h5>
        <div className="text-2xl font-bold text-gray-900 mb-1">
          {comparison.dijkstra.totalDistance.toFixed(1)} m
        </div>
        {comparison.summary.allPathsEqual && (
          <p className="text-xs text-gray-600">All algorithms found the same optimal path</p>
        )}
      </div>

      {/* Execution Time */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Execution Time</h5>
        <p className="text-xs text-gray-500 mb-4">Lower is faster</p>
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

      {/* Nodes Visited */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <h5 className="text-sm font-semibold text-gray-700 mb-3">Search Efficiency</h5>
        <p className="text-xs text-gray-500 mb-4">Buildings explored (lower = more efficient)</p>
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

      {/* Accessibility for winner's path */}
      {winnerData && winnerData.path.length > 0 && (
        <AccessibilityBadge path={winnerData.path} accessibilityData={accessibilityData} />
      )}

      {/* Detailed stats */}
      <div className="space-y-3">
        <h5 className="text-sm font-semibold text-gray-700">Detailed Statistics</h5>
        {algorithms.map(({ key, data, name }) => {
          const accInfo = computePathAccessibility(data.path, accessibilityData);
          return (
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
                  {accInfo.rating > 0 && (
                    <>
                      <div>
                        <div className="text-gray-500 text-xs mb-1">Accessibility</div>
                        <div className={`font-medium text-sm ${ratingColor(accInfo.rating)}`}>
                          {accInfo.rating}/10 {ratingLabel(accInfo.rating)}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500 text-xs mb-1">Total Stairs</div>
                        <div className="font-mono text-gray-900">{accInfo.totalStairs}</div>
                      </div>
                    </>
                  )}
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-2">Complete Route</div>
                  <div className="space-y-1.5">
                    {data.pathNames.map((buildingName, i) => {
                      const bid = data.path[i];
                      const acc = accessibilityData[bid];
                      return (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <div className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-medium text-gray-700">
                            {i + 1}
                          </div>
                          <span className="text-gray-700 flex-1 truncate">{buildingName}</span>
                          {acc && (
                            <span className={`text-[10px] font-medium ${ratingColor(acc.accessibility_rating)}`}>
                              ♿{acc.accessibility_rating}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </details>
          );
        })}
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

