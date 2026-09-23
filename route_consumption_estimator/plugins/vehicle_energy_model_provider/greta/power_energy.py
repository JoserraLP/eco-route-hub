"""
Power and energy estimation module for vehicle speed profiles.

Calculates instantaneous traction forces, engine power, performance factors, 
and cumulative energy/fuel consumption for conventional and electric powertrains.
"""

import logging
from math import exp
from typing import Sequence

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from route_consumption_estimator.plugins.speed_profile_provider.speed_profile import SpeedProfile
from route_consumption_estimator.plugins.vehicle_energy_model_provider.greta import constants

logger = logging.getLogger(__name__)

FloatArray = NDArray[np.float64]


class PowerEnergyEstimator:
    """
    Estimates instantaneous power, traction forces, and energy/fuel consumption 
    over a vehicle drive cycle.
    """

    def __init__(self, speed_profile: SpeedProfile) -> None:
        if speed_profile is None or not hasattr(speed_profile, "time"):
            raise ValueError("SpeedProfile provided to PowerEnergyEstimator cannot be None.")

        times = np.asarray(speed_profile.time, dtype=float).reshape(-1)
        self.time: int = len(times)

        if self.time == 0:
            raise ValueError("SpeedProfile time array is empty.")

        self.speed_profile: SpeedProfile = speed_profile

        # Atributos públicos de estado (arrays NumPy 1D)
        self.traction_force: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.power: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.instant_energy_kw_h: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.instant_energy_fixed_kw_h: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.accumulated_engine_energy_kw_h: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.power_percentage: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.performance: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.consumption_liters: FloatArray = np.zeros(self.time, dtype=np.float64)
        self.consumption_kw_h: FloatArray = np.zeros(self.time, dtype=np.float64)

        # Interpolación de eficiencia
        self._f = interp1d(
            constants.POWER_PERCENTAGE,
            constants.ENGINE_PERFORMANCE,
            fill_value="extrapolate",
            bounds_error=False,
        )

    def estimate_power_consumption(self, electric: bool = False) -> None:
        """Calculate power and cumulative fuel or battery energy consumption."""
        speeds_m_s = np.asarray(self.speed_profile.speed_m_s, dtype=float).reshape(-1)
        times_s = np.asarray(self.speed_profile.time, dtype=float).reshape(-1)
        resistances = np.asarray(self.speed_profile.resistances, dtype=float).reshape(-1)
        grav_resistances = np.asarray(
            self.speed_profile.gravitational_resistances, dtype=float
        ).reshape(-1)
        accelerations = np.asarray(self.speed_profile.acceleration, dtype=float).reshape(-1)

        vehicle = self.speed_profile.vehicle
        total_mass = float(getattr(vehicle, "total_mass", 1000.0))
        gamma = float(getattr(vehicle, "gamma", 1.0))
        p_max_kw = float(getattr(vehicle, "p_max_kw", 100.0))
        v1_km_h = float(getattr(vehicle, "v1_km_h", 50.0))
        liters_conversion = float(getattr(vehicle, "liters_conversion", 9.0))

        if p_max_kw <= 0.0:
            raise ValueError(f"Vehicle p_max_kw must be strictly positive: {p_max_kw}")

        speeds_km_h = speeds_m_s * 3.6

        for i in range(1, self.time):
            # Fuerzas de tracción (mínimo 0 N)
            raw_force = (
                resistances[i]
                + grav_resistances[i]
                + total_mass * gamma * accelerations[i]
            )
            self.traction_force[i] = max(0.0, float(raw_force))

            # Potencia instantánea (Watts)
            self.power[i] = self.traction_force[i] * speeds_m_s[i]

            # Energía instantánea trapezoidal (kWh)
            delta_t_s = times_s[i] - times_s[i - 1]
            self.instant_energy_kw_h[i] = (
                0.5 * (self.power[i] + self.power[i - 1]) * delta_t_s / (3600.0 * 1000.0)
            )

            self.accumulated_engine_energy_kw_h[i] = (
                self.accumulated_engine_energy_kw_h[i - 1] + self.instant_energy_kw_h[i]
            )

            # Porcentaje de potencia respecto al máximo
            self.power_percentage[i] = (
                100.0 * self.power[i] / (p_max_kw * 1000.0)
            )

            # Factor de corrección según velocidad
            if speeds_km_h[i] < v1_km_h:
                factor = ((constants.R1 * speeds_km_h[i]) / v1_km_h) + constants.R2
            else:
                factor = 1.0

            safe_factor = max(factor, 1e-6)

            # Rendimiento del motor
            perf_val = (
                (0.01 - (constants.CEXP * safe_factor))
                * exp(-constants.BEXP * self.power_percentage[i] / safe_factor)
                + (constants.CEXP * safe_factor)
            )
            self.performance[i] = max(perf_val, 1e-6)

            self.instant_energy_fixed_kw_h[i] = (
                self.instant_energy_kw_h[i] / self.performance[i]
            )

            if electric:
                # Rendimiento global estimado en vehículo eléctrico (~90%)
                self.consumption_kw_h[i] = (
                    self.accumulated_engine_energy_kw_h[i] / 0.90
                )
            else:
                # Motor de combustión / híbrido
                if speeds_km_h[i] < 0.1:
                    idle_liters = constants.IDLING_CONSUMPTION * delta_t_s / 3600.0
                    self.consumption_liters[i] = (
                        self.consumption_liters[i - 1] + idle_liters
                    )
                else:
                    avg_fixed_energy = 0.5 * (
                        self.instant_energy_fixed_kw_h[i]
                        + self.instant_energy_fixed_kw_h[i - 1]
                    )
                    self.consumption_liters[i] = self.consumption_liters[i - 1] + (
                        avg_fixed_energy / liters_conversion
                    )

                self.consumption_kw_h[i] = self.accumulated_engine_energy_kw_h[i]

    def calculate_experiment_consumption(
        self, experiment_consumptions: Sequence[float]
    ) -> None:
        """Integrate experimental consumption rate values over time."""
        exp_array = np.asarray(experiment_consumptions, dtype=float).reshape(-1)
        times_s = np.asarray(self.speed_profile.time, dtype=float).reshape(-1)
        limit = min(len(exp_array), self.time, len(times_s))

        for i in range(1, limit):
            val_current = max(0.0, float(exp_array[i]))
            val_previous = max(0.0, float(exp_array[i - 1]))
            delta_t_s = times_s[i] - times_s[i - 1]

            self.consumption_liters[i] = self.consumption_liters[i - 1] + (
                0.5 * (val_current + val_previous) * delta_t_s / 3600.0
            )
