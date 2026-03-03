// Type definitions for SIUE Campus Router

/**
 * Node building types — maps directly to the category values produced by
 * backend/campus_data.py (via CATEGORY_MAP).
 */
export type NodeType =
  | 'academic'      // lecture halls, libraries, departments
  | 'residential'   // on-campus housing (residence halls)
  | 'recreation'    // fitness centres, sports facilities
  | 'parking'       // parking lots
  | 'research'      // research drive buildings, labs
  | 'other';        // landmarks, facilities, art & design, etc.

export interface Node {
  id: string;
  name: string;
  shortName: string;
  x: number;          // Normalized 0-100 for SVG map (west=0, east=100)
  y: number;          // Normalized 0-100 for SVG map (north=0, south=100)
  type: NodeType;
  // Real GPS data (available when loaded from real buildings.json)
  latitude?: number;
  longitude?: number;
  elevation?: number; // metres above sea level
}

export interface Edge {
  source: string;
  target: string;
  weight: number;     // Distance in metres
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
  crowdMultiplier?: number;
  preferencesApplied?: boolean;
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
    crowdMultiplier?: number;
    preferencesApplied?: boolean;
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

// ── Routing Preferences ──────────────────────────────────────────────────────

export interface RoutePreferences {
  wheelchair_only: boolean;
  avoid_stairs: boolean;
  max_stairs: number;
  departure_time: string; // "HH:MM" 24-hour format, empty = no time preference
}

// ── Accessibility data (from accessibility.json) ─────────────────────────────

export interface BuildingEntrance {
  name: string;
  accessible: boolean;
  stairs_count: number;
  has_ramp: boolean;
  ramp_slope_percent?: number;
  automatic_doors: boolean;
  notes: string;
}

export interface AccessibilityInfo {
  building_id: string;
  building_name: string;
  entrances: BuildingEntrance[];
  elevators: {
    count: number;
    locations: string[];
    notes: string;
  };
  accessible_restrooms: boolean;
  wheelchair_accessible: boolean;
  accessibility_rating: number; // 1-10
  notes: string;
}

// ── Schedule data (from schedules.json) ──────────────────────────────────────

export interface DayHours {
  open: string | null;  // "HH:MM" or null (closed)
  close: string | null;
}

export interface BuildingSchedule {
  building_id: string;
  building_name: string;
  weekday: DayHours;
  friday?: DayHours;
  saturday: DayHours;
  sunday: DayHours;
  summer_hours_differ: boolean;
  summer_hours: Record<string, DayHours | null> | null;
  indoor_shortcuts_available: boolean;
  allows_through_traffic: boolean;
  notes: string;
}

export interface RushHour {
  id: string;
  start_time: string;
  end_time: string;
  intensity: 'low' | 'medium' | 'high' | 'very_high';
  crowd_multiplier: number;
  affected_buildings: string[];
}

export interface ScheduleStatus {
  time: string;
  crowd_multiplier: number;
  active_rush_hour: RushHour | null;
  is_rush_hour: boolean;
}
