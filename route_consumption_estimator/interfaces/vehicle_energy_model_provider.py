"""
Vehicle energy model provider interface.

Defines the abstract base contract for integrating route kinematics and vehicle dynamics 
to compute speed profiles and estimate overall power and energy consumption.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from route_consumption_estimator.domain.route_model import RouteModel
from route_consumption_estimator.domain.vehicle_model import VehicleModel


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
