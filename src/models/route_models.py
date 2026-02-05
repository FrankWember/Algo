"""
Route and path-related data models.

This module defines structures for representing computed routes
and multi-objective weights.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class OptimizationProfile(Enum):
    """Predefined optimization profiles for common use cases."""
    FASTEST = "fastest"  # Minimize time
    SHORTEST = "shortest"  # Minimize distance
    ACCESSIBLE = "accessible"  # Maximize accessibility
    COMFORTABLE = "comfortable"  # Balance comfort factors
    AVOID_CROWDS = "avoid_crowds"  # Minimize crowdedness
    SHELTERED = "sheltered"  # Maximize covered paths
    CUSTOM = "custom"  # User-defined weights


@dataclass
class MultiObjectiveWeight:
    """
    Represents the multi-dimensional weight/cost of a path segment or route.

    This is the core structure for multi-objective optimization.
    Each dimension can be weighted differently based on user preferences.

    Attributes:
        distance: Total distance in meters
        time: Estimated travel time in seconds
        elevation_gain: Total elevation gained (uphill) in meters
        elevation_loss: Total elevation lost (downhill) in meters
        stairs_count: Total number of stairs
        accessibility_score: Aggregate accessibility (0.0-1.0, higher is better)
        crowdedness: Aggregate crowdedness (0.0-1.0, lower is better)
        covered_ratio: Ratio of path that is covered/sheltered
        indoor_ratio: Ratio of path that is indoors
    """
    distance: float = 0.0
    time: float = 0.0
    elevation_gain: float = 0.0
    elevation_loss: float = 0.0
    stairs_count: int = 0
    accessibility_score: float = 1.0
    crowdedness: float = 0.0
    covered_ratio: float = 0.0
    indoor_ratio: float = 0.0

    def __add__(self, other: "MultiObjectiveWeight") -> "MultiObjectiveWeight":
        """Add two weights together (for path accumulation)."""
        total_distance = self.distance + other.distance
        return MultiObjectiveWeight(
            distance=total_distance,
            time=self.time + other.time,
            elevation_gain=self.elevation_gain + other.elevation_gain,
            elevation_loss=self.elevation_loss + other.elevation_loss,
            stairs_count=self.stairs_count + other.stairs_count,
            accessibility_score=min(self.accessibility_score, other.accessibility_score),
            crowdedness=max(self.crowdedness, other.crowdedness),
            covered_ratio=(
                (self.covered_ratio * self.distance + other.covered_ratio * other.distance)
                / total_distance if total_distance > 0 else 0
            ),
            indoor_ratio=(
                (self.indoor_ratio * self.distance + other.indoor_ratio * other.distance)
                / total_distance if total_distance > 0 else 0
            ),
        )

    def compute_scalar_cost(self, preferences: "UserPreferences") -> float:
        """
        Compute a single scalar cost based on user preferences.

        This is the weighted-sum approach for multi-objective optimization.
        Higher weights mean the user cares MORE about minimizing that factor.
        """
        # Normalize factors to comparable scales
        normalized_distance = self.distance / 100  # per 100m
        normalized_time = self.time / 60  # per minute
        normalized_elevation = (self.elevation_gain + self.elevation_loss) / 10  # per 10m
        normalized_stairs = self.stairs_count / 10  # per 10 stairs
        normalized_accessibility = 1 - self.accessibility_score  # invert (lower is better)
        normalized_crowdedness = self.crowdedness
        normalized_exposure = 1 - self.covered_ratio  # invert (less covered = worse)

        cost = (
            preferences.distance_weight * normalized_distance +
            preferences.time_weight * normalized_time +
            preferences.elevation_weight * normalized_elevation +
            preferences.stairs_weight * normalized_stairs +
            preferences.accessibility_weight * normalized_accessibility +
            preferences.crowdedness_weight * normalized_crowdedness +
            preferences.shelter_weight * normalized_exposure
        )

        return cost

    def dominates(self, other: "MultiObjectiveWeight") -> bool:
        """
        Check if this weight Pareto-dominates another.

        Returns True if this weight is at least as good in all objectives
        and strictly better in at least one.
        """
        dominated_objectives = [
            self.distance <= other.distance,
            self.time <= other.time,
            self.elevation_gain <= other.elevation_gain,
            self.stairs_count <= other.stairs_count,
            self.accessibility_score >= other.accessibility_score,  # Higher is better
            self.crowdedness <= other.crowdedness,
            self.covered_ratio >= other.covered_ratio,  # Higher is better
        ]

        strictly_better = [
            self.distance < other.distance,
            self.time < other.time,
            self.elevation_gain < other.elevation_gain,
            self.stairs_count < other.stairs_count,
            self.accessibility_score > other.accessibility_score,
            self.crowdedness < other.crowdedness,
            self.covered_ratio > other.covered_ratio,
        ]

        return all(dominated_objectives) and any(strictly_better)


@dataclass
class UserPreferences:
    """
    User-specified weights for multi-objective optimization.

    Weights should be non-negative. Higher weight = more important to minimize.
    Default weights create a balanced profile.
    """
    distance_weight: float = 1.0
    time_weight: float = 1.0
    elevation_weight: float = 0.5
    stairs_weight: float = 0.5
    accessibility_weight: float = 0.0  # 0 for able-bodied users
    crowdedness_weight: float = 0.3
    shelter_weight: float = 0.2

    # Hard constraints
    require_wheelchair_accessible: bool = False
    max_stairs: Optional[int] = None
    max_elevation_gain: Optional[float] = None
    avoid_outdoor: bool = False

    @classmethod
    def from_profile(cls, profile: OptimizationProfile) -> "UserPreferences":
        """Create preferences from a predefined profile."""
        profiles = {
            OptimizationProfile.FASTEST: cls(
                time_weight=2.0, distance_weight=0.5, elevation_weight=0.3
            ),
            OptimizationProfile.SHORTEST: cls(
                distance_weight=2.0, time_weight=0.5
            ),
            OptimizationProfile.ACCESSIBLE: cls(
                accessibility_weight=2.0,
                stairs_weight=2.0,
                elevation_weight=1.5,
                require_wheelchair_accessible=True,
                max_stairs=0,
            ),
            OptimizationProfile.COMFORTABLE: cls(
                elevation_weight=1.5,
                stairs_weight=1.5,
                shelter_weight=1.0,
                crowdedness_weight=0.8,
            ),
            OptimizationProfile.AVOID_CROWDS: cls(
                crowdedness_weight=2.0,
                time_weight=0.5,
            ),
            OptimizationProfile.SHELTERED: cls(
                shelter_weight=2.0,
                distance_weight=0.5,
            ),
        }
        return profiles.get(profile, cls())

    def is_edge_allowed(
        self,
        stairs: int,
        elevation_gain: float,
        is_accessible: bool,
        is_indoor: bool,
    ) -> bool:
        """Check if an edge satisfies hard constraints."""
        if self.require_wheelchair_accessible and not is_accessible:
            return False
        if self.max_stairs is not None and stairs > self.max_stairs:
            return False
        if self.max_elevation_gain is not None and elevation_gain > self.max_elevation_gain:
            return False
        if self.avoid_outdoor and not is_indoor:
            return False
        return True


@dataclass
class RouteSegment:
    """
    A single segment of a route (one edge traversal).

    Attributes:
        from_node_id: Starting node ID
        to_node_id: Ending node ID
        from_node_name: Starting node name
        to_node_name: Ending node name
        weight: Multi-objective weight of this segment
        instruction: Human-readable navigation instruction
    """
    from_node_id: str
    to_node_id: str
    from_node_name: str
    to_node_name: str
    weight: MultiObjectiveWeight
    instruction: str = ""


@dataclass
class Route:
    """
    A complete route from origin to destination.

    Attributes:
        origin_id: Starting node ID
        destination_id: Ending node ID
        segments: Ordered list of route segments
        total_weight: Aggregate weight of the entire route
        is_pareto_optimal: Whether this route is Pareto-optimal
        rank: Ranking among returned routes (1 = best)
        metadata: Additional route information
    """
    origin_id: str
    destination_id: str
    segments: List[RouteSegment] = field(default_factory=list)
    total_weight: MultiObjectiveWeight = field(default_factory=MultiObjectiveWeight)
    is_pareto_optimal: bool = True
    rank: int = 1
    metadata: Dict = field(default_factory=dict)

    @property
    def node_path(self) -> List[str]:
        """Get the ordered list of node IDs in this route."""
        if not self.segments:
            return []
        path = [self.segments[0].from_node_id]
        for segment in self.segments:
            path.append(segment.to_node_id)
        return path

    @property
    def total_distance(self) -> float:
        return self.total_weight.distance

    @property
    def total_time(self) -> float:
        return self.total_weight.time

    @property
    def total_stairs(self) -> int:
        return self.total_weight.stairs_count

    def get_instructions(self) -> List[str]:
        """Get human-readable navigation instructions."""
        return [seg.instruction for seg in self.segments if seg.instruction]

    def summary(self) -> str:
        """Get a human-readable summary of the route."""
        time_min = self.total_time / 60
        return (
            f"Route: {self.total_distance:.0f}m, "
            f"{time_min:.1f} min, "
            f"{self.total_stairs} stairs, "
            f"{self.total_weight.elevation_gain:.1f}m climb"
        )


@dataclass
class RouteSet:
    """
    A set of alternative routes (Pareto-optimal set).

    Attributes:
        routes: List of routes, ordered by rank
        origin_id: Starting node ID
        destination_id: Ending node ID
        time_window: Time window used for computation
        computation_time_ms: Time taken to compute routes
    """
    routes: List[Route] = field(default_factory=list)
    origin_id: str = ""
    destination_id: str = ""
    time_window: str = ""
    computation_time_ms: float = 0.0

    @property
    def best_route(self) -> Optional[Route]:
        """Get the top-ranked route."""
        return self.routes[0] if self.routes else None

    @property
    def count(self) -> int:
        return len(self.routes)

    def get_pareto_optimal(self) -> List[Route]:
        """Get only the Pareto-optimal routes."""
        return [r for r in self.routes if r.is_pareto_optimal]
