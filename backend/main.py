"""
SIUE Campus Routing API

FastAPI backend providing:
- Campus graph data
- Three pathfinding algorithms with step-by-step execution
- Algorithm comparison and statistics
- Accessibility and schedule data
- Preference-weighted routing (wheelchair, avoid-stairs, rush-hour avoidance)
"""

import json
import math
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from campus_data import get_graph_data, BUILDINGS, BUILDING_CATEGORIES, get_adjacency_list, EDGES
from algorithms import (
    dijkstra, a_star, bellman_ford, run_all_algorithms,
    ALGORITHM_INFO, AlgorithmResult
)

app = FastAPI(
    title="SIUE Campus Routing API",
    description="Multi-algorithm shortest path finding for SIUE campus navigation",
    version="2.0.0"
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Load accessibility and schedule data once at startup
# ---------------------------------------------------------------------------

def _load_json(filename: str) -> dict:
    data_path = Path(__file__).parent.parent / filename
    with open(data_path, "r") as fh:
        return json.load(fh)


_ACCESSIBILITY_RAW = _load_json("accessibility.json")
_SCHEDULES_RAW = _load_json("schedules.json")

# Index by building_id for O(1) lookup
ACCESSIBILITY: Dict[str, dict] = {
    b["building_id"]: b for b in _ACCESSIBILITY_RAW["buildings"]
}
SCHEDULES: Dict[str, dict] = {
    b["building_id"]: b for b in _SCHEDULES_RAW["building_hours"]
}
RUSH_HOURS: List[dict] = _SCHEDULES_RAW["rush_hours"]


# ---------------------------------------------------------------------------
# Preference-aware edge cost helpers
# ---------------------------------------------------------------------------

def _time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' string to minutes since midnight. Returns -1 on error."""
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return -1


def _get_crowd_multiplier(departure_time: str) -> float:
    """Return the crowd multiplier for a given departure time (HH:MM)."""
    dep_min = _time_to_minutes(departure_time)
    if dep_min < 0:
        return 1.0
    for rh in RUSH_HOURS:
        start = _time_to_minutes(rh["start_time"])
        end = _time_to_minutes(rh["end_time"])
        if start <= dep_min <= end:
            return rh.get("crowd_multiplier", 1.0)
    return 1.0


def _building_stair_count(building_id: str) -> int:
    """Return the minimum stair count at any accessible entrance for a building."""
    info = ACCESSIBILITY.get(building_id)
    if not info:
        return 0
    entrances = info.get("entrances", [])
    if not entrances:
        return 0
    counts = [e.get("stairs_count", 0) for e in entrances]
    return min(counts)


def _building_wheelchair_accessible(building_id: str) -> bool:
    info = ACCESSIBILITY.get(building_id)
    if not info:
        return True  # assume accessible if no data
    return info.get("wheelchair_accessible", True)


def build_preference_adjacency(preferences: dict) -> Dict[str, List]:
    """
    Build an adjacency list with edge weights adjusted by user preferences.

    Adjustments applied:
      - wheelchair_only:  +9999m penalty on edges to/from non-accessible buildings
      - avoid_stairs:     +(stairs_count * 8)m penalty per building on path
      - departure_time:   multiply all weights by crowd multiplier for that time
    """
    wheelchair_only = preferences.get("wheelchair_only", False)
    avoid_stairs = preferences.get("avoid_stairs", False)
    max_stairs = preferences.get("max_stairs", 999)
    departure_time = preferences.get("departure_time", "")

    crowd_mult = _get_crowd_multiplier(departure_time) if departure_time else 1.0

    adj: Dict[str, List] = {bid: [] for bid in BUILDINGS}

    for edge in EDGES:
        src, tgt, base_w = edge.source, edge.target, edge.weight
        cost = base_w * crowd_mult

        # Wheelchair penalty: hard block on inaccessible buildings
        if wheelchair_only:
            if not _building_wheelchair_accessible(src) or not _building_wheelchair_accessible(tgt):
                cost += 9999.0

        # Stair penalty
        if avoid_stairs:
            stairs_src = _building_stair_count(src)
            stairs_tgt = _building_stair_count(tgt)
            max_on_edge = max(stairs_src, stairs_tgt)
            if max_on_edge > max_stairs:
                cost += 9999.0
            else:
                cost += max_on_edge * 8.0  # 8m penalty per stair step

        adj[src].append((tgt, round(cost, 1)))
        adj[tgt].append((src, round(cost, 1)))

    return adj


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class RoutePreferences(BaseModel):
    wheelchair_only: bool = False
    avoid_stairs: bool = False
    max_stairs: int = 999
    departure_time: str = ""   # "HH:MM", e.g. "10:45"


class PathRequest(BaseModel):
    start: str
    end: str
    algorithm: Optional[str] = None
    preferences: Optional[RoutePreferences] = None


class PathResponse(BaseModel):
    algorithm: str
    path: List[str]
    pathNames: List[str]
    totalDistance: float
    executionTimeMs: float
    nodesVisited: int
    edgesRelaxed: int
    success: bool
    errorMessage: str = ""
    steps: List[Dict[str, Any]]
    crowdMultiplier: float = 1.0
    preferencesApplied: bool = False


class ComparisonResponse(BaseModel):
    dijkstra: PathResponse
    astar: PathResponse
    bellmanFord: PathResponse
    winner: str
    summary: Dict[str, Any]


# ---------------------------------------------------------------------------
# Conversion helper
# ---------------------------------------------------------------------------

def result_to_response(result: AlgorithmResult, crowd_mult: float = 1.0, prefs_applied: bool = False) -> PathResponse:
    return PathResponse(
        algorithm=result.algorithm_name,
        path=result.path,
        pathNames=result.path_names,
        totalDistance=round(result.total_distance, 1),
        executionTimeMs=round(result.execution_time_ms, 3),
        nodesVisited=result.nodes_visited,
        edgesRelaxed=result.edges_relaxed,
        success=result.success,
        errorMessage=result.error_message,
        steps=result.steps,
        crowdMultiplier=round(crowd_mult, 2),
        preferencesApplied=prefs_applied,
    )


# ---------------------------------------------------------------------------
# Standard endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "ok", "message": "SIUE Campus Routing API", "version": "2.0.0"}


@app.get("/api/graph")
async def get_graph():
    return get_graph_data()


@app.get("/api/buildings")
async def get_buildings():
    buildings = []
    for bid, building in BUILDINGS.items():
        buildings.append({
            "id": bid,
            "name": building.name,
            "shortName": building.short_name,
            "type": building.building_type,
            "x": building.x,
            "y": building.y,
            "latitude": building.latitude,
            "longitude": building.longitude,
            "elevation": building.elevation,
        })
    return {"buildings": buildings}


@app.get("/api/buildings/categories")
async def get_building_categories():
    return {
        "categories": BUILDING_CATEGORIES,
        "counts": {cat: len(ids) for cat, ids in BUILDING_CATEGORIES.items()}
    }


@app.get("/api/algorithms")
async def get_algorithms():
    return {"algorithms": ALGORITHM_INFO}


# ---------------------------------------------------------------------------
# Accessibility endpoint
# ---------------------------------------------------------------------------

@app.get("/api/accessibility")
async def get_accessibility():
    """
    Return accessibility information for all mapped buildings.
    Includes elevator counts, wheelchair accessibility, entrance stair counts,
    ramp slopes, and an overall accessibility rating (1-10).
    """
    return {
        "buildings": list(ACCESSIBILITY.values()),
        "total": len(ACCESSIBILITY),
        "standards": _ACCESSIBILITY_RAW["metadata"].get("accessibility_standards", {})
    }


@app.get("/api/accessibility/{building_id}")
async def get_building_accessibility(building_id: str):
    info = ACCESSIBILITY.get(building_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"No accessibility data for building: {building_id}")
    return info


# ---------------------------------------------------------------------------
# Schedule endpoint
# ---------------------------------------------------------------------------

@app.get("/api/schedules")
async def get_schedules():
    """
    Return building hours and rush hour schedule for all buildings.
    """
    return {
        "building_hours": list(SCHEDULES.values()),
        "rush_hours": RUSH_HOURS,
        "class_schedule": _SCHEDULES_RAW.get("class_schedule", {}),
        "high_traffic_buildings": _SCHEDULES_RAW.get("high_traffic_buildings", {}),
    }


@app.get("/api/schedules/rush-hours")
async def get_rush_hours():
    return {"rush_hours": RUSH_HOURS}


@app.get("/api/schedules/status")
async def get_schedule_status(time: Optional[str] = None):
    """
    Get current (or specified) schedule status: which rush hour is active,
    crowd multiplier, and open/closed status for key buildings.
    time format: HH:MM (24h)
    """
    check_time = time or datetime.now().strftime("%H:%M")
    crowd_mult = _get_crowd_multiplier(check_time)

    active_rush = None
    dep_min = _time_to_minutes(check_time)
    for rh in RUSH_HOURS:
        if _time_to_minutes(rh["start_time"]) <= dep_min <= _time_to_minutes(rh["end_time"]):
            active_rush = rh
            break

    return {
        "time": check_time,
        "crowd_multiplier": crowd_mult,
        "active_rush_hour": active_rush,
        "is_rush_hour": active_rush is not None,
    }


# ---------------------------------------------------------------------------
# Path-finding endpoints (with optional preferences)
# ---------------------------------------------------------------------------

@app.post("/api/path", response_model=PathResponse)
async def find_path(request: PathRequest):
    """
    Find shortest path. If preferences are provided, edge weights are adjusted
    for wheelchair accessibility, stair avoidance, and crowd level.
    """
    algorithm = request.algorithm or "dijkstra"
    prefs = request.preferences
    prefs_dict = prefs.model_dump() if prefs else {}
    prefs_applied = bool(prefs) and any(prefs_dict.values())

    crowd_mult = _get_crowd_multiplier(prefs_dict.get("departure_time", "")) if prefs_applied else 1.0

    if prefs_applied:
        custom_adj = build_preference_adjacency(prefs_dict)
    else:
        custom_adj = None

    if algorithm == "dijkstra":
        result = dijkstra(request.start, request.end, custom_adj=custom_adj)
    elif algorithm == "astar":
        result = a_star(request.start, request.end, custom_adj=custom_adj)
    elif algorithm == "bellmanFord":
        result = bellman_ford(request.start, request.end, custom_adj=custom_adj)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown algorithm: {algorithm}. Use 'dijkstra', 'astar', or 'bellmanFord'"
        )

    return result_to_response(result, crowd_mult, prefs_applied)


