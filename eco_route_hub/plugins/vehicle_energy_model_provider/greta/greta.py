"""
GRETA vehicle energy model provider module.

Estimates speed profile, mechanical resistances, and powertrain energy/power 
consumption based on physical route and vehicle parameters.
"""

import logging
from typing import Any, Dict, Optional

import numpy as np

from eco_route_hub.domain.route_model import RouteModel
from eco_route_hub.domain.vehicle_model import VehicleModel
from eco_route_hub.interfaces import VehicleEnergyModelProvider
from eco_route_hub.plugins.speed_profile_provider.speed_profile import SpeedProfile
from eco_route_hub.plugins.vehicle_energy_model_provider.greta.power_energy import (
    PowerEnergyEstimator,
)

logger = logging.getLogger(__name__)

KWH_PER_GGE = 33.7
LITERS_PER_GALLON = 3.785411784
KWH_PER_LITER = KWH_PER_GGE / LITERS_PER_GALLON


def _is_electric_vehicle(vehicle: Optional[VehicleModel]) -> bool:
    """Determine if vehicle is an Electric Vehicle (EV/BEV)."""
    if vehicle is None:
        return False

    motor_type = str(getattr(vehicle, "motor_type", "")).strip().lower()
    return motor_type in {
        "electric",
        "ev",
        "bev",
        "battery_electric",
        "battery electric",
    }


def _get_last_element(sequence: Any, name: str) -> float:
    """Safely extract the terminal value from a list or NumPy array as a float."""
    if sequence is None:
        raise ValueError(f"Sequence '{name}' cannot be None.")

    array = np.reshape(np.asarray(sequence, dtype=float),-1)
    if len(array) == 0:
        raise ValueError(f"Sequence '{name}' is empty.")

    val = float(array[-1])
    if not np.isfinite(val):
        raise ValueError(
            f"Sequence '{name}' contains a non-finite terminal value: {val}."
        )

    return val


class GretaEnergyModel(VehicleEnergyModelProvider):
    """
    Energy model provider using the GRETA physical movement and powertrain estimation engine.
    """

    def __init__(
        self,
        route: Optional[RouteModel] = None,
        vehicle: Optional[VehicleModel] = None,
    ) -> None:
        super().__init__(route, vehicle)
        self.speed_profile: Optional[SpeedProfile] = (
            SpeedProfile(route=self.route, vehicle=self.vehicle)
            if self.route is not None and self.vehicle is not None
            else None
        )
        self.power_estimator: Optional[PowerEnergyEstimator] = None

    def load_route_and_vehicle(
        self,
        route: RouteModel,
        vehicle: VehicleModel,
    ) -> None:
        super().load_route_and_vehicle(route, vehicle)
        self.speed_profile = SpeedProfile(
            route=self.route,
            vehicle=self.vehicle,
        )
        self.power_estimator = None
        logger.debug("Loaded new route and vehicle into GretaEnergyModel.")

    def perform_speed_profile_processing(self) -> None:
        if self.speed_profile is None:
            raise RuntimeError("Speed profile is not initialized.")

        self.speed_profile.calculate_acceleration()
        self.speed_profile.calculate_resistances()
        self.speed_profile.calculate_gravitational_resistances()

    def perform_speed_profile_estimation(self) -> None:
        if self.speed_profile is None:
            raise RuntimeError("Speed profile is not initialized.")

        self.speed_profile.estimate_speed_profile()
        self.perform_speed_profile_processing()

    def perform_power_energy_consumption_calculation(self) -> None:
        if self.speed_profile is None or self.vehicle is None:
            raise RuntimeError(
                "Cannot calculate power/energy consumption: route or vehicle not loaded."
            )

        self.power_estimator = PowerEnergyEstimator(self.speed_profile)
        is_ev = _is_electric_vehicle(self.vehicle)

        logger.debug(f"Estimating power consumption in GRETA (is_ev={is_ev}).")
        self.power_estimator.estimate_power_consumption(electric=is_ev)

    def retrieve_estimations(self) -> Dict[str, Any]:
        if self.route is None:
            raise RuntimeError("Route object is missing.")
        if self.speed_profile is None:
            raise RuntimeError("Speed profile object is missing.")
        if self.power_estimator is None:
            raise RuntimeError(
                "Power energy estimations have not been calculated yet. "
                "Call perform_power_energy_consumption_calculation() first."
            )

        distance_m = float(getattr(self.route, "total_distance", 0.0))
        time_s = _get_last_element(
            getattr(self.speed_profile, "time", None),
            "speed_profile.time",
        )

        if distance_m <= 0.0:
            raise ValueError(f"Invalid total distance: {distance_m} m.")
        if time_s <= 0.0:
            raise ValueError(f"Invalid total time: {time_s} s.")

        distance_km = distance_m / 1000.0

        energy_kwh = _get_last_element(
            getattr(self.power_estimator, "consumption_kw_h", None),
            "power_estimator.consumption_kw_h",
        )

        if energy_kwh < 0.0:
            raise ValueError(f"Invalid energy consumption: {energy_kwh} kWh.")

        is_ev = _is_electric_vehicle(self.vehicle)

        if is_ev:
            battery_energy_kwh = float(energy_kwh)
            battery_kwh_per_100_km = (battery_energy_kwh / distance_km) * 100.0

            fuel_energy_kwh = None
            fuel_energy_kwh_per_100_km = None
            traction_energy_kwh = None
            traction_energy_kwh_per_100_km = None
            fuel_liters = None
            fuel_liters_per_100_km = None
        else:
            fuel_liters = _get_last_element(
                getattr(self.power_estimator, "consumption_liters", None),
                "power_estimator.consumption_liters",
            )
            if fuel_liters < 0.0:
                raise ValueError(f"Invalid fuel consumption: {fuel_liters} L.")

            battery_energy_kwh = None
            battery_kwh_per_100_km = None

            traction_energy_kwh = float(energy_kwh)
            traction_energy_kwh_per_100_km = (
                traction_energy_kwh / distance_km
            ) * 100.0

            fuel_energy_kwh = fuel_liters * KWH_PER_LITER
            fuel_liters_per_100_km = (fuel_liters / distance_km) * 100.0
            fuel_energy_kwh_per_100_km = (
                fuel_energy_kwh / distance_km
            ) * 100.0

        return {
            "distance": float(distance_m),
            "time": float(time_s),
            "distanceKm": float(distance_km),
            "fuelEnergyKwh": fuel_energy_kwh,
            "fuelEnergyKwhPer100Km": fuel_energy_kwh_per_100_km,
            "tractionEnergyKwh": traction_energy_kwh,
            "tractionEnergyKwhPer100Km": traction_energy_kwh_per_100_km,
            "fuelLiters": fuel_liters,
            "fuelLitersPer100Km": fuel_liters_per_100_km,
            "batteryEnergyKwh": battery_energy_kwh,
            "batteryKwhPer100Km": battery_kwh_per_100_km,
        }
