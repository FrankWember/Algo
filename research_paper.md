# Smart Multi-Modal Campus Routing and Scheduling Optimizer: A Multi-Algorithm Approach to Accessible, Time-Aware Pathfinding on the SIUE Campus Graph

**Odedairo Oluwaferanmi**
Department of Computer Science
Southern Illinois University Edwardsville
Edwardsville, IL 62026

---

## Abstract

Campus pedestrian navigation presents a fundamentally multi-objective optimization problem that single-criterion shortest-path solvers fail to address adequately. We are trying to build an intelligent routing system for the Southern Illinois University Edwardsville (SIUE) campus that simultaneously optimizes for travel distance, estimated walking time, elevation gain, crowd density, weather shelter, and accessibility constraints. Today, campus navigation is handled either by general-purpose mapping applications (Google Maps) that lack campus-specific contextual intelligence or by static printed maps that ignore real-time conditions entirely. What is new in this work is a layered three-algorithm architecture that combines (A) a Multi-Criteria Dijkstra greedy solver for single-best-path queries, (B) a NAMOA*-based Pareto optimizer exposing the full trade-off frontier of non-dominated routes, and (C) a Divide-and-Conquer time-window scheduler that partitions the day into nine crowd-calibrated temporal segments and pre-computes per-window edge weights to enable departure-time recommendation. Our dataset comprises 57 GPS-surveyed SIUE buildings digitized from Google Earth Pro with sub-meter precision, spanning a 1,618 m × 2,882 m campus footprint and a 28.16 m elevation range, connected by 158 proximity-generated edges. We demonstrate that A* guided by a GPS-accurate equirectangular heuristic visits 3–6 nodes on routes where Dijkstra visits 9–24, yielding 3–4× search-space reduction. The practical payoff is a navigation assistant that can answer "Which route avoids stairs and minimizes sun exposure during the 12:00 lunch rush?" — a query no existing campus tool supports.

---

## I. The Big Problem

### A. Campus Navigation Is Not a Single-Criterion Problem

University campuses are dense, heterogeneous environments that demand navigation decisions across multiple competing criteria. A student rushing between back-to-back classes 10 minutes apart must simultaneously reason about walking distance, terrain slope (campuses frequently occupy hilly terrain), crowd bottlenecks at building entrances, weather exposure when crossing open quads, and the physical accessibility of connecting pathways. General-purpose mapping applications such as Google Maps optimize primarily for driving or public-transit time and apply pedestrian routing as a secondary mode with no campus-specific intelligence. They know nothing about which SIUE hallways are covered walkways, which parking lots flood at peak hours, or which accessibility ramps exist between buildings with significant elevation change.

### B. The Multi-Objective Optimization Challenge

Formally, a route on a campus graph G = (V, E) must minimize a vector objective **f**(p) = [d(p), t(p), Δe(p), s(p), c(p), w(p), a(p)] where d is total distance in meters, t is walking time in seconds, Δe is cumulative elevation gain in meters, s is stair count, c is a crowd-density score integrated along the path, w is uncovered weather-exposure distance, and a is an inverse accessibility score (penalizing routes that are impassable for wheelchair users). No single path simultaneously minimizes all seven dimensions. The set of paths for which no other path is strictly better in every dimension forms the **Pareto frontier** — and exposing this frontier to users, rather than forcing them to commit to a single objective weighting, is the central contribution of our Pareto optimizer component.

### C. Time-Dependent Edge Weights

Campus crowd density is strongly time-dependent. The hallway connecting the Morris University Center cafeteria to the Peck Hall lecture complex carries near-zero load at 07:00 but becomes a severe bottleneck during the 12:00 lunch rush, inflating effective traversal time by a factor of 1.8× or more. Static graphs with fixed edge weights cannot model this behavior. An accurate campus router must treat edge weight as a function of time: w(e, t), not merely w(e). Computing shortest paths on time-expanded graphs is significantly harder — naïve expansion inflates the graph by a factor equal to the number of time steps — motivating a coarser, window-based approximation.

### D. Accessibility as a First-Class Constraint

Approximately 10–15% of university students live with a mobility impairment (permanent or temporary). For these users, a route that traverses three flights of stairs or a 15% grade slope is not merely suboptimal — it is infeasible. Standard shortest-path algorithms have no mechanism to enforce hard reachability constraints; accessibility must be built into the graph representation and propagated through the search.

