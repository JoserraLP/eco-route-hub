from route_consumption_estimator.domain.route_model import RouteModel
from route_consumption_estimator.domain.vehicle_model import VehicleModel
from route_consumption_estimator.plugins.vehicle_energy_model_provider.greta.power_energy import PowerEnergyEstimator
from route_consumption_estimator.plugins.speed_profile_provider.speed_profile import SpeedProfile
from route_consumption_estimator.interfaces import VehicleEnergyModelProvider

KWH_PER_GGE = 33.7
LITERS_PER_GALLON = 3.785411784


class GretaEnergyModel(VehicleEnergyModelProvider):

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
        # Estimate the speed profile
        self._speed_profile.estimate_speed_profile()

        self.perform_speed_profile_processing()

    def perform_power_energy_consumption_calculation(self):
        # Initialize power estimator
        self._power_estimator = PowerEnergyEstimator(self._speed_profile)

        self._power_estimator.estimate_power_consumption(electric=self._vehicle.motor_type == 'ELECTRIC')

    def retrieve_estimations(self):
        distance_m = float(self._route.total_distance)
        time_s = float(self._speed_profile.time[-1])

        if distance_m <= 0.0:
            raise ValueError(
                f"Distancia total inválida: {distance_m} m."
            )

        if time_s <= 0.0:
            raise ValueError(
                f"Tiempo total inválido: {time_s} s."
            )

        distance_km = distance_m / 1000.0

        energy_kwh = float(
            self._power_estimator.consumption_kw_h[-1]
        )

        if energy_kwh < 0.0:
            raise ValueError(
                f"Consumo energético inválido: {energy_kwh} kWh."
            )

        motor_type = str(
            self._vehicle.motor_type
        ).strip().lower()

        is_ev = motor_type in {
            "electric",
            "ev",
            "bev",
            "battery_electric",
            "battery electric",
        }

        if is_ev:
            fuel_energy_kwh = None
            fuel_liters = None
            fuel_liters_per_100_km = None
            fuel_energy_kwh_per_100_km = None
            traction_energy_kwh_per_100_km = None
            traction_energy_kwh = None

            battery_energy_kwh = float(energy_kwh)
            battery_kwh_per_100_km = (
                    battery_energy_kwh / distance_km * 100.0
            )
        else:
            fuel_liters = float(self._power_estimator.consumption_liters[-1])
            battery_energy_kwh = None
            battery_kwh_per_100_km = None
            traction_energy_kwh = float(self._power_estimator.consumption_kw_h[-1])

            fuel_energy_kwh_per_liter = (KWH_PER_GGE / LITERS_PER_GALLON)

            fuel_energy_kwh = (fuel_liters * fuel_energy_kwh_per_liter)

            fuel_liters_per_100_km = (fuel_liters / distance_km * 100.0)

            fuel_energy_kwh_per_100_km = (fuel_energy_kwh / distance_km * 100.0)

            traction_energy_kwh_per_100_km = traction_energy_kwh / distance_km * 100.0

        return {
            # Magnitudes comunes.
            "distance": float(distance_m),
            "time": float(time_s),
            "distanceKm": float(distance_km),
            # Energía química del combustible.
            "fuelEnergyKwh": fuel_energy_kwh,
            "fuelEnergyKwhPer100Km": fuel_energy_kwh_per_100_km,
            # Energía útil de tracción.
            "tractionEnergyKwh": traction_energy_kwh,
            "tractionEnergyKwhPer100Km": traction_energy_kwh_per_100_km,
            # Consumo del vehículo de combustible.
            "fuelLiters": fuel_liters,
            "fuelLitersPer100Km": fuel_liters_per_100_km,
            # Consumo del vehículo eléctrico.
            "batteryEnergyKwh": battery_energy_kwh,
            "batteryKwhPer100Km": battery_kwh_per_100_km

        }

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
