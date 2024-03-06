import requests

from route_consumption_estimator.graph.models import Coords
from route_consumption_estimator.routers.utils import process_route


class OSRM:
    """
    Open Source Routing Machine service requestor
    """

    def __init__(self, params: dict):
        self._routes = []
        self._params = params

    def get_routes(self, coords: list, common_source: Coords, common_target: Coords) -> list:
        """
        Get routes from OSRM service with the given coords

        :param coords: list of Coords info
        :type coords: list
        :return: routes
        :rtype: list
        """
        # Perform query
        response = requests.get("https://router.project-osrm.org/route/v1/driving/" +
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
                processed_route = process_route(route_coordinates=route['geometry']['coordinates'],
                                                common_source=common_source, common_target=common_target)
                # Get router service estimated distance and duration
                processed_route['router_distance'] = route['distance']
                processed_route['router_duration'] = route['duration']

                # Append the processed route
                processed_routes.append(processed_route)

        # Update the routes with the parsed geometries
        self._routes = processed_routes

        return self._routes

    @property
    def routes(self):
        """
        Getter of routes

        :return: routes
        """
        return self._routes

    @routes.setter
    def routes(self, routes: list):
        """
        Setter of routes

        :param routes: routes
        :return:
        """
        self._routes = routes

    @property
    def params(self):
        """
        Getter of params

        :return: params
        """
        return self._params

    @params.setter
    def params(self, params: dict):
        """
        Setter of params

        :param params: params
        :return:
        """
        self._params = params
