"""
Road route provider interface.

Defines the abstract base contract for routing engine providers (e.g., OSRM, 
GraphHopper, Google Maps) to calculate routes between geospatial coordinates.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from route_consumption_estimator.domain.graph_models import Coords


class RoadRouteProvider(ABC):
    """
    Abstract Base Class for route calculation provider implementations.

    Attributes:
        endpoint (Optional[str]): Base URL or endpoint for the routing engine API.
        client (Optional[str]): Client identifier or API client instance.
        params (Dict[str, Any]): Parameters and preferences for route generation 
            (e.g., alternative routes, geometries format, profile).
        routes (List[Dict[str, Any]]): Cached or calculated route solutions.
    """

    def __init__(
        self,
        params: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        client: Optional[str] = None,
    ) -> None:
        self.endpoint: Optional[str] = endpoint
        self.client: Optional[str] = client
        self.params: Dict[str, Any] = params or {}
        self.routes: List[Dict[str, Any]] = []

    @abstractmethod
    def get_routes(self, coords: List[Coords]) -> List[Dict[str, Any]]:
        """
        Calculate and retrieve candidate routes connecting a sequence of coordinates.

        Args:
            coords (List[Coords]): Ordered list of geospatial waypoints (origin, stops, destination).

        Returns:
            List[Dict[str, Any]]: List of calculated route payloads returned by the provider engine.
        """
        pass
