from typing import Dict, Any

import polyline
import requests

from route_consumption_estimator.domain import Coords
from route_consumption_estimator.interfaces import RoadInfrastructureInformationProvider

HEIGHT_API_URL = 'http://localhost:5000/v1/srtm30mspain?locations='
DEFAULT_POLYLINE_PRECISION = 6


def split_list(list_data: list, n: int):
    """
    Split a list into list of n size

    :param list_data: list with the data
    :type list_data: list
    :param n: number of items per sublist
    :type n: int
    :return:
    """
    # Iterate over the list and retrieve the requested sublist
    for i in range(0, len(list_data), n):
        yield list_data[i:i + n]

OPENTOPODATA_ROAD_ATTRIBUTES = ["heights"]


class OpenTopoData(RoadInfrastructureInformationProvider):

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config.get("endpoint", HEIGHT_API_URL))
        self._road_attributes = config.get("road_attributes", OPENTOPODATA_ROAD_ATTRIBUTES)

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
