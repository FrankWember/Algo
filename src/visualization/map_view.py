"""
Map visualization using Folium.

Creates interactive maps showing:
- Campus locations
- Computed routes
- Heat maps of crowdedness
"""

from typing import List, Optional, Tuple
from pathlib import Path

try:
    import folium
    from folium import plugins
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

from ..models.graph_models import CampusGraph, Node, NodeType
from ..models.route_models import Route


# Color scheme
COLORS = {
    "route_primary": "#2563eb",      # Blue
    "route_alternative": "#64748b",  # Gray
    "building": "#059669",           # Green
    "parking": "#7c3aed",            # Purple
    "bus_stop": "#dc2626",           # Red
    "housing": "#ea580c",            # Orange
    "landmark": "#0891b2",           # Cyan
    "start": "#22c55e",              # Green
    "end": "#ef4444",                # Red
}

# SIUE campus center
SIUE_CENTER = (38.7945, -89.9975)
DEFAULT_ZOOM = 16


def create_map(
    center: Optional[Tuple[float, float]] = None,
    zoom: int = DEFAULT_ZOOM,
    tiles: str = "cartodbpositron"
) -> "folium.Map":
    """
    Create a base map centered on campus.

    Args:
        center: (lat, lon) center point
        zoom: Initial zoom level
        tiles: Map tile style

    Returns:
        Folium Map object
    """
    if not HAS_FOLIUM:
        raise ImportError("Folium is required for visualization. Install with: pip install folium")

    center = center or SIUE_CENTER

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=tiles,
    )

    return m


def add_locations_to_map(
    m: "folium.Map",
    graph: CampusGraph,
    show_labels: bool = True,
    cluster: bool = False
) -> "folium.Map":
    """
    Add all campus locations to the map.

    Args:
        m: Folium map
        graph: Campus graph with nodes
        show_labels: Whether to show location names
        cluster: Whether to cluster markers

    Returns:
        Modified map
    """
    if not HAS_FOLIUM:
        return m

    # Create feature group for locations
    if cluster:
        location_group = plugins.MarkerCluster(name="Locations")
    else:
        location_group = folium.FeatureGroup(name="Locations")

    for node in graph.get_all_nodes():
        color = _get_node_color(node.node_type)
        icon = _get_node_icon(node.node_type)

        popup_html = f"""
        <div style="min-width: 150px;">
            <b>{node.name}</b><br>
            Type: {node.node_type.value}<br>
            Elevation: {node.elevation:.1f}m
        </div>
        """

        marker = folium.Marker(
            location=(node.lat, node.lon),
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=node.name if show_labels else None,
            icon=folium.Icon(color=color, icon=icon, prefix="fa"),
        )
        marker.add_to(location_group)

    location_group.add_to(m)

    return m


def add_route_to_map(
    m: "folium.Map",
    route: Route,
    graph: CampusGraph,
    color: Optional[str] = None,
    weight: int = 5,
    show_markers: bool = True,
    label: Optional[str] = None
) -> "folium.Map":
    """
    Add a computed route to the map.

    Args:
        m: Folium map
        route: Route to display
        graph: Campus graph for node coordinates
        color: Line color (default: primary blue)
        weight: Line weight
        show_markers: Whether to show start/end markers
        label: Optional label for the route

    Returns:
        Modified map
    """
    if not HAS_FOLIUM:
        return m

    color = color or COLORS["route_primary"]

    # Get coordinates for route path
    coordinates = []
    for node_id in route.node_path:
        node = graph.get_node(node_id)
        if node:
            coordinates.append((node.lat, node.lon))

    if not coordinates:
        return m

    # Create route group
    route_name = label or f"Route (Rank {route.rank})"
    route_group = folium.FeatureGroup(name=route_name)

    # Add route line
    route_line = folium.PolyLine(
        coordinates,
        color=color,
        weight=weight,
        opacity=0.8,
        tooltip=route.summary(),
    )
    route_line.add_to(route_group)

    # Add start and end markers
    if show_markers and len(coordinates) >= 2:
        # Start marker
        start_node = graph.get_node(route.origin_id)
        if start_node:
            start_marker = folium.Marker(
                location=(start_node.lat, start_node.lon),
                popup=f"Start: {start_node.name}",
                icon=folium.Icon(color="green", icon="play", prefix="fa"),
            )
            start_marker.add_to(route_group)

        # End marker
        end_node = graph.get_node(route.destination_id)
        if end_node:
            end_marker = folium.Marker(
                location=(end_node.lat, end_node.lon),
                popup=f"End: {end_node.name}",
                icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
            )
            end_marker.add_to(route_group)

    route_group.add_to(m)

    return m


