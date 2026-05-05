import math
from statistics import mean

import pandas as pd
from flask import current_app

from route_consumption_estimator.domain.constants import EARTH_RADIUS
from route_consumption_estimator.domain import Coords


def calculate_distance(coord1_lat, coord1_lon, coord2_lat, coord2_lon):
    # Parse degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [coord1_lon, coord1_lat, coord2_lon, coord2_lat])

    # Haversine formula
    # Calculate difference of coordinates
    lon_diff = lon2 - lon1
    lat_diff = lat2 - lat1
    # Calculate a value
    a = math.sin(lat_diff / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(lon_diff / 2) ** 2
    # Calculate C value
    c = 2 * math.asin(math.sqrt(a))

    return c * EARTH_RADIUS


def calculate_extended_coords_and_distances(route_coordinates: list):
    """
    Calculate the extended route (with additional coordinates) along with its distances between nodes

    :param route_coordinates: input route coordinates
    :type route_coordinates: list
    :return: list of coordinates of extended route and its distances
    """

    # Create list for extended nodes and distances
    route_extended_coordinates, distances = [], []

    # Define destination as None
    destination = None

    # Iterate over the nodes in packs of two
    for source, destination in zip(route_coordinates, route_coordinates[1:]):
        # Calculate distance between source and destination
        # distance = gd((source.lon, source.lat), (destination.lon, destination.lat)).meters

        # Calculate distance between source and destination
        distance = calculate_distance(source.lat, source.lon, destination.lat, destination.lon)

        # Add source node to extended route
        route_extended_coordinates.append(source)

        # Append the distance
        distances.append(distance)

    # Add destination node outside the loop as it is the last element
    route_extended_coordinates.append(destination)

    return route_extended_coordinates, distances


class RouteProcessor:

    def __init__(self, road_information_providers: list,
                 batching_window_size=None,
                 slope_threshold=None,
                 distance_between_nodes=None,
                 slope_variance_difference=None):
        current_app_config = current_app.config["APP_CONFIG"].system

        self._batching_window_size = batching_window_size if batching_window_size \
            else current_app_config.batching_window_size
        self._slope_threshold = slope_threshold if slope_threshold \
            else current_app_config.slope_threshold
        self._distance_between_nodes = distance_between_nodes if distance_between_nodes \
            else current_app_config.distance_between_nodes
        self._slope_variance_difference = slope_variance_difference if slope_variance_difference \
            else current_app_config.slope_variance_difference
        self._road_information_providers = road_information_providers \
            if isinstance(road_information_providers, list) else [road_information_providers]

    def process_route(self, route_coordinates: list,
                      common_source: Coords,
                      common_target: Coords,
                      router_distance: float = None,
                      router_duration: float = None) -> dict:

        """
        Process and segment the input route coordinates and return its related values (segments, heights, max_speed,
        distances and slopes)

        :param common_source: source coordinates
        :type common_source: Coords
        :param common_target: target coordinates
        :type common_target: Coords
        :param route_coordinates: coordinates of the input route
        :type route_coordinates: list
        :param router_distance: router distance
        :type router_distance: float
        :param router_duration: router duration
        :type router_duration: float
        :return: dictionary with the processed route (segments, heights, max_speed, distances and slopes)
        """
        # Append to routes coordinates the common source
        route_coordinates.insert(0, common_source)

        # Calculate the extended coordinates along with distances
        route_extended_coordinates, distances = calculate_extended_coords_and_distances(route_coordinates)

        # Append to extended route the common target with a distance of 0 (default)
        route_extended_coordinates.append(common_target)
        distances.append(0)

        heights, max_speeds, slopes = [], [], []

        for road_information_provider in self._road_information_providers:
            road_info = road_information_provider.retrieve_road_info(route_extended_coordinates)
            # Retrieve heights to calculate slopes
            if 'heights' in road_info:
                heights = road_info["heights"]
                slopes = self.calculate_slopes(distances, heights)
            # If maximum speed on road information calculate segmented route
            if 'maxspeed' in road_info:
                max_speeds = road_info["maxspeed"]

        # Retrieve indices for segmented route
        # This method is commented as it removes too much points
        indices = self.segment_route(max_speeds, slopes)

        # Calculate sum of distances of the non-selected nodes
        sum_distances_segment = [sum(distances[i:j]) for i, j in zip(indices,
                                                                     indices[1:])]

        # Calculate mean of slopes of the non-selected nodes
        mean_slope_segment = [mean(slopes[i:j]) for i, j in zip(indices,
                                                                indices[1:])]

        # return the segments (also its representation), heights, maximum speeds, distances and slopes
        segment_info = {'segments': [route_extended_coordinates[i] for i in indices],
                        'segments_representation': [route_extended_coordinates[i] for i in range(len(max_speeds))],
                        'heights': [heights[i] for i in indices],
                        'max_speed': [max_speeds[i] for i in indices][:-1],
                        # Last item of max speed removed as it is not used
                        'distances': sum_distances_segment,
                        'slopes': mean_slope_segment}
        if router_distance:
            segment_info['router_distance'] = router_distance
        if router_duration:
            segment_info['router_duration'] = router_duration
        return segment_info

    def segment_route(self, max_speeds: list, slopes: list) -> list:
        """
        Segment the route by selecting only those coordinates (by index) where there is a difference of maximum speeds
        or slopes on adjacent nodes

        :param max_speeds: maximum speeds per a pair of coordinates
        :type max_speeds: list
        :param slopes: slopes per a pair of coordinates
        :type slopes: list

        :return: list with the indices of segmented route
        """
        # First remove the last maximum speed item as it will not be used. One more item than slopes
        max_speeds = max_speeds[:-1]

        # Valid indices (values varies)
        indices = [0]

        # Define first item of slope
        last_slope = slopes[0]
        # Flag for storing a new segment
        new_segment = False

        # We can iterate on any of the two list as their size is the same
        for i in range(1, len(max_speeds)):

            # Check if values are different
            if max_speeds[i] != max_speeds[i - 1]:
                # Update flag
                new_segment = True

            if not new_segment and abs(slopes[i] - last_slope) > self._slope_variance_difference:
                # Store new last slope value
                last_slope = slopes[i]
                # Update flag
                new_segment = True

            if new_segment:
                # Append index if new segment
                indices.append(i)
                # Update flag
                new_segment = False
        return indices

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
