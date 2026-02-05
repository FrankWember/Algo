"""
FastAPI routes for the campus routing service.

Provides REST endpoints for:
- Finding optimal routes
- Comparing departure times
- Querying campus locations
"""

from datetime import datetime, time
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..models.graph_models import CampusGraph
from ..models.route_models import (
    UserPreferences,
    OptimizationProfile,
    Route,
    RouteSet,
)
from ..algorithms.dijkstra import MultiCriteriaDijkstra
from ..algorithms.pareto import ParetoOptimizer
from ..algorithms.scheduler import TimeAwareScheduler, DivideConquerRouter
from ..data.graph_builder import CampusGraphBuilder


# Pydantic models for API
class LocationResponse(BaseModel):
    """Response model for location queries."""
    id: str
    name: str
    type: str
    lat: float
    lon: float
    elevation: float


class RouteRequest(BaseModel):
    """Request model for route computation."""
    origin: str = Field(..., description="Origin node ID")
    destination: str = Field(..., description="Destination node ID")
    profile: Optional[str] = Field("comfortable", description="Optimization profile")
    departure_time: Optional[str] = Field(None, description="Departure time (HH:MM)")
    preferences: Optional[Dict[str, float]] = Field(None, description="Custom weights")
    max_stairs: Optional[int] = Field(None, description="Maximum stairs allowed")
    wheelchair_accessible: Optional[bool] = Field(False, description="Require accessibility")


class RouteSegmentResponse(BaseModel):
    """Response model for a route segment."""
    from_id: str
    from_name: str
    to_id: str
    to_name: str
    distance: float
    time: float
    stairs: int
    instruction: str


class RouteResponse(BaseModel):
    """Response model for a computed route."""
    origin: str
    destination: str
    total_distance: float
    total_time: float
    total_stairs: int
    elevation_gain: float
    crowdedness: float
    segments: List[RouteSegmentResponse]
    path: List[str]
    is_pareto_optimal: bool
    rank: int
    summary: str


class CompareTimesRequest(BaseModel):
    """Request for comparing departure times."""
    origin: str
    destination: str
    times: List[str] = Field(..., description="List of times (HH:MM)")


class CompareTimesResponse(BaseModel):
    """Response for time comparison."""
    results: Dict[str, RouteResponse]
    best_time: str
    reason: str


# Global state (would use proper DI in production)
_graph: Optional[CampusGraph] = None
_scheduler: Optional[TimeAwareScheduler] = None


def get_graph() -> CampusGraph:
    """Get or initialize the campus graph."""
    global _graph, _scheduler

    if _graph is None:
        builder = CampusGraphBuilder(data_dir=Path("data"))
        _graph = builder.build(include_elevation=True, validate=True)
        _scheduler = TimeAwareScheduler(_graph)

    return _graph


def get_scheduler() -> TimeAwareScheduler:
    """Get or initialize the scheduler."""
    global _scheduler

    if _scheduler is None:
        get_graph()  # This initializes both

    return _scheduler


def _validate_locations(graph: CampusGraph, origin: str, destination: str) -> None:
    """Validate that origin and destination exist in the graph."""
    if not graph.get_node(origin):
        raise HTTPException(status_code=404, detail=f"Origin '{origin}' not found")
    if not graph.get_node(destination):
        raise HTTPException(status_code=404, detail=f"Destination '{destination}' not found")


def _parse_departure_time(time_str: Optional[str]) -> Optional[time]:
    """Parse departure time string to time object."""
    if not time_str:
        return None

    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid time format. Use HH:MM"
        )


def _build_user_preferences(request: RouteRequest) -> UserPreferences:
    """Build UserPreferences from route request."""
    if request.preferences:
        prefs = UserPreferences(**request.preferences)
    elif request.profile:
        try:
            profile = OptimizationProfile(request.profile)
            prefs = UserPreferences.from_profile(profile)
        except ValueError:
            prefs = UserPreferences()
    else:
        prefs = UserPreferences()

    # Apply constraints
    if request.wheelchair_accessible:
        prefs.require_wheelchair_accessible = True
        prefs.max_stairs = 0
    if request.max_stairs is not None:
        prefs.max_stairs = request.max_stairs

    return prefs


def _parse_time_list(time_strings: List[str]) -> List[time]:
    """Parse a list of time strings to time objects."""
    times = []
    for time_str in time_strings:
        try:
            times.append(datetime.strptime(time_str, "%H:%M").time())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time: {time_str}"
            )
    return times


def _convert_routes_to_responses(
    results: Dict[str, Route]
) -> Dict[str, RouteResponse]:
    """Convert route results to API response format."""
    return {
        time_str: _route_to_response(route)
        for time_str, route in results.items()
        if route
    }


def _find_best_departure_time(
    results: Dict[str, Route]
) -> tuple[Optional[str], float]:
    """Find the best departure time based on route scores."""
    best_time = None
    best_score = float('inf')

    for time_str, route in results.items():
        if not route:
            continue

        # Score: prefer less crowded, faster routes
        score = route.total_weight.crowdedness * 2 + route.total_time / 60
        if score < best_score:
            best_score = score
            best_time = time_str

    return best_time, best_score


