
from abc import ABC, abstractmethod

from route_consumption_estimator.core.route.route_processor import RouteProcessor


class RoadRoutingServicesWrapper(ABC):

    def __init__(self, params: dict, endpoint: str = None, client: str = None):
        self._endpoint = endpoint
        self._client = client
        self._routes = []
        self._params = params
        self._route_processor = RouteProcessor()

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

    @abstractmethod
    def get_routes(self, coords: list) -> dict:
        """
        Get routes from service with the given coords

        :param coords: list of Coords info
        :type coords: list
        :return: routes
        :rtype: list
        """
        pass