### E. The Gap in Existing Tools

No existing campus navigation tool for SIUE addresses all four challenges simultaneously: multi-objective optimization, time-dependent edge weights, hard accessibility constraints, and an interactive visualization that exposes algorithm internals for educational purposes. This work fills that gap by building a full-stack system — GPS-sourced campus graph, three complementary routing algorithms, and a React-based visualization frontend — on the SIUE campus as a concrete testbed.

---

## II. Dataset

### A. Source and Acquisition

The dataset was constructed by manually digitizing building footprint centroids for all 57 named buildings on the SIUE main campus using **Google Earth Pro** (imagery date: 2026-02-05). For each building, we recorded:

| Field | Type | Description |
|---|---|---|
| `building_code` | string | Official SIUE building abbreviation |
| `name` | string | Full official building name |
| `category` | enum | Functional category (see Table I) |
| `latitude` | float64 | WGS-84 latitude, decimal degrees |
| `longitude` | float64 | WGS-84 longitude, decimal degrees |
| `elevation` | float64 | Elevation above sea level, meters (SRTM-derived) |

All coordinates were recorded at centroid precision (±2 m). The dataset is stored as a JSON file (`buildings.json`, 8.2 KB) with one record per building.

### B. Campus Spatial Extent

The campus occupies a footprint of approximately:

- **North–South extent**: 38.787563° N to 38.802127° N → **1,618 m**
- **East–West extent**: −90.006511° E to −89.973232° E → **2,882 m**
- **Total enclosed area**: approximately 4.66 km²

The campus terrain is distinctly non-flat: the southern residential zone sits at the lowest point while the central academic core rises to higher elevations.

**Table I: Building Category Distribution**

| Category | Count | Examples |
|---|---|---|
| Parking | 23 | Lot A, Lot B, Garage I, Garage II |
| Academic | 10 | Peck Hall, Rendleman Hall, Science Building |
| Research | 7 | Engineering Building, IERC, National Corn-to-Ethanol Research Center |
| Landmark | 4 | Prairie Hall Clocktower, The Sculpture |
| Recreation | 4 | Vadalabene Center, Tennis Courts, Soccer Field, Baseball Field |
| Facility | 3 | Physical Plant, Facilities Management, Warehouse |
| Residence | 4 | Bluff Hall, Prairie Hall, Woodland Hall, Tower Lake Apartments |
| Student Services | 2 | Morris University Center, Cougar Village Community Center |
| Other | 1 | University Park |
| **Total** | **57** | |

### C. Elevation Analysis

Elevation data was extracted from the SRTM 30-m DEM and recorded per building centroid. The dataset exhibits the following elevation statistics:

| Statistic | Value | Building |
|---|---|---|
| Minimum | 161.98 m | Tennis Courts |
| Maximum | 190.14 m | Lovejoy Library |
| Range | **28.16 m** | — |
| Mean | ~174.5 m | — |

This 28.16 m elevation range is substantial for a pedestrian campus — equivalent to climbing a 9-story building — and significantly impacts walking time estimates using Naismith's Rule (add 1 minute per 10 m of ascent, halve for descent).

### D. Graph Construction

No authoritative pedestrian-path dataset was available for SIUE. We therefore developed an automated **proximity-based edge generation** algorithm to construct a connected weighted graph G = (V, E) from the building point dataset.

**Phase 1 — Proximity Thresholding:**
For each pair of buildings (u, v), we compute the Haversine distance d(u,v). An undirected edge (u,v) is added if:
- d(u,v) ≤ 600 m for all non-parking pairs, OR
- d(u,v) ≤ 350 m if both u and v are parking facilities

A degree cap of **MAX_PER_NODE = 6** is enforced: only the 6 nearest eligible neighbors are retained per node. Edge weight is set to d(u,v) in meters. Edges connecting to or from a parking lot receive a 1.1× distance penalty to model the indirect routing typically required through parking infrastructure.

**Phase 2 — Connectivity Bridging:**
Isolated subgraphs (components) can arise when buildings are spatially remote. A BFS scan identifies all connected components. For each non-main component, the single minimum-weight cross-component edge is unconditionally added regardless of the degree cap, ensuring **57/57 buildings are reachable** (fully connected graph). This handles the Physics Observatory (38.802127° N, −89.973232° E), which lies approximately 1.5 km from the nearest main-campus cluster.

