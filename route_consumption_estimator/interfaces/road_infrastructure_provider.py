from abc import ABC, abstractmethod

from route_consumption_estimator.domain import Coords


class RoadInfrastructureInformationProvider(ABC):

    def __init__(self, endpoint):
        self._endpoint = endpoint
        self._road_information = {}
        self._road_attributes = []

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

    @property
    def road_attributes(self):
        return self._road_attributes

    @road_attributes.setter
    def road_attributes(self, value):
        self._road_attributes = value
