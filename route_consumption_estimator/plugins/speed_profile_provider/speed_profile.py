"""
Speed profile estimation plugin module.

Simulates vehicle kinematics along route micro-segments considering speed limits,
traction profiles, braking limits, and road geometry (slopes).
"""

import logging
from typing import List, Optional, Union

import numpy as np

from route_consumption_estimator.domain.constants import GRAVITY
from route_consumption_estimator.domain.route_model import RouteModel
from route_consumption_estimator.domain.vehicle_model import VehicleModel
from route_consumption_estimator.interfaces import SpeedProfileProvider

logger = logging.getLogger(__name__)

MIN_SPEED_MS = 0.1  # Minimum threshold speed in m/s (~0.36 km/h) to prevent division by zero
MAX_SIMULATION_STEPS_PER_SEGMENT = 10000
DEFAULT_ACCELERATION_LIMIT = 2.5
DEFAULT_SPEED = 50.0
DEFAULT_V1_KM_H = 50.0
DEFAULT_V2_KM_H = 100.0
DEFAULT_AX_BRAKE = -2.0
MAX_SLOPE_VARIANCE = 0.2


def calculate_acceleration_factor(speed_t: float, speed_limit: float) -> float:
    """
    Calculate acceleration factor based on proximity to the target speed limit.

    Args:
        speed_t (float): Current instantaneous speed in m/s.
        speed_limit (float): Speed limit in m/s.

    Returns:
        float: Acceleration smoothing factor (0.25, 0.5, or 1.0).
    """
    difference = abs(speed_t - speed_limit)
    if difference < 1.0:
        return 0.25
    elif difference < 3.0:
        return 0.5
    return 1.0


