import math
from statistics import mean

import pandas as pd
from flask import current_app

from route_consumption_estimator.domain import Coords
from route_consumption_estimator.interfaces.route_segmentation_provider import RouteSegmentationProvider

DEFAULT_CONFIG_DICT = {
    "batching_window_size": 20,
    "smoothing_factor_alpha": 0.3,
    "slope_threshold": 12,  # maximum degrees
    "slope_variance_difference": 0.5,
    "distance_between_nodes": 50  # meters
}


class RouteSegmentator(RouteSegmentationProvider):
    def __init__(self, config=None):
        super().__init__(config)

        if config is None:
            self._config = DEFAULT_CONFIG_DICT

        self._batching_window_size = config['batching_window_size']
        self._smoothing_factor_alpha = config['smoothing_factor_alpha']
        self._slope_threshold = config['slope_threshold']
        self._distance_between_nodes = config['distance_between_nodes']
        self._slope_variance_difference = config['slope_variance_difference']

    def segment_route(self, attributes_info: dict) -> list:
        """
        Segment the route by selecting only those coordinates (by index) where there is a difference of maximum speeds
        or slopes on adjacent nodes

        :return: list with the indices of segmented route
        """
        max_speeds = attributes_info['maxspeed']
        slopes = attributes_info['slopes']

        # Valid indices (values varies)
        self._indices = [0]

        # Define first item of slope
        last_slope = attributes_info['slopes'][0]
        # Flag for storing a new segment
        new_segment = False

        # We can iterate on any of the two list as their size is the same
        for i in range(1, len(max_speeds)):

            # Check if values are different
            if max_speeds[i] != max_speeds[i - 1]:
                # Update flag
                new_segment = True

            if not new_segment and abs(slopes[i - 1] - last_slope) > self._slope_variance_difference:
                # Store new last slope value
                last_slope = slopes[i]
                # Update flag
                new_segment = True

            if new_segment:
                # Append index if new segment
                self._indices.append(i - 1)
                # Update flag
                new_segment = False
        return self._indices

    def retrieve_segmented_route_information(self, route_coordinates: list, attributes_info: dict):
        # Calculate sum of distances of the non-selected nodes
        sum_distances_segment = [sum(attributes_info['distances'][i:j]) for i, j in zip(self._indices,
                                                                                        self._indices[1:])]

        # Calculate mean of slopes of the non-selected nodes
        mean_slope_segment = [mean(attributes_info['slopes'][i:j]) for i, j in zip(self._indices,
                                                                                   self._indices[1:])]

        # return the segments and info
        segment_info = {'segments': [route_coordinates[i] for i in self._indices],
                        'segments_representation': [route_coordinates[i] for i in self._indices],
                        'heights': [attributes_info['heights'][i] for i in self._indices],
                        'maxspeed': [attributes_info['maxspeed'][i] for i in self._indices][:-1],
                        'temp': [attributes_info['temp'][i] for i in self._indices][:-1],
                        # Last item of max speed removed as it is not used
                        'distances': sum_distances_segment,
                        'slopes': mean_slope_segment}

        return segment_info

    def calculate_slopes(self, distances: list, heights: list) -> list:
        """
        Calculate the slopes of the segments based on the distance and heights of the coordinates

        :param distances: distances of the route segments
        :type distances: list
        :param heights: heights of the route segments
        :type heights: list
        :return: list with the slope segments
        :rtype: list
        """
        # Create a dataframe with the distances, heights
        df = pd.DataFrame(list(zip(distances, heights)), columns=['distance', 'height'])
        # Create a column with mean of heights with the window size -> use a rolling function with "center"
        # flag to enable next and previous values
        df['mean_height'] = df['height'].rolling(self._batching_window_size, center=True).mean()

        # Create a column with distance traveled -> Iterate over a loop
        distance_traveled = [0]
        for i in range(1, len(df)):
            # distance_traveled[i] = 0.5*(speed_m_s[i] + speed_m_s[i-1]) + distance_traveled[i-1]
            distance_traveled.append(
                0.5 * (df.loc[i, 'distance'] + df.loc[i - 1, 'distance']) + distance_traveled[i - 1])
        # Store the list
        df['distance_traveled'] = distance_traveled

        # Create a column with the slope -> Iterate over a loop
        slope = [0]
        for i in range(1, len(df)):
            # Calculate difference of heights
            height_difference = df.loc[i, 'mean_height'] - df.loc[i - 1, 'mean_height']
            # Calculate difference of distance traveled
            distance_traveled_difference = df.loc[i, 'distance_traveled'] - df.loc[i - 1, 'distance_traveled']

            # Check the difference of distance traveled is valid
            if distance_traveled_difference != 0:
                slope.append((height_difference / distance_traveled_difference) * 100)
            else:
                # Otherwise set 0
                slope.append(0)

        # Store the list
        df['slope'] = slope
        # Replace slope NaN values with 0
        df['slope'] = df['slope'].fillna(0)
        # Limit the values of the slope based on a realistic range
        df['slope'] = df['slope'].clip(lower=-self._slope_threshold, upper=self._slope_threshold)

        return list(df['slope'])

    def calculate_intermediate_coords(self, source: Coords, destination: Coords, distance: float):
        """
        Calculate intermediate coordinates

        :param source: Source coordinates
        :type source: Coords
        :param destination: Destination coordinates
        :type destination: Coords
        :param distance: distance between the source and destination
        :type distance: float
        :return: list with intermediate coords and the number of segments
        """
        # Initialize intermediate coords list
        intermediate_coords = []
        # Calculate the difference of longitude and latitude (destination-source)
        delta_lon = destination.lon - source.lon
        delta_lat = destination.lat - source.lat
        # Calculate the number of segments
        num_segments = math.ceil(distance / self._distance_between_nodes)
        # Calculate the proportion per each segment
        delta_t = 1 / num_segments
        # Multiply longitude and latitude by the proportion
        cons_lon = delta_lon * delta_t
        cons_lat = delta_lat * delta_t

        # Store actual longitude and latitude
        lon_act = source.lon
        lat_act = source.lat

        # Iterate over the segmentes
        for i in range(num_segments - 1):
            # Sum actual values with the constant
            lon_act += cons_lon
            lat_act += cons_lat
            # Append intermediate coords
            intermediate_coords.append(Coords(lat=lat_act, lon=lon_act))

        return intermediate_coords, num_segments
