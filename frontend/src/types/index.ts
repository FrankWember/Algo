// Type definitions for SIUE Campus Router

export interface Node {
  id: string;
  name: string;
  shortName: string;
  x: number;
  y: number;
  type: 'academic' | 'residential' | 'athletic' | 'parking' | 'other';
}

export interface Edge {
  source: string;
  target: string;
  weight: number;
  pathType: 'walkway' | 'road' | 'covered';
}

export interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

export interface AlgorithmStep {
  step: number;
  action: string;
  current: string;
  updated?: string;
  newDistance?: number;
  fScore?: number;
  heuristic?: number;
  iteration?: number;
  relaxed?: string[];
  distances: Record<string, number>;
  visited: string[];
  queue: string[];
  message: string;
}

export interface PathResponse {
  algorithm: string;
  path: string[];
  pathNames: string[];
  totalDistance: number;
  executionTimeMs: number;
  nodesVisited: number;
  edgesRelaxed: number;
  success: boolean;
  errorMessage: string;
  steps: AlgorithmStep[];
}

export interface ComparisonResponse {
  dijkstra: PathResponse;
  astar: PathResponse;
  bellmanFord: PathResponse;
  winner: string;
  summary: {
    allPathsEqual: boolean;
    fastestExecution: string;
    fewestNodesVisited: string;
    analysis: string;
  };
}

export interface AlgorithmInfo {
  name: string;
  description: string;
  timeComplexity: string;
  spaceComplexity: string;
  pros: string[];
  cons: string[];
  bestFor: string;
}

export type AlgorithmType = 'dijkstra' | 'astar' | 'bellmanFord';
