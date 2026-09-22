from route_consumption_estimator.domain import VehicleDAO, VehicleModel, VehicleDTO
from route_consumption_estimator.domain.parsers import vehicle_dao_to_dto
from route_consumption_estimator.extensions import db
from route_consumption_estimator.interfaces import VehicleInformationProvider


class VehicleInformationRepository(VehicleInformationProvider):

    def __init__(self, config=None):
        super().__init__(config)
        self._database = db

    def get_vehicle_info_by_id(self, vehicle_id: str) -> VehicleDTO:
        return vehicle_dao_to_dto(self._database.session().get(VehicleDAO, vehicle_id))

    def get_vehicle_model(self, vehicle: VehicleDTO, additional_mass: int = None):
        if additional_mass:
            vehicle.recalculate_a(int(additional_mass))

        # Create a vehicle using the simulator model
        return VehicleModel(total_veh_mass=int(vehicle.unladen_veh_mass) + int(additional_mass),
                            liters_conversion=float(vehicle.liters_conversion),
                            p_max_kw=float(vehicle.p_max_kw),
                            A=float(vehicle.A),
                            B=float(vehicle.B),
                            C=float(vehicle.C),
                            motor_type=str(vehicle.motor_type))
