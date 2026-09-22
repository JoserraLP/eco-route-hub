from typing import Dict, Any

import requests
from openrouteservice import Client, convert
from openrouteservice.directions import directions

from route_consumption_estimator.domain import Coords
from route_consumption_estimator.interfaces import RoadRouteProvider

ORS_ENDPOINT = "http://localhost:8081/ors"
ORS_QUERY_PARAMS = {"share_factor": 0.6, "target_count": 3, "weight_factor": 0.8}


class OpenRouteService(RoadRouteProvider):
    """
    Open Route Service requestor
    """

    def __init__(self, config: Dict[str, Any]):
        endpoint = config.get("endpoint", ORS_ENDPOINT)
        super().__init__(params=config.get("params", ORS_QUERY_PARAMS),
                         endpoint=endpoint)
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

            # Create a list for the preprocessed routes
            preprocessed_routes = []

            # Check if there exists the routes
            if routes:

                for route in routes:
                    # Decode each route polyline
                    route['geometry'] = convert.decode_polyline(route['geometry'])

                    # Parse coordinates to Coords class
                    route['geometry']['coordinates'] = [Coords(lat=item[1], lon=item[0]) for item in
                                                        route['geometry']['coordinates']]

                    preprocessed_route = {
                        'route_coordinates': route['geometry']['coordinates'],
                        'common_source': common_source,
                        'common_target': common_target,
                        'router_distance': route['summary']['distance'],
                        'router_duration': route['summary']['duration']
                    }

                    # Append the preprocessed route
                    preprocessed_routes.append(preprocessed_route)

            # Update the routes with the parsed geometries
            self._routes = preprocessed_routes
        except requests.exceptions.Timeout:
            print(f"There is a timeout retrieving routes from ORS service...")
            self._routes = []

        return self._routes
