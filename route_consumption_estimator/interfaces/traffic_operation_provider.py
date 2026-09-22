"""
Traffic operation provider interface.

Defines the abstract base contract for external traffic telematics and real-time 
congestion information providers along route coordinates or polylines.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from route_consumption_estimator.domain.graph_models import Coords


class TrafficOperationInformationProvider(ABC):
    """
    Abstract Base Class for traffic operation information provider implementations.

    Attributes:
        endpoint (Optional[str]): Base URL or endpoint for the traffic service API.
        traffic_information (Dict[str, Any]): Retrieved real-time or historical traffic data payload.
        traffic_attributes (List[str]): List of tracked traffic attributes 
            (e.g., ['jam_factor', 'free_flow_speed', 'current_speed', 'incidents']).
    """

    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.endpoint: Optional[str] = endpoint
        self.traffic_information: Dict[str, Any] = {}
        self.traffic_attributes: List[str] = []

    @abstractmethod
    def retrieve_traffic_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Retrieve traffic information for a list of geospatial coordinates.

        Args:
            route_coordinates (List[Coords]): Sequence of route coordinates.

        Returns:
            Dict[str, Any]: Traffic operational attributes mapped along the path coordinates.
        """
        pass

    @abstractmethod
    def retrieve_traffic_info_by_polyline(
        self, encoded_polyline: str
    ) -> Dict[str, Any]:
        """
        Retrieve traffic information for a route specified by an encoded polyline.

        Args:
            encoded_polyline (str): Encoded polyline string representing the path geometry.

        Returns:
            Dict[str, Any]: Traffic operational attributes mapped along the polyline path.
        """
        pass
