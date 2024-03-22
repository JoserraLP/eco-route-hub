import requests
from openrouteservice import Client, convert
from openrouteservice.directions import directions

from route_consumption_estimator.graph.models import Coords
from route_consumption_estimator.routers.utils import process_route


class OpenRouteService:
    """
    Open Route Service requestor
    """

    def __init__(self, params: dict):
        self._routes = []
        self._params = params
        self._client = Client(base_url='http://localhost:8081/ors')

    def get_routes(self, coords: list, common_source: Coords, common_target: Coords) -> list:
        """
        Get routes from Open Route Service with the given coords

        :param coords: list of pair coordinates
        :type coords: list
        :return: routes
        :rtype: list
        """

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
                    processed_route = process_route(route_coordinates=route['geometry']['coordinates'],
                                                    common_source=common_source, common_target=common_target)
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
