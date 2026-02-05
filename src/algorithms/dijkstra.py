"""
Multi-Criteria Dijkstra's Algorithm Implementation.

This module implements a modified version of Dijkstra's shortest path algorithm
that handles multiple objectives simultaneously using a weighted-sum approach.

ALGORITHM OVERVIEW:
==================

Standard Dijkstra:
    - Single scalar weight per edge
    - Priority queue ordered by cumulative distance
    - Returns single optimal path

Multi-Criteria Dijkstra:
    - Vector weight per edge: (distance, time, elevation, stairs, ...)
    - Priority queue ordered by weighted scalar combination
    - User preferences determine weight combination
    - Can filter edges based on hard constraints (accessibility, max stairs)

COMPLEXITY:
    - Time: O((V + E) log V) where V = vertices, E = edges
    - Space: O(V) for distance tracking and path reconstruction

PSEUDOCODE:
==========

function MultiCriteriaDijkstra(graph, source, target, preferences):
    // Initialize
    dist[v] = infinity for all vertices v
    dist[source] = MultiObjectiveWeight(0, 0, 0, ...)
    prev[v] = null for all vertices v
    priority_queue Q = [(0, source)]  // (scalar_cost, node)

    while Q is not empty:
        (current_cost, u) = Q.pop_min()

        if u == target:
            return reconstruct_path(prev, target)

        if current_cost > dist[u].compute_scalar_cost(preferences):
            continue  // Already found better path

        for each neighbor v of u:
            edge = graph.get_edge(u, v)

            // Check hard constraints
            if not preferences.is_edge_allowed(edge):
                continue

            // Compute new weight vector
            edge_weight = compute_edge_weight(edge, time_window)
            new_dist = dist[u] + edge_weight
            new_cost = new_dist.compute_scalar_cost(preferences)

            if new_cost < dist[v].compute_scalar_cost(preferences):
                dist[v] = new_dist
                prev[v] = u
                Q.push((new_cost, v))

    return null  // No path found

function compute_edge_weight(edge, time_window):
    return MultiObjectiveWeight(
        distance = edge.distance,
        time = edge.estimated_time * crowd_factor(time_window),
        elevation_gain = max(0, edge.elevation_change),
        elevation_loss = max(0, -edge.elevation_change),
        stairs_count = edge.total_stairs,
        accessibility_score = edge.accessibility.mobility_score,
        crowdedness = edge.get_crowd_factor(time_window),
        covered_ratio = 1.0 if edge.is_covered else 0.0,
        indoor_ratio = 1.0 if edge.is_indoor else 0.0
    )
"""

import heapq
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..models.graph_models import CampusGraph, Edge, Node
from ..models.route_models import (
    MultiObjectiveWeight,
    UserPreferences,
    Route,
    RouteSegment,
)
from ..models.time_models import TimeWindow


@dataclass
class DijkstraState:
    """Internal state for Dijkstra algorithm."""
    cost: float
    weight: MultiObjectiveWeight
    node_id: str

    def __lt__(self, other: "DijkstraState") -> bool:
        return self.cost < other.cost


