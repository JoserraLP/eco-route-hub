"""
Speed profile provider interface.

Defines the abstract base contract and simulation state structures for 
calculating dynamic vehicle speed profiles, resistances, accelerations, 
and slope-dependent kinematics along a route.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np

from eco_route_hub.domain.constants import GRAVITY
from eco_route_hub.domain.route_model import RouteModel
from eco_route_hub.domain.vehicle_model import VehicleModel

# Maximum longitudinal acceleration limit threshold (0.7 * g)
ACC_LIMIT_PROPORTION: float = 0.7 * GRAVITY


class SpeedProfileProvider(ABC):
    """
    Abstract Base Class for vehicle speed profile calculation engines.

    Maintains time-series kinematics vectors (speed, position, acceleration, forces) 
    and segment boundaries during numerical integration.

    Attributes:
        route (Optional[RouteModel]): Route profile under evaluation.
        vehicle (Optional[VehicleModel]): Vehicle dynamics model.
        acceleration_limit (float): Upper physical boundary for acceleration in m/s².
        step (int): Time-step index counter during simulation execution.
    """

    def __init__(
        self,
        route: Optional[RouteModel] = None,
        vehicle: Optional[VehicleModel] = None,
    ) -> None:
        self.route: Optional[RouteModel] = route
        self._vehicle: Optional[VehicleModel] = vehicle

        # Number of segments in route
        self.num_segments: int = len(route.segment_start_point) if route else 0

        # Segment boundary vectors (NumPy arrays)
        self.segment_end_point: np.ndarray = np.zeros(self.num_segments)
        self.final_speed: np.ndarray = np.zeros(self.num_segments)
        self.segment_length: np.ndarray = np.zeros(self.num_segments)

        # Simulation state time-series vectors
        self.time: List[float] = [0.0]
        self.space: List[float] = [0.0]
        self.state: List[int] = [0]
        self.brake_distance: List[float] = [0.0]
        self.acceleration: List[float] = [0.0]
        self.acceleration_calc: List[float] = [0.0]
        self.resistances: List[float] = [0.0]
        self.gravitational_resistances: List[float] = [0.0]
        self.slope_t: List[float] = [0.0]
        self.delta_t: List[float] = []

        self.acceleration_limit: float = ACC_LIMIT_PROPORTION
        self.speed_m_s: List[float] = [0.0]
        self.step: int = 1

        # Tractive acceleration lookup table by speed tier
        self.ax_trac: Dict[int, float] = (
            {
                1: vehicle.ax_trac1,
                2: vehicle.ax_trac2,
                3: vehicle.ax_trac3,
            }
            if vehicle
            else {}
        )

    @property
    def vehicle(self) -> Optional[VehicleModel]:
        """Get the current vehicle model."""
        return self._vehicle

    @vehicle.setter
    def vehicle(self, value: Optional[VehicleModel]) -> None:
        """Set the vehicle model and automatically sync tractive acceleration limits."""
        self._vehicle = value
        if value:
            self.ax_trac = {
                1: value.ax_trac1,
                2: value.ax_trac2,
                3: value.ax_trac3,
            }

    @abstractmethod
    def estimate_speed_profile(self) -> List[float]:
        """
        Estimate the complete velocity profile (m/s) across the route.

        Returns:
            List[float]: Time-series sequence of vehicle speeds in m/s.
        """
        pass

    @abstractmethod
    def calculate_acceleration(self) -> List[float]:
        """
        Calculate instantaneous longitudinal acceleration profile.

        Returns:
            List[float]: Time-series sequence of accelerations in m/s².
        """
        pass

    @abstractmethod
    def calculate_resistances(self) -> List[float]:
        """
        Calculate total passive resistance forces (aerodynamic, rolling, mechanical).

        Returns:
            List[float]: Time-series sequence of total resistance forces in Newtons.
        """
        pass

    @abstractmethod
    def calculate_slopes_instant(self, heights: List[float]) -> List[float]:
        """
        Calculate instantaneous road slope angles along the profile based on elevation data.

        Args:
            heights (List[float]): Elevation values in meters along route nodes.

        Returns:
            List[float]: Instantaneous slopes (percentage or rads).
        """
        pass

    @abstractmethod
    def calculate_gravitational_resistances(self) -> List[float]:
        """
        Calculate grade/slope resistance forces.

        Returns:
            List[float]: Time-series sequence of gravitational resistance forces in Newtons.
        """
        pass