def add_multiple_routes_to_map(
    m: "folium.Map",
    routes: List[Route],
    graph: CampusGraph
) -> "folium.Map":
    """
    Add multiple routes with different colors.

    Args:
        m: Folium map
        routes: List of routes
        graph: Campus graph

    Returns:
        Modified map
    """
    colors = [
        COLORS["route_primary"],
        "#f59e0b",  # Amber
        "#8b5cf6",  # Violet
        "#ec4899",  # Pink
        "#14b8a6",  # Teal
    ]

    for i, route in enumerate(routes):
        color = colors[i % len(colors)]
        weight = 6 - i  # Thicker for higher-ranked routes
        label = f"Route {i+1}: {route.summary()}"

        add_route_to_map(
            m, route, graph,
            color=color,
            weight=max(3, weight),
            show_markers=(i == 0),  # Only show markers for best route
            label=label
        )

    return m


def add_crowd_heatmap(
    m: "folium.Map",
    graph: CampusGraph,
    time_window: str = "lunch_rush"
) -> "folium.Map":
    """
    Add a heatmap showing crowdedness.

    Args:
        m: Folium map
        graph: Campus graph
        time_window: Time window for crowd data

    Returns:
        Modified map
    """
    if not HAS_FOLIUM:
        return m

    heat_data = []

    for edge in graph.get_all_edges():
        source = graph.get_node(edge.source_id)
        target = graph.get_node(edge.target_id)

        if source and target:
            # Get midpoint
            mid_lat = (source.lat + target.lat) / 2
            mid_lon = (source.lon + target.lon) / 2

            # Get crowdedness
            crowd = edge.get_crowd_factor(time_window)

            # Add to heat data (lat, lon, intensity)
            heat_data.append([mid_lat, mid_lon, crowd])

    if heat_data:
        heat_layer = plugins.HeatMap(
            heat_data,
            name="Crowdedness",
            min_opacity=0.3,
            radius=25,
            blur=15,
            gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1: 'red'}
        )
        heat_layer.add_to(m)

    return m


def save_map(m: "folium.Map", filepath: Path) -> None:
    """Save map to HTML file."""
    if not HAS_FOLIUM:
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(filepath))
    print(f"Map saved to {filepath}")


def _get_node_color(node_type: NodeType) -> str:
    """Get marker color for node type."""
    color_map = {
        NodeType.BUILDING: "green",
        NodeType.BUILDING_ENTRANCE: "green",
        NodeType.PARKING_LOT: "purple",
        NodeType.BUS_STOP: "red",
        NodeType.LANDMARK: "blue",
        NodeType.INTERSECTION: "gray",
        NodeType.PATH_POINT: "gray",
    }
    return color_map.get(node_type, "blue")


def _get_node_icon(node_type: NodeType) -> str:
    """Get Font Awesome icon for node type."""
    icon_map = {
        NodeType.BUILDING: "building",
        NodeType.BUILDING_ENTRANCE: "door-open",
        NodeType.PARKING_LOT: "car",
        NodeType.BUS_STOP: "bus",
        NodeType.LANDMARK: "map-marker",
        NodeType.INTERSECTION: "circle",
        NodeType.PATH_POINT: "circle",
    }
    return icon_map.get(node_type, "circle")


def create_route_comparison_map(
    graph: CampusGraph,
    routes: List[Route],
    title: str = "Route Comparison"
) -> "folium.Map":
    """
    Create a map comparing multiple routes.

    Args:
        graph: Campus graph
        routes: Routes to compare
        title: Map title

    Returns:
        Folium map with all routes
    """
    if not routes:
        return create_map()

    # Calculate bounds
    all_coords = []
    for route in routes:
        for node_id in route.node_path:
            node = graph.get_node(node_id)
            if node:
                all_coords.append((node.lat, node.lon))

    if not all_coords:
        return create_map()

    # Create map
    m = create_map()

    # Add locations
    add_locations_to_map(m, graph, show_labels=True)

    # Add routes
    add_multiple_routes_to_map(m, routes, graph)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Fit bounds
    if len(all_coords) > 1:
        m.fit_bounds(all_coords)

    return m
