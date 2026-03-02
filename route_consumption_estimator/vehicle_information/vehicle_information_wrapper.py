from abc import ABC

from route_consumption_estimator.api.models import Vehicle


class VehicleInformationWrapper(ABC):

    def __init__(self):
        pass

    def get_vehicle_info_by_id(self, vehicle_id: str):
        pass

    def get_vehicle_model(self, vehicle_information: Vehicle, additional_mass: int = None):
        pass
