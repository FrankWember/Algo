"""
Time-related data models for scheduling and temporal optimization.

This module handles time windows, crowd patterns, and shuttle schedules
for the Divide & Conquer scheduling component.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum


class DayOfWeek(Enum):
    """Days of the week."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class TimeWindow:
    """
    Represents a time window for scheduling purposes.

    The campus day is divided into distinct windows with different
    traffic and crowd patterns.

    Attributes:
        name: Human-readable name (e.g., "Morning Rush")
        start_time: Window start time
        end_time: Window end time
        crowd_multiplier: Base multiplier for crowd levels
        description: Optional description
    """
    name: str
    start_time: time
    end_time: time
    crowd_multiplier: float = 1.0
    description: str = ""

    def contains(self, t: time) -> bool:
        """Check if a given time falls within this window."""
        if self.start_time <= self.end_time:
            return self.start_time <= t < self.end_time
        else:
            # Handle overnight windows (e.g., 22:00 - 06:00)
            return t >= self.start_time or t < self.end_time

    def duration_minutes(self) -> int:
        """Get the duration of this window in minutes."""
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        return int((end_dt - start_dt).total_seconds() / 60)


# Predefined time windows for SIUE campus
DEFAULT_TIME_WINDOWS = [
    TimeWindow(
        name="early_morning",
        start_time=time(6, 0),
        end_time=time(8, 0),
        crowd_multiplier=0.3,
        description="Early morning - very low traffic"
    ),
    TimeWindow(
        name="morning_rush",
        start_time=time(8, 0),
        end_time=time(10, 0),
        crowd_multiplier=1.5,
        description="Morning class rush - high traffic"
    ),
    TimeWindow(
        name="mid_morning",
        start_time=time(10, 0),
        end_time=time(11, 30),
        crowd_multiplier=0.8,
        description="Mid-morning - moderate traffic"
    ),
    TimeWindow(
        name="lunch_rush",
        start_time=time(11, 30),
        end_time=time(13, 30),
        crowd_multiplier=1.8,
        description="Lunch rush - very high traffic near dining"
    ),
    TimeWindow(
        name="early_afternoon",
        start_time=time(13, 30),
        end_time=time(15, 0),
        crowd_multiplier=1.2,
        description="Early afternoon classes"
    ),
    TimeWindow(
        name="late_afternoon",
        start_time=time(15, 0),
        end_time=time(17, 0),
        crowd_multiplier=1.0,
        description="Late afternoon - moderate traffic"
    ),
    TimeWindow(
        name="evening_rush",
        start_time=time(17, 0),
        end_time=time(19, 0),
        crowd_multiplier=1.3,
        description="Evening class rush and departures"
    ),
    TimeWindow(
        name="evening",
        start_time=time(19, 0),
        end_time=time(22, 0),
        crowd_multiplier=0.5,
        description="Evening - low traffic"
    ),
    TimeWindow(
        name="night",
        start_time=time(22, 0),
        end_time=time(6, 0),
        crowd_multiplier=0.1,
        description="Night - minimal traffic"
    ),
]


@dataclass
class CrowdPattern:
    """
    Crowd pattern data for an edge or area.

    Models how crowdedness varies throughout the day and week.

    Attributes:
        base_level: Base crowdedness level (0.0-1.0)
        time_window_modifiers: Multipliers per time window
        day_of_week_modifiers: Multipliers per day of week
        special_events: Special event impacts
    """
    base_level: float = 0.5
    time_window_modifiers: Dict[str, float] = field(default_factory=dict)
    day_of_week_modifiers: Dict[DayOfWeek, float] = field(default_factory=lambda: {
        DayOfWeek.MONDAY: 1.0,
        DayOfWeek.TUESDAY: 1.0,
        DayOfWeek.WEDNESDAY: 1.0,
        DayOfWeek.THURSDAY: 1.0,
        DayOfWeek.FRIDAY: 0.9,
        DayOfWeek.SATURDAY: 0.3,
        DayOfWeek.SUNDAY: 0.2,
    })
    special_events: List[Dict] = field(default_factory=list)

    def get_crowdedness(
        self,
        time_window: str,
        day: Optional[DayOfWeek] = None
    ) -> float:
        """
        Calculate crowdedness for a given time window and day.

        Returns a value between 0.0 and 1.0.
        """
        crowdedness = self.base_level

        # Apply time window modifier
        if time_window in self.time_window_modifiers:
            crowdedness *= self.time_window_modifiers[time_window]

        # Apply day of week modifier
        if day is not None and day in self.day_of_week_modifiers:
            crowdedness *= self.day_of_week_modifiers[day]

        # Clamp to valid range
        return max(0.0, min(1.0, crowdedness))


