"""
Domain route model representation for consumption estimation pipelines.

Defines the RouteModel structure used by calculation engines and providers 
to evaluate distance-based route profiles and additional path metadata.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RouteModel:
    """
    Analytical route entity represented by cumulative distance markers.

    Attributes:
        segment_start_point (List[float]): Vector containing the start position 
            of each segment, measured in meters from the origin (e.g., [0.0, 150.0, 400.0]).
        additional_info (Dict[str, Any]): Dictionary containing route telemetry and metadata 
            (e.g., speed profiles, elevation/slopes, weather, traffic data).
        total_distance (float): Total length of the route in meters. Automatically 
            computed from segment_start_point if not explicitly provided.
    """

    segment_start_point: List[float] = field(default_factory=list)
    additional_info: Dict[str, Any] = field(default_factory=dict)
    total_distance: float = 0.0

    def __post_init__(self) -> None:
        """Calculate total_distance defensively from segment start points if zero."""
        if not self.total_distance and self.segment_start_point:
            self.total_distance = float(max(self.segment_start_point))

    def update_segment_start_points(self, new_points: List[float]) -> None:
        """
        Update the segment start points vector and automatically recalculate total_distance.

        Args:
            new_points (List[float]): New list of cumulative segment start distances.
        """
        self.segment_start_point = new_points
        self.total_distance = float(max(new_points)) if new_points else 0.0
