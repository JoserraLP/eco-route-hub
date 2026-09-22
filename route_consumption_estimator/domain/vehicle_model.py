"""
Physical vehicle domain model for consumption estimation algorithms.

Defines mechanical, aerodynamic, powertrain, and dynamic limits 
used by physics calculation engines.
"""

from dataclasses import dataclass
from typing import Union

from route_consumption_estimator.domain.enums import MotorTypeEnum


@dataclass
class VehicleModel:
    """
    Physical vehicle entity representation used in consumption simulations.

    Attributes:
        total_mass (float): Total vehicle mass in kg (unladen mass + payload/passengers).
        p_max_kw (float): Maximum engine power output in kW.
        liters_conversion (float): Energy conversion factor to equivalent fuel/energy units.
        A (float): Coastdown resistance coefficient A (rolling resistance in N).
        B (float): Coastdown resistance coefficient B (viscous resistance in N/(km/h)).
        C (float): Coastdown resistance coefficient C (aerodynamic drag in N/(km/h)²).
        motor_type (Union[MotorTypeEnum, str]): Powertrain classification.
        gamma (float): Rotational mass factor (accounts for rotating inertia, default 1.05).
        auxiliar_consumption_l_h (float): Auxiliary equipment power/fuel consumption rate (L/h).
        v1_km_h (float): First speed threshold for dynamic acceleration limits in km/h.
        v2_km_h (float): Second speed threshold for dynamic acceleration limits in km/h.
        ax_trac1 (float): Max tractive acceleration under v1_km_h (m/s²).
        ax_trac2 (float): Max tractive acceleration between v1_km_h and v2_km_h (m/s²).
        ax_trac3 (float): Max tractive acceleration above v2_km_h (m/s²).
        ax_brake (float): Max braking deceleration limit in m/s² (negative value).
    """

    total_mass: float
    p_max_kw: float
    liters_conversion: float
    A: float
    B: float
    C: float
    motor_type: Union[MotorTypeEnum, str]
    gamma: float = 1.05
    auxiliar_consumption_l_h: float = 0.0

    # Driving dynamics criteria parameters
    v1_km_h: float = 50.0
    v2_km_h: float = 100.0
    ax_trac1: float = 2.0
    ax_trac2: float = 1.0
    ax_trac3: float = 0.5
    ax_brake: float = -2.0

    def get_max_acceleration(self, speed_km_h: float) -> float:
        """
        Get maximum tractive acceleration limit based on current vehicle speed range.

        Args:
            speed_km_h (float): Current vehicle speed in km/h.

        Returns:
            float: Maximum allowable acceleration in m/s².
        """
        if speed_km_h < self.v1_km_h:
            return self.ax_trac1
        if speed_km_h < self.v2_km_h:
            return self.ax_trac2
        return self.ax_trac3
