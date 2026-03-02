from route_consumption_estimator.api.models import Vehicle
from route_consumption_estimator.core.vehicle.vehicle_model import VehicleModel
from route_consumption_estimator.vehicle_information.vehicle_information_wrapper import VehicleInformationWrapper


class VehicleInformationDatabase(VehicleInformationWrapper):

    def __init__(self):
        super().__init__()

    def get_vehicle_info_by_id(self, vehicle_id: str) -> Vehicle:
        return Vehicle.query.get(vehicle_id)

    def get_vehicle_model(self, vehicle: Vehicle, additional_mass: int = None):
        if additional_mass:
            vehicle.recalculate_a(int(additional_mass))

        # Create a vehicle using the simulator model
        return VehicleModel(total_veh_mass=int(vehicle.UnladenVehMass) + int(additional_mass),
                            liters_conversion=float(vehicle.LitersConversion),
                            p_max_kw=float(vehicle.PMaxKw),
                            A=float(vehicle.A),
                            B=float(vehicle.B),
                            C=float(vehicle.C),
                            motor_type=str(vehicle.MotorType))
