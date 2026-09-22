"""
Ambient weather provider interface.

Defines the abstract base contract for external weather API integrations 
and environmental telemetry services along route coordinates or polylines.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from route_consumption_estimator.domain.graph_models import Coords


class AmbientWeatherInformationProvider(ABC):
    """
    Abstract Base Class for weather information provider implementations.

    Attributes:
        endpoint (Optional[str]): Base URL or endpoint for the weather service API.
        ambient_weather_information (Dict[str, Any]): Retrieved weather data payload.
        ambient_weather_attributes (List[str]): List of tracked/requested weather metrics 
            (e.g., ['temperature', 'wind_speed', 'wind_direction', 'humidity']).
    """

    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.endpoint: Optional[str] = endpoint
        self.ambient_weather_information: Dict[str, Any] = {}
        self.ambient_weather_attributes: List[str] = []

    @abstractmethod
    def retrieve_ambient_weather_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Retrieve ambient weather metrics for a list of geospatial coordinates.

        Args:
            route_coordinates (List[Coords]): Sequence of route points.

        Returns:
            Dict[str, Any]: Weather attributes mapped along the path coordinates.
        """
        pass

    @abstractmethod
    def retrieve_ambient_weather_info_by_polyline(
        self, encoded_polyline: str
    ) -> Dict[str, Any]:
        """
        Retrieve ambient weather metrics for a route specified by an encoded polyline.

        Args:
            encoded_polyline (str): Encoded polyline string representing the path geometry.

        Returns:
            Dict[str, Any]: Weather attributes mapped along the polyline path.
        """
        pass
