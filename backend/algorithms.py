"""
======================================================================
PATHFINDING ALGORITHMS FOR SIUE CAMPUS ROUTING
======================================================================

This file contains three different algorithms to find the shortest path
between buildings on campus:

1. DIJKSTRA'S ALGORITHM
   - How it works: Always visits the closest unvisited building first
   - Like spreading water from a source - reaches nearest places first
   - Good for: Finding shortest paths when all distances are positive

2. A* ALGORITHM
   - How it works: Like Dijkstra but "smarter" - heads toward the goal
   - Uses straight-line distance to guide the search
   - Good for: Finding paths faster when you know where you're going

3. BELLMAN-FORD ALGORITHM
   - How it works: Checks all paths multiple times to find the best
   - Slower but can handle negative distances (not needed here)
   - Good for: Understanding dynamic programming concepts

Each algorithm returns:
- The path (list of buildings to walk through)
- Total distance in meters
- Step-by-step execution (for animation/visualization)
======================================================================
"""

import heapq  # For priority queue (like a smart to-do list)
import math   # For calculating distances
import time   # For measuring how fast the algorithm runs
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from campus_data import BUILDINGS, get_adjacency_list, Building


@dataclass
class AlgorithmStep:
    """
    Represents ONE STEP in the algorithm (for animation purposes)

    Think of this like a frame in a video - it shows what the algorithm
    is doing at one particular moment.
    """
    step_number: int              # Which step is this? (1, 2, 3, etc.)
    current_node: str             # Which building are we looking at?
    action: str                   # What are we doing? ('visit', 'update', 'skip')
    distances: Dict[str, float]   # Current best distances to all buildings
    visited: List[str]            # Buildings we've already visited
    queue_state: List[str]        # Buildings waiting to be visited
    message: str                  # Human-readable description of this step


@dataclass
class AlgorithmResult:
    """
    FINAL RESULT after running a pathfinding algorithm

    This contains everything we learned:
    - The path (how to get from A to B)
    - How long it took
    - How efficient it was
    """
    algorithm_name: str           # Which algorithm did we use?
    path: List[str]               # The route (list of building IDs)
    path_names: List[str]         # The route (list of building names)
    total_distance: float         # Total walking distance in meters
    steps: List[Dict]             # Step-by-step execution (for visualization)
    execution_time_ms: float      # How fast did the algorithm run?
    nodes_visited: int            # How many buildings did we check?
    edges_relaxed: int            # How many paths did we consider?
    success: bool                 # Did we find a path?
    error_message: str = ""       # If it failed, why?


def get_node_coords(node_id: str) -> Tuple[float, float]:
    """
    Get the (x, y) coordinates of a building on the map

    This is used by A* to calculate straight-line distance
    """
    if node_id in BUILDINGS:
        return (BUILDINGS[node_id].x, BUILDINGS[node_id].y)
    return (0, 0)  # Default if building not found


def heuristic(node1: str, node2: str) -> float:
    """
    Calculate STRAIGHT-LINE distance between two buildings (for A*)

    This is called a "heuristic" - it's our GUESS of how far apart
    two buildings are, measured as the crow flies.

    Formula: Uses Pythagorean theorem (distance = sqrt(x² + y²))
    We multiply by 20 to scale the map coordinates to approximate meters
    """
    # Get coordinates of both buildings
    x1, y1 = get_node_coords(node1)
    x2, y2 = get_node_coords(node2)

    # Calculate straight-line distance
    straight_line_distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    # Scale to approximate real meters
    return straight_line_distance * 20


