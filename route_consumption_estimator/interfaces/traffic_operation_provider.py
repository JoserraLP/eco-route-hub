from abc import ABC, abstractmethod

from route_consumption_estimator.domain import Coords


class TrafficOperationInformationProvider(ABC):

    def __init__(self, endpoint):
        self._endpoint = endpoint
        self._traffic_information = {}
        self._traffic_attributes = []

    @property
    def traffic_information(self):
        return self._traffic_information

    @traffic_information.setter
    def traffic_information(self, value):
        self._traffic_information = value

    @abstractmethod
    def retrieve_traffic_info(self, route_coordinates: list[Coords]) -> dict:
        pass

    @abstractmethod
    def retrieve_traffic_info_by_polyline(self, encoded_polyline: str) -> dict:
        pass

    @property
    def traffic_attributes(self):
        return self._traffic_attributes

    @traffic_attributes.setter
    def traffic_attributes(self, value):
        self._traffic_attributes = value
