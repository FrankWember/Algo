"""
SIUE Campus Graph Data

Loads real building data from buildings.json (57 buildings with GPS coordinates
collected from Google Earth Pro). Edges are auto-generated based on proximity
using a Haversine distance threshold with full-connectivity bridging.

Data source: buildings.json — 57 SIUE buildings with lat/lon, elevation,
             building code, and category.
"""

import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Building:
    """Represents a campus building or location node."""
    id: str
    name: str
    short_name: str
    x: float          # Normalized 0-100 for SVG visualization (west=0, east=100)
    y: float          # Normalized 0-100 for SVG visualization (north=0, south=100)
    building_type: str  # See CATEGORY_MAP values below
    latitude: float   # Real GPS latitude (WGS-84)
    longitude: float  # Real GPS longitude (WGS-84)
    elevation: float  # Elevation in meters above sea level


@dataclass
class Edge:
    """Represents a walkway or road between two buildings."""
    source: str
    target: str
    weight: float   # Estimated walking distance in meters
    path_type: str  # 'walkway' or 'road'


# ---------------------------------------------------------------------------
# Category mapping: buildings.json → frontend display type
# ---------------------------------------------------------------------------

CATEGORY_MAP: Dict[str, str] = {
    "academic": "academic",
    "research": "research",
    "residence": "residential",
    "recreation": "recreation",
    "student_services": "academic",   # MUC / ECC grouped with academic
    "facility": "other",
    "landmark": "other",
    "parking": "parking",
    "other": "other",
}


