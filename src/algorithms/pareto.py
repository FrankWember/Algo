"""
Pareto Optimization for Multi-Objective Route Planning.

This module implements dynamic programming-based algorithms for computing
Pareto-optimal route sets (non-dominated solutions).

CONCEPTUAL OVERVIEW:
===================

In multi-objective optimization, there's often no single "best" solution.
Instead, we have a set of Pareto-optimal solutions where no solution
dominates another.

Solution A dominates Solution B if:
    - A is at least as good as B in ALL objectives
    - A is strictly better than B in AT LEAST ONE objective

Example:
    Route 1: 500m, 3 stairs, low crowd
    Route 2: 400m, 10 stairs, medium crowd
    Route 3: 600m, 0 stairs, high crowd

    None dominates the others → All three are Pareto-optimal

The user can then choose based on their current priorities.

ALGORITHM: NAMOA* (Multi-Objective A*)
=====================================

Extension of A* for multiple objectives. Instead of maintaining a single
best cost per node, we maintain a SET of non-dominated costs (labels).

PSEUDOCODE:
==========

function ParetoOptimalRoutes(graph, source, target, objectives):
    // Labels: map from node to set of non-dominated (cost_vector, path) pairs
    labels[v] = {} for all vertices v
    labels[source] = {(zero_vector, [source])}

    // Priority queue of (estimated_total_cost, node, label_index)
    // Uses lexicographic ordering or sum for priority
    Q = PriorityQueue()
    Q.push((heuristic(source, target), source, 0))

    while Q is not empty:
        (_, u, label_idx) = Q.pop()

        if u == target:
            continue  // Found one solution, but keep searching for others

        current_label = labels[u][label_idx]
        (current_cost, current_path) = current_label

        for each neighbor v of u:
            edge_cost = compute_edge_cost(u, v)
            new_cost = current_cost + edge_cost
            new_path = current_path + [v]

            // Check if new_cost is dominated by any existing label at v
            if is_dominated(new_cost, labels[v]):
                continue

            // Remove any labels at v that are dominated by new_cost
            labels[v] = filter_dominated(labels[v], new_cost)

            // Add new label
            labels[v].add((new_cost, new_path))
            estimated = new_cost + heuristic(v, target)
            Q.push((estimated, v, len(labels[v]) - 1))

    return labels[target]  // Set of Pareto-optimal routes


DYNAMIC PROGRAMMING FORMULATION:
===============================

For the trade-off handling between objectives, we use DP:

Let OPT(v, budget) = set of Pareto-optimal paths from source to v
                     using at most 'budget' of primary resource

Recurrence:
    OPT(v, b) = non_dominated(
        for each predecessor u of v:
            for each path p in OPT(u, b - cost(u,v)):
                extend(p, edge(u,v))
    )

This allows us to explore trade-offs: "I'm willing to walk 100m more
to avoid 10 stairs" type decisions.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import heapq
from copy import deepcopy

from ..models.graph_models import CampusGraph, Edge
from ..models.route_models import (
    MultiObjectiveWeight,
    UserPreferences,
    Route,
    RouteSegment,
    RouteSet,
)


@dataclass
class Label:
    """
    A label represents a non-dominated partial solution at a node.

    In multi-objective shortest path, each node can have multiple
    labels representing different trade-offs.
    """
    cost: MultiObjectiveWeight
    path: List[str]
    dominated: bool = False

    def __hash__(self):
        return hash(tuple(self.path))


class ParetoOptimizer:
    """
    Computes Pareto-optimal route sets using label-setting algorithm.

    This implementation finds ALL non-dominated routes between two points,
    allowing users to choose based on their priorities.

    Attributes:
        graph: Campus graph
        max_labels_per_node: Limit on labels to prevent explosion
        max_routes: Maximum routes to return
    """

    def __init__(
        self,
        graph: CampusGraph,
        max_labels_per_node: int = 10,
        max_routes: int = 5
    ):
        self.graph = graph
        self.max_labels_per_node = max_labels_per_node
        self.max_routes = max_routes

    def find_pareto_routes(
        self,
        source_id: str,
        target_id: str,
        time_window: str = "mid_morning",
        objectives: Optional[List[str]] = None
    ) -> RouteSet:
        """
        Find all Pareto-optimal routes between source and target.

        Args:
            source_id: Starting node ID
            target_id: Destination node ID
            time_window: Time window for crowd estimation
            objectives: Which objectives to consider for Pareto dominance

        Returns:
            RouteSet containing all non-dominated routes
        """
        if objectives is None:
            objectives = ["distance", "time", "stairs_count", "elevation_gain"]

        # Labels: node_id -> list of Label objects
        labels: Dict[str, List[Label]] = {source_id: []}

        # Initialize source with zero-cost label
        initial_cost = MultiObjectiveWeight()
        initial_label = Label(cost=initial_cost, path=[source_id])
        labels[source_id].append(initial_label)

        # Priority queue: (priority, node_id, label_index)
        # Priority is sum of objectives (simple heuristic)
        pq: List[Tuple[float, str, int]] = []
        heapq.heappush(pq, (0.0, source_id, 0))

        # Track which labels have been processed
        processed: Set[Tuple[str, int]] = set()

        while pq:
            _, current_id, label_idx = heapq.heappop(pq)

            # Skip if already processed
            if (current_id, label_idx) in processed:
                continue
            processed.add((current_id, label_idx))

            # Skip if label was marked as dominated
            if label_idx >= len(labels.get(current_id, [])):
                continue
            current_label = labels[current_id][label_idx]
            if current_label.dominated:
                continue

            # Don't expand from target (but keep finding paths to it)
            if current_id == target_id:
                continue

            # Explore neighbors
            for neighbor_id in self.graph.get_neighbors(current_id):
                edge = self.graph.get_edge(current_id, neighbor_id)
                if edge is None:
                    continue

                # Compute new cost
                edge_cost = self._compute_edge_cost(edge, time_window)
                new_cost = current_label.cost + edge_cost
                new_path = current_label.path + [neighbor_id]

                # Initialize labels for neighbor if needed
                if neighbor_id not in labels:
                    labels[neighbor_id] = []

                # Check dominance
                if self._is_dominated(new_cost, labels[neighbor_id], objectives):
                    continue

                # Mark dominated labels
                self._mark_dominated(new_cost, labels[neighbor_id], objectives)

                # Add new label if under limit
                if len(labels[neighbor_id]) < self.max_labels_per_node:
                    new_label = Label(cost=new_cost, path=new_path)
                    labels[neighbor_id].append(new_label)
                    new_idx = len(labels[neighbor_id]) - 1

                    # Priority: simple sum of normalized objectives
                    priority = self._compute_priority(new_cost)
                    heapq.heappush(pq, (priority, neighbor_id, new_idx))

        # Extract routes to target
        return self._extract_routes(source_id, target_id, labels)

    def _compute_edge_cost(
        self,
        edge: Edge,
        time_window: str
    ) -> MultiObjectiveWeight:
        """Compute multi-objective cost for an edge."""
        crowdedness = edge.get_crowd_factor(time_window)
        crowd_time_factor = 1.0 + (crowdedness * 0.2)

        return MultiObjectiveWeight(
            distance=edge.distance,
            time=edge.estimated_time * crowd_time_factor,
            elevation_gain=max(0, edge.elevation_change),
            elevation_loss=max(0, -edge.elevation_change),
            stairs_count=edge.total_stairs,
            accessibility_score=edge.accessibility.mobility_score,
            crowdedness=crowdedness,
            covered_ratio=1.0 if edge.is_covered else 0.0,
            indoor_ratio=1.0 if edge.is_indoor else 0.0,
        )

    def _is_dominated(
        self,
        cost: MultiObjectiveWeight,
        existing_labels: List[Label],
        objectives: List[str]
    ) -> bool:
        """Check if a cost vector is dominated by any existing label."""
        for label in existing_labels:
            if label.dominated:
                continue
            if self._dominates(label.cost, cost, objectives):
                return True
        return False

    def _mark_dominated(
        self,
        new_cost: MultiObjectiveWeight,
        existing_labels: List[Label],
        objectives: List[str]
    ) -> None:
        """Mark any labels dominated by the new cost."""
        for label in existing_labels:
            if label.dominated:
                continue
            if self._dominates(new_cost, label.cost, objectives):
                label.dominated = True

    def _dominates(
        self,
        cost_a: MultiObjectiveWeight,
        cost_b: MultiObjectiveWeight,
        objectives: List[str]
    ) -> bool:
        """
        Check if cost_a Pareto-dominates cost_b.

        A dominates B if A is at least as good in all objectives
        and strictly better in at least one.
        """
        return _check_dominance(cost_a, cost_b, objectives)

    def _compute_priority(self, cost: MultiObjectiveWeight) -> float:
        """Compute priority for the search queue."""
        # Simple weighted sum for priority ordering
        return (
            cost.distance / 100 +
            cost.time / 60 +
            cost.stairs_count +
            cost.elevation_gain / 5
        )

    def _extract_routes(
        self,
        source_id: str,
        target_id: str,
        labels: Dict[str, List[Label]]
    ) -> RouteSet:
        """Extract Route objects from computed labels."""
        routes: List[Route] = []

        if target_id not in labels:
            return RouteSet(
                routes=[],
                origin_id=source_id,
                destination_id=target_id
            )

        # Get non-dominated labels at target
        target_labels = [l for l in labels[target_id] if not l.dominated]

        # Sort by total "cost" for ranking
        target_labels.sort(key=lambda l: self._compute_priority(l.cost))

        # Convert to Route objects
        for rank, label in enumerate(target_labels[:self.max_routes], 1):
            route = self._label_to_route(label, rank)
            routes.append(route)

        return RouteSet(
            routes=routes,
            origin_id=source_id,
            destination_id=target_id
        )

    def _label_to_route(self, label: Label, rank: int) -> Route:
        """Convert a Label to a Route object."""
        segments: List[RouteSegment] = []

        for i in range(len(label.path) - 1):
            from_id = label.path[i]
            to_id = label.path[i + 1]

            from_node = self.graph.get_node(from_id)
            to_node = self.graph.get_node(to_id)
            edge = self.graph.get_edge(from_id, to_id)

            segment = RouteSegment(
                from_node_id=from_id,
                to_node_id=to_id,
                from_node_name=from_node.name if from_node else from_id,
                to_node_name=to_node.name if to_node else to_id,
                weight=self._compute_edge_cost(edge, "mid_morning") if edge else MultiObjectiveWeight(),
                instruction=""
            )
            segments.append(segment)

        return Route(
            origin_id=label.path[0],
            destination_id=label.path[-1],
            segments=segments,
            total_weight=label.cost,
            is_pareto_optimal=True,
            rank=rank
        )


def compute_pareto_frontier(
    costs: List[MultiObjectiveWeight],
    objectives: Optional[List[str]] = None
) -> List[int]:
    """
    Compute indices of Pareto-optimal solutions from a list of costs.

    This is a utility function for filtering any set of solutions
    down to the non-dominated set.

    Args:
        costs: List of MultiObjectiveWeight objects
        objectives: Which objectives to consider

    Returns:
        List of indices into 'costs' that are Pareto-optimal
    """
    if objectives is None:
        objectives = ["distance", "time", "stairs_count", "elevation_gain"]

    n = len(costs)
    dominated = [False] * n

    for i in range(n):
        if dominated[i]:
            continue
        for j in range(n):
            if i == j or dominated[j]:
                continue

            # Check if j dominates i
            i_dominated = _check_dominance(costs[j], costs[i], objectives)
            if i_dominated:
                dominated[i] = True
                break

            # Check if i dominates j
            j_dominated = _check_dominance(costs[i], costs[j], objectives)
            if j_dominated:
                dominated[j] = True

    return [i for i in range(n) if not dominated[i]]


def _is_maximization_objective(objective: str) -> bool:
    """Check if an objective should be maximized (higher is better)."""
    return objective in ["accessibility_score", "covered_ratio", "indoor_ratio"]


def _check_dominance(
    cost_a: MultiObjectiveWeight,
    cost_b: MultiObjectiveWeight,
    objectives: List[str]
) -> bool:
    """
    Check if cost_a Pareto-dominates cost_b.

    Returns True if cost_a is at least as good in all objectives
    and strictly better in at least one.
    """
    is_at_least_as_good_in_all = True
    is_strictly_better_in_any = False

    for objective in objectives:
        value_a = getattr(cost_a, objective)
        value_b = getattr(cost_b, objective)

        if _is_maximization_objective(objective):
            # Higher is better
            if value_a < value_b:
                is_at_least_as_good_in_all = False
            if value_a > value_b:
                is_strictly_better_in_any = True
        else:
            # Lower is better (distance, time, stairs, etc.)
            if value_a > value_b:
                is_at_least_as_good_in_all = False
            if value_a < value_b:
                is_strictly_better_in_any = True

    return is_at_least_as_good_in_all and is_strictly_better_in_any