@dataclass
class ShuttleStop:
    """
    A shuttle stop location.

    Attributes:
        id: Unique identifier
        name: Stop name
        node_id: Associated graph node ID
        routes: List of route IDs that serve this stop
    """
    id: str
    name: str
    node_id: str
    routes: List[str] = field(default_factory=list)


@dataclass
class ShuttleRoute:
    """
    A shuttle bus route.

    Attributes:
        id: Route identifier
        name: Route name (e.g., "Red Route", "Blue Route")
        stops: Ordered list of stop IDs
        frequency_minutes: How often the shuttle runs (minutes between buses)
        operating_hours: (start_time, end_time) tuple
        days_of_operation: Days the route operates
    """
    id: str
    name: str
    stops: List[str]
    frequency_minutes: int = 15
    operating_hours: Tuple[time, time] = (time(7, 0), time(22, 0))
    days_of_operation: List[DayOfWeek] = field(default_factory=lambda: [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    ])

    def is_operating(self, t: time, day: DayOfWeek) -> bool:
        """Check if the shuttle is operating at the given time and day."""
        if day not in self.days_of_operation:
            return False
        start, end = self.operating_hours
        if start <= end:
            return start <= t <= end
        else:
            return t >= start or t <= end

    def estimated_wait_time(self) -> float:
        """Estimate average wait time in seconds."""
        # Average wait is half the frequency
        return (self.frequency_minutes * 60) / 2


@dataclass
class ShuttleSchedule:
    """
    Complete shuttle schedule for the campus.

    Attributes:
        routes: All shuttle routes
        stops: All shuttle stops
    """
    routes: List[ShuttleRoute] = field(default_factory=list)
    stops: List[ShuttleStop] = field(default_factory=list)

    def get_stop_by_node(self, node_id: str) -> Optional[ShuttleStop]:
        """Find a shuttle stop by its associated graph node."""
        for stop in self.stops:
            if stop.node_id == node_id:
                return stop
        return None

    def get_routes_for_stop(self, stop_id: str) -> List[ShuttleRoute]:
        """Get all routes that serve a given stop."""
        return [r for r in self.routes if stop_id in r.stops]

    def can_travel(
        self,
        from_stop_id: str,
        to_stop_id: str,
        current_time: time,
        day: DayOfWeek
    ) -> Optional[Tuple[ShuttleRoute, float]]:
        """
        Check if shuttle travel is possible between two stops.

        Returns (route, estimated_time) if possible, None otherwise.
        """
        for route in self.routes:
            if not route.is_operating(current_time, day):
                continue

            if from_stop_id in route.stops and to_stop_id in route.stops:
                from_idx = route.stops.index(from_stop_id)
                to_idx = route.stops.index(to_stop_id)

                # Can only travel forward along the route
                if from_idx < to_idx:
                    # Estimate travel time: wait time + transit time
                    wait = route.estimated_wait_time()
                    stops_between = to_idx - from_idx
                    transit = stops_between * 120  # ~2 min per stop
                    return (route, wait + transit)

        return None


def get_current_time_window(
    t: Optional[time] = None,
    windows: List[TimeWindow] = None
) -> TimeWindow:
    """
    Get the time window for a given time.

    Args:
        t: Time to check (defaults to current time)
        windows: List of time windows (defaults to DEFAULT_TIME_WINDOWS)

    Returns:
        The matching TimeWindow
    """
    if t is None:
        t = datetime.now().time()
    if windows is None:
        windows = DEFAULT_TIME_WINDOWS

    for window in windows:
        if window.contains(t):
            return window

    # Fallback to first window
    return windows[0]


def get_day_of_week(dt: Optional[datetime] = None) -> DayOfWeek:
    """Get the DayOfWeek enum for a datetime."""
    if dt is None:
        dt = datetime.now()
    return DayOfWeek(dt.weekday())
