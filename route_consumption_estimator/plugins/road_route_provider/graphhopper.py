"""
GraphHopper routing provider plugin implementation.

Calculates vehicle routes, geometries, distances, and travel times 
using the GraphHopper Routing API.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from route_consumption_estimator.domain.graph_models import Coords
from route_consumption_estimator.interfaces.road_route_provider import (
    RoadRouteProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_GRAPHHOPPER_ENDPOINT: str = "https://graphhopper.com/api/1/route"
DEFAULT_GRAPHHOPPER_PARAMS: Dict[str, Any] = {
    "profile": "car",
    "locale": "en",
    "elevation": False,
    "optimize": False,
    "instructions": True,
    "calc_points": True,
    "debug": False,
    "points_encoded": False,
    "ch.disable": True,
    "heading": 0,
    "heading_penalty": 120,
    "pass_through": False,
}


class GraphHopper(RoadRouteProvider):
    """
    GraphHopper service requestor for route calculation.

    Attributes:
        api_key (Optional[str]): GraphHopper API authentication key.
        timeout (float): Request timeout limit in seconds.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        endpoint = config.get("endpoint", DEFAULT_GRAPHHOPPER_ENDPOINT)
        params = {**DEFAULT_GRAPHHOPPER_PARAMS, **config.get("params", {})}
        super().__init__(params=params, endpoint=endpoint, client=None)

        self.api_key: Optional[str] = config.get("api_key") or os.environ.get(
            "GRAPHHOPPER_KEY"
        )
        self.timeout: float = config.get("timeout", 10.0)

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
                "GraphHopper requires at least two coordinates (origin and destination)."
            )
            self.routes = []
            return self.routes

        common_source = coords[0]
        common_target = coords[-1]

        # Build isolated request parameters per query to prevent mutating shared state
        request_params = self.params.copy()
        request_params["point"] = [f"{coord.lat},{coord.lon}" for coord in coords]

        if self.api_key:
            request_params["key"] = self.api_key

        preprocessed_routes: List[Dict[str, Any]] = []

        try:
            response = requests.get(
                self.endpoint, params=request_params, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                paths = data.get("paths", [])

                for path in paths:
                    # GraphHopper GeoJSON returns coordinates in [lon, lat] format
                    raw_points = path.get("points", {}).get("coordinates", [])
                    route_coords = [
                        Coords(lat=point[1], lon=point[0]) for point in raw_points
                    ]

                    preprocessed_route = {
                        "route_coordinates": route_coords,
                        "common_source": common_source,
                        "common_target": common_target,
                        "router_distance": path.get("distance", 0.0),
                        "router_duration": path.get("time", 0.0) / 1000.0,  # ms to seconds
                    }
                    preprocessed_routes.append(preprocessed_route)
            else:
                logger.warning(
                    f"GraphHopper status {response.status_code}: {response.text}"
                )

        except requests.RequestException as e:
            logger.error(f"Error requesting route from GraphHopper service: {e}")

        self.routes = preprocessed_routes
        return self.routes