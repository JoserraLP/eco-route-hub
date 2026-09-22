from route_consumption_estimator.domain.constants import GRAVITY
from route_consumption_estimator.domain.route_model import RouteModel
from route_consumption_estimator.domain.vehicle_model import VehicleModel
from route_consumption_estimator.interfaces import SpeedProfileProvider


def calculate_acceleration_factor(speed_t: float, speed_limit: float):
    """
    Calculate acceleration factor based on speed at a given instant and the limit

    :param speed_t: speed value at a given instant
    :type speed_t: float
    :param speed_limit: speed limit value
    :type speed_limit: float

    :return: acceleration factor
    """
    difference = abs(speed_t - speed_limit)
    if difference < 1:
        return 0.25
    elif difference < 3:
        return 0.5
    else:
        return 1


class SpeedProfile(SpeedProfileProvider):
    """
    Class representing the relation between the route and a given vehicle
    """

    def __init__(self, route: RouteModel = None, vehicle: VehicleModel = None):
        # Store the number of segments
        super().__init__(route, vehicle)

    def estimate_speed_profile(self) -> list:
        """
        Estimate speed profile

        :return:
        """
        # Iterate over the segments
        for i in range(0, len(self.route.segment_start_point) - 1):
            # Coincides with the limit speed of the following section
            if i < self.num_segments:
                # Segment end point
                segment_end_point = self.route.segment_start_point[i + 1]
                # Final speed of the segment (m/s) is the next one
                final_speed = self.route.additional_info['maxspeed'][i + 1] / 3.6

            # Last segment, arrival at destination
            else:
                # Segment end point
                segment_end_point = max(self.route.segment_start_point)
                # Final speed of the segment (m/s) is the actual one
                final_speed = self.route.additional_info['maxspeed'][i] / 3.6

            # Segment length (m)
            segment_length = segment_end_point - self.route.segment_start_point[i]
            self.segment_length[i] = segment_length
            # Calculation of speed limit
            speed_limit = final_speed

            self.delta_t.append(float(segment_length / speed_limit))

            # The kinematics of the vehicle is calculated at each simulation step.
            while self.space[self.step - 1] <= segment_end_point:
                self.slope_t.append(self.route.additional_info['slopes'][i])
                # Braking distance calculation
                brake_distance = (final_speed ** 2 - self.speed_m_s[self.step - 1] ** 2) / (
                        2 * self.vehicle.ax_brake)

                # Determination of state (acceleration / constant speed / braking)
                # If it is in acceleration, state=1, so a=ax_trac
                # If it has reached the maximum speed of the section, state=0. In this case the speed is constant and
                # a=0.
                # If it must start braking, the state=-1, so a=ax_brake

                # Condition of speed greater than the final speed. In this case it makes sense that braking may exist.
                if self.speed_m_s[self.step - 1] >= final_speed:
                    #  You do not have to brake, the current position indicates that you have not reached the braking
                    #  starting point.
                    if self.space[self.step - 1] < (segment_end_point - brake_distance):
                        # Definition of state-dependent acceleration
                        # If you do not reach the speed limit, you can speed up
                        if self.speed_m_s[self.step - 1] < speed_limit:
                            # Acceleration is smoothed, in case of being close to the speed limit.
                            factor = calculate_acceleration_factor(self.speed_m_s[self.step - 1], speed_limit)
                            # Calculate acceleration
                            if self.speed_m_s[self.step - 1] < (self.vehicle.v1_km_h / 3.6):
                                a = factor * self.ax_trac[1]
                            elif self.speed_m_s[self.step - 1] > (self.vehicle.v2_km_h / 3.6):
                                a = factor * self.ax_trac[3]
                            else:
                                a = factor * self.ax_trac[2]
                            # State = 1 -> acceleration
                            self.state.append(1)
                        else:
                            # If the speed limit of the section has been reached, the speed is kept constant,
                            # This implies that the acceleration is zero.
                            if self.speed_m_s[self.step - 1] > speed_limit:
                                # In this case you have to brake up to the maximum speed of the section
                                factor = calculate_acceleration_factor(self.speed_m_s[self.step - 1], speed_limit)
                                # Calculate acceleration
                                a = factor * self.vehicle.ax_brake
                                # State = -1 -> braking
                                self.state.append(-1)
                            else:
                                # Acceleration equal to 0
                                a = 0
                                # State = 0 -> Maximum speed reached
                                self.state.append(0)
                    # It is in braking
                    else:
                        # Acceleration is smoothed, in case of being close to the speed limit.
                        factor = calculate_acceleration_factor(self.speed_m_s[self.step - 1], speed_limit)
                        # Calculate acceleration
                        a = factor * self.vehicle.ax_brake
                        # State = -1 -> braking
                        self.state.append(-1)
                # In case of speed(self.step)<final_speed: No braking
                else:
                    # Definition of acceleration as a function of sub-segment
                    if self.speed_m_s[self.step - 1] < speed_limit:
                        # Acceleration is smoothed, in case of being close to the speed limit.
                        factor = calculate_acceleration_factor(self.speed_m_s[self.step - 1], speed_limit)
                        # Calculate acceleration
                        if self.speed_m_s[self.step - 1] < (self.vehicle.v1_km_h / 3.6):
                            a = factor * self.ax_trac[1]
                        elif self.speed_m_s[self.step - 1] > (self.vehicle.v2_km_h / 3.6):
                            a = factor * self.ax_trac[3]
                        else:
                            a = factor * self.ax_trac[2]
                        # State = 1 -> acceleration
                        self.state.append(1)
                    # Speed limit case
                    else:
                        # Acceleration equal to 0
                        a = 0
                        # State = 0 -> Maximum speed reached
                        self.state.append(0)

                # Acceleration value is updated
                if a > self.acceleration_limit:
                    a = self.acceleration_limit

                # A speed is calculated as a function of the acceleration imposed in the previous steps
                speed_calc = max(self.speed_m_s[self.step - 1] + a * self.delta_t[i], 0)
                # Speed is smoothed to avoid oscillations
                if speed_calc - speed_limit < 0.1 or speed_calc > speed_limit:
                    self.speed_m_s.append(speed_limit)
                else:
                    self.speed_m_s.append(speed_calc)

                # Also the space is calculated as a function of the smoothed speed
                self.space.append(self.space[self.step - 1] + self.speed_m_s[self.step] *
                                   self.delta_t[i] + 0.5 * a * (self.delta_t[i] ** 2))

                # Time is updated
                self.time.append(self.time[self.step - 1] + self.delta_t[i])
                # Step is updated
                self.step += 1
            # print(contador)

        # The only relevant feature here is the speed
        return self.speed_m_s

    def calculate_acceleration(self):
        self.acceleration = [0]  # Restart to 0
        # Parse speed to km/h
        speed_km_h = [speed * 3.6 for speed in self.speed_m_s]

        # Iterate over all number of segments (e.g. retrieved from length of speed
        for i in range(1, len(speed_km_h)):

            if self.time[i] - self.time[i - 1] > 0:
                # Calculate acceleration value with the difference of speeds in time
                value = (1 / 3.6) * (speed_km_h[i] - speed_km_h[i - 1]) / (self.time[i] - self.time[i - 1])
            else:
                value = 0

            if value > self.acceleration_limit:
                self.acceleration.append(self.acceleration_limit)
            else:
                self.acceleration.append(value)

        return self.acceleration

    def calculate_resistances(self):
        self.resistances = [0]  # Restart to 0
        # Parse speed to km/h
        speed_km_h = [speed * 3.6 for speed in self.speed_m_s]

        # Iterate over all number of segments (e.g. retrieved from length of speed
        for i in range(len(self.speed_m_s)):
            self.resistances.append(self.vehicle.A + self.vehicle.B * speed_km_h[i] +
                                     self.vehicle.C * (speed_km_h[i] * speed_km_h[i]))

        return self.resistances

    def calculate_slopes_instant(self, heights):
        """
        Calculate slopes at each instant. Used only for experiments
        :param heights:
        :return:
        """
        self.slope_t = [0]  # Restart to 0
        # Parse speed to km/h
        speed_km_h = [speed * 3.6 for speed in self.speed_m_s]

        for i in range(1, len(heights)):
            segment_length = (0.5 / 3.6) * (speed_km_h[i] + speed_km_h[i - 1]) * \
                             (self.time[i] - self.time[i - 1])
            delta_h = heights[i] - heights[i - 1]

            if segment_length == 0:
                self.slope_t.append(0)
            else:
                slope_value = delta_h / segment_length
                if abs(slope_value) > 0.2:
                    if speed_km_h[i] < 5:
                        self.slope_t.append(0)
                    else:
                        self.slope_t.append(0.2 * slope_value / abs(slope_value))
                else:
                    self.slope_t.append(slope_value)

    def calculate_gravitational_resistances(self):
        self.gravitational_resistances = [0]  # Restart to 0

        for i in range(len(self.speed_m_s)):
            self.gravitational_resistances.append(GRAVITY * self.vehicle.total_mass * self.slope_t[i])
        return self.gravitational_resistances
