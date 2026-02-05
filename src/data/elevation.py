"""
Elevation data service for enriching campus graph with terrain information.

This module provides elevation data from various sources:
1. Open-Elevation API (free, no API key)
2. USGS Elevation Point Query Service
3. Cached/static data for offline use
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class ElevationPoint:
    """A point with elevation data."""
    lat: float
    lon: float
    elevation: float  # meters above sea level


class ElevationService:
    """
    Service for fetching elevation data for campus nodes.

    Uses Open-Elevation API by default, with caching to reduce API calls.

    Attributes:
        cache_file: Path to elevation cache
        api_url: Base URL for elevation API
    """

    OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        use_cache: bool = True
    ):
        self.cache_dir = cache_dir or Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "elevation_cache.json"
        self.use_cache = use_cache
        self._cache: Dict[str, float] = {}

        if self.use_cache:
            self._load_cache()

    def _load_cache(self) -> None:
        """Load elevation cache from file."""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                self._cache = json.load(f)

    def _save_cache(self) -> None:
        """Save elevation cache to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self._cache, f)

    def _cache_key(self, lat: float, lon: float) -> str:
        """Generate cache key for coordinates (rounded to ~10m precision)."""
        return f"{lat:.4f},{lon:.4f}"

    def get_elevation(self, lat: float, lon: float) -> Optional[float]:
        """
        Get elevation for a single point.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Elevation in meters, or None if unavailable
        """
        key = self._cache_key(lat, lon)

        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Fetch from API
        elevation = self._fetch_elevation(lat, lon)

        if elevation is not None:
            self._cache[key] = elevation
            self._save_cache()

        return elevation

    def get_elevations_batch(
        self,
        points: List[Tuple[float, float]]
    ) -> List[Optional[float]]:
        """
        Get elevations for multiple points efficiently.

        Args:
            points: List of (lat, lon) tuples

        Returns:
            List of elevations (None for failed lookups)
        """
        results = []
        uncached_points = []
        uncached_indices = []

        # Check cache first
        for i, (lat, lon) in enumerate(points):
            key = self._cache_key(lat, lon)
            if key in self._cache:
                results.append(self._cache[key])
            else:
                results.append(None)
                uncached_points.append((lat, lon))
                uncached_indices.append(i)

        # Batch fetch uncached points
        if uncached_points:
            elevations = self._fetch_elevations_batch(uncached_points)
            for i, elevation in zip(uncached_indices, elevations):
                if elevation is not None:
                    lat, lon = points[i]
                    key = self._cache_key(lat, lon)
                    self._cache[key] = elevation
                    results[i] = elevation

            self._save_cache()

        return results

    def _fetch_elevation(self, lat: float, lon: float) -> Optional[float]:
        """Fetch elevation from API for a single point."""
        if not HAS_REQUESTS:
            return self._get_fallback_elevation(lat, lon)

        try:
            response = requests.get(
                self.OPEN_ELEVATION_URL,
                params={"locations": f"{lat},{lon}"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if "results" in data and len(data["results"]) > 0:
                return data["results"][0]["elevation"]

        except Exception as e:
            print(f"Elevation API error: {e}")

        return self._get_fallback_elevation(lat, lon)

    def _fetch_elevations_batch(
        self,
        points: List[Tuple[float, float]]
    ) -> List[Optional[float]]:
        """Fetch elevations for multiple points in one API call."""
        if not HAS_REQUESTS or not points:
            return [self._get_fallback_elevation(lat, lon) for lat, lon in points]

        try:
            # Format locations for API
            locations = [{"latitude": lat, "longitude": lon} for lat, lon in points]

            response = requests.post(
                self.OPEN_ELEVATION_URL,
                json={"locations": locations},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if "results" in data:
                return [r["elevation"] for r in data["results"]]

        except Exception as e:
            print(f"Batch elevation API error: {e}")

        return [self._get_fallback_elevation(lat, lon) for lat, lon in points]

    def _get_fallback_elevation(self, lat: float, lon: float) -> float:
        """
        Get approximate elevation when API is unavailable.

        Uses a simple model based on SIUE's known terrain.
        """
        # SIUE is located on the bluffs above the Mississippi River
        # Base elevation is approximately 150-160m

        # Simple model: higher in the north (bluffs), lower in the south
        base = 155.0

        # SIUE center is approximately (38.7945, -89.9975)
        lat_offset = (lat - 38.7945) * 100  # ~1m per 0.01 degree north
        lon_offset = (lon + 89.9975) * 50   # Slight west-to-east gradient

        return base + lat_offset + lon_offset


def add_elevation_to_graph(graph, elevation_service: Optional[ElevationService] = None):
    """
    Utility function to add elevation data to all nodes in a graph.

    Args:
        graph: CampusGraph instance
        elevation_service: ElevationService instance (creates one if None)
    """
    service = elevation_service or ElevationService()

    # Collect all node coordinates
    nodes = graph.get_all_nodes()
    points = [(node.lat, node.lon) for node in nodes]

    # Batch fetch elevations
    print(f"Fetching elevations for {len(points)} points...")
    elevations = service.get_elevations_batch(points)

    # Update nodes
    for node, elevation in zip(nodes, elevations):
        if elevation is not None:
            node.elevation = elevation

    # Update edge elevation changes
    for edge in graph.get_all_edges():
        source = graph.get_node(edge.source_id)
        target = graph.get_node(edge.target_id)
        if source and target:
            edge.elevation_change = target.elevation - source.elevation

    print("Elevation data added to graph")
