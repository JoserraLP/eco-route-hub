from route_consumption_estimator.domain import RouteModel, VehicleModel, GRAVITY
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
        for i in range(0, len(self._route.segment_start_point) - 1):
            # Coincides with the limit speed of the following section
            if i < self._num_segments:
                # Segment end point
                segment_end_point = self._route.segment_start_point[i + 1]
                # Final speed of the segment (m/s) is the next one
                final_speed = self._route.additional_info['maxspeed'][i + 1] / 3.6

            # Last segment, arrival at destination
            else:
                # Segment end point
                segment_end_point = max(self._route.segment_start_point)
                # Final speed of the segment (m/s) is the actual one
                final_speed = self._route.additional_info['maxspeed'][i] / 3.6

            # Segment length (m)
            segment_length = segment_end_point - self._route.segment_start_point[i]
            self.segment_length[i] = segment_length
            # Calculation of speed limit
            speed_limit = final_speed

            self._delta_t.append(float(segment_length / speed_limit))

            # The kinematics of the vehicle is calculated at each simulation step.
            while self._space[self._step - 1] <= segment_end_point:
                self._slope_t.append(self._route.additional_info['slopes'][i])
                # Braking distance calculation
                brake_distance = (final_speed ** 2 - self._speed_m_s[self._step - 1] ** 2) / (
                        2 * self._vehicle.ax_brake)

                # Determination of state (acceleration / constant speed / braking)
                # If it is in acceleration, state=1, so a=ax_trac
                # If it has reached the maximum speed of the section, state=0. In this case the speed is constant and
                # a=0.
                # If it must start braking, the state=-1, so a=ax_brake

                # Condition of speed greater than the final speed. In this case it makes sense that braking may exist.
                if self._speed_m_s[self._step - 1] >= final_speed:
                    #  You do not have to brake, the current position indicates that you have not reached the braking
                    #  starting point.
                    if self._space[self._step - 1] < (segment_end_point - brake_distance):
                        # Definition of state-dependent acceleration
                        # If you do not reach the speed limit, you can speed up
                        if self._speed_m_s[self._step - 1] < speed_limit:
                            # Acceleration is smoothed, in case of being close to the speed limit.
                            factor = calculate_acceleration_factor(self._speed_m_s[self._step - 1], speed_limit)
                            # Calculate acceleration
                            if self._speed_m_s[self._step - 1] < (self._vehicle.v1_km_h / 3.6):
                                a = factor * self._ax_trac[1]
                            elif self._speed_m_s[self._step - 1] > (self._vehicle.v2_km_h / 3.6):
                                a = factor * self._ax_trac[3]
                            else:
                                a = factor * self._ax_trac[2]
                            # State = 1 -> acceleration
                            self._state.append(1)
                        else:
                            # If the speed limit of the section has been reached, the speed is kept constant,
                            # This implies that the acceleration is zero.
                            if self._speed_m_s[self._step - 1] > speed_limit:
                                # In this case you have to brake up to the maximum speed of the section
                                factor = calculate_acceleration_factor(self._speed_m_s[self._step - 1], speed_limit)
                                # Calculate acceleration
                                a = factor * self._vehicle.ax_brake
                                # State = -1 -> braking
                                self._state.append(-1)
                            else:
                                # Acceleration equal to 0
                                a = 0
                                # State = 0 -> Maximum speed reached
                                self._state.append(0)
                    # It is in braking
                    else:
                        # Acceleration is smoothed, in case of being close to the speed limit.
                        factor = calculate_acceleration_factor(self._speed_m_s[self._step - 1], speed_limit)
                        # Calculate acceleration
                        a = factor * self._vehicle.ax_brake
                        # State = -1 -> braking
                        self._state.append(-1)
                # In case of speed(self._step)<final_speed: No braking
                else:
                    # Definition of acceleration as a function of sub-segment
                    if self._speed_m_s[self._step - 1] < speed_limit:
                        # Acceleration is smoothed, in case of being close to the speed limit.
                        factor = calculate_acceleration_factor(self._speed_m_s[self._step - 1], speed_limit)
                        # Calculate acceleration
                        if self._speed_m_s[self._step - 1] < (self._vehicle.v1_km_h / 3.6):
                            a = factor * self._ax_trac[1]
                        elif self._speed_m_s[self._step - 1] > (self._vehicle.v2_km_h / 3.6):
                            a = factor * self._ax_trac[3]
                        else:
                            a = factor * self._ax_trac[2]
                        # State = 1 -> acceleration
                        self._state.append(1)
                    # Speed limit case
                    else:
                        # Acceleration equal to 0
                        a = 0
                        # State = 0 -> Maximum speed reached
                        self._state.append(0)

                # Acceleration value is updated
                if a > self._acceleration_limit:
                    a = self._acceleration_limit

                # A speed is calculated as a function of the acceleration imposed in the previous steps
                speed_calc = max(self._speed_m_s[self._step - 1] + a * self._delta_t[i], 0)
                # Speed is smoothed to avoid oscillations
                if speed_calc - speed_limit < 0.1 or speed_calc > speed_limit:
                    self._speed_m_s.append(speed_limit)
                else:
                    self._speed_m_s.append(speed_calc)

                # Also the space is calculated as a function of the smoothed speed
                self._space.append(self._space[self._step - 1] + self._speed_m_s[self._step] *
                                   self._delta_t[i] + 0.5 * a * (self._delta_t[i] ** 2))

                # Time is updated
                self._time.append(self._time[self._step - 1] + self._delta_t[i])
                # Step is updated
                self._step += 1
            # print(contador)

        # The only relevant feature here is the speed
        return self._speed_m_s

    def calculate_acceleration(self):
        self._acceleration = [0]  # Restart to 0
        # Parse speed to km/h
        speed_km_h = [speed * 3.6 for speed in self._speed_m_s]

        # Iterate over all number of segments (e.g. retrieved from length of speed
        for i in range(1, len(speed_km_h)):

            if self._time[i] - self._time[i - 1] > 0:
                # Calculate acceleration value with the difference of speeds in time
                value = (1 / 3.6) * (speed_km_h[i] - speed_km_h[i - 1]) / (self._time[i] - self._time[i - 1])
            else:
                value = 0

            if value > self._acceleration_limit:
                self._acceleration.append(self._acceleration_limit)
            else:
                self._acceleration.append(value)

        return self._acceleration

    def calculate_resistances(self):
        self._resistances = [0]  # Restart to 0
        # Parse speed to km/h
        speed_km_h = [speed * 3.6 for speed in self._speed_m_s]

        # Iterate over all number of segments (e.g. retrieved from length of speed
        for i in range(len(self._speed_m_s)):
            self._resistances.append(self._vehicle.A + self._vehicle.B * speed_km_h[i] +
                                     self._vehicle.C * (speed_km_h[i] * speed_km_h[i]))

        return self._resistances

    def calculate_slopes_instant(self, heights):
        """
        Calculate slopes at each instant. Used only for experiments
        :param heights:
        :return:
        """
        self._slope_t = [0]  # Restart to 0
        # Parse speed to km/h
        speed_km_h = [speed * 3.6 for speed in self._speed_m_s]

        for i in range(1, len(heights)):
            segment_length = (0.5 / 3.6) * (speed_km_h[i] + speed_km_h[i - 1]) * \
                             (self._time[i] - self._time[i - 1])
            delta_h = heights[i] - heights[i - 1]

            if segment_length == 0:
                self._slope_t.append(0)
            else:
                slope_value = delta_h / segment_length
                if abs(slope_value) > 0.2:
                    if speed_km_h[i] < 5:
                        self._slope_t.append(0)
                    else:
                        self._slope_t.append(0.2 * slope_value / abs(slope_value))
                else:
                    self._slope_t.append(slope_value)

    def calculate_gravitational_resistances(self):
        self._gravitational_resistances = [0]  # Restart to 0

        for i in range(len(self._speed_m_s)):
            self._gravitational_resistances.append(GRAVITY * self.vehicle.total_mass * self._slope_t[i])
        return self._gravitational_resistances
