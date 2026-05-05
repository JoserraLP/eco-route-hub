from flask import current_app


def calculate_distances(speeds, timestamps):
    # Ensure that both lists have the same length
    assert len(speeds) == len(timestamps), "Speeds and timestamps lists must have the same length"

    distances = [0]
    acc_distance = 0
    for i in range(1, len(speeds)):
        # Calculate the distance travelled m/s * s
        distance = speeds[i] * (timestamps[i] - timestamps[i - 1])

        acc_distance += distance

        distances.append(acc_distance)

    return distances


def calculate_slopes(heights, speeds, times):
    slopes = [0]
    for i in range(1, len(speeds)):
        # Speeds is in m/s
        segment_long = (0.5 * (speeds[i] + speeds[i - 1]) * (times[i] - times[i - 1]))

        delta_height = heights[i] - heights[i - 1]

        if segment_long == 0:
            slope_value = 0
        else:
            slope_value = delta_height / segment_long
            if abs(slope_value) > 0.2:
                if speeds[i] < 5:
                    slope_value = 0
                else:
                    slope_value = 0.2 * slope_value / abs(slope_value)

        slopes.append(slope_value)

    return slopes


def smoothing_process(input_list: list, alpha: float = None):
    current_app_config = current_app.config["APP_CONFIG"].system
    alpha = alpha if alpha else current_app_config.smoothing_factor_alpha

    assert 0 <= alpha <= 1, "Error value, alpha should be between 0 and 1"

    # Smoothing function
    # alpha depends on vehicle and device (needs calibration) between 0 and 1 e.g. 0.3 or 0.4
    # a[0]' = a[0]
    # a[1]' = a[1]*alpha + a[0]'*(1-alpha)
    # a[n]' = a[n]*alpha + a[n-1]'*(1-alpha)

    # Initialize to first item
    smoothed_list = [input_list[0]]
    for i in range(1, len(input_list)):
        smoothed_list.append(input_list[i] * alpha + smoothed_list[i - 1] * (1 - alpha))

    return smoothed_list


def evaluate_consumption(speeds, accelerations, total_length, times):
    # Initialize variables
    stops = 0
    lower_threshold = 0.1
    greater_threshold = 2.5
    num_acceleration_lower_threshold = 0
    num_acceleration_greater_threshold = 0

    total_time = sum(times)

    # Iterate over the speeds
    for i in range(1, len(speeds)):
        # If the speed is lower than 3 km/h (0.8333333  m/s), increment the stops counter
        if speeds[i - 1] > 0.8333333 > speeds[i] > 0:
            stops += 1

        # Calculate the acceleration and add it to the list
        # acceleration = abs((speeds[i] - speeds[i - 1]) / (times[i] - times[i - 1]))
        # acceleration_list.append(acceleration)

        # Count number of times the acceleration is greater than thresholds
        if abs(accelerations[i]) > lower_threshold:
            num_acceleration_lower_threshold += times[i]
        if abs(accelerations[i]) > greater_threshold:
            num_acceleration_greater_threshold += times[i]

    stops_per_km = stops / (total_length / 1000)  # Parse to km
    percentage_acceleration_lower_threshold = num_acceleration_lower_threshold / total_time
    percentage_acceleration_greater_threshold = num_acceleration_greater_threshold / total_time

    # Print the results
    """
    print(
        f"Number of stops (where the speed is lower than 3km/h): {stops} ({stops_per_km} per km) of a total of {len(speeds)}")
    print(f"% of time acceleration greater than {lower_threshold}: {percentage_acceleration_lower_threshold}")
    print(f"% of time acceleration greater than {greater_threshold}: {percentage_acceleration_greater_threshold}")
    """

    total_score = {'NumStopsKm': get_num_stops_per_km_score(stops_per_km),
                   'SpeedVariationNum': get_acceleration_lower_threshold_score(percentage_acceleration_lower_threshold),
                   'DrivingAggressiveness': get_acceleration_greater_threshold_score(
                       percentage_acceleration_greater_threshold)
                   }
    return total_score


def get_num_stops_per_km_score(value):
    if value >= 1:
        return 1  # 'Manifiestamente mejorable'
    elif 0.75 <= value < 1:
        return 2  # 'Mejorable'
    elif 0.50 <= value < 0.75:
        return 3  # 'Aceptable'
    elif 0.25 <= value < 0.50:
        return 4  # 'Bien'
    else:
        return 5  # 'Muy bien'


def get_acceleration_lower_threshold_score(value):
    if value >= 0.60:
        return 1  # 'Manifiestamente mejorable'
    elif 0.60 < value <= 0.40:
        return 2  # 'Mejorable'
    elif 0.40 < value <= 0.20:
        return 3  # 'Aceptable'
    elif 0.20 < value <= 0.10:
        return 4  # 'Bien'
    else:
        return 5  # 'Muy bien'


def get_acceleration_greater_threshold_score(value):
    if value >= 0.05:
        return 1  # 'Manifiestamente mejorable'
    elif 0.05 < value <= 0.03:
        return 2  # 'Mejorable'
    elif 0.03 < value <= 0.01:
        return 3  # 'Aceptable'
    elif 0.01 < value <= 0.005:
        return 4  # 'Bien'
    else:
        return 5  # 'Muy bien'
