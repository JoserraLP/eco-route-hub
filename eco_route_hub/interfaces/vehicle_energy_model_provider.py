"""
Vehicle energy model provider interface.

Defines the abstract base contract for integrating route kinematics and vehicle dynamics 
to compute speed profiles and estimate overall power and energy consumption.
"""

from abc import ABC
from typing import Any, Dict, List, Optional

from eco_route_hub.domain.route_model import RouteModel
from eco_route_hub.domain.vehicle_model import VehicleModel


class VehicleEnergyModelProvider(ABC):
    """
    Abstract Base Class for vehicle energy consumption calculation models.

    Attributes:
        route (Optional[RouteModel]): Route profile under evaluation.
        vehicle (Optional[VehicleModel]): Vehicle physical and powertrain model.
    """

    def __init__(
            self,
            route: Optional[RouteModel] = None,
            vehicle: Optional[VehicleModel] = None,
    ) -> None:
        self.route: Optional[RouteModel] = route
        self.vehicle: Optional[VehicleModel] = vehicle

    def load_route_and_vehicle(
            self, route: RouteModel, vehicle: VehicleModel
    ) -> None:
        """
        Load or update the target route and vehicle models.

        Args:
            route (RouteModel): Analytical route entity.
            vehicle (VehicleModel): Physical vehicle model.
        """
        self.route = route
        self.vehicle = vehicle

    def perform_speed_profile_processing(self) -> None:
        """
        Calculate kinematic and physical forces for the loaded speed profile.

        Computes acceleration, aerodynamic/rolling resistances, and gravitational
        resistances along the route segments.

        Raises:
            RuntimeError: If speed_profile is not initialized.
        """
        pass

    def perform_speed_profile_estimation(self) -> None:
        """
        Estimate the speed profile along the route and process physical forces.

        Generates the speed profile using route constraints and vehicle attributes,
        then triggers downstream acceleration and resistance force calculations.

        Raises:
            RuntimeError: If speed_profile is not initialized.
        """
        pass

    def perform_power_energy_consumption_calculation(self) -> None:
        """
        Calculate instant power and cumulative energy consumption for the vehicle.

        Instantiates a PowerEnergyEstimator and evaluates power consumption based
        on the vehicle's powertrain type (electric vs. conventional).

        Raises:
            RuntimeError: If speed_profile or vehicle is missing (not loaded).
        """
        pass

    def calculate_speed_profile(self) -> List[float]:
        """
        Calculate or retrieve the speed profile across route segments.

        Returns:
            List[float]: Sequence of speeds in m/s along the route profile.
        """
        pass

    def estimate_power_consumption(self) -> Dict[str, Any]:
        """
        Estimate instantaneous power demand and total energy consumption for the route.

        Returns:
            Dict[str, Any]: Consumption telemetry payload (e.g., total energy, power arrays, efficiency).
        """
        pass

    def retrieve_estimations(self):
        """
        Retrieve calculated energy consumption, fuel, and distance metrics for the route.

        Processes power energy estimation outputs based on vehicle powertrain type
        (Electric Vehicle vs. Conventional/ICE), converting metrics into standard units
        and normalized consumption rates per 100 kilometers.

        Returns:
            Dict[str, Any]: Dictionary containing route metrics and energy consumption statistics:
                - distance (float): Total route distance in meters.
                - time (float): Total travel duration in seconds.
                - distanceKm (float): Total route distance in kilometers.
                - fuelEnergyKwh (Optional[float]): Total fuel energy in kWh (conventional vehicles).
                - fuelEnergyKwhPer100Km (Optional[float]): Fuel energy consumption rate in kWh/100 km.
                - tractionEnergyKwh (Optional[float]): Mechanical traction energy in kWh.
                - tractionEnergyKwhPer100Km (Optional[float]): Traction energy rate in kWh/100 km.
                - fuelLiters (Optional[float]): Total fuel consumed in liters.
                - fuelLitersPer100Km (Optional[float]): Fuel consumption rate in L/100 km.
                - batteryEnergyKwh (Optional[float]): Total battery energy in kWh (electric vehicles).
                - batteryKwhPer100Km (Optional[float]): Battery energy consumption rate in kWh/100 km.

        Raises:
            RuntimeError: If route, speed profile, or power estimator objects are not initialized
                or if calculations have not been executed yet.
            ValueError: If distance, time, energy, or fuel consumption values are non-positive or invalid.
        """
        pass
