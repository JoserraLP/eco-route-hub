"""
Core orchestrator module for route consumption estimation.

Coordinates plugin registries, graph construction, route processors,
speed profile estimation, and vehicle energy model evaluations.
"""

import logging
from typing import Optional, Tuple, Any, Dict, List

from collections import defaultdict

import numpy as np
import pandas as pd
import polyline

from eco_route_hub.core.graph.graph_engine import GraphEngine
from eco_route_hub.core.plugin_registry import PluginRegistry
from eco_route_hub.core.route_processor import RouteProcessor
from eco_route_hub.core.utils import (
    calculate_distances,
    calculate_slopes,
    evaluate_consumption,
    smoothing_process,
    calculate_experiment_info
)
from eco_route_hub.domain.constants import (
    PLUGIN_TYPE_WEATHER_PROVIDER,
    PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER,
    PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER,
    PLUGIN_TYPE_ROAD_ROUTE_PROVIDER,
    PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER,
    PLUGIN_TYPE_SPEED_PROFILE_PROVIDER,
    PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER,
    PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER,
    PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER,
)
from eco_route_hub.domain.graph_models import Coords
from eco_route_hub.domain.route_model import RouteModel
from eco_route_hub.profiling.workflow_profiler import WorkflowProfiler

logger = logging.getLogger(__name__)

DEFAULT_POLYLINE_PRECISION = 5
DEFAULT_ALPHA_SMOOTHING = 0.3


