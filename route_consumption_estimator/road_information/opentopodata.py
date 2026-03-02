import polyline
import requests

from route_consumption_estimator.core.graph.models import Coords
from route_consumption_estimator.road_information.road_information_wrapper import RoadInformationWrapper
from route_consumption_estimator.road_information.utils import split_list
from route_consumption_estimator.core.constants import HEIGHT_API_URL, DEFAULT_POLYLINE_PRECISION


class OpenTopoData(RoadInformationWrapper):

    def __init__(self, endpoint=HEIGHT_API_URL):
        super().__init__(endpoint)

    def retrieve_road_info(self, route_coordinates: list[Coords]) -> list:
        """
        Retrieve heights values of the input route coordinates

        :param route_coordinates: input route coordinates
        :type route_coordinates: list[Coords]
        :return: list with associated heights
        :rtype: list
        """
        split_coordinates = list(split_list(route_coordinates, n=1001))

        heights = []
        # Iterate over the list coordinates
        for inner_list in split_coordinates:
            # Append the coordinates to the query
            request_str = self._endpoint + '|'.join(f'{item.lat},{item.lon}' for item in inner_list)

            # Perform request and parse to json
            results = requests.get(url=request_str).json()

            # Append heights results to list
            heights += [result['elevation'] for result in results['results']]

        self._road_information = {
            "coordinates": route_coordinates,
            "heights": heights
        }

        return self._road_information

    def retrieve_road_info_by_polyline(self, encoded_polyline: str):
        # Append the encoded polyline to the query
        request_str = HEIGHT_API_URL + encoded_polyline

        # Perform request and parse to json
        results = requests.get(url=request_str).json()

        # Add heights results
        heights = [result['elevation'] for result in results['results']]

        self._road_information = {
            "coordinates": polyline.decode(encoded_polyline, DEFAULT_POLYLINE_PRECISION),
            "heights": heights
        }

        return heights
