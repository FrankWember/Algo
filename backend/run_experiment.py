"""
Experiment script: Compare Dijkstra and Floyd-Warshall on SIUE campus graph.
Outputs tables and CSV/JSON for Results and Discussion (tables and charts).
Run from repo root: python backend/run_experiment.py
Or from backend: python run_experiment.py
"""

import sys
import os
import json
import csv
from typing import List, Tuple, Dict, Any

# Allow running from project root or from backend
if __name__ == "__main__":
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)

from campus_data import BUILDINGS
from algorithms import dijkstra, floyd_warshall, run_all_algorithms

# Route pairs: (start_id, end_id, label) — mix of short, medium, long paths
ROUTE_PAIRS: List[Tuple[str, str, str]] = [
    ("8", "5", "MUC → Library (short)"),
    ("4", "6", "Peck → Dunham (short)"),
    ("1", "19", "Rendleman → Engineering (medium)"),
    ("8", "27", "MUC → Pharmacy (medium)"),
    ("5", "20", "Library → Birger Hall (medium)"),
    ("41", "31", "Sports Complex → TMC (long)"),
    ("33", "20", "Evergreen Hall → Birger (long)"),
    ("12", "37", "Fitness Center → Dental Clinic (long)"),
    ("P11", "P9", "Parking P11 → P9 (cross-campus)"),
    ("17", "48", "Woodland Hall → Gardens (long)"),
]

NUM_RUNS = 5  # For execution time: run each (algo, route) this many times, report mean


def run_experiment() -> List[Dict[str, Any]]:
    """Run all algorithms on all routes. Returns list of row dicts."""
    rows = []
    for start, end, label in ROUTE_PAIRS:
        if start not in BUILDINGS or end not in BUILDINGS:
            print(f"Skip (missing node): {label}", file=sys.stderr)
            continue
        results = run_all_algorithms(start, end)
        d, fw = results["dijkstra"], results["floydWarshall"]
        if not (d.success and fw.success):
            print(f"Skip (no path): {label}", file=sys.stderr)
            continue
        # Optional: multiple runs for timing
        times_d = [dijkstra(start, end).execution_time_ms for _ in range(NUM_RUNS)]
        times_fw = [floyd_warshall(start, end).execution_time_ms for _ in range(NUM_RUNS)]
        row = {
            "route": label,
            "start": start,
            "end": end,
            "path_length_steps": len(d.path),
            "total_distance_m": round(d.total_distance, 1),
            "dijkstra_time_ms": sum(times_d) / NUM_RUNS,
            "floyd_warshall_time_ms": sum(times_fw) / NUM_RUNS,
            "dijkstra_nodes": d.nodes_visited,
            "floyd_warshall_nodes": fw.nodes_visited,
            "floyd_warshall_edges_relaxed": fw.edges_relaxed,
            "dijkstra_edges": d.edges_relaxed,
            "floyd_warshall_edges": fw.edges_relaxed,
        }
        rows.append(row)
    return rows


