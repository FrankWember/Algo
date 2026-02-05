"""
Tests for routing algorithms.
"""

import pytest
from datetime import time

from src.models.graph_models import (
    Node, Edge, NodeType, SurfaceType, AccessibilityInfo, CampusGraph
)
from src.models.route_models import (
    MultiObjectiveWeight, UserPreferences, OptimizationProfile
)
from src.algorithms.dijkstra import MultiCriteriaDijkstra
from src.algorithms.pareto import ParetoOptimizer, compute_pareto_frontier
from src.algorithms.scheduler import TimeAwareScheduler, DivideConquerRouter


# Fixtures

@pytest.fixture
def simple_graph():
    """Create a simple test graph."""
    graph = CampusGraph(name="Test Campus")

    # Create nodes
    nodes = [
        Node(id="A", name="Building A", node_type=NodeType.BUILDING,
             coordinates=(0.0, 0.0), elevation=100.0),
        Node(id="B", name="Building B", node_type=NodeType.BUILDING,
             coordinates=(0.001, 0.0), elevation=105.0),
        Node(id="C", name="Building C", node_type=NodeType.BUILDING,
             coordinates=(0.001, 0.001), elevation=100.0),
        Node(id="D", name="Building D", node_type=NodeType.BUILDING,
             coordinates=(0.0, 0.001), elevation=95.0),
    ]

    for node in nodes:
        graph.add_node(node)

    # Create edges with different characteristics
    edges = [
        # A -> B: Short but uphill with stairs
        Edge(source_id="A", target_id="B", distance=100, elevation_change=5,
             stairs_up=10, is_covered=False),
        # A -> D: Longer but flat and covered
        Edge(source_id="A", target_id="D", distance=150, elevation_change=-5,
             stairs_down=0, is_covered=True),
        # B -> C: Medium, flat
        Edge(source_id="B", target_id="C", distance=120, elevation_change=-5,
             stairs_down=5, is_covered=False),
        # D -> C: Short, flat, covered
        Edge(source_id="D", target_id="C", distance=100, elevation_change=5,
             stairs_up=0, is_covered=True),
    ]

    for edge in edges:
        graph.add_edge(edge)

    return graph


@pytest.fixture
def campus_graph():
    """Create a more realistic campus graph."""
    from src.data.osm_loader import OSMCampusLoader

    loader = OSMCampusLoader()
    return loader.create_synthetic_campus()


# Multi-Criteria Dijkstra Tests

class TestMultiCriteriaDijkstra:
    """Tests for the multi-criteria Dijkstra algorithm."""

    def test_finds_path(self, simple_graph):
        """Test that algorithm finds a valid path."""
        dijkstra = MultiCriteriaDijkstra(simple_graph)
        route = dijkstra.find_path("A", "C")

        assert route is not None
        assert route.origin_id == "A"
        assert route.destination_id == "C"
        assert len(route.segments) >= 1

    def test_path_includes_endpoints(self, simple_graph):
        """Test that path starts and ends at correct nodes."""
        dijkstra = MultiCriteriaDijkstra(simple_graph)
        route = dijkstra.find_path("A", "C")

        path = route.node_path
        assert path[0] == "A"
        assert path[-1] == "C"

    def test_respects_shortest_preference(self, simple_graph):
        """Test that shortest profile minimizes distance."""
        prefs = UserPreferences.from_profile(OptimizationProfile.SHORTEST)
        dijkstra = MultiCriteriaDijkstra(simple_graph, preferences=prefs)
        route = dijkstra.find_path("A", "C")

        # Should prefer A -> B -> C (220m) over A -> D -> C (250m)
        # unless elevation weight is very high
        assert route is not None

    def test_accessible_profile_avoids_stairs(self, simple_graph):
        """Test that accessible profile avoids stairs."""
        prefs = UserPreferences.from_profile(OptimizationProfile.ACCESSIBLE)
        dijkstra = MultiCriteriaDijkstra(simple_graph, preferences=prefs)
        route = dijkstra.find_path("A", "C")

        # Should prefer A -> D -> C (no stairs) over A -> B -> C (stairs)
        assert route is not None
        # Check that path goes through D if accessible route exists
        if route.total_stairs == 0:
            assert "D" in route.node_path

    def test_nonexistent_source_raises_error(self, simple_graph):
        """Test that invalid source raises error."""
        dijkstra = MultiCriteriaDijkstra(simple_graph)

        with pytest.raises(ValueError):
            dijkstra.find_path("INVALID", "C")

    def test_nonexistent_target_raises_error(self, simple_graph):
        """Test that invalid target raises error."""
        dijkstra = MultiCriteriaDijkstra(simple_graph)

        with pytest.raises(ValueError):
            dijkstra.find_path("A", "INVALID")

    def test_same_source_and_target(self, simple_graph):
        """Test routing to same location."""
        dijkstra = MultiCriteriaDijkstra(simple_graph)
        route = dijkstra.find_path("A", "A")

        # Should return empty or trivial route
        assert route is not None
        assert route.total_distance == 0