**Phase 1 distance formula (Haversine):**

$$d(u,v) = 2R \arcsin\!\left(\sqrt{\sin^2\!\frac{\Delta\phi}{2} + \cos\phi_u \cos\phi_v \sin^2\!\frac{\Delta\lambda}{2}}\right)$$

where R = 6,371,000 m, φ denotes latitude in radians, and λ denotes longitude in radians.

**Final graph statistics:**

| Property | Value |
|---|---|
| Nodes \|V\| | 57 |
| Edges \|E\| | 158 |
| Average degree | 5.5 |
| Maximum degree | 6 (capped) |
| Graph connectivity | 100% (57/57 reachable) |
| Edge weight unit | meters (Haversine) |
| Min edge weight | ~45 m |
| Max edge weight | ~1,520 m (Observatory bridge) |

### E. Temporal Dataset — Time Windows

Campus crowd dynamics are modeled through **nine time windows** derived from typical university daily schedules. Each window is assigned a multiplicative crowd factor applied to base traversal time:

**Table II: Time Window Definitions**

| Window ID | Time Range | Crowd Factor | Description |
|---|---|---|---|
| `early_morning` | 05:00–07:30 | 0.30 | Pre-class, minimal traffic |
| `morning_rush` | 07:30–09:00 | 1.50 | First class wave |
| `mid_morning` | 09:00–11:30 | 0.80 | Between classes |
| `lunch_rush` | 11:30–13:00 | **1.80** | Peak campus density |
| `early_afternoon` | 13:00–15:00 | 1.20 | Afternoon class wave |
| `late_afternoon` | 15:00–17:00 | 1.00 | Baseline |
| `evening_rush` | 17:00–18:30 | 1.30 | End-of-day surge |
| `evening` | 18:30–22:00 | 0.50 | Evening classes |
| `night` | 22:00–05:00 | **0.10** | Near-empty campus |

Day-of-week modifiers further scale these factors: weekday = 1.0×, Saturday = 0.3×, Sunday = 0.2×.

The effective traversal time for edge e during window w on day-type d is:

$$t_{\text{eff}}(e, w, d) = \frac{d(e)}{v_{\text{base}}} \cdot \mu_w \cdot \delta_d$$

where v_base = 1.4 m/s (standard comfortable walking speed), μ_w is the window crowd factor, and δ_d is the day-type modifier.

### F. Accessibility Dataset

Each edge in the full multi-objective graph carries the following accessibility attributes: `stairs_up` (count), `stairs_down` (count), `has_ramp` (boolean), `is_covered` (boolean, weather shelter), `surface_type` (enum: paved/gravel/grass/indoor), and `max_grade` (percentage). These attributes enable hard-constraint filtering during route computation.

---

## III. Methodology

### A. System Architecture

The system is implemented as a full-stack application with three layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  Building        │  │  Algorithm       │  │  Step-by-Step │  │
│  │  Selector        │  │  Selector        │  │  Visualizer   │  │
│  │  (start / end)   │  │  (A / B / C)     │  │  (playback)   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘  │
│           │                     │                     │          │
│           └─────────────────────┴─────────────────────┘          │
│                                 │                                 │
│                        SVG Campus Map                            │
│                  (zoom · pan · node selection)                   │
└─────────────────────────────────┬───────────────────────────────┘
                                  │  REST API (HTTP/JSON)
                    ┌─────────────▼──────────────┐
                    │      FastAPI Backend         │
                    │  POST /api/path             │
                    │  POST /api/compare          │
                    │  GET  /api/graph            │
                    │  GET  /api/path/steps/{alg} │
                    └─────────────┬───────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│  Algorithm A    │   │  Algorithm B      │   │  Algorithm C     │
│  Multi-Criteria │   │  NAMOA* Pareto    │   │  D&C Time-Window │
│  Dijkstra       │   │  Optimizer        │   │  Scheduler       │
│  (Greedy)       │   │  (DP / Labeling)  │   │  (D&C)          │
└────────┬────────┘   └────────┬──────────┘   └───────┬──────────┘
         │                     │                       │
         └─────────────────────▼───────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Campus Graph G      │
                    │   57 nodes · 158 edges │
                    │   buildings.json       │
                    └───────────────────────┘
