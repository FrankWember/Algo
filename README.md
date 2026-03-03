# SIUE Campus Routing Algorithm Visualizer

**Author:** Frank Wember, Odedairo Oluwaferanmi Shayne Tieman
**Institution:** Southern Illinois University Edwardsville

A full-stack web application for visualizing and comparing shortest path algorithms on the SIUE campus map.

## 🎯 Project Goal

Create and compare 3 different algorithms to find the shortest path between buildings on the SIUE campus, with:
- Buildings as nodes
- Walkways/paths as weighted edges (distance in meters)
- Interactive visualization to understand how each algorithm works

## 🧮 Algorithms Implemented

### 1. Dijkstra's Algorithm
- **Type:** Greedy
- **Time Complexity:** O((V + E) log V)
- **Approach:** Always expands the nearest unvisited node
- **Best for:** General shortest path with non-negative weights

### 2. A* Search Algorithm
- **Type:** Heuristic-guided
- **Time Complexity:** O((V + E) log V) - often faster in practice
- **Approach:** Uses Euclidean distance to guide search toward goal
- **Best for:** Point-to-point pathfinding on spatial graphs

### 3. Bellman-Ford Algorithm
- **Type:** Dynamic Programming
- **Time Complexity:** O(V × E)
- **Approach:** Relaxes all edges V-1 times
- **Best for:** Graphs with negative weights (demonstrates different approach)

## 🗺️ Campus Graph

Based on the official SIUE Campus Core Map:
- **50+ locations** including academic buildings, residence halls, parking lots
- **70+ paths** connecting locations with distance weights
- Building coordinates mapped for accurate visualization

## 🛠️ Technology Stack

### Backend (Python)
- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation
- Custom algorithm implementations with step-by-step tracking

### Frontend (Next.js)
- **React 18** with TypeScript
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- SVG-based interactive campus map

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Backend runs at: http://localhost:8000

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: http://localhost:3000

## 📁 Project Structure

```
Project Algorithm/
├── backend/
│   ├── main.py              # FastAPI server & endpoints
│   ├── algorithms.py        # Dijkstra, A*, Bellman-Ford
│   ├── campus_data.py       # SIUE campus graph definition
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx     # Main application page
│   │   │   ├── layout.tsx   # Root layout
│   │   │   └── globals.css  # Global styles
│   │   ├── components/
│   │   │   ├── CampusMap.tsx       # Interactive SVG map
│   │   │   ├── AlgorithmSelector.tsx
│   │   │   ├── BuildingSelector.tsx
│   │   │   ├── ResultsPanel.tsx    # Algorithm results
│   │   │   ├── StepVisualizer.tsx  # Step-by-step playback
│   │   │   └── Header.tsx
│   │   ├── lib/
│   │   │   └── api.ts       # Backend API client
│   │   └── types/
│   │       └── index.ts     # TypeScript definitions
│   └── package.json
│
└── README.md
```

## 📊 Features

### 1. Building Selection
- Search buildings by name
- Click on map to select start/end
- Swap start and end with one click

### 2. Algorithm Comparison
- Run single algorithm or compare all three
- See which algorithm is most efficient
- View detailed metrics:
  - Total distance
  - Execution time
  - Nodes visited
  - Edges relaxed

### 3. Step-by-Step Visualization
- Play/pause algorithm execution
- Step forward/backward
- Adjustable playback speed
- See which nodes are being visited in real-time

### 4. Interactive Map
- Color-coded building types
- Path highlighting
- Node state visualization (current, visited, path)
- Hover for building details

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph` | GET | Get campus nodes and edges |
| `/api/buildings` | GET | List all buildings |
| `/api/algorithms` | GET | Algorithm information |
| `/api/path` | POST | Find path with one algorithm |
| `/api/compare` | POST | Compare all three algorithms |

### Example Request
```bash
curl -X POST http://localhost:8000/api/path \
  -H "Content-Type: application/json" \
  -d '{
    "start": "8",
    "end": "19",
    "algorithm": "dijkstra"
  }'
```

### Example Response
```json
{
  "algorithm": "Dijkstra",
  "path": ["8", "A", "5", "7", "E", "11", "19"],
  "pathNames": ["Morris University Center", "Parking Lot A", ...],
  "totalDistance": 523.4,
  "executionTimeMs": 0.234,
  "nodesVisited": 15,
  "edgesRelaxed": 42,
  "success": true,
  "steps": [...]
}
```

## 📈 Algorithm Comparison Results

For a typical route (MUC to Engineering Building):

| Metric | Dijkstra | A* | Bellman-Ford |
|--------|----------|-----|--------------|
| Distance | 523.4m | 523.4m | 523.4m |
| Nodes Visited | 15 | 8 | 50 |
| Execution Time | 0.23ms | 0.18ms | 1.45ms |

**Key Insights:**
- All algorithms find the same optimal path (correctness ✓)
- A* visits fewer nodes due to heuristic guidance
- Bellman-Ford is slowest due to O(V×E) complexity

## 🏫 Campus Buildings Included

**Academic:** Rendleman Hall, Founders Hall, Alumni Hall, Peck Hall, Lovejoy Library, Dunham Hall, Science Buildings, Morris University Center (MUC), Art & Design, Engineering Building, and more

**Residential:** Woodland Hall, Prairie Hall, Bluff Hall, Evergreen Hall

**Athletic:** Student Fitness Center, Vadalabene Center

**Parking:** Lots P1-P12, A-G

## 🔮 Future Improvements

- [ ] Real GPS coordinates from campus GIS data
- [ ] Elevation/terrain data for more accurate weights
- [ ] Time-based routing (class schedules, crowd patterns)
- [ ] Accessibility-aware routing (avoid stairs)
- [ ] Mobile-responsive design
- [ ] Export route as directions

## 📚 Educational Value

This project demonstrates:
1. **Graph Theory** - Modeling real-world problems as graphs
2. **Algorithm Design** - Different approaches to the same problem
3. **Complexity Analysis** - Why some algorithms are faster
4. **Full-Stack Development** - Python backend + React frontend
5. **Data Visualization** - Making algorithms understandable

## 📄 License

MIT License

## 🙏 Acknowledgments

- SIUE for the campus map reference
- Course instructors for algorithm guidance
- The open source community
