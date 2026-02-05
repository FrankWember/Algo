"""
Time-Aware Scheduling using Divide & Conquer Strategy.

This module implements the temporal adaptation layer that adjusts
routing behavior based on time of day, day of week, and special events.

CONCEPTUAL OVERVIEW:
===================

Campus traffic patterns vary significantly throughout the day:
- 8-10 AM: Morning rush, high traffic between parking and buildings
- 11 AM - 1 PM: Lunch rush, high traffic near dining facilities
- 5-7 PM: Evening exodus, high traffic toward parking

The Divide & Conquer approach:
1. DIVIDE: Split the day into distinct time windows
2. CONQUER: Pre-compute or adjust routing parameters for each window
3. COMBINE: Select appropriate parameters based on query time

Benefits:
- Avoids real-time computation of time-varying weights
- Can pre-compute popular routes for each window
- Enables "what-if" queries: "What if I leave at 10 AM vs 12 PM?"

ALGORITHM: DIVIDE & CONQUER SCHEDULING
=====================================

Phase 1: Time Window Partitioning
    - Define K time windows based on traffic patterns
    - Each window has characteristic crowd multipliers

Phase 2: Per-Window Weight Computation
    for each time_window W:
        for each edge E in graph:
            E.adjusted_weight[W] = compute_weight(E, W.crowd_multiplier)

Phase 3: Query-Time Selection
    function route(source, target, departure_time):
        W = get_time_window(departure_time)
        return dijkstra(graph, source, target, using E.adjusted_weight[W])

PSEUDOCODE:
==========

class TimeAwareScheduler:
    function precompute_time_windows(graph, windows):
        for each window W in windows:
            weight_cache[W] = {}
            for each edge E in graph:
                base_weight = E.base_weight
                crowd_factor = E.get_crowd_pattern(W) * W.crowd_multiplier

                // Adjust time based on crowdedness
                adjusted_time = E.time * (1 + crowd_factor * 0.3)

                // Crowd affects comfort but not distance
                weight_cache[W][E] = MultiObjectiveWeight(
                    distance = E.distance,
                    time = adjusted_time,
                    crowdedness = crowd_factor,
                    ... // other unchanged factors
                )

    function route_at_time(source, target, departure_time, preferences):
        window = get_current_window(departure_time)
        weights = weight_cache[window]

        // Run multi-criteria Dijkstra with time-adjusted weights
        return dijkstra(graph, source, target, preferences, weights)


DIVIDE & CONQUER FOR LONG TRIPS:
===============================

For trips that span multiple time windows (e.g., cross-campus shuttle):

function route_with_window_transitions(source, target, departure_time):
    current_time = departure_time
    current_location = source
    full_path = []

    while current_location != target:
        current_window = get_window(current_time)
        next_window_start = current_window.end_time

        // Route within current window
        partial = route_within_window(
            current_location,
            target,
            current_window,
            max_time = next_window_start - current_time
        )

        if partial.reaches_target:
            full_path.extend(partial)
            break
        else:
            full_path.extend(partial)
            current_location = partial.end_location
            current_time = next_window_start

    return full_path
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ..models.graph_models import CampusGraph, Edge
from ..models.route_models import (
    MultiObjectiveWeight,
    UserPreferences,
    Route,
    RouteSet,
)
from ..models.time_models import (
    TimeWindow,
    DayOfWeek,
    ShuttleSchedule,
    DEFAULT_TIME_WINDOWS,
    get_current_time_window,
    get_day_of_week,
)
from .dijkstra import MultiCriteriaDijkstra
from .pareto import ParetoOptimizer


@dataclass
class TimeAwareEdgeWeight:
    """Pre-computed edge weights for a specific time window."""
    edge_id: Tuple[str, str]
    time_window: str
    weight: MultiObjectiveWeight


class TimeAwareScheduler:
    """
    Manages time-dependent routing by pre-computing weights per time window.

    This class implements the "Divide" part of Divide & Conquer by
    partitioning time and pre-computing appropriate weights.

    Attributes:
        graph: Campus graph
        time_windows: List of time windows
        weight_cache: Pre-computed weights per window
    """

    def __init__(
        self,
        graph: CampusGraph,
        time_windows: Optional[List[TimeWindow]] = None,
        shuttle_schedule: Optional[ShuttleSchedule] = None
    ):
        self.graph = graph
        self.time_windows = time_windows or DEFAULT_TIME_WINDOWS
        self.shuttle_schedule = shuttle_schedule
        self.weight_cache: Dict[str, Dict[Tuple[str, str], MultiObjectiveWeight]] = {}

        # Pre-compute weights for each time window
        self._precompute_all_weights()

    def _precompute_all_weights(self) -> None:
        """Pre-compute edge weights for all time windows."""
        for window in self.time_windows:
            self.weight_cache[window.name] = {}

            for edge in self.graph.get_all_edges():
                weight = self._compute_time_aware_weight(edge, window)
                edge_key = (edge.source_id, edge.target_id)
                self.weight_cache[window.name][edge_key] = weight

    def _compute_time_aware_weight(
        self,
        edge: Edge,
        window: TimeWindow
    ) -> MultiObjectiveWeight:
        """
        Compute edge weight adjusted for a specific time window.

        The time window affects:
        - Crowdedness (from historical patterns)
        - Effective travel time (crowds slow you down)
        - Route desirability (avoiding crowds)
        """
        # Get base crowdedness for this edge and window
        base_crowdedness = edge.get_crowd_factor(window.name)

        # Apply window's global multiplier
        adjusted_crowdedness = min(1.0, base_crowdedness * window.crowd_multiplier)

        # Crowded paths are slower
        # At max crowdedness (1.0), paths take ~30% longer
        crowd_time_factor = 1.0 + (adjusted_crowdedness * 0.3)
        adjusted_time = edge.estimated_time * crowd_time_factor

        return MultiObjectiveWeight(
            distance=edge.distance,
            time=adjusted_time,
            elevation_gain=max(0, edge.elevation_change),
            elevation_loss=max(0, -edge.elevation_change),
            stairs_count=edge.total_stairs,
            accessibility_score=edge.accessibility.mobility_score,
            crowdedness=adjusted_crowdedness,
            covered_ratio=1.0 if edge.is_covered else 0.0,
            indoor_ratio=1.0 if edge.is_indoor else 0.0,
        )

    def get_weight_for_time(
        self,
        source_id: str,
        target_id: str,
        query_time: Optional[time] = None
    ) -> Optional[MultiObjectiveWeight]:
        """Get the pre-computed weight for an edge at a specific time."""
        window = get_current_time_window(query_time, self.time_windows)
        edge_key = (source_id, target_id)
        return self.weight_cache.get(window.name, {}).get(edge_key)

    def get_current_window(self, t: Optional[time] = None) -> TimeWindow:
        """Get the time window for a given time."""
        return get_current_time_window(t, self.time_windows)

    def compare_departure_times(
        self,
        source_id: str,
        target_id: str,
        departure_times: List[time],
        preferences: Optional[UserPreferences] = None
    ) -> Dict[str, Route]:
        """
        Compare routes for different departure times.

        This enables "what-if" analysis: "When should I leave to avoid crowds?"

        Args:
            source_id: Starting node
            target_id: Destination node
            departure_times: List of times to compare
            preferences: User preferences

        Returns:
            Dict mapping time string to computed Route
        """
        results = {}
        prefs = preferences or UserPreferences()

        for dep_time in departure_times:
            window = self.get_current_window(dep_time)

            # Create router with time-specific weights
            router = DivideConquerRouter(
                graph=self.graph,
                scheduler=self,
                time_window=window.name
            )

            route = router.find_route(source_id, target_id, prefs)
            time_str = dep_time.strftime("%H:%M")
            results[time_str] = route

        return results


class DivideConquerRouter:
    """
    Main routing class that combines Dijkstra with time-aware scheduling.

    This is the primary interface for time-dependent routing queries.

    Attributes:
        graph: Campus graph
        scheduler: TimeAwareScheduler for time-dependent weights
        time_window: Current time window name
        use_pareto: Whether to compute Pareto-optimal alternatives
    """

    def __init__(
        self,
        graph: CampusGraph,
        scheduler: Optional[TimeAwareScheduler] = None,
        time_window: Optional[str] = None,
        use_pareto: bool = False
    ):
        self.graph = graph
        self.scheduler = scheduler or TimeAwareScheduler(graph)
        self.time_window = time_window or "mid_morning"
        self.use_pareto = use_pareto

    def find_route(
        self,
        source_id: str,
        target_id: str,
        preferences: Optional[UserPreferences] = None,
        departure_time: Optional[time] = None
    ) -> Optional[Route]:
        """
        Find the optimal route considering time-of-day factors.

        Args:
            source_id: Starting node ID
            target_id: Destination node ID
            preferences: User optimization preferences
            departure_time: When the user plans to depart

        Returns:
            Optimal Route or None if no path exists
        """
        # Determine time window
        if departure_time:
            window = self.scheduler.get_current_window(departure_time)
            tw_name = window.name
        else:
            tw_name = self.time_window

        # Use Dijkstra with time-aware weights
        dijkstra = MultiCriteriaDijkstra(
            graph=self.graph,
            preferences=preferences,
            time_window=tw_name
        )

        return dijkstra.find_path(source_id, target_id, preferences)

    def find_routes_pareto(
        self,
        source_id: str,
        target_id: str,
        departure_time: Optional[time] = None,
        max_routes: int = 5
    ) -> RouteSet:
        """
        Find Pareto-optimal routes considering time-of-day.

        Args:
            source_id: Starting node ID
            target_id: Destination node ID
            departure_time: Departure time
            max_routes: Maximum routes to return

        Returns:
            RouteSet with non-dominated alternatives
        """
        if departure_time:
            window = self.scheduler.get_current_window(departure_time)
            tw_name = window.name
        else:
            tw_name = self.time_window

        optimizer = ParetoOptimizer(
            graph=self.graph,
            max_routes=max_routes
        )

        return optimizer.find_pareto_routes(
            source_id,
            target_id,
            time_window=tw_name
        )

    def route_with_shuttle(
        self,
        source_id: str,
        target_id: str,
        preferences: Optional[UserPreferences] = None,
        departure_time: Optional[time] = None,
        day: Optional[DayOfWeek] = None
    ) -> Optional[Route]:
        """
        Find route that may include shuttle segments.

        This method considers whether taking a shuttle would be faster
        than walking the entire distance.

        Args:
            source_id: Starting node
            target_id: Destination node
            preferences: User preferences
            departure_time: Departure time
            day: Day of week

        Returns:
            Route possibly including shuttle segments
        """
        if not self.scheduler.shuttle_schedule:
            return self.find_route(source_id, target_id, preferences, departure_time)

        dep_time = departure_time or datetime.now().time()
        day = day or get_day_of_week()

        walk_route = self.find_route(source_id, target_id, preferences, dep_time)
        if walk_route is None:
            return None

        self._add_shuttle_info_if_available(
            walk_route, source_id, target_id, dep_time, day
        )
        return walk_route

    def _add_shuttle_info_if_available(
        self,
        route: Route,
        source_id: str,
        target_id: str,
        departure_time: time,
        day: DayOfWeek
    ) -> None:
        """Add shuttle information to route metadata if shuttle is available."""
        schedule = self.scheduler.shuttle_schedule

        source_stop = schedule.get_stop_by_node(source_id)
        target_stop = schedule.get_stop_by_node(target_id)

        if not (source_stop and target_stop):
            return

        shuttle_info = schedule.can_travel(
            source_stop.id, target_stop.id, departure_time, day
        )

        if shuttle_info:
            shuttle_route, shuttle_time = shuttle_info
            if shuttle_time < route.total_time:
                route.metadata["shuttle_available"] = True
                route.metadata["shuttle_route"] = shuttle_route.name
                route.metadata["shuttle_time"] = shuttle_time


def _compute_route_score(
    route: Route,
    preferences: UserPreferences,
    minutes_before_deadline: int
) -> float:
    """
    Compute a score for route quality.

    Lower scores are better. Considers both comfort and earliness.
    """
    comfort_score = route.total_weight.compute_scalar_cost(preferences)
    earliness_penalty = minutes_before_deadline * 0.1
    return comfort_score + earliness_penalty


def _will_arrive_on_time(
    departure_datetime: datetime,
    route: Route,
    deadline_datetime: datetime
) -> bool:
    """Check if route will arrive before deadline."""
    arrival_datetime = departure_datetime + timedelta(seconds=route.total_time)
    return arrival_datetime <= deadline_datetime


def suggest_departure_time(
    graph: CampusGraph,
    source_id: str,
    target_id: str,
    arrival_deadline: time,
    preferences: Optional[UserPreferences] = None,
    time_windows: Optional[List[TimeWindow]] = None
) -> Tuple[time, Route]:
    """
    Suggest the best departure time to meet an arrival deadline.

    This function tries different departure times and finds the one
    that results in the most comfortable journey while still arriving
    on time.

    Args:
        graph: Campus graph
        source_id: Starting node
        target_id: Destination node
        arrival_deadline: Must arrive by this time
        preferences: User preferences
        time_windows: Time windows to consider

    Returns:
        (suggested_departure_time, route) tuple
    """
    windows = time_windows or DEFAULT_TIME_WINDOWS
    scheduler = TimeAwareScheduler(graph, windows)
    prefs = preferences or UserPreferences()

    deadline_dt = datetime.combine(datetime.today(), arrival_deadline)
    router = DivideConquerRouter(graph, scheduler)

    best_departure = None
    best_route = None
    best_score = float('inf')

    # Try departures in 10-minute increments from 60 minutes before deadline
    for minutes_before in range(60, 0, -10):
        departure_dt = deadline_dt - timedelta(minutes=minutes_before)
        route = router.find_route(source_id, target_id, prefs, departure_dt.time())

        if route is None:
            continue

        if not _will_arrive_on_time(departure_dt, route, deadline_dt):
            continue

        score = _compute_route_score(route, prefs, minutes_before)
        if score < best_score:
            best_score = score
            best_departure = departure_dt.time()
            best_route = route

    if best_departure is None:
        # Couldn't find valid time, suggest leaving ASAP
        best_route = router.find_route(source_id, target_id, prefs)
        fallback_buffer_seconds = best_route.total_time if best_route else 600
        best_departure = (deadline_dt - timedelta(seconds=fallback_buffer_seconds)).time()

    return (best_departure, best_route)
