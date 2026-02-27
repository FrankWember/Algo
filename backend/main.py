"""
SIUE Campus Routing API

FastAPI backend providing:
- Campus graph data
- Three pathfinding algorithms with step-by-step execution
- Algorithm comparison and statistics
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from campus_data import get_graph_data, BUILDINGS, BUILDING_CATEGORIES
from algorithms import (
    dijkstra, a_star, bellman_ford, run_all_algorithms,
    ALGORITHM_INFO, AlgorithmResult
)

app = FastAPI(
    title="SIUE Campus Routing API",
    description="Multi-algorithm shortest path finding for SIUE campus navigation",
    version="1.0.0"
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class PathRequest(BaseModel):
    start: str
    end: str
    algorithm: Optional[str] = None  # If None, run all algorithms


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


class ComparisonResponse(BaseModel):
    dijkstra: PathResponse
    astar: PathResponse
    bellmanFord: PathResponse
    winner: str
    summary: Dict[str, Any]


def result_to_response(result: AlgorithmResult) -> PathResponse:
    """Convert AlgorithmResult to PathResponse."""
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
        steps=result.steps
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "SIUE Campus Routing API",
        "version": "1.0.0"
    }


@app.get("/api/graph")
async def get_graph():
    """
    Get the complete campus graph for visualization.

    Returns nodes (buildings) and edges (paths) with their properties.
    """
    return get_graph_data()


@app.get("/api/buildings")
async def get_buildings():
    """
    Get list of all buildings with their details.
    """
    buildings = []
    for bid, building in BUILDINGS.items():
        buildings.append({
            "id": bid,
            "name": building.name,
            "shortName": building.short_name,
            "type": building.building_type,
            "x": building.x,
            "y": building.y
        })
    return {"buildings": buildings}


@app.get("/api/buildings/categories")
async def get_building_categories():
    """
    Get buildings grouped by category.
    """
    return {
        "categories": BUILDING_CATEGORIES,
        "counts": {cat: len(ids) for cat, ids in BUILDING_CATEGORIES.items()}
    }


@app.get("/api/algorithms")
async def get_algorithms():
    """
    Get information about available algorithms.
    """
    return {"algorithms": ALGORITHM_INFO}


@app.post("/api/path", response_model=PathResponse)
async def find_path(request: PathRequest):
    """
    Find shortest path using specified algorithm.

    Available algorithms: dijkstra, astar, bellmanFord
    """
    algorithm = request.algorithm or "dijkstra"

    if algorithm == "dijkstra":
        result = dijkstra(request.start, request.end)
    elif algorithm == "astar":
        result = a_star(request.start, request.end)
    elif algorithm == "bellmanFord":
        result = bellman_ford(request.start, request.end)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown algorithm: {algorithm}. Use 'dijkstra', 'astar', or 'bellmanFord'"
        )

    return result_to_response(result)


@app.post("/api/compare", response_model=ComparisonResponse)
async def compare_algorithms(request: PathRequest):
    """
    Run all three algorithms and compare their performance.
    """
    results = run_all_algorithms(request.start, request.end)

    dijkstra_resp = result_to_response(results["dijkstra"])
    astar_resp = result_to_response(results["astar"])
    bellman_resp = result_to_response(results["bellmanFord"])

    # Determine winner based on execution time and correctness
    valid_results = []
    if dijkstra_resp.success:
        valid_results.append(("dijkstra", dijkstra_resp))
    if astar_resp.success:
        valid_results.append(("astar", astar_resp))
    if bellman_resp.success:
        valid_results.append(("bellmanFord", bellman_resp))

    if not valid_results:
        winner = "none"
    else:
        # Winner is the one with fewest nodes visited (more efficient)
        winner = min(valid_results, key=lambda x: x[1].nodesVisited)[0]

    # Build summary
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
        "analysis": generate_analysis(dijkstra_resp, astar_resp, bellman_resp)
    }

    return ComparisonResponse(
        dijkstra=dijkstra_resp,
        astar=astar_resp,
        bellmanFord=bellman_resp,
        winner=winner,
        summary=summary
    )


def generate_analysis(dijkstra: PathResponse, astar: PathResponse, bellman: PathResponse) -> str:
    """Generate human-readable analysis of algorithm comparison."""
    if not all([dijkstra.success, astar.success, bellman.success]):
        return "Some algorithms failed to find a path."

    analysis_parts = []

    # Distance comparison
    if dijkstra.totalDistance == astar.totalDistance == bellman.totalDistance:
        analysis_parts.append(
            f"All algorithms found the optimal path of {dijkstra.totalDistance}m."
        )
    else:
        analysis_parts.append(
            f"Path distances vary: Dijkstra={dijkstra.totalDistance}m, "
            f"A*={astar.totalDistance}m, Bellman-Ford={bellman.totalDistance}m."
        )

    # Efficiency comparison
    if astar.nodesVisited < dijkstra.nodesVisited:
        savings = ((dijkstra.nodesVisited - astar.nodesVisited) / dijkstra.nodesVisited) * 100
        analysis_parts.append(
            f"A* visited {savings:.0f}% fewer nodes than Dijkstra due to its heuristic guidance."
        )
    elif astar.nodesVisited == dijkstra.nodesVisited:
        analysis_parts.append(
            "A* and Dijkstra visited the same number of nodes for this path."
        )

    # Bellman-Ford analysis
    analysis_parts.append(
        f"Bellman-Ford relaxed {bellman.edgesRelaxed} edges across its iterations, "
        f"which is typical for its O(V×E) approach."
    )

    # Speed comparison
    times = [
        ("Dijkstra", dijkstra.executionTimeMs),
        ("A*", astar.executionTimeMs),
        ("Bellman-Ford", bellman.executionTimeMs)
    ]
    fastest = min(times, key=lambda x: x[1])
    analysis_parts.append(
        f"{fastest[0]} was the fastest at {fastest[1]:.3f}ms."
    )

    return " ".join(analysis_parts)


@app.get("/api/path/steps/{algorithm}")
async def get_algorithm_steps(algorithm: str, start: str, end: str):
    """
    Get detailed step-by-step execution of an algorithm.

    Useful for educational visualization.
    """
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