```

**Figure 1: System Block Diagram**

Data flows from the JSON dataset through the graph construction module into the three algorithm implementations. The FastAPI backend exposes all three algorithms over a unified REST interface. The Next.js frontend renders the campus graph as an interactive SVG with zoom/pan and presents algorithm step-by-step traces for educational visualization.

---

### B. Algorithm A — Multi-Criteria Dijkstra (Greedy)

#### 1. Motivation and Design

Dijkstra's algorithm is a greedy single-source shortest-path algorithm that grows a shortest-path tree by repeatedly extracting the minimum-distance unvisited node from a priority queue. It is guaranteed to find the optimal path in graphs with non-negative edge weights. Our **Multi-Criteria Dijkstra** implementation (`src/algorithms/dijkstra.py`) extends the classical algorithm by replacing the scalar edge weight with a weighted-sum aggregate of seven objective dimensions.

#### 2. Edge Cost Aggregation

Given user preference weights **w** = [w_d, w_t, w_Δe, w_s, w_c, w_sh, w_a] (normalized: Σw_i = 1) and edge attribute vector **f**(e) = [distance, time, elev_gain, stairs, crowd, shelter_penalty, accessibility_penalty], the composite scalar edge cost is:

$$c(e, \mathbf{w}) = \mathbf{w} \cdot \mathbf{f}(e)$$

This reduces the multi-objective problem to a single-objective problem solvable with standard Dijkstra, at the cost of fixing the trade-off weights a priori.

**Pre-defined Optimization Profiles:**

| Profile | Description | Dominant Weights |
|---|---|---|
| `FASTEST` | Minimize time (with crowd factor) | w_t = 0.60, w_d = 0.30 |
| `SHORTEST` | Minimize distance | w_d = 0.80 |
| `ACCESSIBLE` | Avoid stairs, prefer ramps | w_s = 0.50, w_a = 0.30 |
| `COMFORTABLE` | Balance time + shelter | w_t = 0.40, w_sh = 0.40 |
| `AVOID_CROWDS` | Minimize crowd exposure | w_c = 0.60 |
| `SHELTERED` | Maximize covered-walkway usage | w_sh = 0.70 |
| `CUSTOM` | User-specified weights | — |

#### 3. Constraint Enforcement

Hard constraints are enforced by filtering edges from the adjacency list prior to search:
- `wheelchair_accessible = True` → edges with `stairs_up > 0 AND has_ramp = False` are removed
- `max_stairs` → edges with `stairs_up > max_stairs` are removed
- `max_elevation_gain` → edges causing cumulative gain to exceed threshold are pruned during relaxation

#### 4. Algorithm (Pseudocode)

```
Algorithm: MultiCriteriaDijkstra(G, src, dst, w, constraints)
  Input:  Graph G = (V,E), source src, destination dst,
          weight vector w, accessibility constraints
  Output: Optimal route R

  1.  dist[v] ← ∞  for all v ∈ V
  2.  dist[src] ← 0
  3.  prev[v] ← NIL  for all v ∈ V
  4.  Q ← MinHeap{(0, src)}
  5.  while Q ≠ ∅ do
  6.    (d, u) ← Q.extract_min()
  7.    if u = dst then break
  8.    if d > dist[u] then continue       ▷ stale entry
  9.    for each edge (u,v,e) ∈ adj(u) do
  10.     if violates_constraint(e, constraints) then continue
  11.     cost ← w · f(e)                  ▷ weighted-sum aggregate
  12.     if dist[u] + cost < dist[v] then
  13.       dist[v] ← dist[u] + cost
  14.       prev[v] ← u
  15.       Q.insert((dist[v], v))
  16. return reconstruct_path(prev, src, dst)
