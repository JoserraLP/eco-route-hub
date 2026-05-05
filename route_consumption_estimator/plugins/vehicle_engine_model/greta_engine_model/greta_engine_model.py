from route_consumption_estimator.domain import RouteModel, VehicleModel
from route_consumption_estimator.plugins.vehicle_engine_model.greta_engine_model.power_energy import PowerEnergyEstimator
from route_consumption_estimator.plugins.vehicle_engine_model.greta_engine_model.speed_profile import SpeedProfile
from route_consumption_estimator.interfaces import VehicleEngineModelProvider


class GretaEngineModel(VehicleEngineModelProvider):

    def __init__(self, route: RouteModel = None, vehicle: VehicleModel = None):
        super().__init__(route, vehicle)
        # Initialize vehicle movement object
        self._speed_profile = SpeedProfile(route=self._route, vehicle=self._vehicle)
        self._power_estimator = None

    def load_route_and_vehicle(self, route: RouteModel, vehicle: VehicleModel):
        super().__init__(route, vehicle)
        # Initialize vehicle movement object
        self._speed_profile = SpeedProfile(route=self._route, vehicle=self._vehicle)
        self._power_estimator = None

    def perform_speed_profile_processing(self):
        # Calculate acceleration
        self._speed_profile.calculate_acceleration()

        # Calculate resistances
        self._speed_profile.calculate_resistances()

        # Calculate slopes
        self._speed_profile.calculate_gravitational_resistances()

    def perform_speed_profile_estimation(self):
        print(self._speed_profile)
        # Estimate the speed profile
        self._speed_profile.estimate_speed_profile()

        self.perform_speed_profile_processing()

    def perform_power_energy_consumption_calculation(self):
        # Initialize power estimator
        self._power_estimator = PowerEnergyEstimator(self._speed_profile)

        self._power_estimator.estimate_power_consumption(electric=self._vehicle.motor_type == 'ELECTRIC')

    def retrieve_estimations(self):
        return {'EnergyConsumption': self._power_estimator.consumption[-1],
                'Distance': self._route.total_distance,
                'Time': self._speed_profile.time[-1]}

    @property
    def speed_profile(self):
        """
        Getter of speed_profile

        :return: speed_profile
        """
        return self._speed_profile

    @speed_profile.setter
    def speed_profile(self, speed_profile: SpeedProfile):
        """
        Setter of speed_profile

        :param speed_profile: speed_profile
        :return:
        """
        self._speed_profile = speed_profile

    @property
    def power_estimator(self):
        """
        Getter of power_estimator

        :return: power_estimator
        """
        return self._power_estimator

    @power_estimator.setter
    def power_estimator(self, power_estimator: PowerEnergyEstimator):
        """
        Setter of power_estimator

        :param power_estimator: power_estimator
        :return:
        """
        self._power_estimator = power_estimator
