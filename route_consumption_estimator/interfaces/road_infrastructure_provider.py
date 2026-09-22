"""
Road infrastructure information provider interface.

Defines the abstract base contract for external map, GIS, and road infrastructure 
telemetry services along route coordinates or polylines.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from route_consumption_estimator.domain.graph_models import Coords


class RoadInfrastructureInformationProvider(ABC):
    """
    Abstract Base Class for road infrastructure provider implementations.

    Attributes:
        endpoint (Optional[str]): Base URL or endpoint for the GIS/road infrastructure service.
        road_information (Dict[str, Any]): Retrieved road infrastructure payload.
        road_attributes (List[str]): List of requested or tracked road attributes 
            (e.g., ['slope', 'surface', 'lanes', 'maxspeed', 'highway']).
    """

    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.endpoint: Optional[str] = endpoint
        self.road_information: Dict[str, Any] = {}
        self.road_attributes: List[str] = []

    @abstractmethod
    def retrieve_road_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Retrieve road infrastructure details for a list of geospatial coordinates.

        Args:
            route_coordinates (List[Coords]): Sequence of route coordinates.

        Returns:
            Dict[str, Any]: Road infrastructure attributes mapped along the path coordinates.
        """
        pass

    @abstractmethod
    def retrieve_road_info_by_polyline(
        self, encoded_polyline: str
    ) -> Dict[str, Any]:
        """
        Retrieve road infrastructure details for a route specified by an encoded polyline.

        Args:
            encoded_polyline (str): Encoded polyline string representing the path geometry.

        Returns:
            Dict[str, Any]: Road infrastructure attributes mapped along the polyline path.
        """
        pass