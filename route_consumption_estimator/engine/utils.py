from route_consumption_estimator.api.models import Vehicle
from route_consumption_estimator.vehicle.constants import ACC_LIMIT_PROPORTION


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

        delta_height = heights[i] - heights[i-1]

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


def calculate_acceleration(speeds, times):
    acceleration = [0]

    for i in range(1, len(times)):
        value = (1 / 3.6) * (speeds[i] - speeds[i - 1]) / (times[i] - times[i - 1])

        if value > ACC_LIMIT_PROPORTION:
            acceleration.append(ACC_LIMIT_PROPORTION)
        else:
            acceleration.append(value)


def calculate_resistances(speeds, vehicle: Vehicle):
    resistances = [0]
    for i in range(len(speeds)):
        resistances.append(vehicle.A + vehicle.B * speeds[i] +
                           vehicle.C * (speeds[i] * speeds[i]))

    return resistances