def dijkstra(start: str, end: str) -> AlgorithmResult:
    """
    ====================================================================
    DIJKSTRA'S ALGORITHM - Find the shortest path between two buildings
    ====================================================================

    HOW IT WORKS (simple explanation):
    1. Start at the starting building
    2. Always visit the closest unvisited building next
    3. Update distances to neighbors when you find a shorter path
    4. Repeat until you reach the destination

    ANALOGY: Imagine water spreading from a source - it reaches
    the closest places first, then gradually spreads outward.

    Time Complexity: O((V + E) log V) - Pretty fast!
    Space Complexity: O(V) - Uses memory for all buildings
    """

    # ============================================================
    # STEP 0: SETUP AND VALIDATION
    # ============================================================
    start_time = time.perf_counter()  # Start timer
    adj = get_adjacency_list()        # Get all connections between buildings
    steps = []                        # Will store each step for visualization

    # Check if start building exists
    if start not in BUILDINGS:
        return AlgorithmResult(
            algorithm_name="Dijkstra",
            path=[], path_names=[], total_distance=0,
            steps=[], execution_time_ms=0, nodes_visited=0,
            edges_relaxed=0, success=False,
            error_message=f"Start node '{start}' not found"
        )

    # Check if end building exists
    if end not in BUILDINGS:
        return AlgorithmResult(
            algorithm_name="Dijkstra",
            path=[], path_names=[], total_distance=0,
            steps=[], execution_time_ms=0, nodes_visited=0,
            edges_relaxed=0, success=False,
            error_message=f"End node '{end}' not found"
        )

    # ============================================================
    # STEP 1: INITIALIZE DATA STRUCTURES
    # ============================================================

    # distances: Stores the shortest known distance to each building
    # Initially, all distances are infinity (we don't know yet)
    distances: Dict[str, float] = {node: float('inf') for node in BUILDINGS}
    distances[start] = 0  # Distance to starting building is 0

    # predecessors: Stores the building we came from to reach each building
    # This lets us reconstruct the path at the end
    predecessors: Dict[str, Optional[str]] = {node: None for node in BUILDINGS}

    # visited: Set of buildings we've already fully processed
    visited: set = set()

    # Counters for statistics
    nodes_visited = 0      # How many buildings did we visit?
    edges_relaxed = 0      # How many paths did we check?

    # Priority Queue: Stores buildings we need to visit, sorted by distance
    # Format: [(distance, building_id), ...]
    # The building with smallest distance is always first
    pq = [(0, start)]
    step_count = 0

    # Record the initial state for visualization
    steps.append({
        "step": step_count,
        "action": "initialize",
        "current": start,
        "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
        "visited": list(visited),
        "queue": [start],
        "message": f"Initialize: Set distance to {BUILDINGS[start].name} = 0"
    })

    # ============================================================
    # STEP 2: MAIN LOOP - Visit buildings in order of distance
    # ============================================================
    while pq:  # While there are still buildings to visit
        # Get the building with smallest distance from priority queue
        current_dist, current = heapq.heappop(pq)
        step_count += 1

        # Skip if we've already visited this building
        # (Can happen if we added it to queue multiple times)
        if current in visited:
            steps.append({
                "step": step_count,
                "action": "skip",
                "current": current,
                "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
                "visited": list(visited),
                "queue": [n for _, n in pq],
                "message": f"Skip: {BUILDINGS[current].name} already visited"
            })
            continue

        # Mark this building as visited
        visited.add(current)
        nodes_visited += 1

        # Record this step for visualization
        steps.append({
            "step": step_count,
            "action": "visit",
            "current": current,
            "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
            "visited": list(visited),
            "queue": [n for _, n in pq],
            "message": f"Visit: {BUILDINGS[current].name} (distance: {current_dist:.1f}m)"
        })

        # SUCCESS! We found the destination
        if current == end:
            steps.append({
                "step": step_count + 1,
                "action": "found",
                "current": end,
                "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
                "visited": list(visited),
                "queue": [],
                "message": f"Found destination: {BUILDINGS[end].name}!"
            })
            break

        # ============================================================
        # STEP 3: UPDATE NEIGHBORS ("Relaxation")
        # ============================================================
        # For each building connected to the current building:
        for neighbor, weight in adj[current]:
            # Skip if we already visited this neighbor
            if neighbor in visited:
                continue

            edges_relaxed += 1

            # Calculate new distance: distance to current + distance from current to neighbor
            new_dist = current_dist + weight

            # If this new path is shorter than what we knew before, update it!
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist       # Update shortest distance
                predecessors[neighbor] = current     # Remember we came from 'current'
                heapq.heappush(pq, (new_dist, neighbor))  # Add to queue to visit later

                # Record this update for visualization
                step_count += 1
                steps.append({
                    "step": step_count,
                    "action": "update",
                    "current": current,
                    "updated": neighbor,
                    "newDistance": new_dist,
                    "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
                    "visited": list(visited),
                    "queue": [n for _, n in pq],
                    "message": f"Update: {BUILDINGS[neighbor].name} distance = {new_dist:.1f}m (via {BUILDINGS[current].name})"
                })

    # ============================================================
    # STEP 4: RECONSTRUCT THE PATH
    # ============================================================
    # We now know the shortest distance, but we need to figure out
    # the actual path (which buildings to walk through)
    #
    # We do this by following the 'predecessors' backwards from
    # the destination to the start
    path = []
    current = end

    # Walk backwards from destination to start
    while current is not None:
        path.append(current)           # Add this building to the path
        current = predecessors[current]  # Move to the previous building

    path.reverse()  # Reverse to get start -> end order

    # Stop the timer
    execution_time = (time.perf_counter() - start_time) * 1000

    # Check if we actually found a valid path
    if path[0] != start:
        return AlgorithmResult(
            algorithm_name="Dijkstra",
            path=[], path_names=[], total_distance=0,
            steps=steps, execution_time_ms=execution_time,
            nodes_visited=nodes_visited, edges_relaxed=edges_relaxed,
            success=False, error_message="No path found"
        )

    # Convert building IDs to building names for display
    path_names = [BUILDINGS[n].name for n in path]

    # ============================================================
    # RETURN THE RESULTS
    # ============================================================
    return AlgorithmResult(
        algorithm_name="Dijkstra",
        path=path,                      # List of building IDs
        path_names=path_names,          # List of building names
        total_distance=distances[end],  # Total walking distance
        steps=steps,                    # All steps for visualization
        execution_time_ms=execution_time,
        nodes_visited=nodes_visited,
        edges_relaxed=edges_relaxed,
        success=True
    )


