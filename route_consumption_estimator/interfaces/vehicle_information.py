from abc import ABC
from typing import Dict, Any

from route_consumption_estimator.domain import VehicleDTO


class VehicleInformationProvider(ABC):

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_vehicle_info_by_id(self, vehicle_id: str):
        pass

    def get_vehicle_model(self, vehicle_information: VehicleDTO, additional_mass: int = None):
        pass
