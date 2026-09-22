
from abc import ABC

from route_consumption_estimator.domain import RouteModel, VehicleModel


class RouteSegmentationProvider(ABC):

    def __init__(self, config: dict = None):
        self._indices = []
        self._config = config

    def segment_route(self, attributes_info: dict) -> list:
        """
        Segment the route by selecting only those coordinates (by index) where there is a difference based on arguments

        :param attributes_info: attributes info per pair of coordinates
        :type attributes_info: dict

        :return: list with the indices of segmented route
        """
        pass

    def retrieve_segmented_route_information(self, route_coordinates: list, attributes_info: dict):
        """
        Retrieve all the information related to the segmented route


        :param route_coordinates: route coordinates
        :type route_coordinates: list
        :param attributes_info: attributes info per pair of coordinates
        :type attributes_info: dict

        :return: dict with segmented route information
        """
        pass

    @property
    def indices(self):
        """Get the value of indices."""
        return self._indices

    @indices.setter
    def indices(self, value):
        """Set the value of indices."""
        self._indices = value
