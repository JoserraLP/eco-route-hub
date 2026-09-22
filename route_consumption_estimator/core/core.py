import numpy as np
import polyline
from flask import current_app

from route_consumption_estimator.core import GraphEngine, PluginRegistry, \
    calculate_distances, calculate_slopes, smoothing_process, evaluate_consumption
from route_consumption_estimator.core.route_processor import RouteProcessor
from route_consumption_estimator.domain import Coords, RouteModel
from route_consumption_estimator.domain.constants import PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER, \
    PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER, PLUGIN_TYPE_AMBIENT_WEATHER_PROVIDER, PLUGIN_TYPE_ROAD_ROUTE_PROVIDER, \
    PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER, PLUGIN_TYPE_SPEED_PROFILE_PROVIDER, PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER, \
    PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER, PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER

class Core:

    def __init__(self, registry: PluginRegistry,
                 vehicle_id: str,
                 additional_mass: int = 0,
                 alpha=None,
                 models=None):

        self._registry = registry

        self._road_infrastructure_providers = registry.get_all(PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER)
        self._traffic_operation_providers = registry.get_all(PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER)
        self._ambient_weather_providers = registry.get_all(PLUGIN_TYPE_AMBIENT_WEATHER_PROVIDER)
        self._road_route_providers = registry.get_all(PLUGIN_TYPE_ROAD_ROUTE_PROVIDER)
        self._driving_behavior_providers = registry.get_all(PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER)
        self._speed_profile_provider = registry.get(PLUGIN_TYPE_SPEED_PROFILE_PROVIDER)
        self._route_segmentation_provider = registry.get(PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER)
        if not models:
            self._vehicle_energy_model_providers = registry.get_all(PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER)
        else:
            self._vehicle_energy_model_providers = registry.get_specific_plugins(
                PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER, models)
            self._specific_vehicle_energy_model_names = models

        self._vehicle_information_provider = registry.get(PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER)

        self._graph_engine = GraphEngine()
        self._route_processor = RouteProcessor(route_segmentation_provider=self._route_segmentation_provider,
                                               road_infrastructure_providers=self._road_infrastructure_providers,
                                               road_route_providers=self._road_route_providers,
                                               traffic_operation_providers=self._traffic_operation_providers,
                                               ambient_weather_providers=self._ambient_weather_providers)

        current_app_config = current_app.config["APP_CONFIG"].system
        self._alpha = alpha if alpha else current_app_config.smoothing_factor_alpha

        # Get vehicle information and core model
        vehicle_information = self._vehicle_information_provider.get_vehicle_info_by_id(vehicle_id)

        self._vehicle_model = self._vehicle_information_provider.get_vehicle_model(vehicle=vehicle_information,
                                                                                    additional_mass=additional_mass)

    def execute_benchmarking_workflow(self, coordinates: str):
        # Request routes
        routes = self._route_processor.request_all_routes(coordinates)
        if routes:
            # Process routes information
            routes_information = self.store_routes_into_graph(routes)

            estimations = self.estimate_consumption_routes(routes, routes_information,
                                                           self._specific_vehicle_energy_model_names)

            # Merge both routes and estimations
            routes_estimations = [{**x, **y} for x, y in zip(routes, estimations)]

            # Define final routes
            final_routes = routes_estimations
        else:
            # Define final routes
            final_routes = {}

        return final_routes

    def execute_route_estimation_workflow(self, coordinates: str):
        # Request routes
        routes = self._route_processor.request_all_routes(coordinates)
        if routes:
            # Process routes information
            routes_information = self.store_routes_into_graph(routes)

            estimations = self.estimate_consumption_routes(routes, routes_information)

            # Merge both routes and estimations
            routes_estimations = [{**x, **y} for x, y in zip(routes, estimations)]

            # Filter the route: Eco, Shortest and Fastest
            consumption_index = min(enumerate(routes_estimations), key=lambda x: x[1]['EnergyConsumption'])[0]
            distance_index = min(enumerate(routes_estimations), key=lambda x: x[1]['Distance'])[0]
            time_index = min(enumerate(routes_estimations), key=lambda x: x[1]['Time'])[0]

            # Define final routes
            final_routes = {
                'eco': estimations[consumption_index],
                'shortest': estimations[distance_index],
                'fastest': estimations[time_index]
            }
        else:
            # Define final routes
            final_routes = {}

        return final_routes

    def store_routes_into_graph(self, routes: list):
        # Store the routes information into graph
        self._graph_engine.routes = routes

        self._graph_engine.store_routes_graph()

        self._graph_engine.extend_graph_info()

        # router_distance
        avg_route_distance = np.mean([route['router_distance'] for route in routes if 'router_distance' in route])

        if avg_route_distance == 0:
            avg_route_distance = routes[0]['distances'][-1]

        # Get the routes' information (by micro segments)
        return self._graph_engine.get_routes_information(avg_route_distance)

    # CONSUMPTION ESTIMATION
    def estimate_consumption_routes(self, routes: list, routes_information: list,
                                    specific_energy_providers_names: list = None):
        current_app_config = current_app.config["APP_CONFIG"].system

        all_estimations = []
        # Create a route class with each route
        for i, route_information in enumerate(routes_information):
            # Process route to encode it
            encoded_route = ''
            if 'segments_representation' in routes[i]:
                processed_route = [(item.lat, item.lon) for item in routes[i]['segments_representation']]

                encoded_route = polyline.encode(processed_route, current_app_config.polyline_precision)

            additional_info = {k: v for k, v in route_information.items() if k != 'start_points'}

            route = RouteModel(segment_start_point=route_information['start_points'],
                               additional_info=additional_info)

            for vehicle_model_idx, vehicle_engine_model in enumerate(self._vehicle_energy_model_providers):
                # Set current route and vehicle information
                vehicle_engine_model.load_route_and_vehicle(route, self._vehicle_model)
                vehicle_engine_model.perform_speed_profile_estimation()

                vehicle_engine_model.perform_power_energy_consumption_calculation()

                all_info = vehicle_engine_model.retrieve_estimations() | {'route': fr"{encoded_route}"}

                if specific_energy_providers_names:
                    all_info = all_info | {'model': specific_energy_providers_names[vehicle_model_idx]}

                all_estimations.append(all_info)

        return all_estimations

    # REAL CONSUMPTION CALCULATION
    def process_polyline_route(self, route_polyline: str):
        current_app_config = current_app.config["APP_CONFIG"].system
        performed_route_coords = polyline.decode(route_polyline, current_app_config.polyline_precision)

        # Parse polyline into list of coords
        performed_route_coords = [Coords(lat=item[0], lon=item[1]) for item in performed_route_coords]

        processed_performed_route = self._route_processor.process_route(route_coordinates=performed_route_coords,
                                                                        common_source=performed_route_coords[0],
                                                                        common_target=performed_route_coords[-1])
        routes_information = self.store_routes_into_graph([processed_performed_route])

        return routes_information

    def smooth_sensor_data(self, speeds: list, heights: list):
        speeds = smoothing_process([item / 3.6 for item in speeds], alpha=self._alpha)

        heights = smoothing_process(heights, alpha=self._alpha)

        return speeds, heights

    def execute_route_real_consumption_workflow(self, vehicle_id: str, additional_mass: int, heights: list,
                                                speeds: list, times: list):
        # Get vehicle information and core model
        vehicle_information = self._vehicle_information_provider.get_vehicle_info_by_id(vehicle_id)

        vehicle = self._vehicle_information_provider.get_vehicle_model(vehicle=vehicle_information,
                                                                        additional_mass=additional_mass)

        # Create a path model with the input data
        all_consumptions = []
        # Create the segment start point using the speed and the times
        segment_start_point = calculate_distances(speeds, times)

        slopes = calculate_slopes(heights=heights, speeds=speeds, times=times)

        route = RouteModel(segment_start_point=segment_start_point,
                           slope=slopes, speed_limit_km_h=speeds)

        for vehicle_engine_model in self._vehicle_energy_model_providers:
            vehicle_engine_model.vehicle = vehicle
            vehicle_engine_model.route = route

            # Store the real speed profile, times and slope_t
            vehicle_engine_model.segment_length = segment_start_point
            vehicle_engine_model.speed_m_s = speeds
            vehicle_engine_model.time = times
            vehicle_engine_model.slope_t = slopes

            vehicle_engine_model.perform_speed_profile_processing()

            vehicle_engine_model.perform_power_energy_consumption_calculation()

            performed_route_metrics = vehicle_engine_model.retrieve_estimations()

            # Rename keys
            performed_route_metrics = {'PerformedRouteConsumption': performed_route_metrics['EnergyConsumption'],
                                       'PerformedRouteDistance': performed_route_metrics['Distance'],
                                       'PerformedRouteTime': performed_route_metrics['Time']}

            evaluation = evaluate_consumption(speeds=speeds,
                                              accelerations=vehicle_engine_model.speed_profile.accelerations,
                                              total_length=performed_route_metrics['PerformedRouteDistance'],
                                              times=times)

            all_consumptions.append({**performed_route_metrics, **evaluation})

        return all_consumptions
