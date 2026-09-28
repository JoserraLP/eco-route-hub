"""
Route Processor module.

Coordinates route generation, geographical distance calculations, map matching,
and enrichment with infrastructure, traffic, and weather provider telemetry.
"""

import math
import logging
from typing import Any, Dict, List, Optional, Tuple

from eco_route_hub.domain.graph_models import Coords
from eco_route_hub.domain.constants import EARTH_RADIUS
from eco_route_hub.interfaces import (
    AmbientWeatherInformationProvider,
    RoadInfrastructureInformationProvider,
    RoadRouteProvider,
    RouteSegmentationProvider,
    TrafficOperationInformationProvider,
)

logger = logging.getLogger(__name__)

def calculate_distance(
        coord1_lat: float, coord1_lon: float, coord2_lat: float, coord2_lon: float
) -> float:
    """
    Calculate the Great Circle (Haversine) distance between two coordinate pairs in meters.

    Args:
        coord1_lat (float): Source latitude in degrees.
        coord1_lon (float): Source longitude in degrees.
        coord2_lat (float): Destination latitude in degrees.
        coord2_lon (float): Destination longitude in degrees.

    Returns:
        float: Distance in meters.
    """
    lon1, lat1, lon2, lat2 = map(
        math.radians, [coord1_lon, coord1_lat, coord2_lon, coord2_lat]
    )

    lon_diff = lon2 - lon1
    lat_diff = lat2 - lat1

    a = (
            math.sin(lat_diff / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(lon_diff / 2) ** 2
    )
    # Clamp to handle floating point inaccuracy
    a = min(1.0, max(0.0, a))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return c * EARTH_RADIUS


def calculate_extended_coords_and_distances(
        route_coordinates: List[Coords],
) -> Tuple[List[Coords], List[float]]:
    """
    Calculate inter-node distances along a route coordinate path.

    Args:
        route_coordinates (List[Coords]): Input list of coordinate nodes.

    Returns:
        Tuple[List[Coords], List[float]]: Extended coordinates list and step-wise distances in meters.
    """
    if not route_coordinates:
        return [], []

    route_extended_coordinates: List[Coords] = []
    distances: List[float] = []

    destination: Optional[Coords] = None

    for source, destination in zip(
            route_coordinates, route_coordinates[1:]
    ):
        distance = calculate_distance(
            source.lat, source.lon, destination.lat, destination.lon
        )
        route_extended_coordinates.append(source)
        distances.append(distance)

    if destination is not None:
        route_extended_coordinates.append(destination)
    elif route_coordinates:
        route_extended_coordinates.append(route_coordinates[0])

    return route_extended_coordinates, distances



def _normalize_provider_list(providers: Any) -> List[Any]:
    """Helper to ensure provider inputs are flattened non-None lists."""
    if providers is None:
        return []
    if isinstance(providers, list):
        return [p for p in providers if p is not None]
    return [providers]


class RouteProcessor:
    """
    Processor responsible for querying routing services and enriching routes with micro-segment attributes.
    """

    def __init__(
            self,
            route_segmentation_provider: RouteSegmentationProvider,
            road_infrastructure_providers: Any,
            road_route_providers: Any,
            traffic_operation_providers: Any = None,
            ambient_weather_providers: Any = None,
    ) -> None:
        """
        Initialize the RouteProcessor with segmentation and attribute providers.
        """
        self._route_segmentation_provider = route_segmentation_provider

        self._road_infrastructure_providers: List[
            RoadInfrastructureInformationProvider
        ] = _normalize_provider_list(road_infrastructure_providers)

        self._road_route_providers: List[
            RoadRouteProvider
        ] = _normalize_provider_list(road_route_providers)

        self._traffic_operation_providers: List[
            TrafficOperationInformationProvider
        ] = _normalize_provider_list(traffic_operation_providers)

        self._ambient_weather_providers: List[
            AmbientWeatherInformationProvider
        ] = _normalize_provider_list(ambient_weather_providers)

    def request_all_routes(self, coordinates_str: str) -> List[Dict[str, Any]]:
        """
        Parse a formatted coordinates string and request route paths from all registered routing providers.

        Args:
            coordinates_str (str): Semicolon-delimited coordinates string (e.g. "lat1,lon1;lat2,lon2").

        Returns:
            List[Dict[str, Any]]: List of processed route dictionaries.
        """
        route_coordinates: List[Coords] = []

        try:
            for coord_pair in coordinates_str.split(";"):
                parts = coord_pair.strip().split(",")
                if len(parts) == 2:
                    route_coordinates.append(
                        Coords(lat=float(parts[0]), lon=float(parts[1]))
                    )
        except (ValueError, IndexError) as err:
            logger.error(
                f"Invalid coordinates string format '{coordinates_str}': {err}"
            )
            return []

        if not route_coordinates:
            logger.warning("No valid coordinates parsed from input string.")
            return []

        routes: List[Dict[str, Any]] = []
        for road_routing_service in self._road_route_providers:
            try:
                service_routes = road_routing_service.get_routes(
                    route_coordinates
                )
                for service_route in service_routes:
                    processed = self.process_route(
                        route_coordinates=service_route["route_coordinates"],
                        common_source=service_route["common_source"],
                        common_target=service_route["common_target"],
                        router_distance=service_route.get("router_distance"),
                        router_duration=service_route.get("router_duration"),
                    )
                    routes.append(processed)
            except Exception as err:
                logger.error(
                    f"Error fetching routes from routing service '{road_routing_service}': {err}"
                )

        logger.info(f"Total candidate routes processed: {len(routes)}")
        return routes

    def process_route(
            self,
            route_coordinates: List[Coords],
            common_source: Coords,
            common_target: Coords,
            router_distance: Optional[float] = None,
            router_duration: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Process, extend, and enrich route coordinates with provider telemetry and segmentation data.

        Args:
            route_coordinates (List[Coords]): Raw sequence of route coordinates.
            common_source (Coords): Common starting coordinate node.
            common_target (Coords): Common target coordinate node.
            router_distance (Optional[float]): Distance returned by routing provider.
            router_duration (Optional[float]): Travel duration returned by routing provider.

        Returns:
            Dict[str, Any]]: Micro-segmented route information dictionary.
        """
        # Create a new list copy to avoid mutating the original input argument
        full_coordinates = [common_source] + list(route_coordinates)

        # Calculate extended coordinates and node-to-node distances
        (
            route_extended_coordinates,
            distances,
        ) = calculate_extended_coords_and_distances(full_coordinates)

        # Append common target node with trailing zero distance
        route_extended_coordinates.append(common_target)
        distances.append(0.0)

        info: Dict[str, Any] = {"distances": distances}

        # Populate road infrastructure attributes
        for road_provider in self._road_infrastructure_providers:
            road_info = road_provider.retrieve_road_info(
                route_extended_coordinates
            )
            attributes = getattr(road_provider, "road_attributes", []) or []
            for attr in attributes:
                if attr in road_info:
                    info[attr] = road_info[attr]
                    if attr == "heights":
                        info["slopes"] = (
                            self._route_segmentation_provider.calculate_slopes(
                                distances, road_info[attr]
                            )
                        )

        # Populate traffic operation attributes
        for traffic_provider in self._traffic_operation_providers:
            traffic_info = traffic_provider.retrieve_traffic_info(
                route_extended_coordinates
            )
            attributes = getattr(traffic_provider, "traffic_attributes", []) or []
            for attr in attributes:
                if attr in traffic_info:
                    info[attr] = traffic_info[attr]

        # Populate ambient weather attributes
        for weather_provider in self._ambient_weather_providers:
            weather_info = weather_provider.retrieve_ambient_weather_info(
                route_extended_coordinates
            )
            attributes = (
                    getattr(weather_provider, "ambient_weather_attributes", []) or []
            )
            for attr in attributes:
                if attr in weather_info:
                    info[attr] = weather_info[attr]

        # Apply segmentation rules and retrieve segment metadata
        self._route_segmentation_provider.segment_route(info)
        segment_info = (
            self._route_segmentation_provider.retrieve_segmented_route_information(
                full_coordinates, info
            )
        )

        if router_distance is not None:
            segment_info["router_distance"] = router_distance
        if router_duration is not None:
            segment_info["router_duration"] = router_duration

        return segment_info