```

#### 5. Complexity

| Measure | Complexity |
|---|---|
| Time | O((V + E) log V) |
| Space | O(V + E) |

With |V| = 57 and |E| = 158, worst-case operations ≈ 57 × log(57) ≈ 342. In practice, A*-guided search (used in the visualization layer) terminates with 3–6 node expansions for typical campus routes.

#### 6. Experimental A* Enhancement

The educational visualization layer implements **A\*** as a heuristic-guided variant of Dijkstra. The admissible heuristic h(n, goal) is the straight-line geodesic distance computed via equirectangular projection:

$$h(n, \text{goal}) = \sqrt{(\Delta x)^2 + (\Delta y)^2}$$

where Δx and Δy are the east–west and north–south metric separations:

$$\Delta x = R \cdot (\lambda_n - \lambda_\text{goal}) \cdot \cos\phi_\text{ref}$$
$$\Delta y = R \cdot (\phi_n - \phi_\text{goal})$$

with φ_ref = 38.793° (campus centroid latitude), R = 6,371,000 m. Since all edge weights are Haversine distances in meters, the heuristic never overestimates — the admissibility condition h(n) ≤ d*(n, goal) is satisfied.

**A* Performance Gains (empirical):**

| Route | Dijkstra Visited | A* Visited | Reduction |
|---|---|---|---|
| Lovejoy Library → Morris University Center | 9 | 3 | 67% |
| Morris University Center → Engineering Building | 14 | 3 | 79% |
| Bluff Hall → Lovejoy Library | 20 | 6 | 70% |
| Prairie Hall → Rendleman Hall | 24 | 6 | 75% |

---

### C. Algorithm B — NAMOA* Pareto Optimizer (Dynamic Programming)

#### 1. Motivation

The weighted-sum approach of Algorithm A collapses the multi-objective problem to a scalar at the cost of requiring the user to specify weights before seeing alternatives. A fundamentally different approach is to compute the entire **Pareto frontier** — the set of all non-dominated routes — and present it to the user for post-hoc selection. This is solved by the NAMOA* algorithm (Mandow & Pérez de la Cruz, 2010), which extends A* to vector cost spaces using a label-setting paradigm.

#### 2. Pareto Dominance

A route p₁ **dominates** route p₂ (written p₁ ≺ p₂) if and only if:

$$\mathbf{f}(p_1) \leq \mathbf{f}(p_2) \text{ componentwise, and } \mathbf{f}(p_1) \neq \mathbf{f}(p_2)$$

That is, p₁ is at least as good as p₂ in every dimension and strictly better in at least one. The Pareto frontier Π(src, dst) is the maximal antichain of non-dominated routes under ≺.

#### 3. Label-Setting Algorithm

Each node v maintains a **label set** L(v) — a set of (cost_vector, path) pairs. A label ℓ = (g, p) represents reaching v via path p with accumulated cost vector **g**. A new label ℓ' is added to L(v) only if it is not dominated by any existing label in L(v); dominated existing labels are simultaneously pruned.

```
Algorithm: NAMOA_Star(G, src, dst)
  Input:  Graph G = (V,E), source src, destination dst
  Output: Pareto frontier Π(src, dst)

  1.  L(v) ← ∅  for all v ∈ V
  2.  OPEN ← {Label(g=0⃗, path=[src], node=src)}
  3.  CLOSED ← ∅
  4.  Π ← ∅                                    ▷ solutions found so far

  5.  while OPEN ≠ ∅ do
  6.    ℓ ← OPEN.extract_min()                 ▷ by f = g + h (vector)
  7.    u ← ℓ.node
  8.    if dominated_by_any(ℓ, Π) then continue
  9.    if |L(u)| ≥ MAX_LABELS_PER_NODE then continue   ▷ bound = 10
  10.   if u = dst then
  11.     Π ← Π ∪ {ℓ}
  12.     if |Π| ≥ MAX_ROUTES then break        ▷ bound = 5
  13.     continue
  14.   L(u) ← prune_dominated(L(u) ∪ {ℓ})
  15.   for each (u,v,e) ∈ adj(u) do
  16.     g' ← ℓ.g + f(e)                      ▷ vector addition
  17.     ℓ' ← Label(g=g', path=ℓ.path+[v], node=v)
  18.     if not dominated_by_any(ℓ', L(v) ∪ Π) then
  19.       OPEN.insert(ℓ')

  20. return compute_pareto_frontier(Π)
```

#### 4. Implementation Details

The implementation (`src/algorithms/pareto.py`) uses the following bounding strategies to keep computation tractable on the 57-node campus graph:

| Bound | Value | Rationale |
|---|---|---|
| `max_labels_per_node` | 10 | Prevents combinatorial explosion in dense subgraphs |
| `max_routes` | 5 | Presents user with manageable choice set |
| Cost vector dimensions | 7 | distance, time, elev_gain, elev_loss, stairs, crowd, shelter |

#### 5. Pareto Frontier Post-Processing

After NAMOA* terminates, the raw solution set is filtered by the `compute_pareto_frontier()` utility:

$$\Pi^* = \{ p \in \Pi \mid \nexists\, p' \in \Pi : p' \prec p \}$$

The result is a collection of 2–5 routes offering distinct trade-offs, e.g.:
- Route 1: Shortest distance, but crosses open plazas (no shelter) and includes stairs
- Route 2: Slightly longer, fully sheltered, wheelchair accessible
- Route 3: Fastest at lunchtime, uses covered walkways, modest elevation gain

#### 6. Complexity

| Measure | Complexity |
|---|---|
| Worst-case time | O(V · E · k) where k = max Pareto labels per node |
| Space | O(V · k) |
| Practical (campus) | O(57 · 158 · 10) ≈ 90,060 operations |

---

### D. Algorithm C — Divide-and-Conquer Time-Window Scheduler

#### 1. Motivation

Algorithms A and B operate on static edge weights. Algorithm C extends the system to handle the time-dependent campus routing problem: find the optimal departure time and route given a desired arrival window. The core insight is that the 24-hour day can be **divided** into T = 9 non-overlapping time windows (Table II), within each of which edge weights are approximately constant. This allows pre-computing T static shortest-path problems offline and **combining** (conquering) them at query time.

#### 2. Divide Phase — Pre-computation

At system initialization, for each time window w ∈ {1, ..., T}, the `TimeAwareScheduler` pre-computes a crowd-adjusted edge weight for every edge e:

$$w_{\text{eff}}(e, w) = \frac{d(e)}{v_{\text{base}}} \cdot \mu_w \cdot \delta_d$$

These T weight matrices are stored in memory (total size: T × |E| = 9 × 158 = 1,422 floats). This is the **divide** step: the continuous-time problem is decomposed into T independent static sub-problems.

#### 3. Conquer Phase — Query Processing

At query time, given a departure time t_dep and route request (src, dst), the scheduler:

1. Identifies the applicable time window w* = argmin_w |t_dep - midpoint(w)|
2. Looks up the pre-computed edge weights for w*
3. Runs Multi-Criteria Dijkstra on the time-window-adjusted graph
4. Returns the route with time-annotated step-by-step instructions

```
Algorithm: TimeAwareDivideConquer(src, dst, t_dep, prefs)
  Input:  source src, destination dst, departure time t_dep,
          user preferences prefs
  Output: Route R with crowd-adjusted travel time

  ── DIVIDE (pre-computed at init) ──────────────────────────
  1.  for w = 1 to T do
  2.    for each edge e ∈ E do
  3.      weight_table[w][e] ← compute_effective_weight(e, w)

  ── CONQUER (per query) ────────────────────────────────────
  4.  w* ← identify_time_window(t_dep)
  5.  G_w ← apply_weights(G, weight_table[w*])
  6.  R ← MultiCriteriaDijkstra(G_w, src, dst, prefs)
  7.  R.departure ← t_dep
  8.  R.arrival ← t_dep + R.travel_time
  9.  return R
```

#### 4. Departure-Time Recommendation

The `suggest_departure_time()` function extends Algorithm C to find the **globally optimal departure time** within a user-specified window [t_earliest, t_latest]:

```
Algorithm: SuggestDeparture(src, dst, t_earliest, t_latest, prefs)
  1.  best_route ← NIL
  2.  best_score ← ∞
  3.  for t_dep = t_earliest to t_latest step Δt=10min do
  4.    R ← TimeAwareDivideConquer(src, dst, t_dep, prefs)
  5.    score ← compute_score(R, prefs)
  6.    if score < best_score then
  7.      best_score ← score
  8.      best_route ← R
  9.  return best_route
```

This is a linear scan over at most (t_latest − t_earliest) / 10 candidate departure times, each resolved in O((V+E) log V) time.

#### 5. What-If Analysis

`compare_departure_times()` computes routes for a set of candidate departure times simultaneously, enabling users to compare options interactively (e.g., "How much faster is the 11:15 departure vs. 12:00?").

#### 6. Complexity

| Phase | Complexity |
|---|---|
| Divide (pre-computation) | O(T × E) = O(9 × 158) = O(1,422) |
| Conquer (single query) | O((V + E) log V) = O(776 log 57) |
| Departure suggestion | O(W × (V + E) log V) where W = candidate windows |
| Space (weight table) | O(T × E) |

---

### E. Integration and Visualization

The three algorithms share a unified interface: given (source, destination, time, preferences), each returns a `Route` object containing the path node sequence, total cost vector, step-by-step execution trace, and human-readable navigation instructions. The FastAPI backend serializes these to JSON and serves them to the Next.js frontend.

The educational visualization component renders each algorithm's step-by-step execution on the SVG campus map:
- **Green fill**: start building
- **Red fill**: destination building
- **Blue highlights**: currently explored nodes (per step)
- **Highlighted edges**: current shortest-path tree
- **Playback controls**: step forward, step backward, play at configurable speed

The SVG campus map supports GPU-accelerated zoom (via CSS `transform: scale()`) and pointer-based pan implemented with native DOM event listeners (bypassing React's passive-wheel limitation) and `useRef`-based drag state (avoiding stale-closure bugs in React's event batching model).

---

## IV. Results

### A. Path Accuracy

All three algorithm variants (Dijkstra, A*, Bellman-Ford) produce identical optimal path distances on the same (src, dst) pair, confirming implementation correctness. Sample route distances:

| Route | Distance | Path Hops |
|---|---|---|
| Lovejoy Library → Morris University Center | 205.8 m | 2 |
| Morris University Center → Engineering Building | 386.8 m | 3 |
| Bluff Hall → Lovejoy Library | 633.6 m | 4 |
| Prairie Hall → Rendleman Hall | 973.3 m | 6 |

### B. Search Efficiency

A* with the GPS-accurate equirectangular heuristic achieves 3–4× search-space reduction over plain Dijkstra across all tested routes (see Table in Section III-B-6), confirming the heuristic is both admissible and effective for the SIUE campus geometry.

### C. Time-Window Sensitivity

Routes computed during `lunch_rush` (μ = 1.80) show 80% longer effective traversal times compared to the same physical route during `night` (μ = 0.10), demonstrating meaningful time-window differentiation. The departure-time recommender correctly identifies `early_morning` and `evening` windows as optimal for time-sensitive routes through the MUC central corridor.

---

## V. Conclusion

We presented a three-layer routing architecture for the SIUE campus combining greedy (Dijkstra), dynamic programming (NAMOA* Pareto), and divide-and-conquer (time-window scheduling) algorithmic paradigms to address the multi-objective, time-dependent, accessibility-aware campus routing problem. Our GPS-surveyed 57-building, 158-edge campus graph demonstrates that A* with an admissible geodesic heuristic achieves 67–79% node-visit reduction over blind Dijkstra. The Pareto optimizer surfaces non-dominated route alternatives that the weighted-sum approach would never find without prior knowledge of user preferences. The time-window scheduler decomposes the continuous-time routing problem into tractable static sub-problems without sacrificing temporal fidelity. Together, these components deliver a routing system capable of answering complex navigation queries no existing campus tool supports.

---

## References

[1] E. W. Dijkstra, "A note on two problems in connexion with graphs," *Numerische Mathematik*, vol. 1, pp. 269–271, 1959.

[2] P. E. Hart, N. J. Nilsson, and B. Raphael, "A formal basis for the heuristic determination of minimum cost paths," *IEEE Transactions on Systems Science and Cybernetics*, vol. 4, no. 2, pp. 100–107, 1968.

[3] R. Bellman, "On a routing problem," *Quarterly of Applied Mathematics*, vol. 16, pp. 87–90, 1958.

[4] L. Mandow and J. L. Pérez de la Cruz, "Multiobjective A* search with consistent heuristics," *Journal of the ACM*, vol. 57, no. 5, pp. 27:1–27:25, 2010.

[5] W. Naismith, "Excursions: Cruach Ardrain," *Scottish Mountaineering Club Journal*, vol. 2, p. 135, 1892.

[6] T. H. Cormen, C. E. Leiserson, R. L. Rivest, and C. Stein, *Introduction to Algorithms*, 4th ed. Cambridge, MA: MIT Press, 2022.

[7] Google LLC, *Google Earth Pro*, Version 7.3, 2026.

[8] NASA/METI/AIST/Japan Spacesystems, "ASTER Global Digital Elevation Map," Version 3, 2019.
