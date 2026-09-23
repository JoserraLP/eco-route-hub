"""
OpenRouteService (ORS) routing provider plugin implementation.

Calculates vehicle routes, geometry polylines, distances, and durations 
using OpenRouteService API or self-hosted ORS instances.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

try:
    from openrouteservice import Client, convert
    from openrouteservice.directions import directions
    from openrouteservice.exceptions import ApiError
except ImportError:
    Client = None
    convert = None
    directions = None
    ApiError = Exception

from route_consumption_estimator.domain.graph_models import Coords
from route_consumption_estimator.interfaces.road_route_provider import (
    RoadRouteProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_ORS_ENDPOINT: str = "http://localhost:8081/ors"
DEFAULT_ORS_PARAMS: Dict[str, Any] = {
    "share_factor": 0.6,
    "target_count": 3,
    "weight_factor": 0.8,
}


class OpenRouteService(RoadRouteProvider):
    """
    OpenRouteService client for route calculation and alternative path planning.

    Attributes:
        api_key (Optional[str]): OpenRouteService API authentication key.
        client (Optional[Client]): OpenRouteService SDK client instance.
        timeout (float): HTTP request timeout limit in seconds.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        endpoint = config.get("endpoint", DEFAULT_ORS_ENDPOINT)
        params = config.get("params", DEFAULT_ORS_PARAMS)
        super().__init__(params=params, endpoint=endpoint)

        self.api_key: Optional[str] = (
            config.get("api_key")
            or os.environ.get("ORS_KEY")
            or os.environ.get("OPENROUTESERVICE_KEY")
        )
        self.timeout: float = config.get("timeout", 10.0)

        if Client is not None:
            client_kwargs: Dict[str, Any] = {}
            if self.api_key:
                client_kwargs["key"] = self.api_key
            if endpoint:
                client_kwargs["base_url"] = endpoint

            self.client = Client(**client_kwargs)
        else:
            self.client = None
            logger.warning(
                "The 'openrouteservice' library is not installed. "
                "Install it using 'pip install openrouteservice'."
            )

    def get_routes(self, coords: List[Coords]) -> List[Dict[str, Any]]:
        """
        Calculate route options connecting an ordered sequence of coordinates.

        Args:
            coords (List[Coords]): Ordered list of waypoints (minimum origin and destination).

        Returns:
            List[Dict[str, Any]]: List of preprocessed route payloads.
        """
        if not coords or len(coords) < 2:
            logger.warning(
                "OpenRouteService requires at least two coordinates (origin and destination)."
            )
            self.routes = []
            return self.routes

        if self.client is None:
            logger.error("OpenRouteService SDK client is not initialized.")
            self.routes = []
            return self.routes

        common_source = coords[0]
        common_target = coords[-1]

        # ORS API requires coordinates in [longitude, latitude] order
        ors_coords = [[coord.lon, coord.lat] for coord in coords]

        preprocessed_routes: List[Dict[str, Any]] = []

        try:
            kwargs: Dict[str, Any] = {"coordinates": ors_coords}
            if self.params:
                kwargs["alternative_routes"] = self.params

            response = directions(self.client, **kwargs)
            routes = response.get("routes", [])

            for route in routes:
                raw_geometry = route.get("geometry")

                # Decode polyline string to [lon, lat] points
                if isinstance(raw_geometry, str) and convert:
                    decoded_geo = convert.decode_polyline(raw_geometry)
                    raw_coords = decoded_geo.get("coordinates", [])
                elif isinstance(raw_geometry, dict):
                    raw_coords = raw_geometry.get("coordinates", [])
                else:
                    raw_coords = []

                # Re-map [lon, lat] back to domain Coords(lat, lon)
                route_coords = [
                    Coords(lat=item[1], lon=item[0]) for item in raw_coords
                ]

                summary = route.get("summary", {})
                preprocessed_route = {
                    "route_coordinates": route_coords,
                    "common_source": common_source,
                    "common_target": common_target,
                    "router_distance": summary.get("distance", 0.0),
                    "router_duration": summary.get("duration", 0.0),
                }
                preprocessed_routes.append(preprocessed_route)

        except (ApiError, requests.RequestException) as e:
            logger.error(f"Error retrieving routes from ORS service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing ORS route response: {e}")

        self.routes = preprocessed_routes
        return self.routes