def print_tables(rows: List[Dict[str, Any]]) -> None:
    """Print formatted tables for copy-paste into paper."""
    print("\n" + "=" * 100)
    print("TABLE 1: Per-route results (distance, execution time ms, nodes visited)")
    print("=" * 100)
    print(f"{'Route':<45} {'Dist(m)':>8} {'Dijkstra':>12} {'Floyd-Warshall':>16}  |  Nodes: D / FW")
    print("-" * 95)
    for r in rows:
        print(
            f"{r['route']:<45} {r['total_distance_m']:>8.1f} "
            f"{r['dijkstra_time_ms']:>10.3f} {r['floyd_warshall_time_ms']:>14.3f}  |  "
            f"{r['dijkstra_nodes']:>4} / {r['floyd_warshall_nodes']:>4}"
        )
    print()

    print("=" * 100)
    print("TABLE 2: Summary statistics (mean across routes)")
    print("=" * 100)
    n = len(rows)
    avg_d_time = sum(r["dijkstra_time_ms"] for r in rows) / n
    avg_fw_time = sum(r["floyd_warshall_time_ms"] for r in rows) / n
    avg_d_nodes = sum(r["dijkstra_nodes"] for r in rows) / n
    avg_fw_nodes = sum(r["floyd_warshall_nodes"] for r in rows) / n
    avg_d_edges = sum(r["dijkstra_edges"] for r in rows) / n
    avg_fw_edges = sum(r["floyd_warshall_edges"] for r in rows) / n
    print(f"Mean execution time (ms):  Dijkstra = {avg_d_time:.4f},  Floyd-Warshall = {avg_fw_time:.4f}")
    print(f"Mean nodes visited:        Dijkstra = {avg_d_nodes:.2f},  Floyd-Warshall = {avg_fw_nodes:.2f}  (FW: |V|, all nodes in matrix)")
    print(f"Mean edges relaxed:        Dijkstra = {avg_d_edges:.2f},  Floyd-Warshall = {avg_fw_edges:.2f}")
    print()

    print("=" * 100)
    print("TABLE 3: Path length (number of segments) and total distance by route")
    print("=" * 100)
    print(f"{'Route':<45} {'Segments':>10} {'Distance (m)':>14}")
    print("-" * 72)
    for r in rows:
        print(f"{r['route']:<45} {r['path_length_steps']:>10} {r['total_distance_m']:>14.1f}")
    print()


def write_csv_for_charts(rows: List[Dict[str, Any]], out_dir: str) -> None:
    """Write CSV files for use in Excel/Google Sheets/plotting."""
    os.makedirs(out_dir, exist_ok=True)

    # execution_time_by_route.csv: one row per route, columns = algorithm times
    path1 = os.path.join(out_dir, "execution_time_by_route.csv")
    with open(path1, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["route", "Dijkstra_ms", "FloydWarshall_ms", "distance_m"])
        for r in rows:
            w.writerow([
                r["route"],
                round(r["dijkstra_time_ms"], 4),
                round(r["floyd_warshall_time_ms"], 4),
                r["total_distance_m"],
            ])
    print(f"Wrote {path1}")

    # nodes_visited_by_route.csv
    path2 = os.path.join(out_dir, "nodes_visited_by_route.csv")
    with open(path2, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["route", "Dijkstra_nodes", "FloydWarshall_nodes", "FloydWarshall_edges_relaxed", "path_segments", "distance_m"])
        for r in rows:
            w.writerow([
                r["route"],
                r["dijkstra_nodes"],
                r["floyd_warshall_nodes"],
                r["floyd_warshall_edges_relaxed"],
                r["path_length_steps"],
                r["total_distance_m"],
            ])
    print(f"Wrote {path2}")

    # summary_for_charts.json (for scripting charts)
    summary = {
        "routes": [r["route"] for r in rows],
        "mean_execution_time_ms": {
            "Dijkstra": round(avg(rows, "dijkstra_time_ms"), 4),
            "Floyd-Warshall": round(avg(rows, "floyd_warshall_time_ms"), 4),
        },
        "mean_nodes_visited": {
            "Dijkstra": round(avg(rows, "dijkstra_nodes"), 2),
            "Floyd-Warshall": round(avg(rows, "floyd_warshall_nodes"), 2),
        },
        "mean_edges_relaxed": {
            "Dijkstra": round(avg(rows, "dijkstra_edges"), 2),
            "Floyd-Warshall": round(avg(rows, "floyd_warshall_edges"), 2),
        },
        "per_route": rows,
    }
    path3 = os.path.join(out_dir, "summary_for_charts.json")
    with open(path3, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {path3}")


def avg(rows: List[Dict], key: str) -> float:
    n = len(rows)
    return sum(r[key] for r in rows) / n if n else 0


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base, "output")

    print("Running experiment (Dijkstra, Floyd-Warshall) on SIUE campus graph...")
    rows = run_experiment()
    if not rows:
        print("No results. Check BUILDINGS and ROUTE_PAIRS.")
        return

    print_tables(rows)
    write_csv_for_charts(rows, out_dir)
    print("\nDone. Use output/*.csv and output/summary_for_charts.json for tables and charts.")


if __name__ == "__main__":
    main()
