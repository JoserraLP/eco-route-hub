"""
Vehicle information provider interface.

Defines the abstract base contract for fetching vehicle specs from external databases/APIs
and constructing domain vehicle models with payload/additional mass adjustments.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from route_consumption_estimator.domain.dto_models import VehicleDTO
from route_consumption_estimator.domain.vehicle_model import VehicleModel


class VehicleInformationProvider(ABC):
    """
    Abstract Base Class for vehicle data lookup and instantiation providers.

    Attributes:
        config (Dict[str, Any]): Provider configuration settings or connection details.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or {}

    @abstractmethod
    def get_vehicle_info_by_id(self, vehicle_id: str) -> VehicleDTO:
        """
        Retrieve raw vehicle specifications and parameters by identifier.

        Args:
            vehicle_id (str): Unique vehicle identification key or code.

        Returns:
            VehicleDTO: Data Transfer Object containing vehicle specification telemetry.
        """
        pass

    @abstractmethod
    def get_vehicle_model(
        self,
        vehicle_information: VehicleDTO,
        additional_mass: Optional[float] = None,
    ) -> VehicleModel:
        """
        Build a physical VehicleModel domain entity from a VehicleDTO and optional extra payload.

        Args:
            vehicle_information (VehicleDTO): Raw vehicle specification data object.
            additional_mass (Optional[float]): Cargo or passenger load in kg to add to base mass.

        Returns:
            VehicleModel: Instantiated domain vehicle entity ready for physics calculation.
        """
        pass
