from abc import ABC, abstractmethod

from route_consumption_estimator.core.graph.models import Coords


class RoadInformationWrapper(ABC):

    def __init__(self, endpoint):
        self._endpoint = endpoint
        self._road_information = {}

    @property
    def road_information(self):
        return self._road_information

    @road_information.setter
    def road_information(self, value):
        self._road_information = value

    @abstractmethod
    def retrieve_road_info(self, route_coordinates: list[Coords]) -> dict:
        pass

    @abstractmethod
    def retrieve_road_info_by_polyline(self, encoded_polyline: str) -> dict:
        pass