def a_star(start: str, end: str) -> AlgorithmResult:
    """
    ====================================================================
    A* ALGORITHM - "Smart" shortest path using a heuristic
    ====================================================================

    HOW IT WORKS (simple explanation):
    1. Like Dijkstra, but with a "hint" about where to go
    2. Uses straight-line distance to estimate how far away the goal is
    3. Prioritizes exploring paths that seem to head toward the goal
    4. Much faster than Dijkstra because it doesn't explore as much

    ANALOGY: Imagine you're trying to find a friend in a mall.
    - Dijkstra: Search every store equally
    - A*: Search stores in the direction your friend probably went

    THE "MAGIC" OF A*:
    - g(n) = actual distance from start to building n
    - h(n) = estimated distance from building n to goal (straight line)
    - f(n) = g(n) + h(n) = total estimated cost through building n
    - Always expand the building with lowest f(n)

    Time Complexity: O((V + E) log V) - Often faster than Dijkstra!
    Space Complexity: O(V)
    """

    # ============================================================
    # STEP 0: SETUP AND VALIDATION
    # ============================================================
    start_time = time.perf_counter()
    adj = get_adjacency_list()
    steps = []

    # Validate start building
    if start not in BUILDINGS:
        return AlgorithmResult(
            algorithm_name="A*",
            path=[], path_names=[], total_distance=0,
            steps=[], execution_time_ms=0, nodes_visited=0,
            edges_relaxed=0, success=False,
            error_message=f"Start node '{start}' not found"
        )

    # Validate end building
    if end not in BUILDINGS:
        return AlgorithmResult(
            algorithm_name="A*",
            path=[], path_names=[], total_distance=0,
            steps=[], execution_time_ms=0, nodes_visited=0,
            edges_relaxed=0, success=False,
            error_message=f"End node '{end}' not found"
        )

    # ============================================================
    # STEP 1: INITIALIZE DATA STRUCTURES
    # ============================================================

    # g_score: Actual distance from start to each building
    # (This is like the 'distances' in Dijkstra)
    g_score: Dict[str, float] = {node: float('inf') for node in BUILDINGS}
    g_score[start] = 0  # Distance to start is 0

    # f_score: ESTIMATED total distance through each building
    # f = g + h (actual distance so far + estimated remaining distance)
    f_score: Dict[str, float] = {node: float('inf') for node in BUILDINGS}
    f_score[start] = heuristic(start, end)  # f(start) = 0 + straight_line_to_goal

    # predecessors: Remember where we came from (for path reconstruction)
    predecessors: Dict[str, Optional[str]] = {node: None for node in BUILDINGS}

    # visited: Buildings we've fully processed
    visited: set = set()

    # Statistics
    nodes_visited = 0
    edges_relaxed = 0

    # Priority Queue: Buildings to visit, sorted by f_score
    # Format: [(f_score, g_score, building_id), ...]
    # The building with lowest f_score is visited first!
    pq = [(f_score[start], 0, start)]
    step_count = 0

    # Record initial state
    h_initial = heuristic(start, end)
    steps.append({
        "step": step_count,
        "action": "initialize",
        "current": start,
        "distances": {k: v if v != float('inf') else -1 for k, v in g_score.items()},
        "fScores": {k: v if v != float('inf') else -1 for k, v in f_score.items()},
        "visited": list(visited),
        "queue": [start],
        "message": f"Initialize: g({BUILDINGS[start].name})=0, h={h_initial:.1f}, f={f_score[start]:.1f}"
    })

    while pq:
        current_f, current_g, current = heapq.heappop(pq)
        step_count += 1

        if current in visited:
            steps.append({
                "step": step_count,
                "action": "skip",
                "current": current,
                "distances": {k: v if v != float('inf') else -1 for k, v in g_score.items()},
                "visited": list(visited),
                "queue": [n for _, _, n in pq],
                "message": f"Skip: {BUILDINGS[current].name} already visited"
            })
            continue

        visited.add(current)
        nodes_visited += 1

        h_val = heuristic(current, end)
        steps.append({
            "step": step_count,
            "action": "visit",
            "current": current,
            "heuristic": h_val,
            "distances": {k: v if v != float('inf') else -1 for k, v in g_score.items()},
            "visited": list(visited),
            "queue": [n for _, _, n in pq],
            "message": f"Visit: {BUILDINGS[current].name} (g={current_g:.1f}, h={h_val:.1f}, f={current_f:.1f})"
        })

        if current == end:
            steps.append({
                "step": step_count + 1,
                "action": "found",
                "current": end,
                "distances": {k: v if v != float('inf') else -1 for k, v in g_score.items()},
                "visited": list(visited),
                "queue": [],
                "message": f"Found destination: {BUILDINGS[end].name}!"
            })
            break

        for neighbor, weight in adj[current]:
            if neighbor in visited:
                continue

            edges_relaxed += 1
            tentative_g = g_score[current] + weight

            if tentative_g < g_score[neighbor]:
                predecessors[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, end)
                heapq.heappush(pq, (f_score[neighbor], tentative_g, neighbor))

                step_count += 1
                steps.append({
                    "step": step_count,
                    "action": "update",
                    "current": current,
                    "updated": neighbor,
                    "newDistance": tentative_g,
                    "fScore": f_score[neighbor],
                    "distances": {k: v if v != float('inf') else -1 for k, v in g_score.items()},
                    "visited": list(visited),
                    "queue": [n for _, _, n in pq],
                    "message": f"Update: {BUILDINGS[neighbor].name} g={tentative_g:.1f}, f={f_score[neighbor]:.1f}"
                })

    # Reconstruct path
    path = []
    current = end
    while current is not None:
        path.append(current)
        current = predecessors[current]
    path.reverse()

    execution_time = (time.perf_counter() - start_time) * 1000

    if path[0] != start:
        return AlgorithmResult(
            algorithm_name="A*",
            path=[], path_names=[], total_distance=0,
            steps=steps, execution_time_ms=execution_time,
            nodes_visited=nodes_visited, edges_relaxed=edges_relaxed,
            success=False, error_message="No path found"
        )

    path_names = [BUILDINGS[n].name for n in path]

    return AlgorithmResult(
        algorithm_name="A*",
        path=path,
        path_names=path_names,
        total_distance=g_score[end],
        steps=steps,
        execution_time_ms=execution_time,
        nodes_visited=nodes_visited,
        edges_relaxed=edges_relaxed,
        success=True
    )