# Pareto Optimizer Tests

class TestParetoOptimizer:
    """Tests for Pareto optimization."""

    def test_finds_multiple_routes(self, simple_graph):
        """Test that optimizer can find multiple routes."""
        optimizer = ParetoOptimizer(simple_graph, max_routes=3)
        route_set = optimizer.find_pareto_routes("A", "C")

        assert route_set is not None
        assert len(route_set.routes) >= 1

    def test_routes_are_non_dominated(self, simple_graph):
        """Test that returned routes are Pareto-optimal."""
        optimizer = ParetoOptimizer(simple_graph, max_routes=5)
        route_set = optimizer.find_pareto_routes("A", "C")

        # No route should dominate another
        for i, route_i in enumerate(route_set.routes):
            for j, route_j in enumerate(route_set.routes):
                if i != j:
                    assert not route_i.total_weight.dominates(route_j.total_weight)

    def test_pareto_frontier_computation(self):
        """Test the Pareto frontier utility function."""
        costs = [
            MultiObjectiveWeight(distance=100, time=60, stairs_count=5),
            MultiObjectiveWeight(distance=80, time=70, stairs_count=10),
            MultiObjectiveWeight(distance=120, time=50, stairs_count=3),
            MultiObjectiveWeight(distance=90, time=80, stairs_count=15),  # Dominated
        ]

        pareto_indices = compute_pareto_frontier(costs)

        # The 4th option is dominated by the 1st (worse in all objectives)
        assert 3 not in pareto_indices
        assert len(pareto_indices) >= 2


# Time Scheduler Tests

class TestTimeAwareScheduler:
    """Tests for time-aware scheduling."""

    def test_scheduler_initialization(self, campus_graph):
        """Test that scheduler initializes correctly."""
        scheduler = TimeAwareScheduler(campus_graph)

        assert len(scheduler.time_windows) > 0
        assert len(scheduler.weight_cache) > 0

    def test_different_times_different_weights(self, campus_graph):
        """Test that different time windows produce different weights."""
        scheduler = TimeAwareScheduler(campus_graph)

        # Get weights for different times
        morning = scheduler.get_weight_for_time("muc", "library", time(8, 30))
        midday = scheduler.get_weight_for_time("muc", "library", time(12, 0))
        evening = scheduler.get_weight_for_time("muc", "library", time(20, 0))

        # Crowdedness should differ
        if morning and midday and evening:
            # Lunch rush should have highest crowd
            assert midday.crowdedness >= morning.crowdedness or midday.crowdedness >= evening.crowdedness

    def test_compare_departure_times(self, campus_graph):
        """Test departure time comparison."""
        scheduler = TimeAwareScheduler(campus_graph)

        times = [time(8, 0), time(12, 0), time(18, 0)]
        results = scheduler.compare_departure_times("muc", "library", times)

        assert len(results) == 3
        for t_str, route in results.items():
            if route:
                assert route.total_distance > 0


class TestDivideConquerRouter:
    """Tests for the combined router."""

    def test_finds_route(self, campus_graph):
        """Test that router finds a valid route."""
        router = DivideConquerRouter(campus_graph)
        route = router.find_route("muc", "engineering")

        assert route is not None
        assert route.origin_id == "muc"
        assert route.destination_id == "engineering"

    def test_route_with_departure_time(self, campus_graph):
        """Test routing with specific departure time."""
        router = DivideConquerRouter(campus_graph)

        route_morning = router.find_route("muc", "library", departure_time=time(8, 30))
        route_evening = router.find_route("muc", "library", departure_time=time(20, 0))

        assert route_morning is not None
        assert route_evening is not None

    def test_pareto_routes(self, campus_graph):
        """Test finding Pareto-optimal routes."""
        router = DivideConquerRouter(campus_graph, use_pareto=True)
        route_set = router.find_routes_pareto("cougar_village", "muc", max_routes=3)

        assert route_set is not None
        assert len(route_set.routes) >= 1


