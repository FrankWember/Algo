// API client for communicating with the Python backend

import type {
  GraphData, PathResponse, ComparisonResponse, AlgorithmType,
  AccessibilityInfo, BuildingSchedule, RushHour, ScheduleStatus, RoutePreferences
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Get campus graph data
  async getGraph(): Promise<GraphData> {
    return this.fetch<GraphData>('/api/graph');
  }

  // Get all buildings
  async getBuildings(): Promise<{ buildings: Array<{
    id: string; name: string; shortName: string; type: string;
    x: number; y: number;
  }> }> {
    return this.fetch('/api/buildings');
  }

  // Get building categories
  async getBuildingCategories(): Promise<{
    categories: Record<string, string[]>;
    counts: Record<string, number>;
  }> {
    return this.fetch('/api/buildings/categories');
  }

  // Get algorithm information
  async getAlgorithmsInfo(): Promise<{ algorithms: Record<string, any> }> {
    return this.fetch('/api/algorithms');
  }

  // Get accessibility data for all buildings
  async getAccessibility(): Promise<{
    buildings: AccessibilityInfo[];
    total: number;
    standards: Record<string, string>;
  }> {
    return this.fetch('/api/accessibility');
  }

  // Get accessibility data for a single building
  async getBuildingAccessibility(buildingId: string): Promise<AccessibilityInfo> {
    return this.fetch(`/api/accessibility/${buildingId}`);
  }

  // Get all schedule data
  async getSchedules(): Promise<{
    building_hours: BuildingSchedule[];
    rush_hours: RushHour[];
    class_schedule: Record<string, any>;
    high_traffic_buildings: Record<string, any>;
  }> {
    return this.fetch('/api/schedules');
  }

  // Get current schedule status (crowd multiplier, active rush hour)
  async getScheduleStatus(time?: string): Promise<ScheduleStatus> {
    const query = time ? `?time=${encodeURIComponent(time)}` : '';
    return this.fetch(`/api/schedules/status${query}`);
  }

  // Find path with single algorithm (with optional preferences)
  async findPath(
    start: string,
    end: string,
    algorithm: AlgorithmType,
    preferences?: RoutePreferences
  ): Promise<PathResponse> {
    return this.fetch<PathResponse>('/api/path', {
      method: 'POST',
      body: JSON.stringify({ start, end, algorithm, preferences: preferences ?? null }),
    });
  }

  // Compare all algorithms (with optional preferences)
  async compareAlgorithms(
    start: string,
    end: string,
    preferences?: RoutePreferences
  ): Promise<ComparisonResponse> {
    return this.fetch<ComparisonResponse>('/api/compare', {
      method: 'POST',
      body: JSON.stringify({ start, end, preferences: preferences ?? null }),
    });
  }

  // Get algorithm steps for visualization
  async getAlgorithmSteps(
    algorithm: AlgorithmType,
    start: string,
    end: string
  ): Promise<{
    algorithm: string;
    totalSteps: number;
    steps: any[];
    success: boolean;
  }> {
    return this.fetch(
      `/api/path/steps/${algorithm}?start=${start}&end=${end}`
    );
  }
}

export const api = new ApiClient(API_BASE);
