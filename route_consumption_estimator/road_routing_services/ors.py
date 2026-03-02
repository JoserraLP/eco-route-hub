import requests
from openrouteservice import Client, convert
from openrouteservice.directions import directions

from route_consumption_estimator.core.graph.models import Coords
from route_consumption_estimator.road_routing_services.road_routing_services_wrapper import RoadRoutingServicesWrapper


class OpenRouteService(RoadRoutingServicesWrapper):
    """
    Open Route Service requestor
    """

    def __init__(self, params: dict, endpoint: str = None):
        if not endpoint:
            endpoint = "http://localhost:8081/ors"

        super().__init__(params, endpoint)
        self._client = Client(base_url=endpoint)
        self._routes = []

    def get_routes(self, coords: list = None) -> list:
        # Define source and target to be the same over all routes
        common_source = coords[0]
        common_target = coords[-1]

        # Swap order of the coordinates (longitude, latitude)
        coords = [[item.lon, item.lat] for item in coords]

        # If there is a timeout, then return an empty list
        try:
            # Perform query using params if they exists
            if self._params:
                routes = directions(self._client, coords, alternative_routes=self._params)['routes']
            else:
                routes = directions(self._client, coords)['routes']

            # Create a list for the processed routes
            processed_routes = []

            # Check if there exists the routes
            if routes:

                for route in routes:
                    # Decode each route polyline
                    route['geometry'] = convert.decode_polyline(route['geometry'])

                    # Parse coordinates to Coords class
                    route['geometry']['coordinates'] = [Coords(lat=item[1], lon=item[0]) for item in
                                                        route['geometry']['coordinates']]

                    # Create processed route
                    processed_route = self._route_processor.process_route(
                        route_coordinates=route['geometry']['coordinates'],
                        common_source=common_source,
                        common_target=common_target)
                    # Get router service estimated distance and duration
                    processed_route['router_distance'] = route['summary']['distance']
                    processed_route['router_duration'] = route['summary']['duration']

                    # Append the processed route
                    processed_routes.append(processed_route)

            # Update the routes with the parsed geometries
            self._routes = processed_routes
        except requests.exceptions.Timeout:
            print(f"There is a timeout retrieving routes from ORS service...")
            self._routes = []

        return self._routes
