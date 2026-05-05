import os
from typing import Dict, Any

import requests

from route_consumption_estimator.domain import Coords
from route_consumption_estimator.interfaces import RoadRoutingServiceProvider

GRAPHHOPPER_ENDPOINT = "https://graphhopper.com/api/1/route"
GRAPHHOPPER_QUERY_PARAMS = {
    "profile": "car",
    "point": '',
    "locale": "en",
    "elevation": "false",
    "optimize": "false",
    "instructions": "true",
    "calc_points": "true",
    "debug": "false",
    "points_encoded": "false",
    "ch.disable": "true",
    "heading": "0",
    "heading_penalty": "120",
    "pass_through": "false",
    "round_trip.distance": "10000",
    "round_trip.seed": "0",
    "key": os.environ.get("GRAPHHOPPER_KEY")
}


class GraphHopper(RoadRoutingServiceProvider):
    """
    GraphHopper service requestor
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(params=config.get("params", GRAPHHOPPER_QUERY_PARAMS),
                         endpoint=config.get("endpoint", GRAPHHOPPER_ENDPOINT),
                         client=None)
        self._routes = []

    def get_routes(self, coords: list = None) -> list:
        # Define source and target to be the same over all routes
        common_source = coords[0]
        common_target = coords[-1]
        # Set the coordinates as the params
        self._params['point'] = [f"{coord.lat},{coord.lon}" for coord in coords]

        # If there is a timeout, then return an empty list
        try:
            # Perform query
            response = requests.get(self._endpoint, params=self._params)

            # Create a list for the preprocessed routes
            preprocessed_routes = []

            # Check if there exists the response
            if response.status_code == 200:
                # Store the routes from response
                routes = response.json()['paths']

                for route in routes:
                    # Parse coordinates to Coords class
                    route['points']['coordinates'] = [Coords(lat=item[1], lon=item[0]) for item in
                                                      route['points']['coordinates']]

                    preprocessed_route = {
                        'route_coordinates': route['points']['coordinates'],
                        'common_source': common_source,
                        'common_target': common_target,
                        'router_distance': route['distance'],
                        'router_duration': route['time'] / 1000.0
                    }

                    # Append the processed route
                    preprocessed_routes.append(preprocessed_route)

            # Update the routes with the parsed geometries
            self._routes = preprocessed_routes

        except requests.exceptions.Timeout:
            print(f"There is a timeout retrieving routes from GraphHopper service...")
            self._routes = []

        return self._routes
