#!/usr/bin/env python3
"""
================================================================================
SIUE CAMPUS ROUTING SYSTEM - MAIN PROGRAM
================================================================================

This is the MAIN FILE that starts the campus routing application.

YOU CAN RUN THIS PROGRAM IN 4 DIFFERENT MODES:
================================================

1. SERVE MODE - Start the web server
   Command: python main.py serve
   What it does: Starts an API server that the frontend can talk to
   When to use: When you want to use the web interface

2. DEMO MODE - See the algorithms in action
   Command: python main.py demo
   What it does: Runs example routes and shows results
   When to use: To see how the algorithms work with real campus data

3. BUILD MODE - Create/update the campus map data
   Command: python main.py build
   What it does: Processes the campus map and saves it
   When to use: If you updated the campus map data

4. CLI MODE - Interactive text interface
   Command: python main.py cli
   What it does: Lets you find routes by typing commands
   When to use: For quick testing without the web interface

================================================================================
"""

import argparse
import sys
from pathlib import Path
from datetime import time


def cmd_serve(args):
    """
    ============================================================
    SERVE MODE: Start the web API server
    ============================================================
    This function starts a web server that:
    - Listens for requests from the frontend (website)
    - Runs pathfinding algorithms when asked
    - Sends back the results

    Think of it like a restaurant kitchen - the frontend is
    the waiter taking orders, and this server is the kitchen
    that prepares the food (runs the algorithms).
    """
    # Try to import the necessary libraries
    try:
        import uvicorn  # Web server library
        from src.api.routes import app  # Our API code
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print("Install with: pip install -r requirements.txt")
        sys.exit(1)

    # Display startup information
    print("Starting SIUE Campus Router API...")
    print(f"API docs available at: http://{args.host}:{args.port}/docs")

    # Start the server!
    uvicorn.run(
        "src.api.routes:app",
        host=args.host,        # Where to listen (default: localhost)
        port=args.port,        # What port to use (default: 8000)
        reload=args.reload,    # Auto-restart when code changes?
    )


def cmd_build(args):
    """Build/rebuild the campus graph."""
    from src.data.graph_builder import CampusGraphBuilder

    builder = CampusGraphBuilder(data_dir=Path(args.data_dir))
    graph = builder.build(
        include_elevation=not args.no_elevation,
        validate=True
    )

    output_path = Path(args.output)
    builder.save_graph(output_path)

    print(f"\nGraph Statistics:")
    print(f"  Nodes: {graph.node_count}")
    print(f"  Edges: {graph.edge_count}")


def cmd_demo(args):
    """
    ============================================================
    DEMO MODE: See the routing algorithms in action
    ============================================================
    This function demonstrates the routing system by:
    1. Loading the campus map
    2. Running example routes between different buildings
    3. Comparing different algorithms and optimization profiles
    4. (Optional) Creating a visual map

    This is a great way to understand what the system does!
    """
    # Import the necessary modules
    from src.data.graph_builder import CampusGraphBuilder
    from src.algorithms.scheduler import DivideConquerRouter, TimeAwareScheduler
    from src.models.route_models import UserPreferences, OptimizationProfile

    print("=" * 60)
    print("SIUE Campus Routing System - Demo")
    print("=" * 60)

    # STEP 1: Load the campus map
    print("\n[1] Building campus graph...")
    builder = CampusGraphBuilder(data_dir=Path("data"))
    graph = builder.build(include_elevation=True, validate=False)
    print(f"    Graph: {graph.node_count} locations, {graph.edge_count} paths")

    # Initialize scheduler
    print("\n[2] Initializing time-aware scheduler...")
    scheduler = TimeAwareScheduler(graph)
    router = DivideConquerRouter(graph, scheduler)

    # Demo routes
    demo_routes = [
        ("cougar_village", "engineering", "Student walking from dorms to Engineering"),
        ("lot_a", "library", "Commuter from Parking Lot A to Library"),
        ("muc", "stadium", "Student going from MUC to Stadium"),
    ]

    for origin, destination, description in demo_routes:
        print(f"\n[Route] {description}")
        print(f"        From: {origin} -> To: {destination}")

        # Default route
        route = router.find_route(origin, destination)
        if route:
            print(f"        Result: {route.summary()}")
        else:
            print("        Result: No route found")

    # Compare profiles
    print("\n[3] Comparing optimization profiles...")
    print("    Route: MUC -> Engineering")

    profiles = [
        OptimizationProfile.FASTEST,
        OptimizationProfile.COMFORTABLE,
        OptimizationProfile.ACCESSIBLE,
    ]

    for profile in profiles:
        prefs = UserPreferences.from_profile(profile)
        route = router.find_route("muc", "engineering", prefs)
        if route:
            print(f"    {profile.value:12s}: {route.summary()}")

    # Compare departure times
    print("\n[4] Comparing departure times (MUC -> Library)...")
    times = [time(8, 0), time(10, 0), time(12, 0), time(15, 0)]

    results = scheduler.compare_departure_times("muc", "library", times)
    for t_str, route in results.items():
        if route:
            crowd = route.total_weight.crowdedness
            crowd_level = "HIGH" if crowd > 0.6 else "LOW" if crowd < 0.3 else "MED"
            print(f"    {t_str}: {route.total_time/60:.1f} min, Crowds: {crowd_level}")

    # Pareto alternatives
    print("\n[5] Finding alternative routes (Pareto-optimal)...")
    route_set = router.find_routes_pareto("cougar_village", "muc", max_routes=3)

    for route in route_set.routes:
        print(f"    Option {route.rank}: {route.summary()}")

    # Visualization
    if args.visualize:
        print("\n[6] Creating visualization...")
        try:
            from src.visualization.map_view import (
                create_map,
                add_locations_to_map,
                add_multiple_routes_to_map,
                save_map,
            )
            import folium

            m = create_map()
            add_locations_to_map(m, graph)

            if route_set.routes:
                add_multiple_routes_to_map(m, route_set.routes, graph)

            folium.LayerControl().add_to(m)

            output_path = Path("output/demo_map.html")
            save_map(m, output_path)
            print(f"    Map saved to: {output_path}")

        except ImportError:
            print("    (Folium not installed, skipping visualization)")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


