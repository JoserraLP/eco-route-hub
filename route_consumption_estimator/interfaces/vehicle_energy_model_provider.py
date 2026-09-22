from abc import ABC

from route_consumption_estimator.domain import RouteModel, VehicleModel


class VehicleEnergyModelProvider(ABC):

    def __init__(self, route: RouteModel, vehicle: VehicleModel):
        self._route = route
        self._vehicle = vehicle

    def load_route_and_vehicle(self, route: RouteModel, vehicle: VehicleModel):
        self._route = route
        self._vehicle = vehicle

    def calculate_speed_profile(self):
        pass

    def estimate_power_consumption(self):
        pass

    @property
    def route(self):
        """
        Getter of route

        :return: route
        """
        return self._route

    @route.setter
    def route(self, route: RouteModel):
        """
        Setter of route

        :param route: route
        :return:
        """
        self._route = route

    @property
    def vehicle(self):
        """
        Getter of vehicle

        :return: vehicle
        """
        return self._vehicle

    @vehicle.setter
    def vehicle(self, vehicle: VehicleModel):
        """
        Setter of vehicle

        :param vehicle: vehicle
        :return:
        """
        self._vehicle = vehicle
