"""
Graph data models for campus representation.

This module defines the core data structures for representing the campus
as a weighted, directed graph with multi-objective edge weights.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import networkx as nx


class NodeType(Enum):
    """Classification of node types in the campus graph."""
    BUILDING = "building"
    BUILDING_ENTRANCE = "building_entrance"
    INTERSECTION = "intersection"
    BUS_STOP = "bus_stop"
    PARKING_LOT = "parking_lot"
    LANDMARK = "landmark"
    PATH_POINT = "path_point"


class SurfaceType(Enum):
    """Types of walking surfaces."""
    PAVED = "paved"
    CONCRETE = "concrete"
    BRICK = "brick"
    GRAVEL = "gravel"
    GRASS = "grass"
    INDOOR = "indoor"


@dataclass
class AccessibilityInfo:
    """
    Accessibility information for a node or edge.

    Attributes:
        wheelchair_accessible: Can be traversed by wheelchair
        has_automatic_doors: Building entrance has automatic doors
        has_elevator: Building has elevator access
        has_braille_signage: Location has braille signage
        mobility_score: Overall mobility accessibility (0.0-1.0)
        notes: Additional accessibility notes
    """
    wheelchair_accessible: bool = True
    has_automatic_doors: bool = False
    has_elevator: bool = True
    has_braille_signage: bool = False
    mobility_score: float = 1.0
    notes: str = ""


@dataclass
class Node:
    """
    Represents a location (vertex) in the campus graph.

    Attributes:
        id: Unique identifier for the node
        name: Human-readable name
        node_type: Classification of the node
        coordinates: (latitude, longitude) tuple
        elevation: Elevation in meters above sea level
        is_indoor: Whether this node is inside a building
        building_id: Associated building ID if applicable
        accessibility: Accessibility information
        metadata: Additional arbitrary data
    """
    id: str
    name: str
    node_type: NodeType
    coordinates: Tuple[float, float]  # (lat, lon)
    elevation: float = 0.0
    is_indoor: bool = False
    building_id: Optional[str] = None
    accessibility: AccessibilityInfo = field(default_factory=AccessibilityInfo)
    metadata: Dict = field(default_factory=dict)

    @property
    def lat(self) -> float:
        return self.coordinates[0]

    @property
    def lon(self) -> float:
        return self.coordinates[1]


@dataclass
class Edge:
    """
    Represents a connection (edge) between two nodes.

    This is the core data structure for multi-objective optimization.
    Each edge carries multiple weight dimensions that can be combined
    based on user preferences.

    Attributes:
        source_id: ID of the source node
        target_id: ID of the target node
        distance: Physical distance in meters
        elevation_change: Change in elevation (positive = uphill)
        stairs_up: Number of stairs going up
        stairs_down: Number of stairs going down
        has_ramp: Whether a ramp alternative exists
        is_covered: Whether the path is covered/sheltered
        surface_type: Type of walking surface
        is_indoor: Whether this edge is indoors
        bidirectional: Whether edge can be traversed both ways
        accessibility: Accessibility information
        crowd_patterns: Crowdedness by time window (0.0-1.0)
        estimated_time: Base walking time in seconds
        metadata: Additional arbitrary data
    """
    source_id: str
    target_id: str
    distance: float  # meters
    elevation_change: float = 0.0  # meters (positive = uphill)
    stairs_up: int = 0
    stairs_down: int = 0
    has_ramp: bool = True
    is_covered: bool = False
    surface_type: SurfaceType = SurfaceType.PAVED
    is_indoor: bool = False
    bidirectional: bool = True
    accessibility: AccessibilityInfo = field(default_factory=AccessibilityInfo)
    crowd_patterns: Dict[str, float] = field(default_factory=dict)
    estimated_time: float = 0.0  # seconds
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Calculate estimated walking time if not provided."""
        if self.estimated_time == 0.0:
            # Base walking speed: ~1.4 m/s (5 km/h)
            base_time = self.distance / 1.4

            # Add time for elevation (Naismith's rule: +1 min per 10m climb)
            if self.elevation_change > 0:
                base_time += (self.elevation_change / 10) * 60

            # Add time for stairs (~3 seconds per stair)
            base_time += (self.stairs_up + self.stairs_down) * 3

            self.estimated_time = base_time

    @property
    def total_stairs(self) -> int:
        return self.stairs_up + self.stairs_down

    def get_crowd_factor(self, time_window: str) -> float:
        """Get crowdedness factor for a given time window."""
        return self.crowd_patterns.get(time_window, 0.5)


class CampusGraph:
    """
    Main graph structure representing the entire campus.

    Wraps NetworkX DiGraph with campus-specific functionality.
    """

    def __init__(self, name: str = "SIUE Campus"):
        self.name = name
        self._graph = nx.DiGraph()
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[Tuple[str, str], Edge] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        self._graph.add_node(
            node.id,
            name=node.name,
            node_type=node.node_type.value,
            lat=node.lat,
            lon=node.lon,
            elevation=node.elevation,
            is_indoor=node.is_indoor,
        )

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        key = (edge.source_id, edge.target_id)
        self._edges[key] = edge

        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            distance=edge.distance,
            elevation_change=edge.elevation_change,
            stairs=edge.total_stairs,
            estimated_time=edge.estimated_time,
            is_covered=edge.is_covered,
            accessibility_score=edge.accessibility.mobility_score,
        )

        # Add reverse edge if bidirectional
        if edge.bidirectional:
            reverse_key = (edge.target_id, edge.source_id)
            reverse_edge = Edge(
                source_id=edge.target_id,
                target_id=edge.source_id,
                distance=edge.distance,
                elevation_change=-edge.elevation_change,
                stairs_up=edge.stairs_down,
                stairs_down=edge.stairs_up,
                has_ramp=edge.has_ramp,
                is_covered=edge.is_covered,
                surface_type=edge.surface_type,
                is_indoor=edge.is_indoor,
                bidirectional=False,  # Prevent infinite recursion
                accessibility=edge.accessibility,
                crowd_patterns=edge.crowd_patterns,
            )
            self._edges[reverse_key] = reverse_edge
            self._graph.add_edge(
                reverse_edge.source_id,
                reverse_edge.target_id,
                distance=reverse_edge.distance,
                elevation_change=reverse_edge.elevation_change,
                stairs=reverse_edge.total_stairs,
                estimated_time=reverse_edge.estimated_time,
                is_covered=reverse_edge.is_covered,
                accessibility_score=reverse_edge.accessibility.mobility_score,
            )

    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve a node by ID."""
        return self._nodes.get(node_id)

    def get_edge(self, source_id: str, target_id: str) -> Optional[Edge]:
        """Retrieve an edge by source and target IDs."""
        return self._edges.get((source_id, target_id))

    def get_neighbors(self, node_id: str) -> List[str]:
        """Get all neighboring node IDs."""
        return list(self._graph.successors(node_id))

    def get_all_nodes(self) -> List[Node]:
        """Get all nodes in the graph."""
        return list(self._nodes.values())

    def get_all_edges(self) -> List[Edge]:
        """Get all edges in the graph."""
        return list(self._edges.values())

    @property
    def networkx_graph(self) -> nx.DiGraph:
        """Access the underlying NetworkX graph."""
        return self._graph

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def __repr__(self) -> str:
        return f"CampusGraph(name='{self.name}', nodes={self.node_count}, edges={self.edge_count})"
