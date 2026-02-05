# 🎓 GETTING STARTED - FOR STUDENTS

Welcome! This guide will help you understand the campus routing project step by step.

## 📚 What Does This Project Do?

This project finds the **shortest path between two buildings on campus**, just like Google Maps but specifically for SIUE campus!

**The cool part:** We compare 3 different algorithms to see which one is fastest!

---

## 🗂️ PROJECT STRUCTURE (Simplified)

```
Project Algorithm/
│
├── 📁 backend/                    ← THE SIMPLE VERSION (Start here!)
│   ├── algorithms.py              ← ⭐ THREE PATHFINDING ALGORITHMS
│   ├── campus_data.py             ← Campus map (buildings & paths)
│   └── main.py                    ← Web server (connects to frontend)
│
├── 📁 src/                        ← THE ADVANCED VERSION
│   ├── algorithms/                ← More complex routing algorithms
│   ├── models/                    ← Data structures
│   ├── data/                      ← Map loading code
│   └── api/                       ← Web API endpoints
│
├── 📁 frontend/                   ← THE WEBSITE (React/Next.js)
│   └── src/                       ← React components for visualization
│
├── main.py                        ← ⭐ MAIN PROGRAM (Start the app!)
└── README.md                      ← Project documentation
```

---

## 🎯 THE THREE ALGORITHMS (Explained Simply)

### 1. **Dijkstra's Algorithm** 🌊
- **How it works:** Like water spreading from a source
- **Strategy:** Always visit the closest unvisited building next
- **Pros:** Guaranteed to find shortest path
- **Cons:** Explores a lot of buildings
- **Speed:** Medium

**Real-world analogy:** A flood spreading outward - water reaches nearest places first.

### 2. **A* Algorithm** 🧭
- **How it works:** Like Dijkstra but "smarter"
- **Strategy:** Uses straight-line distance to guide search toward goal
- **Pros:** Much faster than Dijkstra
- **Cons:** Needs to know coordinates
- **Speed:** Fast

**Real-world analogy:** A GPS that knows where you're going and avoids searching in wrong directions.

### 3. **Bellman-Ford Algorithm** 🔄
- **How it works:** Checks all paths multiple times
- **Strategy:** Relax all edges V-1 times
- **Pros:** Can handle negative weights, simple concept
- **Cons:** Slowest of the three
- **Speed:** Slow

**Real-world analogy:** Being extra careful - checking every possible route multiple times to be sure.

---

## 🚀 HOW TO RUN THE PROJECT

### Step 1: Install Dependencies
```bash
# Install Python packages
pip install -r requirements.txt

# Install frontend packages (if using the website)
cd frontend
npm install
```

### Step 2: Run the Demo
```bash
# See the algorithms in action!
python main.py demo
```

This will:
- Load the campus map
- Run example routes
- Show you the results
- Compare the three algorithms

### Step 3: Try the Interactive CLI
```bash
# Interactive command-line interface
python main.py cli
```

Then you can type commands like:
- `locations` - See all buildings
- `route muc engineering` - Find a route
- `compare muc library` - Compare routes at different times

### Step 4: Run the Web Server (Optional)
```bash
# Terminal 1: Start the backend
python main.py serve

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

Then open http://localhost:3000 in your browser!

---

## 📖 UNDERSTANDING THE CODE

### Where to Start Reading?

**For beginners, read in this order:**

1. **`backend/campus_data.py`** - See the campus map data
   - Buildings (nodes)
   - Paths between buildings (edges)

2. **`backend/algorithms.py`** - The three algorithms
   - Start with Dijkstra
   - Each function has LOTS of comments
   - Read the step-by-step explanations

3. **`main.py`** - How the program starts
   - See how different modes work

4. **`backend/main.py`** - The simple web server
   - If you want to understand the API

### Key Concepts You Should Understand

#### 🔸 **Graph Terminology**
- **Node** = A building on campus
- **Edge** = A path between two buildings
- **Weight** = Distance of the path (in meters)
- **Path** = A sequence of buildings to walk through

#### 🔸 **Data Structures Used**
- **Dictionary (Dict)** - Stores distances, predecessors
- **Set** - Stores visited buildings
- **Priority Queue (heapq)** - Stores buildings to visit next, ordered by distance

#### 🔸 **Algorithm Steps** (All three follow similar pattern)
1. **Initialize** - Set up data structures
2. **Main Loop** - Visit buildings one by one
3. **Update Neighbors** - Check if we found shorter paths
4. **Reconstruct Path** - Build the route from start to end

---

## 🧪 HOW TO TEST YOUR UNDERSTANDING

### Beginner Level ✅
- [ ] Run the demo and understand the output
- [ ] Read the comments in `backend/algorithms.py`
- [ ] Explain what Dijkstra's algorithm does in your own words

### Intermediate Level 🔥
- [ ] Modify the campus map (add a new building)
- [ ] Change the algorithm to find the LONGEST path instead
- [ ] Add a new building and test the algorithms

### Advanced Level 💪
- [ ] Implement your own pathfinding algorithm
- [ ] Add support for different types of paths (stairs, ramps, etc.)
- [ ] Optimize the algorithms for better performance

---

## 🐛 COMMON ISSUES & SOLUTIONS

### "Module not found"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### "Port already in use"
**Solution:** Change the port
```bash
python main.py serve --port 8001
```

### "No path found"
**Solution:** Check if both buildings exist
```bash
python main.py cli
> locations  # See all valid building IDs
```

---

## 🎓 LEARNING RESOURCES

### Understanding Graphs
- [Graph Theory Basics](https://www.youtube.com/watch?v=LFKZLXVO-Dg) (YouTube)
- [Visualizing Pathfinding Algorithms](https://www.youtube.com/watch?v=msttfIHHkak)

### Algorithm Explanations
- **Dijkstra's Algorithm:** https://www.youtube.com/watch?v=pVfj6mxhdMw
- **A* Algorithm:** https://www.youtube.com/watch?v=ySN5Wnu88nE
- **Bellman-Ford:** https://www.youtube.com/watch?v=obWXjtg0L64

### Python Data Structures
- **heapq (Priority Queue):** https://docs.python.org/3/library/heapq.html
- **Dictionaries:** https://realpython.com/python-dicts/

---

## 💡 PROJECT IDEAS TO EXTEND THIS

1. **Add More Buildings** - Expand the campus map
2. **Weather Integration** - Prefer covered paths when raining
3. **Time-Based Routing** - Avoid crowded areas during class changes
4. **Accessibility Mode** - Find wheelchair-accessible routes
5. **Multiple Destinations** - Visit several buildings in order (Traveling Salesman)
6. **Real GPS Data** - Use actual GPS coordinates instead of made-up ones

---

## 🤝 NEED HELP?

1. **Read the code comments** - There are detailed explanations everywhere
2. **Run the demo** - See the algorithms in action
3. **Try the CLI** - Experiment with different routes
4. **Check the README.md** - More technical documentation

**Good luck and happy coding! 🚀**
