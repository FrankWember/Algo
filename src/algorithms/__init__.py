"""
Routing algorithms for the campus navigation system.

This module contains three main algorithmic components:
1. Multi-Criteria Dijkstra - Base routing with multiple objectives
2. Pareto Optimizer - Dynamic programming for trade-off handling
3. Time-Aware Scheduler - Divide & Conquer for temporal adaptation
"""

from .dijkstra import MultiCriteriaDijkstra
from .pareto import ParetoOptimizer, compute_pareto_frontier
from .scheduler import TimeAwareScheduler, DivideConquerRouter

__all__ = [
    "MultiCriteriaDijkstra",
    "ParetoOptimizer",
    "compute_pareto_frontier",
    "TimeAwareScheduler",
    "DivideConquerRouter",
]
