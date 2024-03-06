import numpy as np

from route_consumption_estimator.path.path_model import PathModel
from route_consumption_estimator.vehicle.constants import GRAVITY
from route_consumption_estimator.vehicle.veh_model import VehicleModel


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


class SpeedProfile:
    """
    Class representing the relation between the route and a given vehicle
    """

    def __init__(self, route: PathModel, vehicle: VehicleModel):

        # Store the number of segments
        self._num_segments = len(route.segment_start_point)

        # Store both route and vehicle variables
        self._route = route
        self._vehicle = vehicle

        # Create variables related to segment end point, final speed and segment length
        self._segment_end_point = np.zeros(self._num_segments)
        self._final_speed = np.zeros(self._num_segments)
        self._segment_length = np.zeros(self._num_segments)

        # Create variables related to time, space, state, brake distance, acceleration, calculated acceleration,
        # resistances, slope at a given instan and speed
        self._time = [0]
        self._space = [0]
        self._state = [0]
        self._brake_distance = [0]
        self._acceleration = [0]
        self._acceleration_calc = [0]
        self._resistances = [0]
        self._gravitational_resistances = [0]
        self._slope_t = [0]
        self._delta_t = []

        self._acceleration_limit = 0.7 * GRAVITY

        # This will be the output
        self._speed_m_s = [0]

        # Start time - General counter
        self._step = 1

        # Define acceleration
        self._ax_trac = {1: vehicle.ax_trac1, 2: vehicle.ax_trac2, 3: vehicle.ax_trac3}

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
                final_speed = self._route.speed_limit_km_h[i + 1] / 3.6

            # Last segment, arrival at destination
            else:
                # Segment end point
                segment_end_point = max(self._route.segment_start_point)
                # Final speed of the segment (m/s) is the actual one
                final_speed = self._route.speed_limit_km_h[i] / 3.6

            # Segment length (m)
            segment_length = segment_end_point - self._route.segment_start_point[i]
            # Calculation of speed limit
            speed_limit = final_speed

            self._delta_t.append(float(segment_length / speed_limit))

            # The kinematics of the vehicle is calculated at each simulation step.
            while self._space[self._step - 1] <= segment_end_point:
                self._slope_t.append(self._route.slope[i])
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
                speed_calc = self._speed_m_s[self._step - 1] + a * self._delta_t[i]
                # Speed is smoothed to avoid oscillations
                if abs(speed_calc - speed_limit) < 0.1:
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

            # Calculate acceleration value with the difference of speeds in time
            value = (1 / 3.6) * (speed_km_h[i] - speed_km_h[i - 1]) / (self._time[i] - self._time[i - 1])

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

    def calculo_pendientes(self, V, t, h, pasos):
        # TODO adjust the next method to this one
        l_tramo = [0]
        trip = [0]
        Delta_h = [0]
        seno_rampa = [0]
        for i in range(1, pasos):

            l_tramo.append((0.5 / 3.6) * (V[i] + V[i - 1]) * (t[i] - t[i - 1]))  # Longitud(m)
            trip.append(trip[i - 1] + l_tramo[i])  # Distancia recorrida(m)

            Delta_h.append(h[i] - h[i - 1])

            if l_tramo[i] == 0:
                seno_rampa.append(0)
            else:
                seno_rampa.append(Delta_h[i] / l_tramo[i])
                if abs(seno_rampa[i]) > 0.2:
                    if V[i] < 5:
                        seno_rampa[i] = 0
                    else:
                        seno_rampa[i] = 0.2 * seno_rampa[i] / abs(seno_rampa[i])

        return seno_rampa, trip

    def calculate_slopes(self, heights):
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

    @property
    def num_segments(self):
        """Get the value of num_segments."""
        return self._num_segments

    @num_segments.setter
    def num_segments(self, value):
        """Set the value of num_segments."""
        self._num_segments = value

    @property
    def route(self):
        """Get the value of route."""
        return self._route

    @route.setter
    def route(self, value):
        """Set the value of route."""
        self._route = value

    @property
    def vehicle(self):
        """Get the value of vehicle."""
        return self._vehicle

    @vehicle.setter
    def vehicle(self, value):
        """Set the value of vehicle."""
        self._vehicle = value

    @property
    def segment_end_point(self):
        """Get the value of segment_end_point."""
        return self._segment_end_point

    @segment_end_point.setter
    def segment_end_point(self, value):
        """Set the value of segment_end_point."""
        self._segment_end_point = value

    @property
    def final_speed(self):
        """Get the value of final_speed."""
        return self._final_speed

    @final_speed.setter
    def final_speed(self, value):
        """Set the value of final_speed."""
        self._final_speed = value

    @property
    def segment_length(self):
        """Get the value of segment_length."""
        return self._segment_length

    @segment_length.setter
    def segment_length(self, value):
        """Set the value of segment_length."""
        self._segment_length = value

    @property
    def time(self):
        """Get the value of time."""
        return self._time

    @time.setter
    def time(self, value):
        """Set the value of time."""
        self._time = value

    @property
    def space(self):
        """Get the value of space."""
        return self._space

    @space.setter
    def space(self, value):
        """Set the value of space."""
        self._space = value

    @property
    def brake_distance(self):
        """Get the value of brake_distance."""
        return self._brake_distance

    @brake_distance.setter
    def brake_distance(self, value):
        """Set the value of brake_distance."""
        self._brake_distance = value

    @property
    def speed_m_s(self):
        """Get the value of speed."""
        return self._speed_m_s

    @speed_m_s.setter
    def speed_m_s(self, value):
        """Set the value of speed."""
        self._speed_m_s = value

    @property
    def acceleration(self):
        """Get the value of acceleration."""
        return self._acceleration

    @acceleration.setter
    def acceleration(self, value):
        """Set the value of acceleration."""
        self._acceleration = value

    @property
    def acceleration_calc(self):
        """Get the value of acceleration_calc."""
        return self._acceleration_calc

    @acceleration_calc.setter
    def acceleration_calc(self, value):
        """Set the value of acceleration_calc."""
        self._acceleration_calc = value

    @property
    def state(self):
        """Get the value of state."""
        return self._state

    @state.setter
    def state(self, value):
        """Set the value of state."""
        self._state = value

    @property
    def slope_t(self):
        """Get the value of slope_t."""
        return self._slope_t

    @slope_t.setter
    def slope_t(self, value):
        """Set the value of slope_t."""
        self._slope_t = value

    @property
    def step(self):
        """Get the value of step."""
        return self._step

    @step.setter
    def step(self, value):
        """Set the value of step."""
        self._step = value

    @property
    def ax_trac(self):
        """Get the value of ax_trac."""
        return self._ax_trac

    @ax_trac.setter
    def ax_trac(self, value):
        """Set the value of ax_trac."""
        self._ax_trac = value

    @property
    def gravitational_resistances(self):
        """Get the value of gravitational_resistances."""
        return self._gravitational_resistances

    @gravitational_resistances.setter
    def gravitational_resistances(self, value):
        """Set the value of gravitational_resistances."""
        self._gravitational_resistances = value

    @property
    def resistances(self):
        """Get the value of resistances."""
        return self._resistances

    @resistances.setter
    def resistances(self, value):
        """Set the value of resistances."""
        self._resistances = value
