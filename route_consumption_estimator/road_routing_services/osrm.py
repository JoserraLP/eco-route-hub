import os

import requests

from route_consumption_estimator.core.graph.models import Coords
from route_consumption_estimator.road_routing_services.road_routing_services_wrapper import RoadRoutingServicesWrapper


class OSRM(RoadRoutingServicesWrapper):
    """
    Open Source Routing Machine service requestor
    """

    def __init__(self, params, endpoint: str = None):
        if not endpoint:
            # Change the address
            if os.name == 'nt':
                endpoint = 'http://127.0.0.1:5002/route/v1/driving/'
            else:
                endpoint = 'http://localhost:5002/route/v1/driving/'
        super().__init__(params=params, endpoint=endpoint, client=None)
        self._routes = []

    def get_routes(self, coords: list = None) -> list:
        # Define source and target to be the same over all routes
        common_source = coords[0]
        common_target = coords[-1]
        # Perform query
        # If there is a timeout, then return an empty list
        try:
            response = requests.get(self._endpoint +
                                    ";".join(f"{coord.lon},{coord.lat}" for coord in coords),
                                    params=self._params)

            # Create a list for the processed routes
            processed_routes = []

            # Check if there exists the response
            if response:
                # Store the routes from response
                routes = response.json()['routes']

                for route in routes:
                    # Parse coordinates to Coords class
                    route['geometry']['coordinates'] = [Coords(lat=item[1], lon=item[0]) for item in
                                                        route['geometry']['coordinates']]

                    # Create processed route
                    processed_route = self._route_processor.process_route(
                        route_coordinates=route['geometry']['coordinates'],
                        common_source=common_source,
                        common_target=common_target)
                    # Get router service estimated distance and duration
                    processed_route['router_distance'] = route['distance']
                    processed_route['router_duration'] = route['duration']

                    # Append the processed route
                    processed_routes.append(processed_route)

            # Update the routes with the parsed geometries
            self._routes = processed_routes
        except requests.exceptions.Timeout:
            print(f"There is a timeout retrieving routes from OSRM service...")
            self._routes = []

        return self._routes