def bellman_ford(start: str, end: str) -> AlgorithmResult:
    """
    Bellman-Ford Algorithm - Dynamic programming approach.

    Time Complexity: O(V * E)
    Space Complexity: O(V)

    Can handle negative weights (though not needed here).
    Slower than Dijkstra but more versatile.
    """
    start_time = time.perf_counter()
    adj = get_adjacency_list()
    steps = []

    # Validation
    if start not in BUILDINGS:
        return AlgorithmResult(
            algorithm_name="Bellman-Ford",
            path=[], path_names=[], total_distance=0,
            steps=[], execution_time_ms=0, nodes_visited=0,
            edges_relaxed=0, success=False,
            error_message=f"Start node '{start}' not found"
        )
    if end not in BUILDINGS:
        return AlgorithmResult(
            algorithm_name="Bellman-Ford",
            path=[], path_names=[], total_distance=0,
            steps=[], execution_time_ms=0, nodes_visited=0,
            edges_relaxed=0, success=False,
            error_message=f"End node '{end}' not found"
        )

    # Build edge list from adjacency list
    edges_list = []
    for node, neighbors in adj.items():
        for neighbor, weight in neighbors:
            edges_list.append((node, neighbor, weight))

    # Initialize
    distances: Dict[str, float] = {node: float('inf') for node in BUILDINGS}
    distances[start] = 0
    predecessors: Dict[str, Optional[str]] = {node: None for node in BUILDINGS}
    nodes_visited = len(BUILDINGS)  # BF visits all nodes in each iteration
    edges_relaxed = 0
    step_count = 0

    steps.append({
        "step": step_count,
        "action": "initialize",
        "current": start,
        "iteration": 0,
        "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
        "visited": [start],
        "queue": [],
        "message": f"Initialize: Set distance to {BUILDINGS[start].name} = 0"
    })

    num_vertices = len(BUILDINGS)

    # Relax all edges V-1 times
    for i in range(num_vertices - 1):
        updated_this_round = False
        relaxed_in_round = []

        for u, v, weight in edges_list:
            edges_relaxed += 1

            if distances[u] != float('inf') and distances[u] + weight < distances[v]:
                distances[v] = distances[u] + weight
                predecessors[v] = u
                updated_this_round = True
                relaxed_in_round.append(v)

        step_count += 1
        if relaxed_in_round:
            steps.append({
                "step": step_count,
                "action": "iteration",
                "iteration": i + 1,
                "relaxed": relaxed_in_round,
                "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
                "visited": [k for k, v in distances.items() if v != float('inf')],
                "queue": [],
                "message": f"Iteration {i+1}: Relaxed {len(relaxed_in_round)} edges ({', '.join([BUILDINGS[n].short_name for n in relaxed_in_round[:5]])}{'...' if len(relaxed_in_round) > 5 else ''})"
            })

        # Early termination if no updates
        if not updated_this_round:
            steps.append({
                "step": step_count + 1,
                "action": "converged",
                "iteration": i + 1,
                "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
                "visited": [k for k, v in distances.items() if v != float('inf')],
                "queue": [],
                "message": f"Converged after {i+1} iterations"
            })
            break

    # Check for negative cycles (not expected in our graph)
    for u, v, weight in edges_list:
        if distances[u] != float('inf') and distances[u] + weight < distances[v]:
            return AlgorithmResult(
                algorithm_name="Bellman-Ford",
                path=[], path_names=[], total_distance=0,
                steps=steps, execution_time_ms=0,
                nodes_visited=nodes_visited, edges_relaxed=edges_relaxed,
                success=False, error_message="Negative cycle detected"
            )

    # Reconstruct path
    path = []
    current = end
    while current is not None:
        path.append(current)
        current = predecessors[current]
    path.reverse()

    execution_time = (time.perf_counter() - start_time) * 1000

    if not path or path[0] != start:
        return AlgorithmResult(
            algorithm_name="Bellman-Ford",
            path=[], path_names=[], total_distance=0,
            steps=steps, execution_time_ms=execution_time,
            nodes_visited=nodes_visited, edges_relaxed=edges_relaxed,
            success=False, error_message="No path found"
        )

    path_names = [BUILDINGS[n].name for n in path]

    steps.append({
        "step": step_count + 2,
        "action": "found",
        "current": end,
        "distances": {k: v if v != float('inf') else -1 for k, v in distances.items()},
        "visited": [k for k, v in distances.items() if v != float('inf')],
        "queue": [],
        "message": f"Path found to {BUILDINGS[end].name}!"
    })

    return AlgorithmResult(
        algorithm_name="Bellman-Ford",
        path=path,
        path_names=path_names,
        total_distance=distances[end],
        steps=steps,
        execution_time_ms=execution_time,
        nodes_visited=nodes_visited,
        edges_relaxed=edges_relaxed,
        success=True
    )


