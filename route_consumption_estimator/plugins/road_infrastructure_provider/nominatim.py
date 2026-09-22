"""
Nominatim GIS infrastructure provider plugin implementation.

Retrieves road infrastructure attributes (e.g., max speed limits) by reverse-geocoding 
route coordinates using OpenStreetMap Nominatim / Overpass services.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

try:
    import polyline
except ImportError:
    polyline = None

from route_consumption_estimator.domain.graph_models import Coords
from route_consumption_estimator.interfaces.road_infrastructure_provider import (
    RoadInfrastructureInformationProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_NOMINATIM_URL: str = "http://localhost:8082/reverse"
DEFAULT_ROAD_ATTRIBUTES: List[str] = ["maxspeed"]
DEFAULT_POLYLINE_PRECISION: int = 6
DEFAULT_MAX_SPEED: int = 50


class Nominatim(RoadInfrastructureInformationProvider):
    """
    Nominatim GIS infrastructure provider for road telemetry and attributes.

    Attributes:
        polyline_precision (int): Decimal precision used when decoding polylines.
        default_max_speed (int): Fallback speed limit in km/h when telemetry is missing.
        timeout (float): HTTP request timeout in seconds.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        endpoint = config.get("endpoint", DEFAULT_NOMINATIM_URL)
        super().__init__(endpoint=endpoint)

        self.road_attributes: List[str] = config.get(
            "road_attributes", DEFAULT_ROAD_ATTRIBUTES
        )
        self.polyline_precision: int = config.get(
            "polyline_precision", DEFAULT_POLYLINE_PRECISION
        )
        self.default_max_speed: int = config.get(
            "default_max_speed", DEFAULT_MAX_SPEED
        )
        self.timeout: float = config.get("timeout", 5.0)

    def retrieve_road_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Retrieve road infrastructure attributes for a list of route coordinates.

        Args:
            route_coordinates (List[Coords]): List of geospatial route waypoints.

        Returns:
            Dict[str, Any]: Road infrastructure attributes mapped along coordinates.
        """
        self.road_information = {
            "coordinates": route_coordinates,
            "additional_info": [],
        }
        for attr in self.road_attributes:
            self.road_information[attr] = []

        session = requests.Session()

        for coords in route_coordinates:
            params = {
                "lat": coords.lat,
                "lon": coords.lon,
                "format": "json",
                "extratags": 1,
                "zoom": 16,  # Zoom level 16 targets roads and avoids building POIs
            }

            try:
                response = session.get(
                    self.endpoint, params=params, timeout=self.timeout
                )
                if response.status_code == 200:
                    results = response.json()
                    extratags = results.get("extratags", {})

                    for attr in self.road_attributes:
                        if attr in extratags:
                            val_str = str(extratags[attr]).split("|")[0].strip()
                            try:
                                val = int(val_str)
                            except ValueError:
                                val = -1
                            self.road_information[attr].append(val)
                        else:
                            self.road_information[attr].append(-1)

                    self.road_information["additional_info"].append(extratags)
                else:
                    logger.warning(
                        f"Nominatim returned status {response.status_code} for ({coords.lat}, {coords.lon})"
                    )
                    self._append_empty_entry()

            except requests.RequestException as e:
                logger.error(
                    f"Error requesting Nominatim road info for ({coords.lat}, {coords.lon}): {e}"
                )
                self._append_empty_entry()

        # Post-process speed limits (fill missing/default values)
        if "maxspeed" in self.road_attributes:
            self._post_process_maxspeed()

        return self.road_information

    def retrieve_road_info_by_polyline(
        self, encoded_polyline: str
    ) -> Dict[str, Any]:
        """
        Retrieve road infrastructure details by decoding an encoded polyline string.

        Args:
            encoded_polyline (str): Encoded polyline geometry string.

        Returns:
            Dict[str, Any]: Road infrastructure attributes mapped along coordinates.
        """
        if polyline is None:
            raise ImportError(
                "The 'polyline' library is required to decode polylines. "
                "Install it using 'pip install polyline'."
            )

        decoded_points = polyline.decode(
            encoded_polyline, precision=self.polyline_precision
        )
        route_coords = [
            Coords(lat=point[0], lon=point[1]) for point in decoded_points
        ]
        return self.retrieve_road_info(route_coords)

    def _append_empty_entry(self) -> None:
        """Helper method to append fallback values when an API call fails."""
        for attr in self.road_attributes:
            self.road_information[attr].append(-1)
        self.road_information["additional_info"].append({})

    def _post_process_maxspeed(self) -> None:
        """Propagate known speed limits forward and replace missing values (-1) with defaults."""
        speeds = self.road_information.get("maxspeed", [])
        if not speeds:
            return

        current_speed = self.default_max_speed
        for i in range(len(speeds)):
            if speeds[i] != -1:
                current_speed = speeds[i]
            else:
                speeds[i] = current_speed