@app.post("/api/compare", response_model=ComparisonResponse)
async def compare_algorithms(request: PathRequest):
    """
    Run all three algorithms and compare performance.
    Preferences are applied identically to all three.
    """
    prefs = request.preferences
    prefs_dict = prefs.model_dump() if prefs else {}
    prefs_applied = bool(prefs) and any(prefs_dict.values())
    crowd_mult = _get_crowd_multiplier(prefs_dict.get("departure_time", "")) if prefs_applied else 1.0

    custom_adj = build_preference_adjacency(prefs_dict) if prefs_applied else None

    results = run_all_algorithms(request.start, request.end, custom_adj=custom_adj)

    dijkstra_resp = result_to_response(results["dijkstra"], crowd_mult, prefs_applied)
    astar_resp = result_to_response(results["astar"], crowd_mult, prefs_applied)
    bellman_resp = result_to_response(results["bellmanFord"], crowd_mult, prefs_applied)

    valid_results = []
    if dijkstra_resp.success:
        valid_results.append(("dijkstra", dijkstra_resp))
    if astar_resp.success:
        valid_results.append(("astar", astar_resp))
    if bellman_resp.success:
        valid_results.append(("bellmanFord", bellman_resp))

    winner = min(valid_results, key=lambda x: x[1].nodesVisited)[0] if valid_results else "none"

    summary = {
        "allPathsEqual": (
            dijkstra_resp.totalDistance == astar_resp.totalDistance == bellman_resp.totalDistance
            if all(r.success for r in [dijkstra_resp, astar_resp, bellman_resp])
            else False
        ),
        "fastestExecution": min(
            [("dijkstra", dijkstra_resp.executionTimeMs),
             ("astar", astar_resp.executionTimeMs),
             ("bellmanFord", bellman_resp.executionTimeMs)],
            key=lambda x: x[1]
        )[0] if valid_results else "none",
        "fewestNodesVisited": min(
            [("dijkstra", dijkstra_resp.nodesVisited),
             ("astar", astar_resp.nodesVisited),
             ("bellmanFord", bellman_resp.nodesVisited)],
            key=lambda x: x[1]
        )[0] if valid_results else "none",
        "analysis": generate_analysis(dijkstra_resp, astar_resp, bellman_resp),
        "crowdMultiplier": crowd_mult,
        "preferencesApplied": prefs_applied,
    }

    return ComparisonResponse(
        dijkstra=dijkstra_resp,
        astar=astar_resp,
        bellmanFord=bellman_resp,
        winner=winner,
        summary=summary
    )


