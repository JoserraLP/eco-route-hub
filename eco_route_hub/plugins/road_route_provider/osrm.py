"""
OSRM (Open Source Routing Machine) routing provider plugin implementation.

Calculates vehicle routes, GeoJSON geometries, distances, and durations 
using an OSRM engine server instance.
"""

import logging
import os
from typing import Any, Dict, List

import requests

from eco_route_hub.domain.graph_models import Coords
from eco_route_hub.interfaces.road_route_provider import (
    RoadRouteProvider,
)

logger = logging.getLogger(__name__)

# Default host assignment based on target operating system
_DEFAULT_HOST: str = "127.0.0.1" if os.name == "nt" else "localhost"
DEFAULT_OSRM_ENDPOINT: str = f"http://{_DEFAULT_HOST}:5002/route/v1/driving"

DEFAULT_OSRM_PARAMS: Dict[str, Any] = {
    "alternatives": 3,
    "geometries": "geojson",
    "annotations": "nodes",
    "overview": "full",  # Full overview returns high-precision route geometries
}


class OSRM(RoadRouteProvider):
    """
    Open Source Routing Machine (OSRM) service client for route calculation.

    Attributes:
        timeout (float): Request timeout limit in seconds.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        endpoint = config.get("endpoint", DEFAULT_OSRM_ENDPOINT)
        params = {**DEFAULT_OSRM_PARAMS, **config.get("params", {})}
        super().__init__(params=params, endpoint=endpoint, client=None)

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
                "OSRM requires at least two coordinates (origin and destination)."
            )
            self.routes = []
            return self.routes

        common_source = coords[0]
        common_target = coords[-1]

        # OSRM REST API format: /route/v1/driving/{lon1},{lat1};{lon2},{lat2}
        coords_str = ";".join(f"{coord.lon},{coord.lat}" for coord in coords)
        base_endpoint = self.endpoint.rstrip("/")
        request_url = f"{base_endpoint}/{coords_str}"

        preprocessed_routes: List[Dict[str, Any]] = []

        try:
            response = requests.get(
                request_url, params=self.params, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                routes = data.get("routes", [])

                for route in routes:
                    # GeoJSON geometry stores points as [longitude, latitude]
                    raw_coords = route.get("geometry", {}).get("coordinates", [])
                    route_coords = [
                        Coords(lat=item[1], lon=item[0]) for item in raw_coords
                    ]

                    preprocessed_route = {
                        "route_coordinates": route_coords,
                        "common_source": common_source,
                        "common_target": common_target,
                        "router_distance": route.get("distance", 0.0),
                        "router_duration": route.get("duration", 0.0),
                    }
                    preprocessed_routes.append(preprocessed_route)
            else:
                logger.warning(
                    f"OSRM returned status code {response.status_code}: {response.text}"
                )

        except requests.RequestException as e:
            logger.error(f"Error requesting routes from OSRM service: {e}")
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Unexpected error parsing OSRM response payload: {e}")

        self.routes = preprocessed_routes
        return self.routes