class SpeedProfile(SpeedProfileProvider):
    """
    Plugin provider for simulating vehicle kinematic speed profiles over route segments.
    """

    def __init__(
            self,
            route: Optional[RouteModel] = None,
            vehicle: Optional[VehicleModel] = None,
    ) -> None:
        super().__init__(route, vehicle)

    def estimate_speed_profile(self) -> List[float]:
        """
        Estimate instantaneous vehicle speed profile (m/s) over time for the target route.

        Returns:
            List[float]: Series of instantaneous vehicle speeds in m/s.
        """
        if not self.route or not self.route.segment_start_point:
            logger.warning("Route model is empty or uninitialized in SpeedProfile.")
            return self.speed_m_s

        maxspeeds = self.route.additional_info.get("maxspeed", [])
        slopes = self.route.additional_info.get("slopes", [])
        num_points = len(self.route.segment_start_point)

        for i in range(0, num_points - 1):
            # Resolve segment destination and target speed limit
            if i < getattr(self, "_num_segments", num_points - 1) and i + 1 < len(maxspeeds):
                segment_end_point = self.route.segment_start_point[i + 1]
                final_speed = maxspeeds[i + 1] / 3.6
            else:
                segment_end_point = max(self.route.segment_start_point)
                final_speed = maxspeeds[i] / 3.6 if i < len(maxspeeds) else (DEFAULT_SPEED / 3.6)

            segment_length = segment_end_point - self.route.segment_start_point[i]
            if i < len(self.segment_length):
                self.segment_length[i] = segment_length
            else:
                self.segment_length = np.append(self.segment_length, segment_length)

            speed_limit = max(final_speed, MIN_SPEED_MS)
            delta_t_segment = segment_length / speed_limit
            self.delta_t.append(delta_t_segment)

            current_slope = slopes[i] if i < len(slopes) else 0.0

            ax_brake = getattr(self.vehicle, "ax_brake", DEFAULT_AX_BRAKE) or DEFAULT_AX_BRAKE
            if ax_brake == 0:
                ax_brake = DEFAULT_AX_BRAKE

            v1_ms = (getattr(self.vehicle, "v1_km_h", DEFAULT_V1_KM_H) or DEFAULT_V1_KM_H) / 3.6
            v2_ms = (getattr(self.vehicle, "v2_km_h", DEFAULT_V2_KM_H) or DEFAULT_V2_KM_H) / 3.6

            sim_steps = 0
            while (
                    self.space[self.step - 1] <= segment_end_point
                    and sim_steps < MAX_SIMULATION_STEPS_PER_SEGMENT
            ):
                sim_steps += 1
                self.slope_t.append(current_slope)

                current_speed = self.speed_m_s[self.step - 1]

                # Braking distance calculation
                brake_distance = (final_speed ** 2 - current_speed ** 2) / (2 * ax_brake)

                # Determine kinematic acceleration state
                if current_speed >= final_speed:
                    if self.space[self.step - 1] < (segment_end_point - brake_distance):
                        if current_speed < speed_limit:
                            factor = calculate_acceleration_factor(current_speed, speed_limit)
                            a = self._get_traction_acceleration(current_speed, v1_ms, v2_ms, factor)
                            self.state.append(1)
                        else:
                            if current_speed > speed_limit:
                                factor = calculate_acceleration_factor(current_speed, speed_limit)
                                a = factor * ax_brake
                                self.state.append(-1)
                            else:
                                a = 0.0
                                self.state.append(0)
                    else:
                        factor = calculate_acceleration_factor(current_speed, speed_limit)
                        a = factor * ax_brake
                        self.state.append(-1)
                else:
                    if current_speed < speed_limit:
                        factor = calculate_acceleration_factor(current_speed, speed_limit)
                        a = self._get_traction_acceleration(current_speed, v1_ms, v2_ms, factor)
                        self.state.append(1)
                    else:
                        a = 0.0
                        self.state.append(0)

                # Bound acceleration to maximum physical limits
                accel_limit = getattr(self, "acceleration_limit", DEFAULT_ACCELERATION_LIMIT)
                if a > accel_limit:
                    a = accel_limit

                speed_calc = max(current_speed + a * delta_t_segment, 0.0)

                # Smooth speed near boundary
                if speed_calc - speed_limit < 0.1 or speed_calc > speed_limit:
                    self.speed_m_s.append(speed_limit)
                else:
                    self.speed_m_s.append(speed_calc)

                next_speed = self.speed_m_s[self.step]
                step_space = (
                        self.space[self.step - 1]
                        + next_speed * delta_t_segment
                        + 0.5 * a * (delta_t_segment ** 2)
                )
                self.space.append(step_space)
                self.time.append(self.time[self.step - 1] + delta_t_segment)
                self.step += 1

            if sim_steps >= MAX_SIMULATION_STEPS_PER_SEGMENT:
                logger.warning(
                    f"Simulation loop reached maximum threshold ({MAX_SIMULATION_STEPS_PER_SEGMENT}) at segment index {i}."
                )

        return self.speed_m_s

    def _get_traction_acceleration(
            self, current_speed: float, v1_ms: float, v2_ms: float, factor: float
    ) -> float:
        """Helper method to calculate traction acceleration based on speed range."""
        ax_trac = getattr(self, "ax_trac", [2.0, 1.0, 0.5])
        if len(ax_trac) < 3:
            ax_trac = [2.0, 1.0, 0.5]

        if current_speed < v1_ms:
            return factor * ax_trac[1]
        elif current_speed > v2_ms:
            return factor * ax_trac[3]
        else:
            return factor * ax_trac[2]

    def calculate_acceleration(self) -> List[float]:
        """
        Calculate step-wise acceleration series (m/s^2) based on speed and time vectors.

        Returns:
            List[float]: Acceleration series in m/s^2.
        """
        self.acceleration = [0.0]
        speed_km_h = [speed * 3.6 for speed in self.speed_m_s]

        for i in range(1, len(speed_km_h)):
            dt = self.time[i] - self.time[i - 1] if i < len(self.time) else 0.0
            if dt > 0.0:
                val = (1.0 / 3.6) * (speed_km_h[i] - speed_km_h[i - 1]) / dt
            else:
                val = 0.0

            accel_limit = getattr(self, "acceleration_limit", DEFAULT_ACCELERATION_LIMIT)
            if val > accel_limit:
                self.acceleration.append(accel_limit)
            else:
                self.acceleration.append(val)

        return self.acceleration

    def calculate_resistances(
            self,
            pressures_pa: Optional[Union[List[float], np.ndarray]] = None,
            temperatures_celsius: Optional[Union[List[float], np.ndarray]] = None,
    ) -> List[float]:
        """Calculate total road-load resistance force (A + B*v + C_adj*v^2) in Newtons using SI units (m/s).

        Dynamically adjusts aerodynamic coefficient C based on atmospheric pressure (Pa)
        and temperature (°C) retrieved from self.route.additional_info or explicit parameters.

        Returns:
            List[float]: Resistance force series in Newtons.
        """
        speeds_m_s = np.asarray(self.speed_m_s, dtype=float)

        # Coefficients in SI units: A [N], B [N/(m/s)], C [N/(m/s)^2]
        a_coeff = float(getattr(self.vehicle, "A", 0.0) or 0.0)
        b_coeff = float(getattr(self.vehicle, "B", 0.0) or 0.0)
        c_ref = float(getattr(self.vehicle, "C", 0.0) or 0.0)

        # Extract additional_info dictionary from self.route if present
        route = getattr(self, "route", None)
        additional_info = getattr(route, "additional_info", {}) if route is not None else {}
        if not isinstance(additional_info, dict):
            additional_info = {}

        # Extract pressure (Pa) from parameters -> route.additional_info
        if pressures_pa is None:
            pressures_pa = additional_info.get("pressures_pa") or additional_info.get("pressure")
            # Remove last pressure
            if pressures_pa:
                pressures_pa = pressures_pa[:-1]

        # Extract temperature (°C) from parameters -> route.additional_info
        if temperatures_celsius is None:
            temperatures_celsius = additional_info.get("temperatures_celsius") or additional_info.get("temp")
            # Remove last temperature
            if temperatures_celsius:
                temperatures_celsius = temperatures_celsius[:-1]

        # Dynamically adjust aerodynamic coefficient C based on local air density
        if pressures_pa is not None and len(pressures_pa) == len(speeds_m_s):
            pressures = np.asarray(pressures_pa, dtype=float)

            p_ref = 101325.0  # Standard sea-level atmospheric pressure (Pa)
            t_ref_k = 288.15  # Standard sea-level temperature (15°C in Kelvin)

            if temperatures_celsius is not None and len(temperatures_celsius) == len(speeds_m_s):
                temps_k = np.asarray(temperatures_celsius, dtype=float) + 273.15
            else:
                temps_k = np.full_like(pressures, t_ref_k)

            # Air density ratio relative to ISA conditions (rho / rho_0)
            air_density_ratio = (pressures / p_ref) * (t_ref_k / temps_k)

            # Vector of point-by-point adjusted C coefficients
            c_coeff = c_ref * air_density_ratio
        else:
            c_coeff = c_ref

        # Road-load equation in SI units: F_res = A + B*v + C_adj*v^2
        resistances_array = a_coeff + (b_coeff * speeds_m_s) + (c_coeff * (speeds_m_s ** 2))
        self.resistances = resistances_array.tolist()
        return self.resistances

    def calculate_slopes_instant(self, heights: List[float]) -> None:
        """
        Calculate instantaneous road slopes per simulation step from height elevation profile.

        Args:
            heights (List[float]): Elevation points in meters.
        """
        self.slope_t = [0.0]
        speed_km_h = [speed * 3.6 for speed in self.speed_m_s]

        for i in range(1, len(heights)):
            dt = self.time[i] - self.time[i - 1] if i < len(self.time) else 0.0
            avg_speed_kmh = (
                0.5 * (speed_km_h[i] + speed_km_h[i - 1])
                if i < len(speed_km_h)
                else 0.0
            )
            segment_length = (avg_speed_kmh / 3.6) * dt
            delta_h = heights[i] - heights[i - 1]

            if segment_length <= 0.0:
                self.slope_t.append(0.0)
            else:
                slope_val = delta_h / segment_length
                if abs(slope_val) > MAX_SLOPE_VARIANCE:
                    if i < len(speed_km_h) and speed_km_h[i] < 5.0:
                        self.slope_t.append(0.0)
                    else:
                        self.slope_t.append(0.2 * (1.0 if slope_val > 0 else -1.0))
                else:
                    self.slope_t.append(slope_val)

    def calculate_gravitational_resistances(self) -> List[float]:
        """
        Calculate gravitational resistance forces (N) based on slope gradient and vehicle mass.

        Returns:
            List[float]: Gravitational resistance force series in Newtons.
        """
        self.gravitational_resistances = []
        mass = getattr(self.vehicle, "total_mass", 1500.0) or 1500.0

        for i in range(len(self.speed_m_s)):
            slope = self.slope_t[i] if i < len(self.slope_t) else 0.0
            grav_resistance = GRAVITY * mass * slope
            self.gravitational_resistances.append(grav_resistance)

        return self.gravitational_resistances