def generate_analysis(dijkstra: PathResponse, astar: PathResponse, bellman: PathResponse) -> str:
    if not all([dijkstra.success, astar.success, bellman.success]):
        return "Some algorithms failed to find a path."

    analysis_parts = []

    if dijkstra.totalDistance == astar.totalDistance == bellman.totalDistance:
        analysis_parts.append(f"All algorithms found the optimal path of {dijkstra.totalDistance}m.")
    else:
        analysis_parts.append(
            f"Path distances vary: Dijkstra={dijkstra.totalDistance}m, "
            f"A*={astar.totalDistance}m, Bellman-Ford={bellman.totalDistance}m."
        )

    if astar.nodesVisited < dijkstra.nodesVisited:
        savings = ((dijkstra.nodesVisited - astar.nodesVisited) / dijkstra.nodesVisited) * 100
        analysis_parts.append(
            f"A* visited {savings:.0f}% fewer nodes than Dijkstra due to its heuristic guidance."
        )
    elif astar.nodesVisited == dijkstra.nodesVisited:
        analysis_parts.append("A* and Dijkstra visited the same number of nodes for this path.")

    analysis_parts.append(
        f"Bellman-Ford relaxed {bellman.edgesRelaxed} edges across its iterations, "
        f"which is typical for its O(V×E) approach."
    )

    times = [
        ("Dijkstra", dijkstra.executionTimeMs),
        ("A*", astar.executionTimeMs),
        ("Bellman-Ford", bellman.executionTimeMs)
    ]
    fastest = min(times, key=lambda x: x[1])
    analysis_parts.append(f"{fastest[0]} was the fastest at {fastest[1]:.3f}ms.")

    return " ".join(analysis_parts)


@app.get("/api/path/steps/{algorithm}")
async def get_algorithm_steps(algorithm: str, start: str, end: str):
    if algorithm == "dijkstra":
        result = dijkstra(start, end)
    elif algorithm == "astar":
        result = a_star(start, end)
    elif algorithm == "bellmanFord":
        result = bellman_ford(start, end)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm: {algorithm}")

    return {
        "algorithm": algorithm,
        "totalSteps": len(result.steps),
        "steps": result.steps,
        "success": result.success
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
