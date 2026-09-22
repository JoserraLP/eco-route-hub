import os
from typing import Dict, Any

import requests

from route_consumption_estimator.domain import Coords
from route_consumption_estimator.interfaces import RoadRouteProvider

LINUX_ENDPOINT = "localhost"
WINDOWS_ENDPOINT = "127.0.0.1"
OSRM_ENDPOINT = f"http://{WINDOWS_ENDPOINT if os.name == 'nt' else LINUX_ENDPOINT}:5002/route/v1/driving/"
OSRM_QUERY_PARAMS = {
    "alternatives": 3,
    "geometries": "geojson",
    "annotations": "nodes",
    "overview": "full"  # More precise routing coordinates
}


class OSRM(RoadRouteProvider):
    """
    Open Source Routing Machine service requestor
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(params=config.get("params", OSRM_QUERY_PARAMS),
                         endpoint=config.get("endpoint", OSRM_ENDPOINT),
                         client=None)
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

            # Create a list for the preprocessed routes
            preprocessed_routes = []

            # Check if there exists the response
            if response:
                # Store the routes from response
                routes = response.json()['routes']

                for route in routes:
                    # Parse coordinates to Coords class
                    route['geometry']['coordinates'] = [Coords(lat=item[1], lon=item[0]) for item in
                                                        route['geometry']['coordinates']]

                    preprocessed_route = {
                        'route_coordinates': route['geometry']['coordinates'],
                        'common_source': common_source,
                        'common_target': common_target,
                        'router_distance': route['distance'],
                        'router_duration': route['duration']
                    }

                    # Append the preprocessed route
                    preprocessed_routes.append(preprocessed_route)

            # Update the routes with the parsed geometries
            self._routes = preprocessed_routes
        except requests.exceptions.Timeout:
            print(f"There is a timeout retrieving routes from OSRM service...")
            self._routes = []

        return self._routes