def run_all_algorithms(start: str, end: str) -> Dict[str, AlgorithmResult]:
    """Run all three algorithms and return comparative results."""
    return {
        "dijkstra": dijkstra(start, end),
        "astar": a_star(start, end),
        "bellmanFord": bellman_ford(start, end),
    }


# Algorithm metadata for the frontend
ALGORITHM_INFO = {
    "dijkstra": {
        "name": "Dijkstra's Algorithm",
        "description": "Classic greedy algorithm that finds the shortest path by always expanding the nearest unvisited node.",
        "timeComplexity": "O((V + E) log V)",
        "spaceComplexity": "O(V)",
        "pros": [
            "Guaranteed optimal solution",
            "Efficient for sparse graphs",
            "Well-understood and widely used"
        ],
        "cons": [
            "Cannot handle negative weights",
            "No goal-directed optimization",
            "May explore unnecessary nodes"
        ],
        "bestFor": "General shortest path problems with non-negative weights"
    },
    "astar": {
        "name": "A* Algorithm",
        "description": "Heuristic-guided search that uses estimated distance to goal to prioritize exploration.",
        "timeComplexity": "O((V + E) log V)",
        "spaceComplexity": "O(V)",
        "pros": [
            "Often faster than Dijkstra in practice",
            "Goal-directed (focuses on destination)",
            "Optimal with admissible heuristic"
        ],
        "cons": [
            "Requires a good heuristic function",
            "Memory intensive for large graphs",
            "Heuristic quality affects performance"
        ],
        "bestFor": "Point-to-point pathfinding on spatial graphs"
    },
    "bellmanFord": {
        "name": "Bellman-Ford Algorithm",
        "description": "Dynamic programming approach that relaxes all edges V-1 times to find shortest paths.",
        "timeComplexity": "O(V × E)",
        "spaceComplexity": "O(V)",
        "pros": [
            "Can handle negative edge weights",
            "Detects negative cycles",
            "Simpler to implement"
        ],
        "cons": [
            "Slower than Dijkstra for positive weights",
            "Less efficient for large graphs",
            "No early termination guarantee"
        ],
        "bestFor": "Graphs with negative weights or when cycle detection is needed"
    }
}
