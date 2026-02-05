"""
Campus Graph Builder - Constructs enriched campus graph from various data sources.

This module handles:
1. Combining OSM network with manual annotations
2. Adding elevation data
3. Computing derived attributes (time estimates, accessibility)
4. Validating graph connectivity
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..models.graph_models import (
    Node,
    Edge,
    NodeType,
    SurfaceType,
    AccessibilityInfo,
    CampusGraph,
)
from ..models.time_models import CrowdPattern, DEFAULT_TIME_WINDOWS
from .osm_loader import OSMCampusLoader, SIUE_BUILDINGS


class CampusGraphBuilder:
    """
    Builds a complete campus graph from multiple data sources.

    This class orchestrates:
    1. Loading base network (OSM or synthetic)
    2. Adding manual annotations
    3. Enriching with elevation data
    4. Computing edge weights
    5. Validating the final graph

    Attributes:
        data_dir: Directory containing data files
        graph: The graph being built
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.graph: Optional[CampusGraph] = None

    def build(
        self,
        include_elevation: bool = True,
        validate: bool = True
    ) -> CampusGraph:
        """
        Build the complete campus graph.

        Args:
            include_elevation: Whether to fetch elevation data
            validate: Whether to validate graph connectivity

        Returns:
            Complete CampusGraph ready for routing
        """
        print("Building campus graph...")

        # Step 1: Load base graph
        self._load_base_graph()
        print(f"  Loaded {self.graph.node_count} nodes, {self.graph.edge_count} edges")

        # Step 2: Load manual annotations
        self._load_annotations()

        # Step 3: Add elevation data
        if include_elevation:
            self._add_elevation_data()

        # Step 4: Compute derived attributes
        self._compute_derived_attributes()

        # Step 5: Validate
        if validate:
            self._validate_graph()

        print(f"Graph built: {self.graph.node_count} nodes, {self.graph.edge_count} edges")
        return self.graph

    def _load_base_graph(self) -> None:
        """Load the base graph structure."""
        loader = OSMCampusLoader(cache_dir=self.data_dir / "cache")
        self.graph = loader.create_synthetic_campus()

    def _load_annotations(self) -> None:
        """Load manual annotations to enrich the graph."""
        annotations_file = self.data_dir / "annotations.json"

        if not annotations_file.exists():
            self._create_default_annotations(annotations_file)

        with open(annotations_file) as f:
            annotations = json.load(f)

        self._apply_node_annotations(annotations.get("nodes", {}))
        self._apply_edge_annotations(annotations.get("edges", {}))

    def _apply_node_annotations(self, node_annotations: Dict) -> None:
        """Apply annotations to nodes."""
        for node_id, attrs in node_annotations.items():
            node = self.graph.get_node(node_id)
            if not node:
                continue

            if "stairs_to_entrance" in attrs:
                node.metadata["stairs_to_entrance"] = attrs["stairs_to_entrance"]
            if "accessibility_notes" in attrs:
                node.accessibility.notes = attrs["accessibility_notes"]
            if "has_elevator" in attrs:
                node.accessibility.has_elevator = attrs["has_elevator"]

    def _apply_edge_annotations(self, edge_annotations: Dict) -> None:
        """Apply annotations to edges."""
        for edge_key, attrs in edge_annotations.items():
            parts = edge_key.split("->")
            if len(parts) != 2:
                continue

            source_id, target_id = parts
            edge = self.graph.get_edge(source_id, target_id)
            if not edge:
                continue

            if "stairs_up" in attrs:
                edge.stairs_up = attrs["stairs_up"]
            if "stairs_down" in attrs:
                edge.stairs_down = attrs["stairs_down"]
            if "is_covered" in attrs:
                edge.is_covered = attrs["is_covered"]
            if "has_ramp" in attrs:
                edge.has_ramp = attrs["has_ramp"]
            if "surface_type" in attrs:
                edge.surface_type = SurfaceType(attrs["surface_type"])

    def _create_default_annotations(self, filepath: Path) -> None:
        """Create default annotations file."""
        default_annotations = {
            "nodes": {
                "muc": {
                    "stairs_to_entrance": 0,
                    "has_elevator": True,
                    "accessibility_notes": "Main entrance is wheelchair accessible"
                },
                "library": {
                    "stairs_to_entrance": 5,
                    "has_elevator": True,
                    "accessibility_notes": "Accessible entrance on west side"
                },
                "peck_hall": {
                    "stairs_to_entrance": 3,
                    "has_elevator": True
                },
                "engineering": {
                    "stairs_to_entrance": 0,
                    "has_elevator": True,
                    "accessibility_notes": "Ground floor entrance accessible"
                },
            },
            "edges": {
                "muc->library": {
                    "is_covered": False,
                    "surface_type": "paved"
                },
                "library->peck_hall": {
                    "stairs_up": 3,
                    "is_covered": True,
                    "has_ramp": True
                },
                "muc->vadalabene_center": {
                    "is_covered": False,
                    "surface_type": "paved"
                }
            }
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(default_annotations, f, indent=2)

    def _add_elevation_data(self) -> None:
        """Add elevation data to nodes."""
        # For MVP, use approximate elevations
        # SIUE is on relatively flat terrain with some hills
        # Base elevation around 150-160m

        base_elevation = 155.0  # meters

        # Approximate elevation variations
        elevation_adjustments = {
            # Lower areas (near athletic facilities)
            "vadalabene_center": -5,
            "student_fitness": -5,
            "stadium": -8,
            # Higher areas (academic core)
            "library": 0,
            "muc": 0,
            "peck_hall": 2,
            "founders_hall": 3,
            "alumni_hall": 3,
            # Housing (mixed)
            "cougar_village": -2,
            "evergreen_hall": 0,
            "woodland_hall": 0,
        }

        for node in self.graph.get_all_nodes():
            adjustment = elevation_adjustments.get(node.id, 0)
            node.elevation = base_elevation + adjustment

        # Update edge elevation changes
        for edge in self.graph.get_all_edges():
            source = self.graph.get_node(edge.source_id)
            target = self.graph.get_node(edge.target_id)
            if source and target:
                edge.elevation_change = target.elevation - source.elevation

    def _compute_derived_attributes(self) -> None:
        """Compute derived attributes like time estimates."""
        for edge in self.graph.get_all_edges():
            edge.estimated_time = self._compute_edge_time(edge)
            self._compute_edge_accessibility(edge)

    def _compute_edge_time(self, edge: Edge) -> float:
        """
        Compute estimated traversal time for an edge.

        Considers distance, elevation, stairs, and surface type.
        """
        BASE_WALKING_SPEED = 1.4  # meters per second

        # Base time from distance
        time_seconds = edge.distance / BASE_WALKING_SPEED

        # Elevation penalty (Naismith's rule: 1 minute per 10m elevation gain)
        if edge.elevation_change > 0:
            time_seconds += (edge.elevation_change / 10) * 60

        # Stair time (3 seconds per stair)
        time_seconds += (edge.stairs_up + edge.stairs_down) * 3

        # Surface type multiplier
        surface_multipliers = {
            SurfaceType.PAVED: 1.0,
            SurfaceType.CONCRETE: 1.0,
            SurfaceType.BRICK: 1.05,
            SurfaceType.GRAVEL: 1.15,
            SurfaceType.GRASS: 1.25,
            SurfaceType.INDOOR: 0.95,
        }
        time_seconds *= surface_multipliers.get(edge.surface_type, 1.0)

        return time_seconds

    def _compute_edge_accessibility(self, edge: Edge) -> None:
        """Compute accessibility score and wheelchair accessibility for an edge."""
        score = 1.0

        # Penalty for stairs without ramps
        if edge.total_stairs > 0 and not edge.has_ramp:
            score -= 0.3

        # Additional penalty for many stairs
        if edge.total_stairs > 10:
            score -= 0.2

        # Penalty for steep elevation
        if edge.elevation_change > 5:
            score -= 0.1

        edge.accessibility.mobility_score = max(0.0, score)
        edge.accessibility.wheelchair_accessible = (
            edge.total_stairs == 0 or edge.has_ramp
        )

    def _validate_graph(self) -> None:
        """Validate graph structure and connectivity."""
        import networkx as nx

        G = self.graph.networkx_graph

        # Check connectivity
        if not nx.is_weakly_connected(G):
            components = list(nx.weakly_connected_components(G))
            print(f"  Warning: Graph has {len(components)} disconnected components")
            largest = max(components, key=len)
            print(f"  Largest component has {len(largest)} nodes")
        else:
            print("  Graph is fully connected")

        # Check for isolated nodes
        isolated = list(nx.isolates(G))
        if isolated:
            print(f"  Warning: {len(isolated)} isolated nodes: {isolated}")

        # Check for self-loops
        self_loops = list(nx.selfloop_edges(G))
        if self_loops:
            print(f"  Warning: {len(self_loops)} self-loops found")

    def save_graph(self, filepath: Path) -> None:
        """Save the graph to a JSON file."""
        if self.graph is None:
            raise ValueError("No graph to save. Call build() first.")

        data = {
            "name": self.graph.name,
            "nodes": [],
            "edges": [],
        }

        for node in self.graph.get_all_nodes():
            data["nodes"].append({
                "id": node.id,
                "name": node.name,
                "type": node.node_type.value,
                "lat": node.lat,
                "lon": node.lon,
                "elevation": node.elevation,
                "is_indoor": node.is_indoor,
                "building_id": node.building_id,
                "accessibility": {
                    "wheelchair_accessible": node.accessibility.wheelchair_accessible,
                    "has_elevator": node.accessibility.has_elevator,
                    "mobility_score": node.accessibility.mobility_score,
                    "notes": node.accessibility.notes,
                },
                "metadata": node.metadata,
            })

        for edge in self.graph.get_all_edges():
            data["edges"].append({
                "source": edge.source_id,
                "target": edge.target_id,
                "distance": edge.distance,
                "elevation_change": edge.elevation_change,
                "stairs_up": edge.stairs_up,
                "stairs_down": edge.stairs_down,
                "has_ramp": edge.has_ramp,
                "is_covered": edge.is_covered,
                "surface_type": edge.surface_type.value,
                "is_indoor": edge.is_indoor,
                "estimated_time": edge.estimated_time,
                "accessibility_score": edge.accessibility.mobility_score,
                "crowd_patterns": edge.crowd_patterns,
            })

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Graph saved to {filepath}")

    @classmethod
    def load_graph(cls, filepath: Path) -> CampusGraph:
        """Load a graph from a JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        graph = CampusGraph(name=data.get("name", "Loaded Campus"))

        # Load nodes
        for node_data in data["nodes"]:
            accessibility = AccessibilityInfo(
                wheelchair_accessible=node_data["accessibility"]["wheelchair_accessible"],
                has_elevator=node_data["accessibility"].get("has_elevator", True),
                mobility_score=node_data["accessibility"]["mobility_score"],
                notes=node_data["accessibility"].get("notes", ""),
            )

            node = Node(
                id=node_data["id"],
                name=node_data["name"],
                node_type=NodeType(node_data["type"]),
                coordinates=(node_data["lat"], node_data["lon"]),
                elevation=node_data.get("elevation", 0),
                is_indoor=node_data.get("is_indoor", False),
                building_id=node_data.get("building_id"),
                accessibility=accessibility,
                metadata=node_data.get("metadata", {}),
            )
            graph.add_node(node)

        # Load edges
        for edge_data in data["edges"]:
            accessibility = AccessibilityInfo(
                wheelchair_accessible=edge_data.get("has_ramp", True) or edge_data.get("stairs_up", 0) == 0,
                mobility_score=edge_data.get("accessibility_score", 1.0),
            )

            edge = Edge(
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                distance=edge_data["distance"],
                elevation_change=edge_data.get("elevation_change", 0),
                stairs_up=edge_data.get("stairs_up", 0),
                stairs_down=edge_data.get("stairs_down", 0),
                has_ramp=edge_data.get("has_ramp", True),
                is_covered=edge_data.get("is_covered", False),
                surface_type=SurfaceType(edge_data.get("surface_type", "paved")),
                is_indoor=edge_data.get("is_indoor", False),
                bidirectional=False,  # Already expanded in save
                accessibility=accessibility,
                crowd_patterns=edge_data.get("crowd_patterns", {}),
                estimated_time=edge_data.get("estimated_time", 0),
            )
            graph.add_edge(edge)

        return graph