def _generate_best_time_reason(
    best_time: Optional[str],
    results: Dict[str, Route]
) -> str:
    """Generate human-readable reason for best departure time."""
    if not best_time:
        return ""

    route = results[best_time]
    if route.total_weight.crowdedness < 0.3:
        return f"Low crowds at {best_time}"

    valid_routes = [r for r in results.values() if r]
    if valid_routes and route.total_time == min(r.total_time for r in valid_routes):
        return f"Fastest travel time at {best_time}"

    return f"Best balance of time and crowds at {best_time}"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SIUE Campus Router",
        description="Multi-objective campus routing with time-aware optimization",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """API root - health check."""
        return {"status": "ok", "message": "SIUE Campus Router API"}

    @app.get("/locations", response_model=List[LocationResponse])
    async def get_locations(
        type: Optional[str] = Query(None, description="Filter by type")
    ):
        """Get all campus locations."""
        graph = get_graph()
        locations = []

        for node in graph.get_all_nodes():
            if type and node.node_type.value != type:
                continue

            locations.append(LocationResponse(
                id=node.id,
                name=node.name,
                type=node.node_type.value,
                lat=node.lat,
                lon=node.lon,
                elevation=node.elevation,
            ))

        return locations

    @app.get("/locations/{location_id}", response_model=LocationResponse)
    async def get_location(location_id: str):
        """Get details for a specific location."""
        graph = get_graph()
        node = graph.get_node(location_id)

        if node is None:
            raise HTTPException(status_code=404, detail="Location not found")

        return LocationResponse(
            id=node.id,
            name=node.name,
            type=node.node_type.value,
            lat=node.lat,
            lon=node.lon,
            elevation=node.elevation,
        )

    @app.post("/route", response_model=RouteResponse)
    async def find_route(request: RouteRequest):
        """Find optimal route between two locations."""
        graph = get_graph()
        scheduler = get_scheduler()

        _validate_locations(graph, request.origin, request.destination)
        preferences = _build_user_preferences(request)
        departure_time = _parse_departure_time(request.departure_time)

        router = DivideConquerRouter(graph, scheduler)
        route = router.find_route(
            request.origin, request.destination, preferences, departure_time
        )

        if route is None:
            raise HTTPException(status_code=404, detail="No route found")

        return _route_to_response(route)

    @app.post("/routes/alternatives", response_model=List[RouteResponse])
    async def find_alternative_routes(
        request: RouteRequest,
        max_routes: int = Query(5, ge=1, le=10)
    ):
        """Find Pareto-optimal alternative routes."""
        graph = get_graph()
        scheduler = get_scheduler()

        _validate_locations(graph, request.origin, request.destination)
        departure_time = _parse_departure_time(request.departure_time)

        router = DivideConquerRouter(graph, scheduler, use_pareto=True)
        route_set = router.find_routes_pareto(
            request.origin, request.destination, departure_time, max_routes
        )

        return [_route_to_response(r) for r in route_set.routes]

    @app.post("/routes/compare-times", response_model=CompareTimesResponse)
    async def compare_departure_times(request: CompareTimesRequest):
        """Compare routes at different departure times."""
        graph = get_graph()
        scheduler = get_scheduler()

        times = _parse_time_list(request.times)
        results = scheduler.compare_departure_times(
            request.origin, request.destination, times
        )

        response_results = _convert_routes_to_responses(results)
        best_time, best_score = _find_best_departure_time(results)
        reason = _generate_best_time_reason(best_time, results)

        return CompareTimesResponse(
            results=response_results,
            best_time=best_time or request.times[0],
            reason=reason
        )

    @app.get("/profiles")
    async def get_optimization_profiles():
        """Get available optimization profiles."""
        return {
            "profiles": [
                {
                    "id": "fastest",
                    "name": "Fastest",
                    "description": "Minimize travel time"
                },
                {
                    "id": "shortest",
                    "name": "Shortest",
                    "description": "Minimize walking distance"
                },
                {
                    "id": "accessible",
                    "name": "Accessible",
                    "description": "Wheelchair accessible, avoid stairs"
                },
                {
                    "id": "comfortable",
                    "name": "Comfortable",
                    "description": "Balance time, elevation, and shelter"
                },
                {
                    "id": "avoid_crowds",
                    "name": "Avoid Crowds",
                    "description": "Prefer less crowded paths"
                },
                {
                    "id": "sheltered",
                    "name": "Sheltered",
                    "description": "Maximize covered walkways"
                },
            ]
        }

    @app.get("/time-windows")
    async def get_time_windows():
        """Get the time windows used for scheduling."""
        scheduler = get_scheduler()
        return {
            "windows": [
                {
                    "name": w.name,
                    "start": w.start_time.strftime("%H:%M"),
                    "end": w.end_time.strftime("%H:%M"),
                    "crowd_level": "high" if w.crowd_multiplier > 1.2 else "low" if w.crowd_multiplier < 0.5 else "medium",
                    "description": w.description,
                }
                for w in scheduler.time_windows
            ]
        }

    return app


def _route_to_response(route: Route) -> RouteResponse:
    """Convert internal Route to API response."""
    segments = []
    for seg in route.segments:
        segments.append(RouteSegmentResponse(
            from_id=seg.from_node_id,
            from_name=seg.from_node_name,
            to_id=seg.to_node_id,
            to_name=seg.to_node_name,
            distance=seg.weight.distance,
            time=seg.weight.time,
            stairs=seg.weight.stairs_count,
            instruction=seg.instruction,
        ))

    return RouteResponse(
        origin=route.origin_id,
        destination=route.destination_id,
        total_distance=route.total_weight.distance,
        total_time=route.total_weight.time,
        total_stairs=route.total_weight.stairs_count,
        elevation_gain=route.total_weight.elevation_gain,
        crowdedness=route.total_weight.crowdedness,
        segments=segments,
        path=route.node_path,
        is_pareto_optimal=route.is_pareto_optimal,
        rank=route.rank,
        summary=route.summary(),
    )


# Create default app instance
app = create_app()
