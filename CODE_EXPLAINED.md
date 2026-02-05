# 📝 CODE EXPLAINED - Quick Reference

This document explains the most important files in simple terms.

---

## 🎯 THE CORE FILES (Start Here!)

### 1. `backend/algorithms.py` ⭐ MOST IMPORTANT FILE

**What it does:** Contains the three pathfinding algorithms

**Key functions:**
```python
def dijkstra(start, end)
    # Finds shortest path using Dijkstra's algorithm
    # Returns: Path, distance, and step-by-step execution

def a_star(start, end)
    # Finds shortest path using A* (with heuristic)
    # Returns: Path, distance, and step-by-step execution

def bellman_ford(start, end)
    # Finds shortest path using Bellman-Ford
    # Returns: Path, distance, and step-by-step execution
```

**How to read this file:**
1. Start at line 110: `def dijkstra(start, end)`
2. Read the comments - they explain EVERYTHING
3. Each section is labeled: STEP 0, STEP 1, STEP 2, etc.
4. Look for `# ===` comments - they mark major sections

**Example usage:**
```python
from backend.algorithms import dijkstra

result = dijkstra("8", "19")  # MUC to Engineering
print(f"Path: {result.path_names}")
print(f"Distance: {result.total_distance}m")
```

---

### 2. `backend/campus_data.py`

**What it does:** Stores the campus map (buildings and paths)

**Key data:**
```python
BUILDINGS = {
    "8": Building(
        id="8",
        name="Morris University Center",
        x=500, y=300  # Position on map
    ),
    # ... more buildings
}

EDGES = [
    ("8", "A", 45.0),   # MUC to Parking Lot A: 45 meters
    ("A", "5", 78.0),   # Parking Lot A to Alumni Hall: 78 meters
    # ... more paths
]
```

**How the graph works:**
- Each building is a "node"
- Each path is an "edge" with a weight (distance)
- The algorithms find the shortest total weight

---

### 3. `main.py` (Root folder)

**What it does:** Entry point - starts the application

**Four modes:**
```bash
python main.py serve    # Start web server
python main.py demo     # Run demonstration
python main.py build    # Build campus graph
python main.py cli      # Interactive mode
```

**Most useful for students:** `demo` and `cli` modes

---

### 4. `backend/main.py`

**What it does:** Simple web server (FastAPI)

**API Endpoints:**
```python
GET  /api/graph       # Get all buildings and paths
GET  /api/buildings   # Get list of buildings
POST /api/path        # Find a path (one algorithm)
POST /api/compare     # Compare all three algorithms
```

**Example API request:**
```bash
curl -X POST http://localhost:8000/api/path \
  -H "Content-Type: application/json" \
  -d '{"start": "8", "end": "19", "algorithm": "dijkstra"}'
```

---

## 🧮 UNDERSTANDING THE ALGORITHMS

### How Dijkstra Works (Simplified)

```python
# 1. SETUP
distances = {all_buildings: infinity}
distances[start] = 0
visited = set()
queue = [(0, start)]  # (distance, building)

# 2. MAIN LOOP
while queue:
    current_distance, current_building = pop_smallest_from_queue()

    if current_building == destination:
        break  # FOUND IT!

    for neighbor in current_building.neighbors:
        new_distance = current_distance + distance_to_neighbor

        if new_distance < distances[neighbor]:
            # Found a shorter path!
            distances[neighbor] = new_distance
            add_to_queue(neighbor)

# 3. RECONSTRUCT PATH
# Follow the path backwards from destination to start
```

### How A* is Different

```python
# A* uses two scores instead of one:
g_score = actual_distance_from_start
h_score = estimated_distance_to_goal (straight line)
f_score = g_score + h_score  # Total estimated cost

# Priority queue sorts by f_score instead of just distance
# This makes it "head toward" the goal instead of spreading equally
```

### How Bellman-Ford is Different

```python
# Instead of using a priority queue, it:
# 1. Relaxes ALL edges V-1 times (V = number of buildings)
# 2. Each iteration, tries to improve every path

for i in range(num_buildings - 1):
    for edge in all_edges:
        # Try to find a shorter path through this edge
        if distance[from] + edge_weight < distance[to]:
            distance[to] = distance[from] + edge_weight
```

---

##  KEY DATA STRUCTURES

### 1. Priority Queue (heapq)
```python
import heapq

pq = []
heapq.heappush(pq, (10, "building_a"))  # Add item
heapq.heappush(pq, (5, "building_b"))   # Add item
distance, building = heapq.heappop(pq)  # Get smallest (5, "building_b")
```

