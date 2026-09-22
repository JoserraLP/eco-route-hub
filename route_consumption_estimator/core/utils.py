"""
Utility functions for route analysis, kinematic conversions, signal smoothing, and eco-driving evaluation.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SMOOTHING_ALPHA = 0.3
STOP_SPEED_THRESHOLD_MS = 0.8333333  # ~3 km/h in m/s
SLOPE_SPEED_THRESHOLD_MS = 5.0      # 5 m/s (~18 km/h)
MAX_ABS_SLOPE = 0.2                  # Max 20% gradient


def calculate_distances(
    speeds: List[float], timestamps: List[float]
) -> List[float]:
    """
    Calculate cumulative distances traveled over time intervals.

    Args:
        speeds (List[float]): Speed profile series in m/s.
        timestamps (List[float]): Monotonic timestamp series in seconds.

    Returns:
        List[float]: Cumulative distance series in meters.

    Raises:
        ValueError: If speeds and timestamps lists have differing lengths.
    """
    if len(speeds) != len(timestamps):
        raise ValueError("Speeds and timestamps lists must have equal lengths.")

    if not speeds:
        return []

    distances: List[float] = [0.0]
    acc_distance = 0.0

    for i in range(1, len(speeds)):
        dt = timestamps[i] - timestamps[i - 1]
        distance = speeds[i] * max(0.0, dt)
        acc_distance += distance
        distances.append(acc_distance)

    return distances


def calculate_slopes(
    heights: List[float], speeds: List[float], times: List[float]
) -> List[float]:
    """
    Calculate route segment slopes (gradients) bounded by physical constraints.

    Args:
        heights (List[float]): Elevation points in meters.
        speeds (List[float]): Vehicle speeds in m/s.
        times (List[float]): Timestamp series in seconds.

    Returns:
        List[float]: Calculated road slopes (rise / run).
    """
    if not (len(heights) == len(speeds) == len(times)):
        raise ValueError("Heights, speeds, and times lists must have equal lengths.")

    slopes: List[float] = [0.0]

    for i in range(1, len(speeds)):
        dt = max(0.0, times[i] - times[i - 1])
        avg_speed = 0.5 * (speeds[i] + speeds[i - 1])
        segment_long = avg_speed * dt
        delta_height = heights[i] - heights[i - 1]

        if segment_long <= 0.0:
            slope_value = 0.0
        else:
            slope_value = delta_height / segment_long
            if abs(slope_value) > MAX_ABS_SLOPE:
                if speeds[i] < SLOPE_SPEED_THRESHOLD_MS:
                    slope_value = 0.0
                else:
                    slope_value = MAX_ABS_SLOPE * (1.0 if slope_value > 0 else -1.0)

        slopes.append(slope_value)

    return slopes


def smoothing_process(
    input_list: List[float], alpha: Optional[float] = None
) -> List[float]:
    """
    Apply Exponential Moving Average (EMA) smoothing to a series of numerical inputs.

    Args:
        input_list (List[float]): Raw input numerical series.
        alpha (Optional[float]): Smoothing factor between 0.0 and 1.0. If None, resolves from context or default.

    Returns:
        List[float]: Smoothed numerical series.
    """
    if not input_list:
        return []

    if alpha is None:
        try:
            from flask import current_app

            if current_app:
                cfg = current_app.config.get("APP_CONFIG")
                alpha = getattr(cfg.system, "smoothing_factor_alpha", DEFAULT_SMOOTHING_ALPHA)
        except (ImportError, RuntimeError, AttributeError):
            alpha = DEFAULT_SMOOTHING_ALPHA

    alpha = alpha if alpha is not None else DEFAULT_SMOOTHING_ALPHA

    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"Alpha smoothing factor must be between 0.0 and 1.0, got: {alpha}")

    smoothed_list: List[float] = [input_list[0]]
    for i in range(1, len(input_list)):
        smoothed = input_list[i] * alpha + smoothed_list[i - 1] * (1.0 - alpha)
        smoothed_list.append(smoothed)

    return smoothed_list


def evaluate_consumption(
    speeds: List[float],
    accelerations: List[float],
    total_length: float,
    times: List[float],
) -> Dict[str, int]:
    """
    Evaluate driving aggressiveness, speed variations, and stop metrics based on telemetry.

    Args:
        speeds (List[float]): Vehicle speeds in m/s.
        accelerations (List[float]): Acceleration values in m/s^2.
        total_length (float): Total route length in meters.
        times (List[float]): Timestamp series in seconds.

    Returns:
        Dict[str, int]: Eco-driving scores (1-5 scale) for Stops/km, Speed Variation, and Aggressiveness.
    """
    stops = 0
    lower_threshold = 0.1
    greater_threshold = 2.5
    time_accel_lower = 0.0
    time_accel_greater = 0.0

    total_time = max(0.0, times[-1] - times[0]) if len(times) > 1 else 0.0

    for i in range(1, len(speeds)):
        dt = max(0.0, times[i] - times[i - 1])

        # Stop detection: speed drops under ~3 km/h
        if speeds[i - 1] > STOP_SPEED_THRESHOLD_MS >= speeds[i] > 0:
            stops += 1

        accel = abs(accelerations[i]) if i < len(accelerations) else 0.0

        if accel > lower_threshold:
            time_accel_lower += dt
        if accel > greater_threshold:
            time_accel_greater += dt

    # Prevent ZeroDivisionError for zero length or zero time
    stops_per_km = stops / (total_length / 1000.0) if total_length > 0 else 0.0
    pct_lower = (time_accel_lower / total_time) if total_time > 0 else 0.0
    pct_greater = (time_accel_greater / total_time) if total_time > 0 else 0.0

    return {
        "NumStopsKm": get_num_stops_per_km_score(stops_per_km),
        "SpeedVariationNum": get_acceleration_lower_threshold_score(pct_lower),
        "DrivingAggressiveness": get_acceleration_greater_threshold_score(pct_greater),
    }


def get_num_stops_per_km_score(value: float) -> int:
    """Score stops per kilometer (1 = Poor, 5 = Excellent)."""
    if value >= 1.0:
        return 1
    elif 0.75 <= value < 1.0:
        return 2
    elif 0.50 <= value < 0.75:
        return 3
    elif 0.25 <= value < 0.50:
        return 4
    else:
        return 5


def get_acceleration_lower_threshold_score(value: float) -> int:
    """Score percentage of time accelerating above minor threshold (0.1 m/s^2)."""
    if value >= 0.60:
        return 1
    elif 0.40 <= value < 0.60:
        return 2
    elif 0.20 <= value < 0.40:
        return 3
    elif 0.10 <= value < 0.20:
        return 4
    else:
        return 5


def get_acceleration_greater_threshold_score(value: float) -> int:
    """Score percentage of time accelerating above aggressive threshold (2.5 m/s^2)."""
    if value >= 0.05:
        return 1
    elif 0.03 <= value < 0.05:
        return 2
    elif 0.01 <= value < 0.03:
        return 3
    elif 0.005 <= value < 0.01:
        return 4
    else:
        return 5