class MultiCriteriaDijkstra:
    """
    Multi-criteria Dijkstra's algorithm for campus routing.

    This implementation extends standard Dijkstra to handle multiple
    optimization objectives using a weighted-sum approach.

    Attributes:
        graph: The campus graph to route on
        preferences: User preferences for weight combination
        time_window: Current time window for crowd estimation
    """

    def __init__(
        self,
        graph: CampusGraph,
        preferences: Optional[UserPreferences] = None,
        time_window: Optional[str] = None
    ):
        self.graph = graph
        self.preferences = preferences or UserPreferences()
        self.time_window = time_window or "mid_morning"

    def find_path(
        self,
        source_id: str,
        target_id: str,
        preferences: Optional[UserPreferences] = None
    ) -> Optional[Route]:
        """
        Find the optimal path from source to target.

        Args:
            source_id: Starting node ID
            target_id: Destination node ID
            preferences: Optional override for user preferences

        Returns:
            Route object if path found, None otherwise
        """
        prefs = preferences or self.preferences

        # Validate nodes exist
        if not self.graph.get_node(source_id):
            raise ValueError(f"Source node '{source_id}' not found in graph")
        if not self.graph.get_node(target_id):
            raise ValueError(f"Target node '{target_id}' not found in graph")

        # Initialize data structures
        dist: Dict[str, MultiObjectiveWeight] = {}
        prev: Dict[str, Optional[str]] = {}
        visited: set = set()

        # Initialize source
        initial_weight = MultiObjectiveWeight()
        dist[source_id] = initial_weight
        prev[source_id] = None

        # Priority queue: (scalar_cost, node_id)
        pq: List[Tuple[float, str]] = [(0.0, source_id)]

        while pq:
            current_cost, current_id = heapq.heappop(pq)

            # Skip if already visited
            if current_id in visited:
                continue
            visited.add(current_id)

            # Check if reached target
            if current_id == target_id:
                return self._reconstruct_route(
                    source_id, target_id, prev, dist[target_id]
                )

            # Explore neighbors
            for neighbor_id in self.graph.get_neighbors(current_id):
                if neighbor_id in visited:
                    continue

                edge = self.graph.get_edge(current_id, neighbor_id)
                if edge is None:
                    continue

                # Check hard constraints
                if not self._is_edge_allowed(edge, prefs):
                    continue

                # Compute edge weight
                edge_weight = self._compute_edge_weight(edge)

                # Compute new cumulative weight
                new_weight = dist[current_id] + edge_weight
                new_cost = new_weight.compute_scalar_cost(prefs)

                # Check if this is a better path
                if neighbor_id not in dist:
                    dist[neighbor_id] = new_weight
                    prev[neighbor_id] = current_id
                    heapq.heappush(pq, (new_cost, neighbor_id))
                else:
                    existing_cost = dist[neighbor_id].compute_scalar_cost(prefs)
                    if new_cost < existing_cost:
                        dist[neighbor_id] = new_weight
                        prev[neighbor_id] = current_id
                        heapq.heappush(pq, (new_cost, neighbor_id))

        # No path found
        return None

    def _is_edge_allowed(self, edge: Edge, prefs: UserPreferences) -> bool:
        """Check if an edge satisfies hard constraints."""
        return prefs.is_edge_allowed(
            stairs=edge.total_stairs,
            elevation_gain=max(0, edge.elevation_change),
            is_accessible=edge.accessibility.wheelchair_accessible,
            is_indoor=edge.is_indoor
        )

    def _compute_edge_weight(self, edge: Edge) -> MultiObjectiveWeight:
        """
        Compute the multi-objective weight for an edge.

        Time is adjusted based on crowd levels - crowded paths are slower.
        """
        crowdedness = edge.get_crowd_factor(self.time_window)
        adjusted_time = self._compute_time_with_crowds(edge.estimated_time, crowdedness)

        return MultiObjectiveWeight(
            distance=edge.distance,
            time=adjusted_time,
            elevation_gain=max(0, edge.elevation_change),
            elevation_loss=max(0, -edge.elevation_change),
            stairs_count=edge.total_stairs,
            accessibility_score=edge.accessibility.mobility_score,
            crowdedness=crowdedness,
            covered_ratio=1.0 if edge.is_covered else 0.0,
            indoor_ratio=1.0 if edge.is_indoor else 0.0,
        )

    def _compute_time_with_crowds(self, base_time: float, crowdedness: float) -> float:
        """
        Adjust travel time based on crowd level.

        At maximum crowdedness (1.0), paths take 20% longer.
        """
        CROWD_TIME_PENALTY = 0.2
        crowd_factor = 1.0 + (crowdedness * CROWD_TIME_PENALTY)
        return base_time * crowd_factor

    def _reconstruct_route(
        self,
        source_id: str,
        target_id: str,
        prev: Dict[str, Optional[str]],
        total_weight: MultiObjectiveWeight
    ) -> Route:
        """Reconstruct the route from predecessor map."""
        # Build path in reverse
        path: List[str] = []
        current = target_id
        while current is not None:
            path.append(current)
            current = prev.get(current)
        path.reverse()

        # Build segments
        segments: List[RouteSegment] = []
        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]

            from_node = self.graph.get_node(from_id)
            to_node = self.graph.get_node(to_id)
            edge = self.graph.get_edge(from_id, to_id)

            segment = RouteSegment(
                from_node_id=from_id,
                to_node_id=to_id,
                from_node_name=from_node.name if from_node else from_id,
                to_node_name=to_node.name if to_node else to_id,
                weight=self._compute_edge_weight(edge) if edge else MultiObjectiveWeight(),
                instruction=self._generate_instruction(from_node, to_node, edge)
            )
            segments.append(segment)

        return Route(
            origin_id=source_id,
            destination_id=target_id,
            segments=segments,
            total_weight=total_weight,
            is_pareto_optimal=True,
            rank=1
        )

    def _generate_instruction(
        self,
        from_node: Optional[Node],
        to_node: Optional[Node],
        edge: Optional[Edge]
    ) -> str:
        """Generate a human-readable navigation instruction."""
        if not from_node or not to_node:
            return ""

        instruction_parts = []

        # Determine action
        if to_node.is_indoor and not from_node.is_indoor:
            instruction_parts.append(f"Enter {to_node.name}")
        elif not to_node.is_indoor and from_node.is_indoor:
            instruction_parts.append(f"Exit to {to_node.name}")
        else:
            instruction_parts.append(f"Continue to {to_node.name}")

        # Add edge details
        if edge:
            if edge.stairs_up > 0:
                instruction_parts.append(f"(up {edge.stairs_up} stairs)")
            elif edge.stairs_down > 0:
                instruction_parts.append(f"(down {edge.stairs_down} stairs)")

            if edge.elevation_change > 3:
                instruction_parts.append("(uphill)")
            elif edge.elevation_change < -3:
                instruction_parts.append("(downhill)")

        return " ".join(instruction_parts)


def dijkstra_single_objective(
    graph: CampusGraph,
    source_id: str,
    target_id: str,
    weight_attribute: str = "distance"
) -> Optional[Tuple[List[str], float]]:
    """
    Simple single-objective Dijkstra for comparison/testing.

    Args:
        graph: Campus graph
        source_id: Start node
        target_id: End node
        weight_attribute: Edge attribute to minimize

    Returns:
        (path, total_weight) tuple if found, None otherwise
    """
    import networkx as nx

    try:
        path = nx.dijkstra_path(
            graph.networkx_graph,
            source_id,
            target_id,
            weight=weight_attribute
        )
        weight = nx.dijkstra_path_length(
            graph.networkx_graph,
            source_id,
            target_id,
            weight=weight_attribute
        )
        return (path, weight)
    except nx.NetworkXNoPath:
        return None
