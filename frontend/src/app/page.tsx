'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import Header from '@/components/Header';
import CampusMap from '@/components/CampusMap';
import AlgorithmSelector from '@/components/AlgorithmSelector';
import BuildingSelector from '@/components/BuildingSelector';
import ResultsPanel from '@/components/ResultsPanel';
import StepVisualizer from '@/components/StepVisualizer';
import PreferencesPanel from '@/components/PreferencesPanel';
import { api } from '@/lib/api';
import type {
  Node, Edge, PathResponse, ComparisonResponse, AlgorithmType, AlgorithmStep,
  AccessibilityInfo, RoutePreferences
} from '@/types';

const DEFAULT_PREFERENCES: RoutePreferences = {
  wheelchair_only: false,
  avoid_stairs: false,
  max_stairs: 999,
  departure_time: '',
};

export default function Home() {
  // Graph data state
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selection state
  const [selectedStart, setSelectedStart] = useState<string | null>(null);
  const [selectedEnd, setSelectedEnd] = useState<string | null>(null);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<AlgorithmType | 'compare'>('compare');

  // Results state
  const [result, setResult] = useState<PathResponse | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);

  // Visualization state
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [visitedNodes, setVisitedNodes] = useState<string[]>([]);
  const [currentNode, setCurrentNode] = useState<string | null>(null);
  const [currentSteps, setCurrentSteps] = useState<AlgorithmStep[]>([]);

  // Preferences state
  const [preferences, setPreferences] = useState<RoutePreferences>(DEFAULT_PREFERENCES);
  const [accessibilityData, setAccessibilityData] = useState<Record<string, AccessibilityInfo>>({});

  // UI state
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);

  // Load graph + accessibility data on mount
  useEffect(() => {
    const loadGraph = async () => {
      try {
        setIsLoading(true);
        const [graphData, accessData] = await Promise.all([
          api.getGraph(),
          api.getAccessibility().catch(() => ({ buildings: [], total: 0, standards: {} })),
        ]);
        setNodes(graphData.nodes);
        setEdges(graphData.edges);
        // Index accessibility by building_id for O(1) lookup
        const indexed: Record<string, AccessibilityInfo> = {};
        for (const b of accessData.buildings) indexed[b.building_id] = b;
        setAccessibilityData(indexed);
        setError(null);
      } catch (err) {
        setError('Failed to load campus data. Make sure the backend is running.');
        console.error('Failed to load graph:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadGraph();
  }, []);

  // Handle node click on map
  const handleNodeClick = useCallback((nodeId: string) => {
    if (!selectedStart) {
      setSelectedStart(nodeId);
    } else if (!selectedEnd && nodeId !== selectedStart) {
      setSelectedEnd(nodeId);
    } else if (nodeId === selectedStart) {
      setSelectedStart(null);
    } else if (nodeId === selectedEnd) {
      setSelectedEnd(null);
    } else {
      // Replace end if both are selected
      setSelectedEnd(nodeId);
    }
  }, [selectedStart, selectedEnd]);

  // Swap start and end
  const handleSwap = useCallback(() => {
    setSelectedStart(selectedEnd);
    setSelectedEnd(selectedStart);
  }, [selectedStart, selectedEnd]);

  // Find path
  const handleFindPath = useCallback(async () => {
    if (!selectedStart || !selectedEnd) return;

    setIsCalculating(true);
    setResult(null);
    setComparison(null);
    setCurrentPath([]);
    setVisitedNodes([]);
    setCurrentNode(null);
    setCurrentSteps([]);

    // Only send preferences if any are active
    const prefsActive = preferences.wheelchair_only || preferences.avoid_stairs || !!preferences.departure_time;
    const prefsPayload = prefsActive ? preferences : undefined;

    try {
      if (selectedAlgorithm === 'compare') {
        const compResult = await api.compareAlgorithms(selectedStart, selectedEnd, prefsPayload);
        setComparison(compResult);

        // Show the winner's path (winner can be "none" if no path found)
        const winner = compResult.winner && compResult.winner !== 'none'
          ? (compResult[compResult.winner as keyof typeof compResult] as PathResponse)
          : null;
        if (winner && winner.path) {
          setCurrentPath(winner.path);
          setCurrentSteps(Array.isArray(winner.steps) ? winner.steps : []);
        }
      } else {
        const pathResult = await api.findPath(selectedStart, selectedEnd, selectedAlgorithm, prefsPayload);
        setResult(pathResult);
        setCurrentPath(pathResult.path || []);
        setCurrentSteps(Array.isArray(pathResult.steps) ? pathResult.steps : []);
      }
    } catch (err) {
      console.error('Failed to find path:', err);
      setError('Failed to calculate path. Please try again.');
    } finally {
      setIsCalculating(false);
    }
  }, [selectedStart, selectedEnd, selectedAlgorithm, preferences]);

  // Handle step changes from visualizer
  const handleStepChange = useCallback((step: AlgorithmStep | null) => {
    if (!step) {
      setVisitedNodes([]);
      setCurrentNode(null);
      return;
    }

    setVisitedNodes(step.visited);
    setCurrentNode(step.current);
  }, []);

  // Reset everything
  const handleReset = useCallback(() => {
    setSelectedStart(null);
    setSelectedEnd(null);
    setResult(null);
    setComparison(null);
    setCurrentPath([]);
    setVisitedNodes([]);
    setCurrentNode(null);
    setCurrentSteps([]);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="spinner mx-auto mb-4" />
          <p className="text-gray-600">Loading campus data...</p>
        </div>
      </div>
    );
  }

  if (error && nodes.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Connection Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <p className="text-sm text-gray-500 mb-4">
            Make sure the Python backend is running:<br />
            <code className="bg-gray-100 px-2 py-1 rounded">cd backend && python main.py</code>
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-siue-red text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      <main className="flex-1 relative overflow-hidden">
        {/* Full-screen Map */}
        <div className="absolute inset-0">
          <CampusMap
            nodes={nodes}
            edges={edges}
            path={currentPath}
            visitedNodes={visitedNodes}
            currentNode={currentNode}
            selectedStart={selectedStart}
            selectedEnd={selectedEnd}
            onNodeClick={handleNodeClick}
          />
        </div>

        {/* Left Control Panel - Collapsible */}
        <AnimatePresence>
          {!isPanelCollapsed && (
            <motion.div
              initial={{ x: -350 }}
              animate={{ x: 0 }}
              exit={{ x: -350 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute inset-x-2 md:inset-x-auto md:left-4 top-2 md:top-4 bottom-2 md:bottom-4 w-auto md:w-80 max-w-full md:max-w-none pointer-events-none z-20"
            >
              <div className="h-full overflow-y-auto pointer-events-auto space-y-2 md:space-y-3 pb-4 scrollbar-thin">
                {/* Algorithm Selection */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-4"
                >
                  <AlgorithmSelector
                    selectedAlgorithm={selectedAlgorithm}
                    onSelect={setSelectedAlgorithm}
                  />
                </motion.div>

                {/* Building Selection */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                  className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-4"
                >
                  <BuildingSelector
                    nodes={nodes}
                    selectedStart={selectedStart}
                    selectedEnd={selectedEnd}
                    onStartSelect={setSelectedStart}
                    onEndSelect={setSelectedEnd}
                    onSwap={handleSwap}
                  />
                </motion.div>

                {/* Action Buttons */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className="flex gap-3"
                >
                  <button
                    onClick={handleFindPath}
                    disabled={!selectedStart || !selectedEnd || isCalculating}
                    className="flex-1 bg-gray-900 text-white py-3 px-4 rounded-lg font-medium
                             hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed
                             transition-colors flex items-center justify-center gap-2 shadow-lg"
                  >
                    {isCalculating ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Calculating...
                      </>
                    ) : (
                      'Find Path'
                    )}
                  </button>
                  <button
                    onClick={handleReset}
                    className="bg-white/95 backdrop-blur-sm text-gray-700 py-3 px-4 rounded-lg font-medium
                             hover:bg-gray-100 transition-colors shadow-lg border border-gray-300"
                    title="Reset"
                  >
                    Reset
                  </button>
                </motion.div>

                {/* Preferences Panel */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 }}
                  className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-4"
                >
                  <PreferencesPanel
                    preferences={preferences}
                    onChange={setPreferences}
                  />
                </motion.div>

                {/* Step Visualizer */}
                {currentSteps.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                    className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg"
                  >
                    <StepVisualizer
                      steps={currentSteps}
                      onStepChange={handleStepChange}
                      algorithmName={result?.algorithm || comparison?.winner || ''}
                    />
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Panel Toggle Button */}
        <button
          onClick={() => setIsPanelCollapsed(!isPanelCollapsed)}
          className="absolute top-1/2 -translate-y-1/2 z-30 bg-white/95 backdrop-blur-sm p-2 md:p-3 rounded-lg shadow-lg hover:bg-white transition-all hover:scale-105 border border-gray-200"
          title={isPanelCollapsed ? 'Show Controls' : 'Hide Controls'}
          style={{ left: '1rem' }}
        >
          {isPanelCollapsed ? '›' : '‹'}
        </button>

        {/* Results Modal */}
        <AnimatePresence>
          {(result || comparison) && (
            <motion.div
              initial={{ opacity: 0, x: 100 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 100 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute inset-x-2 md:inset-x-auto md:right-4 top-2 md:top-4 w-auto md:w-[450px] max-w-full md:max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)] overflow-hidden z-20"
            >
              <div className="bg-white rounded-xl shadow-2xl overflow-hidden border border-gray-300">
                <div className="bg-gray-900 text-white px-5 py-4 flex items-center justify-between border-b border-gray-700">
                  <h3 className="font-semibold text-base">Path Results</h3>
                  <button
                    onClick={() => {
                      setResult(null);
                      setComparison(null);
                      setCurrentPath([]);
                      setCurrentSteps([]);
                    }}
                    className="text-white hover:bg-gray-700 rounded px-2 py-1 transition-colors text-sm"
                    title="Close"
                  >
                    Close
                  </button>
                </div>
                <div className="p-5 overflow-y-auto scrollbar-thin bg-gray-50" style={{ maxHeight: 'calc(100vh - 8rem)' }}>
                  <ResultsPanel
                    result={result}
                    comparison={comparison}
                    isLoading={isCalculating}
                    accessibilityData={accessibilityData}
                    preferences={preferences}
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </main>
    </div>
  );
}