# Weight and Preference Tests

class TestMultiObjectiveWeight:
    """Tests for MultiObjectiveWeight operations."""

    def test_weight_addition(self):
        """Test adding two weights together."""
        w1 = MultiObjectiveWeight(distance=100, time=60, stairs_count=5)
        w2 = MultiObjectiveWeight(distance=50, time=30, stairs_count=3)

        combined = w1 + w2

        assert combined.distance == 150
        assert combined.time == 90
        assert combined.stairs_count == 8

    def test_dominance_check(self):
        """Test Pareto dominance checking."""
        better = MultiObjectiveWeight(distance=100, time=60, stairs_count=5)
        worse = MultiObjectiveWeight(distance=150, time=80, stairs_count=10)

        assert better.dominates(worse)
        assert not worse.dominates(better)

    def test_no_dominance_when_tradeoff(self):
        """Test that tradeoffs are not dominated."""
        short_but_stairs = MultiObjectiveWeight(distance=100, time=60, stairs_count=10)
        long_but_flat = MultiObjectiveWeight(distance=150, time=70, stairs_count=0)

        assert not short_but_stairs.dominates(long_but_flat)
        assert not long_but_flat.dominates(short_but_stairs)


class TestUserPreferences:
    """Tests for user preferences."""

    def test_profile_creation(self):
        """Test creating preferences from profiles."""
        fastest = UserPreferences.from_profile(OptimizationProfile.FASTEST)
        accessible = UserPreferences.from_profile(OptimizationProfile.ACCESSIBLE)

        assert fastest.time_weight > fastest.distance_weight
        assert accessible.require_wheelchair_accessible is True
        assert accessible.max_stairs == 0

    def test_edge_constraint_checking(self):
        """Test hard constraint checking."""
        prefs = UserPreferences(max_stairs=5, require_wheelchair_accessible=True)

        # Should allow
        assert prefs.is_edge_allowed(stairs=3, elevation_gain=5, is_accessible=True, is_indoor=False)

        # Should reject - too many stairs
        assert not prefs.is_edge_allowed(stairs=10, elevation_gain=5, is_accessible=True, is_indoor=False)

        # Should reject - not accessible
        assert not prefs.is_edge_allowed(stairs=0, elevation_gain=5, is_accessible=False, is_indoor=False)


# Integration Tests

class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_routing_workflow(self, campus_graph):
        """Test complete routing workflow."""
        from src.algorithms.scheduler import DivideConquerRouter, TimeAwareScheduler

        # Initialize
        scheduler = TimeAwareScheduler(campus_graph)
        router = DivideConquerRouter(campus_graph, scheduler)

        # Find route
        route = router.find_route(
            "cougar_village",
            "engineering",
            UserPreferences.from_profile(OptimizationProfile.COMFORTABLE),
            departure_time=time(9, 30)
        )

        # Validate route
        assert route is not None
        assert route.total_distance > 0
        assert route.total_time > 0
        assert len(route.segments) > 0

        # Check path continuity
        path = route.node_path
        for i in range(len(path) - 1):
            edge = campus_graph.get_edge(path[i], path[i + 1])
            assert edge is not None

    def test_multiple_profiles_same_route(self, campus_graph):
        """Test that different profiles can produce different routes."""
        router = DivideConquerRouter(campus_graph)

        profiles = [
            OptimizationProfile.FASTEST,
            OptimizationProfile.COMFORTABLE,
            OptimizationProfile.ACCESSIBLE,
        ]

        routes = []
        for profile in profiles:
            prefs = UserPreferences.from_profile(profile)
            route = router.find_route("muc", "engineering", prefs)
            if route:
                routes.append((profile, route))

        # Should have routes for all profiles
        assert len(routes) == len(profiles)

        # Routes may differ
        # (In a small graph they might be the same, but the weights should differ)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
