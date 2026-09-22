from abc import ABC, abstractmethod

import numpy as np

from route_consumption_estimator.domain.constants import GRAVITY
from route_consumption_estimator.domain.route_model import RouteModel
from route_consumption_estimator.domain.vehicle_model import VehicleModel

# Max acceleration limit
ACC_LIMIT_PROPORTION = 0.7 * GRAVITY


class SpeedProfileProvider(ABC):

    def __init__(self, route: RouteModel = None, vehicle: VehicleModel = None):
        # Store both route and vehicle variables
        self._route = route
        self._vehicle = vehicle

        # Store the number of segments
        self._num_segments = len(route.segment_start_point) if route else 0

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

        self._acceleration_limit = ACC_LIMIT_PROPORTION

        # This will be the output
        self._speed_m_s = [0]

        # Start time - General counter
        self._step = 1

        # Define acceleration
        self._ax_trac = {1: vehicle.ax_trac1, 2: vehicle.ax_trac2, 3: vehicle.ax_trac3} if vehicle else {}

    @abstractmethod
    def estimate_speed_profile(self) -> list:
        pass

    @abstractmethod
    def calculate_acceleration(self) -> list:
        pass

    @abstractmethod
    def calculate_resistances(self) -> list:
        pass

    @abstractmethod
    def calculate_slopes_instant(self, heights) -> list:
        pass

    @abstractmethod
    def calculate_gravitational_resistances(self) -> list:
        pass

    @property
    def vehicle(self):
        """Get the value of vehicle."""
        return self._vehicle

    @vehicle.setter
    def vehicle(self, value):
        """Set the value of vehicle."""
        self._vehicle = value
        # Update values
        self._ax_trac = {1: value.ax_trac1, 2: value.ax_trac2, 3: value.ax_trac3}

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
