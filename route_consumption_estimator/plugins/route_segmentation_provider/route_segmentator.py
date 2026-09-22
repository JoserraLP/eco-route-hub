"""
Route segmentator plugin implementation.

Segments route coordinates and telematics based on attribute changes (max speed, slope variation)
and provides elevation slope calculation and intermediate coordinate interpolation.
"""

import logging
import math
from statistics import mean
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from route_consumption_estimator.domain.graph_models import Coords
from route_consumption_estimator.interfaces.route_segmentation_provider import (
    RouteSegmentationProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "batching_window_size": 20,
    "smoothing_factor_alpha": 0.3,
    "slope_threshold": 12.0,  # Maximum slope threshold in percentage
    "slope_variance_difference": 0.5,
    "distance_between_nodes": 50.0,  # Step distance in meters
}


class RouteSegmentator(RouteSegmentationProvider):
    """
    Route segmentation provider for identifying homogeneous route sub-segments.

    Attributes:
        batching_window_size (int): Window size for rolling average smoothing of heights.
        smoothing_factor_alpha (float): Alpha factor for exponential smoothing.
        slope_threshold (float): Maximum physical slope limit threshold.
        slope_variance_difference (float): Slope delta threshold triggering a new segment boundary.
        distance_between_nodes (float): Target distance step for intermediate coordinate generation.
    """

    def __init__(self, config: Dict[str, Any] = None) -> None:
        merged_config = {**DEFAULT_CONFIG, **(config or {})}
        super().__init__(config=merged_config)

        self.batching_window_size: int = merged_config["batching_window_size"]
        self.smoothing_factor_alpha: float = merged_config["smoothing_factor_alpha"]
        self.slope_threshold: float = float(merged_config["slope_threshold"])
        self.slope_variance_difference: float = float(
            merged_config["slope_variance_difference"]
        )
        self.distance_between_nodes: float = float(
            merged_config["distance_between_nodes"]
        )

    def segment_route(self, attributes_info: Dict[str, Any]) -> List[int]:
        """
        Segment the route by identifying coordinate indices where speed limit or slope variations occur.

        Args:
            attributes_info (Dict[str, Any]): Route attribute payload containing 'maxspeed' and 'slopes' lists.

        Returns:
            List[int]: Selected coordinate boundary indices defining route segments.
        """
        max_speeds = attributes_info.get("maxspeed", [])
        slopes = attributes_info.get("slopes", [])

        if not max_speeds or not slopes:
            logger.warning(
                "Invalid or mismatched attributes_info for route segmentation."
            )
            self.indices = [0]
            return self.indices

        indices = [0]
        last_slope = slopes[0]
        n_points = len(max_speeds)

        for i in range(1, n_points):
            new_segment = False

            # Check speed limit change
            if max_speeds[i] != max_speeds[i - 1]:
                new_segment = True

            # Check slope variation threshold
            if (
                    not new_segment
                    and abs(slopes[i - 1] - last_slope) > self.slope_variance_difference
            ):
                last_slope = slopes[i]
                new_segment = True

            if new_segment:
                indices.append(i - 1)

        self.indices = indices
        return self.indices

    def retrieve_segmented_route_information(
            self, route_coordinates: List[Coords], attributes_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve aggregated telemetry and geometric info structured by route segments.

        Args:
            route_coordinates (List[Coords]): Full sequence of route coordinates.
            attributes_info (Dict[str, Any]): Detailed route telemetry data.

        Returns:
            Dict[str, Any]: Aggregated segmented route payload.
        """
        if not self.indices or len(self.indices) < 2:
            self.segment_route(attributes_info)

        distances = attributes_info.get("distances", [])
        slopes = attributes_info.get("slopes", [])
        heights = attributes_info.get("heights", [])
        maxspeed = attributes_info.get("maxspeed", [])
        temp = attributes_info.get("temp", [])

        sum_distances_segment: List[float] = []
        mean_slope_segment: List[float] = []

        for i, j in zip(self.indices, self.indices[1:]):
            seg_dist = distances[i:j]
            seg_slopes = slopes[i:j]

            sum_distances_segment.append(sum(seg_dist) if seg_dist else 0.0)
            mean_slope_segment.append(mean(seg_slopes) if seg_slopes else 0.0)

        segment_info = {
            "segments": [route_coordinates[i] for i in self.indices[:-1]],
            "segments_representation": [route_coordinates[i] for i in self.indices[:-1]],
            "heights": [heights[i] for i in self.indices[:-1] if i < len(heights)],
            "maxspeed": [maxspeed[i] for i in self.indices[:-1] if i < len(maxspeed)],
            "temp": [temp[i] for i in self.indices[:-1] if i < len(temp)],
            "distances": sum_distances_segment,
            "slopes": mean_slope_segment,
        }

        return segment_info

    def calculate_slopes(
            self, distances: List[float], heights: List[float]
    ) -> List[float]:
        """Calculate road slopes (%) based on segment distances and coordinate elevations.

        Handles size mismatches (e.g., N-1 distance increments vs N waypoint elevations).

        Args:
            distances (List[float]): Distance increments between consecutive waypoints.
            heights (List[float]): Waypoint elevation profiles in meters.

        Returns:
            List[float]: Calculated road slopes clipped within physics thresholds.
        """
        # Create a dataframe with the distances, heights
        df = pd.DataFrame(list(zip(distances, heights)), columns=['distance', 'height'])

        # Smooth elevation profiles using rolling window
        df['mean_height'] = df['height'].rolling(self.batching_window_size, center=True, min_periods=1).mean()

        # Create a column with distance traveled -> First equal to 0 and cumsum of average distances
        avg_distances = 0.5 * (df["distance"] + df["distance"].shift(1))
        avg_distances.iloc[0] = 0.0
        df["distance_traveled"] = avg_distances.cumsum()

        # Create a column with the slope
        height_diff = df["mean_height"].diff().fillna(0.0)
        dist_traveled_diff = df["distance_traveled"].diff().fillna(0.0)

        # Vectorized slope calculation (avoids division by zero)
        slopes = np.where(
            dist_traveled_diff > 0.0,
            (height_diff / dist_traveled_diff) * 100.0,
            0.0,
        )

        # Store the list
        df['slope'] = slopes
        # Replace slope NaN values with 0
        df['slope'] = df['slope'].fillna(0)
        # Limit the values of the slope based on a realistic range
        df['slope'] = df['slope'].clip(lower=-self.slope_threshold, upper=self.slope_threshold)

        return list(df['slope'])
