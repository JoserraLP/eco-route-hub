import pandas as pd

from route_consumption_estimator.path.path_model import PathModel
from route_consumption_estimator.vehicle.power_energy import PowerEnergyEstimator
from route_consumption_estimator.vehicle.speed_profile import SpeedProfile
from route_consumption_estimator.vehicle.veh_model import VehicleModel


def read_vehicle_obd_info(file: str):
    # dir = '../matlab_simulators/calculo_consumption_v6/resultado1'
    route = pd.read_csv(file, sep='   ',
                        names=["t", "v", "h", "consumo", "regimen_salida", "parmotor_obd_salida_route"],
                        engine='python')

    # Load from file routes
    time_route = pd.to_numeric(route['t'])  # 1
    speed_route = pd.to_numeric(route['v'])  # 2
    height_route = pd.to_numeric(route['h'])  # 3
    consumption_route = pd.to_numeric(route['consumo'])  # 4

    # Calculate difference of time_route
    time_route_difference = [0]
    for i in range(1, len(time_route)):
        time_route_difference.append(time_route[i] - time_route[i - 1])

    # Calculate distance based on speed
    space = [(speed_route[i] / 3.6) * time_route_difference[i] for i in range(len(time_route_difference))]
    # Define list and accumulate
    acc_space, acc_space_list = 0, [0]
    # Append previous value
    for i in range(len(space) - 1):
        acc_space += space[i]
        acc_space_list.append(acc_space)

    # Return all relevant information
    return time_route, speed_route, height_route, consumption_route, acc_space_list


def estimate_consumption_from_file(file: str, vehicle: VehicleModel):
    time_route, speed_route, height_route, consumption_route, acc_space_list = read_vehicle_obd_info(file)

    # Initialize like this is required
    route = PathModel(segment_start_point=[0], speed_limit_km_h=[0], slope=[0])
    # Define Speed Profile and set manually the required values (speed)
    speed_profile = SpeedProfile(vehicle=vehicle, route=route)
    speed_profile.speed_m_s = speed_route
    speed_profile.time = time_route

    # Calculate acceleration, resistances, slopes and gravitational resistances
    speed_profile.calculate_acceleration()
    speed_profile.calculate_resistances()
    speed_profile.calculate_slopes(heights=height_route)
    speed_profile.calculate_gravitational_resistances()

    # Estimate power consumption
    power_estimator = PowerEnergyEstimator(speed_profile)

    power_estimator.calculate_experiment_consumption(consumption_route)

    return power_estimator.consumption
