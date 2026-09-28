"""
OpenTopoData GIS infrastructure provider plugin implementation.

Retrieves elevation and height profiles for route coordinates using an OpenTopoData 
service instance (e.g., SRTM 30m dataset).
"""

import logging
from typing import Any, Dict, Generator, List, Optional

import requests

try:
    import polyline
except ImportError:
    polyline = None

from eco_route_hub.domain.graph_models import Coords
from eco_route_hub.interfaces.road_infrastructure_provider import (
    RoadInfrastructureInformationProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENTOPODATA_URL: str = "http://localhost:5000/v1/srtm30mspain"
DEFAULT_ROAD_ATTRIBUTES: List[str] = ["heights"]
DEFAULT_POLYLINE_PRECISION: int = 6
DEFAULT_BATCH_SIZE: int = 100  # Safe max coordinate limit per HTTP GET request


def _chunk_list(data: List[Any], chunk_size: int) -> Generator[List[Any], None, None]:
    """Yield successive chunks from a list for batch API queries."""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


class OpenTopoData(RoadInfrastructureInformationProvider):
    """
    OpenTopoData elevation provider for road height telemetry.

    Attributes:
        polyline_precision (int): Decimal precision used when decoding polylines.
        batch_size (int): Maximum number of coordinate points per HTTP request chunk.
        timeout (float): HTTP request timeout in seconds.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        endpoint = config.get("endpoint", DEFAULT_OPENTOPODATA_URL)
        super().__init__(endpoint=endpoint)

        self.road_attributes: List[str] = config.get(
            "road_attributes", DEFAULT_ROAD_ATTRIBUTES
        )
        self.polyline_precision: int = config.get(
            "polyline_precision", DEFAULT_POLYLINE_PRECISION
        )
        self.batch_size: int = config.get("batch_size", DEFAULT_BATCH_SIZE)
        self.timeout: float = config.get("timeout", 10.0)

    def retrieve_road_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Retrieve elevation heights for a list of route coordinates.

        Args:
            route_coordinates (List[Coords]): Sequence of route waypoints.

        Returns:
            Dict[str, Any]: Elevation profile mapped along coordinates.
        """
        if not route_coordinates:
            self.road_information = {"coordinates": [], "heights": []}
            return self.road_information

        heights: List[Optional[float]] = []
        session = requests.Session()

        # Sanitize endpoint base URL (strip existing query parameters if present)
        base_url = self.endpoint.split("?")[0] if self.endpoint else DEFAULT_OPENTOPODATA_URL

        for chunk in _chunk_list(route_coordinates, self.batch_size):
            locations_str = "|".join(f"{c.lat},{c.lon}" for c in chunk)
            params = {"locations": locations_str}

            try:
                response = session.get(
                    base_url, params=params, timeout=self.timeout
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    for res in results:
                        heights.append(res.get("elevation"))
                else:
                    logger.warning(
                        f"OpenTopoData status {response.status_code} for chunk of size {len(chunk)}"
                    )
                    heights.extend([None] * len(chunk))

            except requests.RequestException as e:
                logger.error(f"Error requesting OpenTopoData elevation: {e}")
                heights.extend([None] * len(chunk))

        self.road_information = {
            "coordinates": route_coordinates,
            "heights": heights,
        }

        return self.road_information

    def retrieve_road_info_by_polyline(
        self, encoded_polyline: str
    ) -> Dict[str, Any]:
        """
        Retrieve elevation heights by decoding an encoded polyline string.

        Args:
            encoded_polyline (str): Encoded polyline geometry string.

        Returns:
            Dict[str, Any]: Elevation attributes mapped along decoded coordinates.
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