**Why we use it:** Always gives us the building with smallest distance first

### 2. Dictionary
```python
distances = {
    "8": 0,        # MUC: 0 meters (start)
    "A": 45,       # Lot A: 45 meters away
    "5": 123,      # Alumni: 123 meters away
    "19": infinity # Engineering: don't know yet
}
```

**Why we use it:** Fast lookup of distances by building ID

### 3. Set
```python
visited = {"8", "A", "5"}  # Already visited these buildings
if "19" in visited:
    print("Already visited!")
```

**Why we use it:** Fast checking if we visited a building

---

## 🔄 PROGRAM FLOW

### When you run `python main.py demo`:

```
1. main.py starts
   └─> Calls cmd_demo()

2. cmd_demo() runs:
   ├─> Loads campus map from campus_data.py
   ├─> Creates graph (buildings + paths)
   ├─> Runs example routes using algorithms
   └─> Prints results

3. For each route:
   ├─> Calls dijkstra(start, end)
   ├─> Algorithm runs step-by-step
   └─> Returns result (path + statistics)

4. Results displayed to user
```

### When you run `python main.py serve`:

```
1. main.py starts
   └─> Calls cmd_serve()

2. cmd_serve() runs:
   └─> Starts FastAPI web server

3. Server waits for HTTP requests

4. When request arrives:
   ├─> Parse request (start, end, algorithm)
   ├─> Call appropriate algorithm
   ├─> Format result as JSON
   └─> Send back to client
```

---

## 🧪 TESTING YOUR UNDERSTANDING

### Beginner Challenge
**Task:** Find the path from MUC (building "8") to Engineering (building "19")

**Steps:**
1. Open `backend/algorithms.py`
2. Find the `dijkstra()` function
3. Add a print statement at line 230 to see when you reach the destination
4. Run it and observe the output

### Intermediate Challenge
**Task:** Modify Dijkstra to also count how many buildings it visits

**Steps:**
1. Add a counter: `buildings_visited = 0`
2. Increment it each time you visit a building
3. Return it in the `AlgorithmResult`
4. Test it and compare with A* (A* should visit fewer)

### Advanced Challenge
**Task:** Implement a new algorithm - "Greedy Best-First Search"

**Hint:** Like A*, but only use `h_score`, ignore `g_score`
- Only looks at estimated distance to goal
- Faster but NOT guaranteed to find shortest path

---

## 💡 COMMON PATTERNS IN THE CODE

### Pattern 1: Initialization
```python
# Set all distances to infinity (unknown)
distances = {building: float('inf') for building in all_buildings}
# Except the start
distances[start] = 0
```

### Pattern 2: Relaxation (Updating distances)
```python
# Check if we found a shorter path
new_distance = current_distance + edge_weight
if new_distance < distances[neighbor]:
    # Update it!
    distances[neighbor] = new_distance
    predecessors[neighbor] = current
```

### Pattern 3: Path Reconstruction
```python
# Walk backwards from destination to start
path = []
current = destination
while current is not None:
    path.append(current)
    current = predecessors[current]
path.reverse()  # Now it goes start -> end
```

---

## 📈 PERFORMANCE COMPARISON

For a typical campus route (MUC to Engineering):

| Algorithm    | Buildings Visited | Time    | Complexity     |
|--------------|------------------|---------|----------------|
| Dijkstra     | ~15              | 0.23ms  | O((V+E) log V) |
| A*           | ~8               | 0.18ms  | O((V+E) log V) |
| Bellman-Ford | ~50 (all)        | 1.45ms  | O(V × E)       |

**Key insight:** All find the same shortest path, but A* is fastest!

---

## 🎯 WHERE TO GO NEXT

**If you understand the basics:**
1. Read `src/algorithms/dijkstra.py` - Advanced multi-criteria version
2. Look at `src/algorithms/pareto.py` - Finds MULTIPLE good paths
3. Explore `src/models/route_models.py` - Complex data structures

**If you want to build features:**
1. Add new buildings to `campus_data.py`
2. Modify visualization in `frontend/`
3. Add new API endpoints in `backend/main.py`

**If you want to learn more:**
1. Watch the YouTube videos in GETTING_STARTED.md
2. Read about graph theory: https://www.khanacademy.org/computing/computer-science/algorithms
3. Implement variations of the algorithms

---

**Remember:** Code is meant to be READ, not just written. Take your time! 📚