# ---------------------------------------------------------------------------
# Distance utility
# ---------------------------------------------------------------------------

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Geodesic distance in meters between two GPS coordinates."""
    R = 6_371_000  # Earth radius, metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def calculate_distance(b1: Building, b2: Building) -> float:
    """Real-world Haversine distance between two buildings (metres, rounded)."""
    return round(_haversine(b1.latitude, b1.longitude, b2.latitude, b2.longitude), 1)


# ---------------------------------------------------------------------------
# Building loader
# ---------------------------------------------------------------------------

def _load_buildings() -> Dict[str, Building]:
    """
    Parse buildings.json, normalize GPS coordinates to a 0-100 visualization
    grid, and return a dict keyed by building ID.

    Normalization:
      x = 0 → westmost building,  x = 100 → eastmost building
      y = 0 → northmost building, y = 100 → southmost building
      (5% padding on each axis so no building sits right on the SVG border)
    """
    data_path = Path(__file__).parent.parent / "buildings.json"
    with open(data_path, "r") as fh:
        raw_buildings = json.load(fh)["buildings"]

    lats = [b["latitude"] for b in raw_buildings]
    lons = [b["longitude"] for b in raw_buildings]

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    # 5% border padding
    lat_pad = (lat_max - lat_min) * 0.05
    lon_pad = (lon_max - lon_min) * 0.05
    lat_min -= lat_pad
    lat_max += lat_pad
    lon_min -= lon_pad
    lon_max += lon_pad

    buildings: Dict[str, Building] = {}
    for b in raw_buildings:
        x = round((b["longitude"] - lon_min) / (lon_max - lon_min) * 100, 2)
        y = round((lat_max - b["latitude"]) / (lat_max - lat_min) * 100, 2)

        code = b.get("building_code") or ""
        short_name = code if code else b["id"][:8].upper()

        buildings[b["id"]] = Building(
            id=b["id"],
            name=b["name"],
            short_name=short_name,
            x=x,
            y=y,
            building_type=CATEGORY_MAP.get(b.get("category", "other"), "other"),
            latitude=b["latitude"],
            longitude=b["longitude"],
            elevation=b.get("elevation_meters", 0.0),
        )

    return buildings


# ---------------------------------------------------------------------------
# Connectivity helpers
# ---------------------------------------------------------------------------

def _bfs_components(
    node_ids: List[str], adj: Dict[str, List[str]]
) -> List[List[str]]:
    """Return list of connected components via BFS."""
    visited: set = set()
    components: List[List[str]] = []
    for nid in node_ids:
        if nid not in visited:
            comp: List[str] = []
            queue: deque = deque([nid])
            visited.add(nid)
            while queue:
                cur = queue.popleft()
                comp.append(cur)
                for nb in adj.get(cur, []):
                    if nb not in visited:
                        visited.add(nb)
                        queue.append(nb)
            components.append(comp)
    return components


# ---------------------------------------------------------------------------
# Edge generator
# ---------------------------------------------------------------------------

def _generate_edges(buildings: Dict[str, Building]) -> List[Edge]:
    """
    Auto-generate campus edges using a two-phase strategy:

    Phase 1 — Proximity:
      Connect every pair of buildings within THRESHOLD metres.
      Parking-to-parking connections use a tighter limit.
      Each building is capped at MAX_PER_NODE edges to keep the graph sparse.

    Phase 2 — Connectivity bridging:
      Run BFS to detect disconnected components (e.g. remote buildings like the
      Physics Observatory). Repeatedly add the shortest cross-component edge
      until the graph is fully connected.

    Edge weights:
      Roads (any parking endpoint) get a 10% penalty over raw distance to
      reflect that driving/walking along roads is less direct than footpaths.
    """
    THRESHOLD = 600       # metres — comfortable campus walking distance
    PARKING_THRESHOLD = 350   # tighter limit for parking-to-parking edges
    MAX_PER_NODE = 6      # maximum edges per node to keep graph readable

    b_list = list(buildings.values())

    # Pre-compute all pairwise distances (O(n²), fine for n=57)
    dist_cache: Dict[Tuple[str, str], float] = {}
    for i, b1 in enumerate(b_list):
        for j in range(i + 1, len(b_list)):
            b2 = b_list[j]
            d = _haversine(b1.latitude, b1.longitude, b2.latitude, b2.longitude)
            dist_cache[(b1.id, b2.id)] = d

    def get_dist(id1: str, id2: str) -> float:
        key = (id1, id2) if (id1, id2) in dist_cache else (id2, id1)
        return dist_cache.get(key, math.inf)

    # Sort all pairs by ascending distance for greedy selection
    sorted_pairs = sorted(dist_cache.items(), key=lambda kv: kv[1])

    edge_set: set = set()
    connection_count: Dict[str, int] = defaultdict(int)
    edges: List[Edge] = []

    def _add_edge(id1: str, id2: str, dist: float) -> None:
        b1, b2 = buildings[id1], buildings[id2]
        is_road = b1.building_type == "parking" or b2.building_type == "parking"
        path_type = "road" if is_road else "walkway"
        weight = round(dist * (1.1 if is_road else 1.0), 1)
        edges.append(Edge(id1, id2, weight, path_type))
        edge_set.add((id1, id2))
        connection_count[id1] += 1
        connection_count[id2] += 1

    # --- Phase 1: proximity-based edges ---
    for (id1, id2), dist in sorted_pairs:
        if dist > THRESHOLD:
            break  # Already sorted; all remaining pairs exceed threshold

        b1, b2 = buildings[id1], buildings[id2]

        # Extra restriction: parking ↔ parking needs tighter radius
        if (b1.building_type == "parking" and b2.building_type == "parking"
                and dist > PARKING_THRESHOLD):
            continue

        # Respect per-node degree cap
        if connection_count[id1] >= MAX_PER_NODE or connection_count[id2] >= MAX_PER_NODE:
            continue

        _add_edge(id1, id2, dist)

    # --- Phase 2: bridge disconnected components ---
    adj_simple: Dict[str, List[str]] = defaultdict(list)
    for e in edges:
        adj_simple[e.source].append(e.target)
        adj_simple[e.target].append(e.source)

    all_ids = [b.id for b in b_list]
    components = _bfs_components(all_ids, adj_simple)

    while len(components) > 1:
        best_dist = math.inf
        best_pair: Tuple[str, str, float] | None = None

        comp_sets = [set(c) for c in components]
        # Find the cheapest cross-component edge
        for ci, ca in enumerate(comp_sets):
            for cj in range(ci + 1, len(comp_sets)):
                cb = comp_sets[cj]
                for a in ca:
                    for b_id in cb:
                        d = get_dist(a, b_id)
                        if d < best_dist:
                            best_dist = d
                            best_pair = (a, b_id, d)

        if best_pair is None:
            break  # Shouldn't happen with a complete distance cache

        a, b_id, d = best_pair
        _add_edge(a, b_id, d)
        adj_simple[a].append(b_id)
        adj_simple[b_id].append(a)
        components = _bfs_components(all_ids, adj_simple)

    return edges


# ---------------------------------------------------------------------------
# Module-level singletons (loaded once at import time)
# ---------------------------------------------------------------------------

BUILDINGS: Dict[str, Building] = _load_buildings()
EDGES: List[Edge] = _generate_edges(BUILDINGS)


# ---------------------------------------------------------------------------
# Public API (consumed by main.py and algorithms.py)
# ---------------------------------------------------------------------------

def get_graph_data() -> Dict[str, Any]:
    """Return graph nodes and edges in the format expected by the frontend."""
    nodes = [
        {
            "id": b.id,
            "name": b.name,
            "shortName": b.short_name,
            "x": b.x,
            "y": b.y,
            "type": b.building_type,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "elevation": b.elevation,
        }
        for b in BUILDINGS.values()
    ]
    edges_out = [
        {
            "source": e.source,
            "target": e.target,
            "weight": e.weight,
            "pathType": e.path_type,
        }
        for e in EDGES
    ]
    return {"nodes": nodes, "edges": edges_out}


def get_adjacency_list() -> Dict[str, List[Tuple[str, float]]]:
    """Bidirectional adjacency list used by all three pathfinding algorithms."""
    adj: Dict[str, List[Tuple[str, float]]] = {bid: [] for bid in BUILDINGS}
    for edge in EDGES:
        adj[edge.source].append((edge.target, edge.weight))
        adj[edge.target].append((edge.source, edge.weight))
    return adj


# Building categories for the /api/buildings/categories endpoint
BUILDING_CATEGORIES: Dict[str, List[str]] = {
    cat: [b.id for b in BUILDINGS.values() if b.building_type == cat]
    for cat in {b.building_type for b in BUILDINGS.values()}
}