def enrich_simulations_with_telemetry(
        simulation_results: List[Dict[str, Dict[str, Any]]],
        profiler_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Enriches simulation results by route, elevating route information to the route-item

    root and appending model simulation outputs (e.g. 'greta', 'fastsim') along with
    their execution telemetry.
    """
    global_wall_time_ms: float = 0.0
    global_cpu_time_ms: float = 0.0

    route_model_stages: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    model_stages_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # Classify stages into preparation vs model-specific execution per route and model
    for stage in profiler_data.get("stages", []):
        metadata = stage.get("metadata", {})
        model_name = metadata.get("vehicle_engine_model_name") or metadata.get("model")
        route_key = (
                metadata.get("route")
                or metadata.get("route_id")
                or metadata.get("route_index")
        )

        if model_name:
            model_stages_map[model_name].append(stage)
            if route_key is not None:
                route_model_stages[(str(route_key), str(model_name))].append(stage)
        else:
            global_wall_time_ms += stage.get("wall_time_ms", 0.0)
            global_cpu_time_ms += stage.get("cpu_time_ms", 0.0)

    def build_telemetry_dict(stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not stages:
            return {
                "executionWallTimeMs": 0.0,
                "executionCpuTimeMs": 0.0,
                "peakMemoryMb": 0.0,
            }
        exec_wall_ms = sum(s.get("wall_time_ms", 0.0) for s in stages)
        exec_cpu_ms = sum(s.get("cpu_time_ms", 0.0) for s in stages)
        peak_memory_mb = max((s.get("peak_memory_mb", 0.0) for s in stages), default=0.0)

        return {
            "executionWallTimeMs": round(exec_wall_ms, 3),
            "executionCpuTimeMs": round(exec_cpu_ms, 3),
            "peakMemoryMb": round(peak_memory_mb, 4),
        }

    # Fallback accumulated telemetry per model
    model_telemetry_fallback = {
        m: build_telemetry_dict(st) for m, st in model_stages_map.items()
    }

    enriched_simulations: List[Dict[str, Any]] = []

    for route_idx, route_sims in enumerate(simulation_results):
        enriched_route_item: Dict[str, Any] = {}

        # 1. Extract route identifier to root
        route_identifier = None
        for sim_data in route_sims.values():
            if isinstance(sim_data, dict):
                route_identifier = sim_data.get("route") or sim_data.get("route_id")
                if route_identifier:
                    break

        if route_identifier:
            enriched_route_item["route"] = route_identifier

        # 2. Add model with related telemetry
        for model_key, sim_data in route_sims.items():
            sim_copy = sim_data.copy()

            # Remove 'route' from model to avoid duplication
            sim_copy.pop("route", None)

            # Search telemetry related to route and model
            matched_stages = None
            for r_k in (route_identifier, route_idx):
                if r_k is not None and (str(r_k), str(model_key)) in route_model_stages:
                    matched_stages = route_model_stages[(str(r_k), str(model_key))]
                    break

            if matched_stages:
                sim_copy["telemetry"] = build_telemetry_dict(matched_stages)
            else:
                sim_copy["telemetry"] = model_telemetry_fallback.get(
                    model_key,
                    {
                        "executionWallTimeMs": 0.0,
                        "executionCpuTimeMs": 0.0,
                        "peakMemoryMb": 0.0,
                    },
                )

            enriched_route_item[model_key] = sim_copy

        enriched_simulations.append(enriched_route_item)

    return {
        "pipelinePreparationMs": round(global_wall_time_ms, 3),
        "simulations": enriched_simulations,
    }


def read_vehicle_obd_info(file: str):
    """
    Read vehicle OBD telemetry data from a file and calculate cumulative travel distance.

    Args:
        file (str): Path to the whitespace-delimited CSV file containing OBD route data.

    Returns:
        Tuple[List[float], List[float], List[float], List[float], List[float]]: A tuple containing:
            - time_route (List[float]): List of time points.
            - speed_route (List[float]): List of vehicle speed values.
            - height_route (List[float]): List of elevation/height values.
            - consumption_route (List[float]): List of energy/fuel consumption values.
            - acc_space_list (List[float]): List of accumulated distance values.
    """
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
    return time_route.tolist(), speed_route.tolist(), height_route.tolist(), consumption_route.tolist(), acc_space_list


class Core:
    """
    Main orchestration engine for vehicle route energy estimation and benchmarking workflows.

    Attributes:
        registry (PluginRegistry): Loaded plugin registry instance.
        vehicle_id (str): Target vehicle identifier.
        additional_mass (int): Additional vehicle load/payload in kg.
        alpha (Optional[float]): Smoothing factor alpha for exponential moving average.
        models (Optional[List[str]]): List of specific vehicle energy model names to evaluate.
        config (Optional[Dict[str, Any]]): System configuration dictionary overriding Flask context.
    """

    def __init__(
            self,
            registry: PluginRegistry,
            vehicle_id: str,
            additional_mass: int = 0,
            alpha: Optional[float] = None,
            models: Optional[List[str]] = None,
            config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.registry = registry
        self.config = config or {}
        self.vehicle_id = vehicle_id
        self.models = models
        self.additional_mass = additional_mass

        # Resolve system config attributes (dict or Flask context fallback)
        self.polyline_precision = DEFAULT_POLYLINE_PRECISION
        self.all_graph_attributes: Optional[List[str]] = None
        self._extract_config_values(alpha)

        # Retrieve required providers from registry
        self.road_infrastructure_providers = registry.get_all(
            PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER
        )
        self.traffic_operation_providers = registry.get_all(
            PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER
        )
        self.weather_providers = registry.get_all(
            PLUGIN_TYPE_WEATHER_PROVIDER
        )
        self.road_route_providers = registry.get_all(
            PLUGIN_TYPE_ROAD_ROUTE_PROVIDER
        )
        self.driving_behavior_providers = registry.get_all(
            PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER
        )
        self.speed_profile_provider = registry.get(
            PLUGIN_TYPE_SPEED_PROFILE_PROVIDER
        )
        self.route_segmentation_provider = registry.get(
            PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER
        )

        # Retrieve vehicle energy model providers and keep names synchronized
        if not models:
            self.vehicle_energy_model_providers = registry.get_all(
                PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER
            )
            self.specific_vehicle_energy_model_names = [
                getattr(p, "name", type(p).__name__)
                for p in self.vehicle_energy_model_providers
            ]
        else:
            self.vehicle_energy_model_providers = registry.get_specific_plugins(
                PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER, models
            )
            self.specific_vehicle_energy_model_names = models

        self.vehicle_information_provider = registry.get(
            PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER
        )

        # Initialize core components
        self.graph_engine = GraphEngine(
            all_graph_attributes=self.all_graph_attributes,
            config=self.config,
        )
        self.route_processor = RouteProcessor(
            route_segmentation_provider=self.route_segmentation_provider,
            road_infrastructure_providers=self.road_infrastructure_providers,
            road_route_providers=self.road_route_providers,
            traffic_operation_providers=self.traffic_operation_providers,
            weather_providers=self.weather_providers,
        )

        # Instantiate target vehicle model
        vehicle_information = (
            self.vehicle_information_provider.get_vehicle_info_by_id(
                vehicle_id
            )
        )
        self.vehicle_model = (
            self.vehicle_information_provider.get_vehicle_model(
                vehicle=vehicle_information, additional_mass=additional_mass
            )
        )

        self.profiler = WorkflowProfiler(workflow_name="route_simulation_benchmark")

    def _extract_config_values(self, alpha_override: Optional[float]) -> None:
        """
        Extract configuration attributes with fallbacks for CLI or non-Flask execution.

        Args:
            alpha_override (Optional[float]): Custom value to override the default
                alpha parameter setting, if provided.
        """
        sys_config = None
        if "APP_CONFIG" in self.config:
            sys_config = getattr(self.config["APP_CONFIG"], "system", None)

        if sys_config is None:
            try:
                from flask import current_app

                if current_app:
                    app_cfg = current_app.config.get("APP_CONFIG")
                    sys_config = getattr(app_cfg, "system", None) if app_cfg else None
                    self.all_graph_attributes = current_app.config.get(
                        "ALL_ATTRIBUTES"
                    )
            except (ImportError, RuntimeError):
                pass

        if sys_config:
            self.alpha = (
                alpha_override
                if alpha_override is not None
                else getattr(sys_config, "smoothing_factor_alpha", DEFAULT_ALPHA_SMOOTHING)
            )
            self.polyline_precision = getattr(
                sys_config, "polyline_precision", DEFAULT_POLYLINE_PRECISION
            )
        else:
            self.alpha = (
                alpha_override if alpha_override is not None else DEFAULT_ALPHA_SMOOTHING
            )

    def execute_benchmarking_workflow(
            self, coordinates: str
    ) -> List[Dict[str, Any]]:
        """
        Execute energy consumption estimation for all candidate routes across all configured models.

        Args:
            coordinates (str): Semicolon-delimited latitude/longitude waypoint pairs string.

        Returns:
            List[Dict[str, Any]]: Combined list of routes with evaluation metrics and model tags.
        """
        with self.profiler.stage(
                "request_routes",
                provider_type=self.route_processor.__class__.__name__,
                input_coordinates=coordinates,
        ):
            routes = self.route_processor.request_all_routes(coordinates)
            if not routes:
                logger.warning("No routes retrieved for benchmarking workflow.")
                return []

        with self.profiler.stage(
                "graph_processing",
                provider_type=self.graph_engine.__class__.__name__,
                input_coordinates=coordinates,
        ):
            routes_information = self.store_routes_into_graph(routes)

        estimations = self.estimate_consumption_routes(
            routes=routes,
            routes_information=routes_information,
            specific_energy_providers_names=self.specific_vehicle_energy_model_names,
            profiler=self.profiler
        )
        simulation_results = []
        for _ in routes:
            simulation_results.append({item['model']: item for item in estimations})

        return enrich_simulations_with_telemetry(simulation_results=simulation_results,
                                                 profiler_data=self.profiler.to_dict())

    def estimate_consumption_from_file(self, file: str):
        """
        Estimate vehicle energy consumption from an OBD telemetry file across configured models.

        Reads telemetry data, processes speed and elevation profiles, runs simulation models,
        and returns enriched results containing predictions, execution profiling, and actual
        experiment measurements.

        Args:
            file (str): Path to the CSV file containing OBD telemetry route data.

        Returns:
            Dict[str, Any]: Dictionary containing simulation results per model, performance
                profiling telemetry, and experimental measurements (including fuel/energy
                consumption and total route distance).
        """
        with self.profiler.stage(
                "file_reading",
                provider_type=self.__class__.__name__
        ):
            time_route, speed_route, height_route, consumption_route, acc_space_list = read_vehicle_obd_info(file)

        with self.profiler.stage(
                "data_processing",
                provider_type=self.__class__.__name__
        ):
            # From km/h to m/s
            speed_route = [x / 3.6 for x in speed_route]

            all_estimations: List[Dict[str, Any]] = []
            segment_start_point = calculate_distances(speed_route, time_route)
            slopes = calculate_slopes(heights=height_route, speeds=speed_route, times=time_route)
            additional_info = {'slopes': slopes, 'maxspeed': speed_route}
            route = RouteModel(
                segment_start_point=segment_start_point,
                additional_info=additional_info
            )

        for model_idx, vehicle_engine_model in enumerate(
                self.vehicle_energy_model_providers
        ):
            with self.profiler.stage(
                    "vehicle_engine_model.load_route_and_vehicle",
                    provider_type=vehicle_engine_model.__class__.__name__,
                    vehicle_engine_model_name=self.specific_vehicle_energy_model_names[model_idx]
            ):
                vehicle_engine_model.load_route_and_vehicle(
                    route, self.vehicle_model
                )

                vehicle_engine_model.speed_profile.speed_m_s = speed_route
                vehicle_engine_model.speed_profile.time = time_route
                vehicle_engine_model.speed_profile.slope_t = slopes

            with self.profiler.stage(
                    "vehicle_engine_model.perform_speed_profile_estimation",
                    provider_type=vehicle_engine_model.__class__.__name__,
                    vehicle_engine_model_name=self.specific_vehicle_energy_model_names[model_idx]
            ):
                vehicle_engine_model.perform_speed_profile_processing()

            with self.profiler.stage(
                    "vehicle_engine_model.perform_energy_consumption_calculation",
                    provider_type=vehicle_engine_model.__class__.__name__,
                    vehicle_engine_model_name=self.specific_vehicle_energy_model_names[model_idx]
            ):
                vehicle_engine_model.perform_power_energy_consumption_calculation()

            estimations = vehicle_engine_model.retrieve_estimations()

            if (
                    self.specific_vehicle_energy_model_names
                    and model_idx < len(self.specific_vehicle_energy_model_names)
            ):
                estimations["model"] = self.specific_vehicle_energy_model_names[model_idx]

            all_estimations.append(estimations)

        all_simulation_results = enrich_simulations_with_telemetry(
            simulation_results=[{item['model']: item for item in all_estimations}],
            profiler_data=self.profiler.to_dict())

        all_simulation_results['measurements'] = (calculate_experiment_info(time_route, consumption_route)
                                                  | {'distance': segment_start_point[-1]})

        return all_simulation_results

    def execute_route_estimation_workflow(
            self, coordinates: str
    ) -> Dict[str, Any]:
        """
        Execute estimation workflow and extract Eco, Shortest, and Fastest route profiles.

        Args:
            coordinates (str): Semicolon-delimited latitude/longitude waypoint pairs string.

        Returns:
            Dict[str, Any]: Dictionary containing 'eco', 'shortest', and 'fastest' route options.
        """
        routes = self.route_processor.request_all_routes(coordinates)
        if not routes:
            logger.warning("No candidate routes retrieved for estimation workflow.")
            return {}

        routes_information = self.store_routes_into_graph(routes)
        estimations = self.estimate_consumption_routes(routes, routes_information)

        if not estimations:
            return {}

        routes_estimations = [{**r, **e} for r, e in zip(routes, estimations)]
        consumption_idx = min(
            range(len(routes_estimations)),
            key=lambda i: routes_estimations[i].get("EnergyConsumption", float("inf")),
        )
        distance_idx = min(
            range(len(routes_estimations)),
            key=lambda i: routes_estimations[i].get("Distance", float("inf")),
        )
        time_idx = min(
            range(len(routes_estimations)),
            key=lambda i: routes_estimations[i].get("Time", float("inf")),
        )

        return {
            "eco": estimations[consumption_idx],
            "shortest": estimations[distance_idx],
            "fastest": estimations[time_idx],
        }

    def store_routes_into_graph(
            self, routes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Populate the GraphEngine with route data and retrieve micro-segment attributes.

        Args:
            routes (List[Dict[str, Any]]): Raw candidate route dictionaries.

        Returns:
            List[Dict[str, Any]]: Segmented route information extracted from graph engine.
        """
        self.graph_engine.routes = routes
        self.graph_engine.store_routes_graph()
        self.graph_engine.extend_graph_info()

        valid_distances = [
            r["router_distance"]
            for r in routes
            if "router_distance" in r and r["router_distance"] > 0
        ]

        if valid_distances:
            avg_route_distance = float(np.mean(valid_distances))
        elif routes and "distances" in routes[0] and routes[0]["distances"]:
            avg_route_distance = float(routes[0]["distances"][-1])
        else:
            avg_route_distance = 1000.0

        return self.graph_engine.get_routes_information(avg_route_distance)

    def estimate_consumption_routes(
            self,
            routes: List[Dict[str, Any]],
            routes_information: List[Dict[str, Any]],
            specific_energy_providers_names: Optional[List[str]] = None,
            profiler: Optional[WorkflowProfiler] = None
    ) -> List[Dict[str, Any]]:
        """
        Run vehicle energy models over micro-segmented route profiles.

        Args:
            routes (List[Dict[str, Any]]): List of candidate route dictionaries.
            routes_information (List[Dict[str, Any]]): Segmented route metadata from graph engine.
            specific_energy_providers_names (Optional[List[str]]): Model names list to append to output.
            profiler (Optional[WorkflowProfiler]): Metrics profiler

        Returns:
            List[Dict[str, Any]]: List of estimation dictionaries per route and vehicle model.
        """
        specific_energy_providers_names = specific_energy_providers_names if specific_energy_providers_names \
            else self.specific_vehicle_energy_model_names

        all_estimations: List[Dict[str, Any]] = []
        for i, route_info in enumerate(routes_information):
            encoded_route = ""
            if i < len(routes) and "segments_representation" in routes[i]:
                processed_route = [
                    (item.lat, item.lon)
                    for item in routes[i]["segments_representation"]
                ]
                encoded_route = polyline.encode(
                    processed_route, self.polyline_precision
                )

            additional_info = {
                k: v for k, v in route_info.items() if k != "start_points"
            }

            route_model = RouteModel(
                segment_start_point=route_info.get("start_points", []),
                additional_info=additional_info,
            )

            for model_idx, vehicle_engine_model in enumerate(
                    self.vehicle_energy_model_providers
            ):
                with self.profiler.stage(
                        "vehicle_engine_model.load_route_and_vehicle",
                        provider_type=vehicle_engine_model.__class__.__name__,
                        vehicle_engine_model_name=specific_energy_providers_names[model_idx]
                ):
                    vehicle_engine_model.load_route_and_vehicle(
                        route_model, self.vehicle_model
                    )

                with self.profiler.stage(
                        "vehicle_engine_model.perform_speed_profile_estimation",
                        provider_type=vehicle_engine_model.__class__.__name__,
                        vehicle_engine_model_name=specific_energy_providers_names[model_idx]
                ):
                    vehicle_engine_model.perform_speed_profile_estimation()

                with self.profiler.stage(
                        "vehicle_engine_model.perform_energy_consumption_calculation",
                        provider_type=vehicle_engine_model.__class__.__name__,
                        vehicle_engine_model_name=specific_energy_providers_names[model_idx]
                ):
                    vehicle_engine_model.perform_power_energy_consumption_calculation()

                estimations = vehicle_engine_model.retrieve_estimations()
                all_info = {**estimations, "route": rf"{encoded_route}"}

                if (
                        specific_energy_providers_names
                        and model_idx < len(specific_energy_providers_names)
                ):
                    all_info["model"] = specific_energy_providers_names[model_idx]

                all_estimations.append(all_info)

        return all_estimations

    def process_polyline_route(
            self, route_polyline: str
    ) -> List[Dict[str, Any]]:
        """
        Decode a polyline path and process it into graph micro-segments.

        Args:
            route_polyline (str): Encoded polyline path string.

        Returns:
            List[Dict[str, Any]]: Micro-segmented route information.
        """
        decoded_coords = polyline.decode(
            route_polyline, self.polyline_precision
        )
        performed_coords = [Coords(lat=pt[0], lon=pt[1]) for pt in decoded_coords]

        if not performed_coords:
            return []

        processed_performed_route = self.route_processor.process_route(
            route_coordinates=performed_coords,
            common_source=performed_coords[0],
            common_target=performed_coords[-1],
        )
        return self.store_routes_into_graph([processed_performed_route])

    def smooth_sensor_data(
            self, speeds: List[float], heights: List[float]
    ) -> Tuple[List[float], List[float]]:
        """
        Apply EMA smoothing to speed (converted to m/s) and elevation telemetry series.

        Args:
            speeds (List[float]): Raw vehicle speeds in km/h.
            heights (List[float]): Raw elevation points in meters.

        Returns:
            Tuple[List[float], List[float]]: Smoothed speeds (m/s) and smoothed heights (m).
        """
        speeds_m_s = [item / 3.6 for item in speeds]
        smoothed_speeds = smoothing_process(speeds_m_s, alpha=self.alpha)
        smoothed_heights = smoothing_process(heights, alpha=self.alpha)

        return smoothed_speeds, smoothed_heights

    def execute_route_real_consumption_workflow(
            self,
            vehicle_id: str,
            additional_mass: int,
            heights: List[float],
            speeds: List[float],
            times: List[float],
    ) -> List[Dict[str, Any]]:
        """
        Evaluate energy consumption against real recorded OBD sensor telemetry.

        Args:
            vehicle_id (str): Target vehicle identifier.
            additional_mass (int): Added payload mass in kg.
            heights (List[float]): Recorded elevation series in meters.
            speeds (List[float]): Recorded speed profile in m/s.
            times (List[float]): Recorded timestamp intervals in seconds.

        Returns:
            List[Dict[str, Any]]: Combined physical consumption metrics and eco-driving scores.
        """
        vehicle_information = (
            self.vehicle_information_provider.get_vehicle_info_by_id(
                vehicle_id
            )
        )
        vehicle = self.vehicle_information_provider.get_vehicle_model(
            vehicle=vehicle_information, additional_mass=additional_mass
        )

        all_consumptions: List[Dict[str, Any]] = []

        segment_start_point = calculate_distances(speeds, times)
        slopes = calculate_slopes(heights=heights, speeds=speeds, times=times)

        additional_info = {'slopes': slopes, 'speeds': speeds}

        route = RouteModel(
            segment_start_point=segment_start_point,
            additional_info=additional_info
        )

        for vehicle_engine_model in self.vehicle_energy_model_providers:
            vehicle_engine_model.vehicle = vehicle
            vehicle_engine_model.route = route

            vehicle_engine_model.segment_length = segment_start_point
            vehicle_engine_model.speed_m_s = speeds
            vehicle_engine_model.time = times
            vehicle_engine_model.slope_t = slopes

            vehicle_engine_model.perform_speed_profile_processing()
            vehicle_engine_model.perform_power_energy_consumption_calculation()

            performed_route_metrics = vehicle_engine_model.retrieve_estimations()

            metrics_summary = {
                "PerformedRouteConsumption": performed_route_metrics.get(
                    "EnergyConsumption", 0.0
                ),
                "PerformedRouteDistance": performed_route_metrics.get(
                    "Distance", 0.0
                ),
                "PerformedRouteTime": performed_route_metrics.get("Time", 0.0),
            }

            accelerations = getattr(
                getattr(vehicle_engine_model, "speed_profile", None),
                "accelerations",
                [],
            )

            evaluation = evaluate_consumption(
                speeds=speeds,
                accelerations=accelerations,
                total_length=metrics_summary["PerformedRouteDistance"],
                times=times,
            )

            all_consumptions.append({**metrics_summary, **evaluation})

        return all_consumptions
