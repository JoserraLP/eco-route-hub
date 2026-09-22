import math

from route_consumption_estimator.domain import Coords
from route_consumption_estimator.domain.constants import EARTH_RADIUS
from route_consumption_estimator.interfaces import RouteSegmentationProvider


def calculate_distance(coord1_lat, coord1_lon, coord2_lat, coord2_lon):
    # Parse degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [coord1_lon, coord1_lat, coord2_lon, coord2_lat])

    # Haversine formula
    # Calculate difference of coordinates
    lon_diff = lon2 - lon1
    lat_diff = lat2 - lat1
    # Calculate a value
    a = math.sin(lat_diff / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(lon_diff / 2) ** 2
    # Calculate C value
    c = 2 * math.asin(math.sqrt(a))

    return c * EARTH_RADIUS


def calculate_extended_coords_and_distances(route_coordinates: list):
    """
    Calculate the extended route (with additional coordinates) along with its distances between nodes

    :param route_coordinates: input route coordinates
    :type route_coordinates: list
    :return: list of coordinates of extended route and its distances
    """

    # Create list for extended nodes and distances
    route_extended_coordinates, distances = [], []

    # Define destination as None
    destination = None

    # Iterate over the nodes in packs of two
    for source, destination in zip(route_coordinates, route_coordinates[1:]):
        # Calculate distance between source and destination
        # distance = gd((source.lon, source.lat), (destination.lon, destination.lat)).meters

        # Calculate distance between source and destination
        distance = calculate_distance(source.lat, source.lon, destination.lat, destination.lon)

        # Add source node to extended route
        route_extended_coordinates.append(source)

        # Append the distance
        distances.append(distance)

    # Add destination node outside the loop as it is the last element
    route_extended_coordinates.append(destination)

    return route_extended_coordinates, distances


class RouteProcessor:

    def __init__(self,
                 route_segmentation_provider: RouteSegmentationProvider,
                 road_infrastructure_providers: list,
                 road_route_providers: list,
                 traffic_operation_providers: list = None,
                 ambient_weather_providers: list = None,
                 ):
        super().__init__()

        self._road_infrastructure_providers = road_infrastructure_providers \
            if isinstance(road_infrastructure_providers, list) else [road_infrastructure_providers]
        self._road_route_providers = road_route_providers \
            if isinstance(road_route_providers, list) else [road_route_providers]
        self._traffic_operation_providers = traffic_operation_providers \
            if isinstance(traffic_operation_providers, list) else [traffic_operation_providers]
        self._ambient_weather_providers = ambient_weather_providers \
            if isinstance(ambient_weather_providers, list) else [ambient_weather_providers]

        self._route_segmentation_provider = route_segmentation_provider

    def request_all_routes(self, coordinates_str: str):
        route_coordinates = [Coords(lat=float(coordinates.split(',')[0]), lon=float(coordinates.split(',')[1]))
                             for coordinates in coordinates_str.split(';')]

        routes = []
        for road_routing_service in self._road_route_providers:
            service_routes = road_routing_service.get_routes(route_coordinates)
            for service_route in service_routes:
                routes.append(self.process_route(
                    route_coordinates=service_route['route_coordinates'],
                    common_source=service_route['common_source'],
                    common_target=service_route['common_target'],
                    router_distance=service_route['router_distance'],
                    router_duration=service_route['router_duration']
                ))

        print(f"Total possible routes {len(routes)}")

        return routes

    def process_route(self,
                      route_coordinates: list,
                      common_source: Coords,
                      common_target: Coords,
                      router_distance: float = None,
                      router_duration: float = None) -> dict:

        """
        Process and segment the input route coordinates and return its related values (segments, heights, max_speed,
        distances and slopes)

        :param common_source: source coordinates
        :type common_source: Coords
        :param common_target: target coordinates
        :type common_target: Coords
        :param route_coordinates: coordinates of the input route
        :type route_coordinates: list
        :param router_distance: router distance
        :type router_distance: float
        :param router_duration: router duration
        :type router_duration: float
        :return: dictionary with the processed route (segments, heights, max_speed, distances and slopes)
        """
        # Append to routes coordinates the common source
        route_coordinates.insert(0, common_source)

        # Calculate the extended coordinates along with distances
        route_extended_coordinates, distances = calculate_extended_coords_and_distances(route_coordinates)

        # Append to extended route the common target with a distance of 0 (default)
        route_extended_coordinates.append(common_target)
        distances.append(0)

        info = {'distances': distances}
        for road_infrastructure_provider in self._road_infrastructure_providers:
            road_info = road_infrastructure_provider.retrieve_road_info(route_extended_coordinates)
            # maxspeed and heights are mandatory
            if road_infrastructure_provider.road_attributes:
                info.update({k: [] for k in road_infrastructure_provider.road_attributes})
                # Iterate over the road attributes
                for attribute in road_infrastructure_provider.road_attributes:
                    info[attribute] = road_info[attribute]
                    if attribute == 'heights':
                        info['slopes'] = self._route_segmentation_provider.calculate_slopes(distances,
                                                                                            road_info[attribute])

        # Include any other additional info
        for traffic_operation_provider in self._traffic_operation_providers:
            if traffic_operation_provider:
                traffic_info = traffic_operation_provider.retrieve_traffic_info(route_extended_coordinates)
                if traffic_operation_provider.traffic_attributes:
                    info.update({k: [] for k in traffic_operation_provider.traffic_attributes})
                    # Iterate over the traffic attributes
                    for attribute in traffic_operation_provider.traffic_attributes:
                        info[attribute] = traffic_info[attribute]

        for ambient_weather_provider in self._ambient_weather_providers:
            if ambient_weather_provider:
                ambient_weather_info = ambient_weather_provider.retrieve_ambient_weather_info(route_extended_coordinates)
                if ambient_weather_provider.ambient_weather_attributes:
                    info.update({k: [] for k in ambient_weather_provider.ambient_weather_attributes})
                    # Iterate over the ambient weather attributes
                    for attribute in ambient_weather_provider.ambient_weather_attributes:
                        info[attribute] = ambient_weather_info[attribute]

        # Retrieve indices for segmented route
        self._route_segmentation_provider.segment_route(info)

        segment_info = self._route_segmentation_provider.retrieve_segmented_route_information(route_coordinates, info)

        # Also include additional information
        if router_distance:
            segment_info['router_distance'] = router_distance
        if router_duration:
            segment_info['router_duration'] = router_duration
        return segment_info
