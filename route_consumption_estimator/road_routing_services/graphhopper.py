import requests

from route_consumption_estimator.core.constants import GRAPHHOPPER_QUERY_PARAMS
from route_consumption_estimator.core.graph.models import Coords
from route_consumption_estimator.road_routing_services.road_routing_services_wrapper import RoadRoutingServicesWrapper


class GraphHopper(RoadRoutingServicesWrapper):
    """
    GraphHopper service requestor
    """

    def __init__(self, params: dict, endpoint: str = None):
        if not endpoint:
            endpoint = "https://graphhopper.com/api/1/route"
        super().__init__(params=params, endpoint=endpoint, client=None)
        self._params = params
        self._endpoint = endpoint

    def get_routes(self, coords: list = None) -> list:
        # Define source and target to be the same over all routes
        common_source = coords[0]
        common_target = coords[-1]
        # Set the coordinates as the params
        GRAPHHOPPER_QUERY_PARAMS['point'] = [f"{coord.lat},{coord.lon}" for coord in coords]
        self._params = GRAPHHOPPER_QUERY_PARAMS

        # If there is a timeout, then return an empty list
        try:
            # Perform query
            response = requests.get(self._endpoint, params=self._params)

            # Create a list for the processed routes
            processed_routes = []

            # Check if there exists the response
            if response.status_code == 200:
                # Store the routes from response
                routes = response.json()['paths']

                for route in routes:
                    # Parse coordinates to Coords class
                    route['points']['coordinates'] = [Coords(lat=item[1], lon=item[0]) for item in
                                                      route['points']['coordinates']]

                    # Create the processed route
                    processed_route = self._route_processor.process_route(
                        route_coordinates=route['points']['coordinates'],
                        common_source=common_source,
                        common_target=common_target)
                    # Get router service estimated distance and duration
                    processed_route['router_distance'] = route['distance']
                    processed_route['router_duration'] = route['time'] / 1000.0

                    # Append the processed route
                    processed_routes.append(processed_route)

            # Update the routes with the parsed geometries
            self._routes = processed_routes

        except requests.exceptions.Timeout:
            print(f"There is a timeout retrieving routes from GraphHopper service...")
            self._routes = []

        return self._routes