def cmd_cli(args):
    """Interactive command-line interface."""
    from src.data.graph_builder import CampusGraphBuilder
    from src.algorithms.scheduler import DivideConquerRouter, TimeAwareScheduler
    from src.models.route_models import UserPreferences

    print("SIUE Campus Router - Interactive CLI")
    print("Type 'help' for commands, 'quit' to exit")
    print()

    # Build graph
    builder = CampusGraphBuilder(data_dir=Path("data"))
    graph = builder.build(include_elevation=True, validate=False)
    scheduler = TimeAwareScheduler(graph)
    router = DivideConquerRouter(graph, scheduler)

    # List locations
    locations = {node.id: node.name for node in graph.get_all_nodes()}

    while True:
        try:
            user_input = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        parts = user_input.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        elif cmd == "help":
            print("""
Commands:
  locations          - List all campus locations
  route FROM TO      - Find route between locations
  compare FROM TO    - Compare routes at different times
  pareto FROM TO     - Find alternative routes
  help               - Show this help
  quit               - Exit
            """)

        elif cmd == "locations":
            print("\nAvailable locations:")
            for loc_id, loc_name in sorted(locations.items()):
                print(f"  {loc_id:20s} - {loc_name}")

        elif cmd == "route":
            if len(parts) < 3:
                print("Usage: route FROM TO")
                continue

            origin, dest = parts[1], parts[2]
            if origin not in locations:
                print(f"Unknown location: {origin}")
                continue
            if dest not in locations:
                print(f"Unknown location: {dest}")
                continue

            route = router.find_route(origin, dest)
            if route:
                print(f"\nRoute: {locations[origin]} -> {locations[dest]}")
                print(f"  {route.summary()}")
                print("\nDirections:")
                for i, seg in enumerate(route.segments, 1):
                    print(f"  {i}. {seg.instruction}")
            else:
                print("No route found")

        elif cmd == "compare":
            if len(parts) < 3:
                print("Usage: compare FROM TO")
                continue

            origin, dest = parts[1], parts[2]
            times = [time(8, 0), time(10, 0), time(12, 0), time(15, 0), time(18, 0)]

            print(f"\nComparing departure times: {locations.get(origin, origin)} -> {locations.get(dest, dest)}")
            results = scheduler.compare_departure_times(origin, dest, times)

            for t_str, route in results.items():
                if route:
                    crowd = route.total_weight.crowdedness
                    print(f"  {t_str}: {route.total_time/60:.1f} min, crowds: {crowd:.0%}")

        elif cmd == "pareto":
            if len(parts) < 3:
                print("Usage: pareto FROM TO")
                continue

            origin, dest = parts[1], parts[2]
            route_set = router.find_routes_pareto(origin, dest, max_routes=5)

            print(f"\nAlternative routes: {locations.get(origin, origin)} -> {locations.get(dest, dest)}")
            for route in route_set.routes:
                print(f"  Option {route.rank}: {route.summary()}")

        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")


def main():
    parser = argparse.ArgumentParser(
        description="SIUE Campus Routing & Scheduling Optimizer"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Run the API server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # build command
    build_parser = subparsers.add_parser("build", help="Build the campus graph")
    build_parser.add_argument("--data-dir", default="data", help="Data directory")
    build_parser.add_argument("--output", default="data/campus_graph.json", help="Output file")
    build_parser.add_argument("--no-elevation", action="store_true", help="Skip elevation data")

    # demo command
    demo_parser = subparsers.add_parser("demo", help="Run demonstration")
    demo_parser.add_argument("--visualize", action="store_true", help="Create map visualization")

    # cli command
    cli_parser = subparsers.add_parser("cli", help="Interactive CLI")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "cli":
        cmd_cli(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
