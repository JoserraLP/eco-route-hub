"""
Vehicle information repository plugin module.

Fetches vehicle records from database ORM models and instantiates simulator vehicle models.
"""

import logging
from typing import Any, Optional

from route_consumption_estimator.domain.dao_models import VehicleDAO
from route_consumption_estimator.domain.dto_models import VehicleDTO
from route_consumption_estimator.domain.parsers import vehicle_dao_to_dto
from route_consumption_estimator.domain.vehicle_model import VehicleModel
from route_consumption_estimator.extensions import db
from route_consumption_estimator.interfaces import VehicleInformationProvider

logger = logging.getLogger(__name__)


class VehicleInformationRepository(VehicleInformationProvider):
    """
    SQLAlchemy-backed repository for retrieving vehicle records and instantiating vehicle models.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(config)
        self._database = db

    def get_vehicle_info_by_id(self, vehicle_id: str) -> VehicleDTO:
        """
        Retrieve vehicle information DTO by vehicle ID from the database.

        Args:
            vehicle_id (str): Unique vehicle identifier.

        Returns:
            VehicleDTO: Vehicle data transfer object.

        Raises:
            ValueError: If no vehicle matching the given ID exists in the database.
        """
        # Resolve SQLAlchemy session safely whether it's a scoped session property or callable
        session = getattr(self._database, "session", self._database)
        if callable(session):
            session = session()

        vehicle_dao = session.get(VehicleDAO, vehicle_id)
        if not vehicle_dao:
            logger.error(f"Vehicle with ID '{vehicle_id}' not found in database.")
            raise ValueError(f"Vehicle with ID '{vehicle_id}' not found.")

        return vehicle_dao_to_dto(vehicle_dao)

    def get_vehicle_model(
        self, vehicle: VehicleDTO, additional_mass: Optional[int] = None
    ) -> VehicleModel:
        """
        Instantiate a simulator VehicleModel configured with vehicle physical parameters.

        Args:
            vehicle (VehicleDTO): Vehicle data transfer object.
            additional_mass (Optional[int]): Additional payload/mass in kg.

        Returns:
            VehicleModel: Physics model instance for vehicle simulation.
        """
        add_mass = int(additional_mass) if additional_mass is not None else 0

        if add_mass > 0 and hasattr(vehicle, "recalculate_vehicle_coefficients"):
            vehicle.recalculate_vehicle_coefficients(add_mass)

        unladen_mass = int(getattr(vehicle, "unladen_veh_mass", 0) or 0)
        total_mass = unladen_mass + add_mass

        return VehicleModel(
            total_mass=total_mass,
            liters_conversion=float(getattr(vehicle, "liters_conversion", 0.0) or 0.0),
            p_max_kw=float(getattr(vehicle, "p_max_kw", 0.0) or 0.0),
            A=float(getattr(vehicle, "A", 0.0) or 0.0),
            B=float(getattr(vehicle, "B", 0.0) or 0.0),
            C=float(getattr(vehicle, "C", 0.0) or 0.0),
            motor_type=str(getattr(vehicle, "motor_type", "combustion")),
        )
