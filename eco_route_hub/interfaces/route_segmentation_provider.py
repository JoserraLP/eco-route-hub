"""
Route segmentation provider interface.

Defines the abstract base contract for segmenting continuous route coordinates 
and road telemetry into discrete homogeneous segments based on attribute variations 
(e.g., speed limits, slopes, surface types).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from eco_route_hub.domain.graph_models import Coords


class RouteSegmentationProvider(ABC):
    """
    Abstract Base Class for route segmentation provider implementations.

    Attributes:
        config (Dict[str, Any]): Configuration settings and segmentation thresholds.
        indices (List[int]): Selected waypoint indices marking segment boundaries.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or {}
        self.indices: List[int] = []

    @abstractmethod
    def segment_route(self, attributes_info: Dict[str, Any]) -> List[int]:
        """
        Segment a route by identifying key waypoint indices where attribute changes occur.

        Args:
            attributes_info (Dict[str, Any]): Road and ambient attribute data 
                mapped across route points/sections.

            Returns:
                List[int]: List of coordinate indices where new segments begin.
        """
        pass

    @abstractmethod
    def retrieve_segmented_route_information(
        self, route_coordinates: List[Coords], attributes_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve aggregated telemetry and geometric information structured by segments.

        Args:
            route_coordinates (List[Coords]): Full sequence of route coordinates.
            attributes_info (Dict[str, Any]): Detailed attribute data along the route.

        Returns:
            Dict[str, Any]: Segmented route profile data including aggregated features per segment.
        """
        pass

    @abstractmethod
    def calculate_slopes(
        self, distances: List[float], heights: List[float]
    ) -> List[float]:
        """
        Calculate road slopes (%) based on segment distances and coordinate elevations.

        Args:
            distances (List[float]): Distance increments between consecutive waypoints.
            heights (List[float]): Waypoint elevation profiles in meters.

        Returns:
            List[float]: Calculated road slopes clipped within physics thresholds.
        """
        pass
