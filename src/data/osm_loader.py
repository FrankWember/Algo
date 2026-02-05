"""
OpenStreetMap data loader for SIUE campus.

This module handles fetching and processing OSM data to create
the campus walking network graph.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import osmnx as ox
    import networkx as nx
    import geopandas as gpd
    from shapely.geometry import Point, Polygon
    HAS_OSMNX = True
except ImportError:
    HAS_OSMNX = False

from ..models.graph_models import (
    Node,
    Edge,
    NodeType,
    SurfaceType,
    AccessibilityInfo,
    CampusGraph,
)


# SIUE Campus bounding coordinates
SIUE_BOUNDS = {
    "north": 38.8050,
    "south": 38.7850,
    "east": -89.9850,
    "west": -90.0100,
    "center_lat": 38.7945,
    "center_lon": -89.9975,
}

# Known SIUE buildings with approximate coordinates
SIUE_BUILDINGS = {
    "muc": {
        "name": "Morris University Center",
        "lat": 38.7940,
        "lon": -89.9980,
        "type": "building",
        "has_dining": True,
    },
    "library": {
        "name": "Lovejoy Library",
        "lat": 38.7935,
        "lon": -89.9960,
        "type": "building",
    },
    "peck_hall": {
        "name": "Peck Hall",
        "lat": 38.7938,
        "lon": -89.9945,
        "type": "building",
    },
    "founders_hall": {
        "name": "Founders Hall",
        "lat": 38.7948,
        "lon": -89.9955,
        "type": "building",
    },
    "alumni_hall": {
        "name": "Alumni Hall",
        "lat": 38.7952,
        "lon": -89.9948,
        "type": "building",
    },
    "rendleman_hall": {
        "name": "Rendleman Hall",
        "lat": 38.7932,
        "lon": -89.9975,
        "type": "building",
        "is_admin": True,
    },
    "engineering": {
        "name": "Engineering Building",
        "lat": 38.7925,
        "lon": -89.9940,
        "type": "building",
    },
    "science_west": {
        "name": "Science Building West",
        "lat": 38.7922,
        "lon": -89.9955,
        "type": "building",
    },
    "science_east": {
        "name": "Science Building East",
        "lat": 38.7920,
        "lon": -89.9935,
        "type": "building",
    },
    "art_design": {
        "name": "Art & Design Building",
        "lat": 38.7958,
        "lon": -89.9970,
        "type": "building",
    },
    "dunham_hall": {
        "name": "Dunham Hall",
        "lat": 38.7962,
        "lon": -89.9960,
        "type": "building",
    },
    "vadalabene_center": {
        "name": "Vadalabene Center",
        "lat": 38.7910,
        "lon": -89.9990,
        "type": "building",
        "is_gym": True,
    },
    "student_fitness": {
        "name": "Student Fitness Center",
        "lat": 38.7905,
        "lon": -89.9985,
        "type": "building",
        "is_gym": True,
    },
    "stadium": {
        "name": "Korte Stadium",
        "lat": 38.7895,
        "lon": -90.0010,
        "type": "landmark",
    },
    "cougar_village": {
        "name": "Cougar Village",
        "lat": 38.7980,
        "lon": -89.9920,
        "type": "housing",
    },
    "evergreen_hall": {
        "name": "Evergreen Hall",
        "lat": 38.7990,
        "lon": -89.9950,
        "type": "housing",
    },
    "woodland_hall": {
        "name": "Woodland Hall",
        "lat": 38.7985,
        "lon": -89.9935,
        "type": "housing",
    },
    "prairie_hall": {
        "name": "Prairie Hall",
        "lat": 38.7988,
        "lon": -89.9960,
        "type": "housing",
    },
    "bluff_hall": {
        "name": "Bluff Hall",
        "lat": 38.7992,
        "lon": -89.9970,
        "type": "housing",
    },
    "lot_a": {
        "name": "Parking Lot A",
        "lat": 38.7915,
        "lon": -89.9920,
        "type": "parking",
    },
    "lot_b": {
        "name": "Parking Lot B",
        "lat": 38.7970,
        "lon": -89.9990,
        "type": "parking",
    },
    "lot_e": {
        "name": "Parking Lot E",
        "lat": 38.7960,
        "lon": -90.0020,
        "type": "parking",
    },
    "bus_circle": {
        "name": "Bus Circle",
        "lat": 38.7942,
        "lon": -89.9995,
        "type": "bus_stop",
    },
}


class OSMCampusLoader:
    """
    Loads and processes OpenStreetMap data for the SIUE campus.

    This class handles:
    1. Fetching walkable network from OSM
    2. Identifying buildings and points of interest
    3. Creating initial graph structure

    Attributes:
        bounds: Campus bounding box
        cache_dir: Directory for caching downloaded data
    """

    def __init__(
        self,
        bounds: Optional[Dict] = None,
        cache_dir: Optional[Path] = None
    ):
        self.bounds = bounds or SIUE_BOUNDS
        self.cache_dir = cache_dir or Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_walk_network(self) -> Optional[Any]:
        """
        Load the walkable network from OSM.

        Returns:
            NetworkX graph of walkable paths, or None if OSMnx not available
        """
        if not HAS_OSMNX:
            print("Warning: osmnx not installed. Using fallback data.")
            return None

        cache_file = self.cache_dir / "siue_walk_network.graphml"

        if cache_file.exists():
            print(f"Loading cached network from {cache_file}")
            return ox.load_graphml(cache_file)

        print("Downloading walk network from OpenStreetMap...")
        try:
            # Create bounding box
            G = ox.graph_from_bbox(
                north=self.bounds["north"],
                south=self.bounds["south"],
                east=self.bounds["east"],
                west=self.bounds["west"],
                network_type="walk",
                simplify=True,
            )

            # Save to cache
            ox.save_graphml(G, cache_file)
            print(f"Saved network to {cache_file}")

            return G

        except Exception as e:
            print(f"Error loading OSM data: {e}")
            return None

    def load_buildings(self) -> Optional[Any]:
        """
        Load building footprints from OSM.

        Returns:
            GeoDataFrame of buildings, or None if not available
        """
        if not HAS_OSMNX:
            return None

        cache_file = self.cache_dir / "siue_buildings.geojson"

        if cache_file.exists():
            return gpd.read_file(cache_file)

        try:
            tags = {"building": True}
            buildings = ox.features_from_bbox(
                north=self.bounds["north"],
                south=self.bounds["south"],
                east=self.bounds["east"],
                west=self.bounds["west"],
                tags=tags,
            )

            if len(buildings) > 0:
                buildings.to_file(cache_file, driver="GeoJSON")

            return buildings

        except Exception as e:
            print(f"Error loading buildings: {e}")
            return None

    def get_known_buildings(self) -> Dict[str, Dict]:
        """Get the manually curated list of SIUE buildings."""
        return SIUE_BUILDINGS.copy()

    def create_synthetic_campus(self) -> CampusGraph:
        """
        Create a synthetic campus graph when OSM data is unavailable.

        This provides a working graph for development and testing
        based on known SIUE building locations.

        Returns:
            CampusGraph with nodes and edges
        """
        graph = CampusGraph(name="SIUE Campus (Synthetic)")

        # Add all known buildings as nodes
        for building_id, info in SIUE_BUILDINGS.items():
            node_type = self._get_node_type(info.get("type", "building"))

            node = Node(
                id=building_id,
                name=info["name"],
                node_type=node_type,
                coordinates=(info["lat"], info["lon"]),
                elevation=150.0,  # Approximate elevation in meters
                is_indoor=False,
                building_id=building_id if node_type == NodeType.BUILDING else None,
            )
            graph.add_node(node)

        # Create edges between nearby buildings
        self._add_synthetic_edges(graph)

        return graph

    def _get_node_type(self, type_str: str) -> NodeType:
        """Convert string type to NodeType enum."""
        type_map = {
            "building": NodeType.BUILDING,
            "housing": NodeType.BUILDING,
            "parking": NodeType.PARKING_LOT,
            "bus_stop": NodeType.BUS_STOP,
            "landmark": NodeType.LANDMARK,
        }
        return type_map.get(type_str, NodeType.BUILDING)

    def _add_synthetic_edges(self, graph: CampusGraph) -> None:
        """Add edges between buildings based on proximity and logical connections."""
        from geopy.distance import geodesic

        nodes = graph.get_all_nodes()

        # Define logical connections (paths that should exist)
        connections = [
            # Academic core connections
            ("muc", "library"),
            ("library", "peck_hall"),
            ("peck_hall", "founders_hall"),
            ("founders_hall", "alumni_hall"),
            ("muc", "rendleman_hall"),
            ("rendleman_hall", "science_west"),
            ("science_west", "science_east"),
            ("science_east", "engineering"),
            ("engineering", "peck_hall"),
            ("muc", "art_design"),
            ("art_design", "dunham_hall"),

            # Athletic area
            ("muc", "vadalabene_center"),
            ("vadalabene_center", "student_fitness"),
            ("student_fitness", "stadium"),

            # Housing connections
            ("muc", "bus_circle"),
            ("bus_circle", "cougar_village"),
            ("cougar_village", "evergreen_hall"),
            ("evergreen_hall", "woodland_hall"),
            ("woodland_hall", "prairie_hall"),
            ("prairie_hall", "bluff_hall"),
            ("bluff_hall", "lot_b"),

            # Parking connections
            ("engineering", "lot_a"),
            ("art_design", "lot_e"),
            ("lot_b", "muc"),
            ("lot_e", "muc"),

            # Bus stop connections
            ("bus_circle", "evergreen_hall"),
            ("bus_circle", "lot_b"),
        ]

        # Add edges for each connection
        for source_id, target_id in connections:
            source = graph.get_node(source_id)
            target = graph.get_node(target_id)

            if source is None or target is None:
                continue

            # Calculate distance
            distance = geodesic(source.coordinates, target.coordinates).meters

            # Estimate elevation change (simplified)
            elevation_change = 0.0

            # Create edge
            edge = Edge(
                source_id=source_id,
                target_id=target_id,
                distance=distance,
                elevation_change=elevation_change,
                stairs_up=0,
                stairs_down=0,
                has_ramp=True,
                is_covered=False,
                surface_type=SurfaceType.PAVED,
                is_indoor=False,
                bidirectional=True,
                crowd_patterns=self._generate_crowd_patterns(source_id, target_id),
            )
            graph.add_edge(edge)

    def _generate_crowd_patterns(
        self,
        source_id: str,
        target_id: str
    ) -> Dict[str, float]:
        """Generate synthetic crowd patterns for an edge."""
        # Default patterns
        patterns = {
            "early_morning": 0.1,
            "morning_rush": 0.6,
            "mid_morning": 0.4,
            "lunch_rush": 0.5,
            "early_afternoon": 0.5,
            "late_afternoon": 0.4,
            "evening_rush": 0.3,
            "evening": 0.1,
            "night": 0.05,
        }

        # Adjust based on locations
        dining_adjacent = source_id == "muc" or target_id == "muc"
        housing_adjacent = any(
            x in [source_id, target_id]
            for x in ["cougar_village", "evergreen_hall", "woodland_hall", "prairie_hall", "bluff_hall"]
        )

        if dining_adjacent:
            patterns["lunch_rush"] = 0.9
            patterns["morning_rush"] = 0.7

        if housing_adjacent:
            patterns["morning_rush"] = 0.8
            patterns["evening_rush"] = 0.7

        return patterns


def load_or_create_campus_graph(
    use_osm: bool = True,
    cache_dir: Optional[Path] = None
) -> CampusGraph:
    """
    Convenience function to load campus graph.

    Tries OSM first, falls back to synthetic data.

    Args:
        use_osm: Whether to attempt loading from OSM
        cache_dir: Cache directory for OSM data

    Returns:
        CampusGraph ready for routing
    """
    loader = OSMCampusLoader(cache_dir=cache_dir)

    if use_osm and HAS_OSMNX:
        osm_graph = loader.load_walk_network()
        if osm_graph is not None:
            # Convert OSM graph to CampusGraph
            # (This would need more implementation)
            pass

    # Fall back to synthetic
    print("Using synthetic campus graph...")
    return loader.create_synthetic_campus()
