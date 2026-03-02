import numpy as np
import polyline

from route_consumption_estimator.core.constants import SMOOTHING_FACTOR_ALPHA, OSRM_QUERY_PARAMS, \
    GRAPHHOPPER_QUERY_PARAMS, OPENROUTESERVICE_QUERY_PARAMS, DEFAULT_POLYLINE_PRECISION
from route_consumption_estimator.core.graph.graph_engine import GraphEngine
from route_consumption_estimator.core.graph.models import Coords
from route_consumption_estimator.core.route.route_model import RouteModel
from route_consumption_estimator.core.route.route_processor import RouteProcessor
from route_consumption_estimator.core.utils import calculate_distances, calculate_slopes, smoothing_process, \
    evaluate_consumption
from route_consumption_estimator.road_routing_services.graphhopper import GraphHopper
from route_consumption_estimator.road_routing_services.ors import OpenRouteService
from route_consumption_estimator.road_routing_services.osrm import OSRM
from route_consumption_estimator.vehicle_engine_model.greta_engine_model.greta_engine_model import GretaEngineModel
from route_consumption_estimator.vehicle_information.vehicle_information_database import VehicleInformationDatabase


class Core:

    def __init__(self, vehicle_id: str, additional_mass: int = 0, alpha=SMOOTHING_FACTOR_ALPHA):

        self._road_routing_services = [
            OSRM(params=OSRM_QUERY_PARAMS),
            GraphHopper(params=GRAPHHOPPER_QUERY_PARAMS),
            OpenRouteService(params=OPENROUTESERVICE_QUERY_PARAMS)
        ]

        self._vehicle_information_models = [
            VehicleInformationDatabase()
        ]

        self._vehicle_engine_models = [
            GretaEngineModel()
        ]

        self._graph_engine = GraphEngine()

        self._route_processor = RouteProcessor()

        self._alpha = alpha

        # Get vehicle information and core model
        vehicle_information = self._vehicle_information_models[0].get_vehicle_info_by_id(vehicle_id)

        self._vehicle_model = self._vehicle_information_models[0].get_vehicle_model(vehicle=vehicle_information,
                                                                                    additional_mass=additional_mass)

    def request_all_routes(self, coordinates_str: str):
        route_coordinates = [Coords(lat=float(coordinates.split(',')[0]), lon=float(coordinates.split(',')[1]))
                             for coordinates in coordinates_str.split(';')]

        routes = []

        for service in self._road_routing_services:
            service_routes = service.get_routes(route_coordinates)
            routes += service_routes

        print(f"Total possible routes {len(routes)}")

        return routes

    def process_route_information(self, routes: list):
        # Store the routes information into graph
        self._graph_engine.routes = routes

        self._graph_engine.store_routes_graph()

        self._graph_engine.extend_graph_info()

        # router_distance
        avg_route_distance = np.mean([route['router_distance'] for route in routes if 'router_distance' in route])

        if avg_route_distance == 0:
            avg_route_distance = routes[0]['distances'][-1]

        # Get the routes information (by micro segments)
        return self._graph_engine.get_routes_information(avg_route_distance)

    # CONSUMPTION ESTIMATION
    def estimate_consumption_routes(self, routes: list, routes_information: list):
        all_estimations = []
        # Create a route class with each route
        for i, route_information in enumerate(routes_information):
            # Process route to encode it
            encoded_route = ''
            if 'segments_representation' in routes[i]:
                processed_route = [(item.lat, item.lon) for item in routes[i]['segments_representation']]

                encoded_route = polyline.encode(processed_route, DEFAULT_POLYLINE_PRECISION)

            route = RouteModel(segment_start_point=route_information['start_points'],
                               speed_limit_km_h=route_information['max_speeds'],
                               slope=route_information['slopes'])

            for vehicle_engine_model in self._vehicle_engine_models:
                # Set current route and vehicle information
                vehicle_engine_model.route = route
                vehicle_engine_model.vehicle = self._vehicle_model

                vehicle_engine_model.perform_speed_profile_estimation()

                vehicle_engine_model.perform_power_energy_consumption_calculation()

                all_estimations.append(vehicle_engine_model.retrieve_estimations() | {'Route': fr"{encoded_route}"})

        return all_estimations

    def execute_route_estimation_workflow(self, coordinates_str: str):
        # Request routes
        routes = self.request_all_routes(coordinates_str)
        if routes:
            # Process routes information
            routes_information = self.process_route_information(routes)

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

    # REAL CONSUMPTION CALCULATION
    def process_polyline_route(self, route_polyline: str):
        performed_route_coords = polyline.decode(route_polyline, DEFAULT_POLYLINE_PRECISION)

        # Parse polyline into list of coords
        performed_route_coords = [Coords(lat=item[0], lon=item[1]) for item in performed_route_coords]

        processed_performed_route = self._route_processor.process_route(route_coordinates=performed_route_coords,
                                                                        common_source=performed_route_coords[0],
                                                                        common_target=performed_route_coords[-1])
        routes_information = self.process_route_information([processed_performed_route])

        return routes_information

    def smooth_sensor_data(self, speeds: list, heights: list):
        speeds = smoothing_process([item / 3.6 for item in speeds], alpha=self._alpha)

        heights = smoothing_process(heights, alpha=self._alpha)

        return speeds, heights

    def execute_route_real_consumption_workflow(self, vehicle_id: str, additional_mass: int, heights: list,
                                                speeds: list, times: list):
        # Get vehicle information and core model
        vehicle_information = self._vehicle_information_models[0].get_vehicle_info_by_id(vehicle_id)

        vehicle = self._vehicle_information_models[0].get_vehicle_model(vehicle=vehicle_information,
                                                                        additional_mass=additional_mass)

        # Create a path model with the input data
        all_consumptions = []
        # Create the segment start point using the speed and the times
        segment_start_point = calculate_distances(speeds, times)

        slopes = calculate_slopes(heights=heights, speeds=speeds, times=times)

        route = RouteModel(segment_start_point=segment_start_point,
                           slope=slopes, speed_limit_km_h=speeds)

        for vehicle_engine_model in self._vehicle_engine_models:
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
