import polyline
import requests

from route_consumption_estimator.core.graph.models import Coords
from route_consumption_estimator.road_information.road_information_wrapper import RoadInformationWrapper
from route_consumption_estimator.core.constants import HEIGHT_API_URL, NOMINATIM_ROAD_ATTRIBUTES, NOMINATIM_ADD_PARAMS, \
    DEFAULT_MAX_SPEED, DEFAULT_POLYLINE_PRECISION


class Nominatim(RoadInformationWrapper):

    def __init__(self, endpoint=HEIGHT_API_URL, road_attributes=NOMINATIM_ROAD_ATTRIBUTES):
        super().__init__(endpoint)
        self._road_attributes = road_attributes

    def retrieve_road_info(self, route_coordinates: list[Coords]) -> list:
        """
        Retrieve extra info values of the input route coordinates

        :param route_coordinates: input route coordinates
        :type route_coordinates: list[Coords]
        :return: list with associated extra road info
        :rtype: list
        """

        self._road_information = {
                                     "coordinates": route_coordinates,
                                     "additional_info": []
                                 } | {str(attribute): [] for attribute in self._road_attributes}

        for coordinates in route_coordinates:
            # Append the coordinates to the query
            request_str = self._endpoint + "lat=" + str(coordinates.lat) + "&lon=" + \
                          str(coordinates.lon) + NOMINATIM_ADD_PARAMS

            # Perform request and parse to json
            results = requests.get(url=request_str).json()

            if 'extratags' in results:
                extratags = results['extratags']

                for road_attribute in self._road_attributes:
                    # Append value or -1 by default
                    self._road_information[road_attribute].append(int(extratags.pop(road_attribute).split("|")[0])
                                                                  if road_attribute in extratags else -1)

                # Append additional info
                self._road_information["additional_info"].append(results['extratags'])
            else:
                # Append -1 as there is no information
                for road_attribute in self._road_attributes:
                    self._road_information[road_attribute] = -1

        # Process and extend maximum speed info
        for i in range(len(self._road_information["maxspeed"]) - 2):
            # Get current and next speed
            cur_max_speed = self._road_information["maxspeed"]
            next_max_speed = self._road_information["maxspeed"]
            if cur_max_speed == -1:
                # This value is default
                self._road_information["maxspeed"][i] = DEFAULT_MAX_SPEED
            # Check if default value to extend it from previous value
            if next_max_speed == -1:
                self._road_information["maxspeed"][i + 1] = cur_max_speed

        return self._road_information

    def retrieve_road_info_by_polyline(self, encoded_polyline: str) -> dict:
        performed_route_coords = polyline.decode(encoded_polyline, DEFAULT_POLYLINE_PRECISION)

        # Parse polyline into list of coords
        performed_route_coords = [Coords(lat=item[0], lon=item[1]) for item in performed_route_coords]

        return self.retrieve_road_info(performed_route_coords)
