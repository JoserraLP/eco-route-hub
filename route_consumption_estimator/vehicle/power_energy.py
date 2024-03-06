from math import exp

import numpy as np
from scipy.interpolate import interp1d

from route_consumption_estimator.vehicle.constants import *
from route_consumption_estimator.vehicle.speed_profile import SpeedProfile


class PowerEnergyEstimator:
    """
    Class for estimating the power and energy consumption for a given vehicle movement route
    """

    def __init__(self, speed_profile: SpeedProfile):
        # Retrieve vehicle movement number of steps
        self._time = len(speed_profile.time)
        # Store vehicle movement
        self._speed_profile = speed_profile

        # Define traction force, average speed, power, instant energy [(W/s), (kW/h)], accumulated power (kW/h),
        # power percentage, performance, instant energy fuel (kW/h), accumulated energy fuel (kW/h), consumption,
        # total_consumption
        self._traction_force = np.zeros(self._time)
        self._power = np.zeros(self._time)
        self._instant_energy_kw_h = np.zeros(self._time)
        self._instant_energy_fixed_kw_h = np.zeros(self._time)
        self._accumulated_engine_energy_kw_h = np.zeros(self._time)
        self._power_percentage = np.zeros(self._time)
        self._performance = np.zeros(self._time)
        self._consumption = np.zeros(self._time)

        # Interpolation function based on power usage and engine performance
        # Added extrapolate to fix values that are not in interpolation ranges
        self._f = interp1d(POWER_PERCENTAGE, ENGINE_PERFORMANCE)

    def estimate_power_consumption(self, electric: bool = False):
        # TODO ask for these values
        r2 = 0.252
        r1 = 1 - r2
        cexp = 0.35
        bexp = 0.203

        # Parse speed from m/s to km/h
        speed_km_h = [speed * 3.6 for speed in self._speed_profile.speed_m_s]

        for i in range(1, self._time):
            self._traction_force[i] = self._speed_profile.resistances[i] + \
                                      self._speed_profile.gravitational_resistances[i] + \
                                      self._speed_profile.vehicle.total_mass * self._speed_profile.vehicle.gamma * \
                                      self._speed_profile.acceleration[i]

            if self._traction_force[i] < 0:
                self._traction_force[i] = 0

            self._power[i] = self._traction_force[i] * speed_km_h[i] / 3.6
            self._instant_energy_kw_h[i] = 0.5 * (self._power[i] + self._power[i - 1]) * \
                                           (self._speed_profile.time[i] - self._speed_profile.time[i - 1]) / 3600 / 1000
            self._accumulated_engine_energy_kw_h[i] = self._accumulated_engine_energy_kw_h[i - 1] + \
                                                      self._instant_energy_kw_h[i]

            self._power_percentage[i] = 100 * self._power[i] / (self._speed_profile.vehicle.p_max_kw * 1000)

            if speed_km_h[i] < self._speed_profile.vehicle.v1_km_h:
                factor = ((r1 * speed_km_h[i]) / self._speed_profile.vehicle.v1_km_h) + r2
            else:
                factor = 1

            self._performance[i] = (0.01 - (cexp * factor)) * exp(-bexp * self._power_percentage[i] / factor) + (
                    cexp * factor)

            self._instant_energy_fixed_kw_h[i] = self._instant_energy_kw_h[i] / self._performance[i]

            if electric:
                # I suppose there is no idle consumption on electric vehicles
                self._consumption[i] = self._consumption[i - 1] + self._instant_energy_fixed_kw_h[i]
            else:
                # Combustion or hybrid
                if speed_km_h[i] < 0.1:
                    self._consumption[i] = self._consumption[i - 1] + \
                                           IDLING_CONSUMPTION * (
                                                   self._speed_profile.time[i] - self._speed_profile.time[i - 1]) \
                                           / 3600
                else:
                    self._consumption[i] = self._consumption[i - 1] + \
                                           ((0.5 * (self._instant_energy_fixed_kw_h[i] +
                                                    self._instant_energy_fixed_kw_h[i - 1])) /
                                            self._speed_profile.vehicle.liters_conversion)

    def calculate_experiment_consumption(self, experiment_consumptions):
        for i in range(1, len(experiment_consumptions)):
            if experiment_consumptions[i] < 0:
                consumption_value = 0
            else:
                consumption_value = experiment_consumptions[i]

            self._consumption[i] = self._consumption[i - 1] + \
                                   (0.5 * (consumption_value + experiment_consumptions[i - 1]) *
                                    (self._speed_profile.time[i] - self._speed_profile.time[i - 1])/3600)

    @property
    def time(self):
        """Get the value of time."""
        return self._time

    @time.setter
    def time(self, value):
        """Set the value of time."""
        self._time = value

    @property
    def traction_force(self):
        """Get the value of traction_force."""
        return self._traction_force

    @traction_force.setter
    def traction_force(self, value):
        """Set the value of traction_force."""
        self._traction_force = value

    @property
    def power(self):
        """Get the value of power."""
        return self._power

    @power.setter
    def power(self, value):
        """Set the value of power."""
        self._power = value

    @property
    def instant_energy_kw_h(self):
        """Get the value of instant_energy_kw_h."""
        return self._instant_energy_kw_h

    @instant_energy_kw_h.setter
    def instant_energy_kw_h(self, value):
        """Set the value of instant_energy_kw_h."""
        self._instant_energy_kw_h = value

    @property
    def accumulated_engine_energy_kw_h(self):
        """Get the value of accumulated_engine_energy_kw_h."""
        return self._accumulated_engine_energy_kw_h

    @accumulated_engine_energy_kw_h.setter
    def accumulated_engine_energy_kw_h(self, value):
        """Set the value of accumulated_engine_energy_kw_h."""
        self._accumulated_engine_energy_kw_h = value

    @property
    def power_percentage(self):
        """Get the value of power_percentage."""
        return self._power_percentage

    @power_percentage.setter
    def power_percentage(self, value):
        """Set the value of power_percentage."""
        self._power_percentage = value

    @property
    def performance(self):
        """Get the value of performance."""
        return self._performance

    @performance.setter
    def performance(self, value):
        """Set the value of performance."""
        self._performance = value

    @property
    def consumption(self):
        """Get the value of consumption."""
        return self._consumption

    @consumption.setter
    def consumption(self, value):
        """Set the value of consumption."""
        self._consumption = value
