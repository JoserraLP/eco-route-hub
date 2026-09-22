from abc import ABC, abstractmethod

from route_consumption_estimator.domain.graph_models import Coords


class AmbientWeatherInformationProvider(ABC):

    def __init__(self, endpoint):
        self._endpoint = endpoint
        self._ambient_weather_information = {}
        self._ambient_weather_attributes = []

    @property
    def ambient_weather_information(self):
        return self._ambient_weather_information

    @ambient_weather_information.setter
    def ambient_weather_information(self, value):
        self._ambient_weather_information = value

    @abstractmethod
    def retrieve_ambient_weather_info(self, route_coordinates: list[Coords]) -> dict:
        pass

    @abstractmethod
    def retrieve_ambient_weather_info_by_polyline(self, encoded_polyline: str) -> dict:
        pass

    @property
    def ambient_weather_attributes(self):
        return self._ambient_weather_attributes

    @ambient_weather_attributes.setter
    def ambient_weather_attributes(self, value):
        self._ambient_weather_attributes = value
