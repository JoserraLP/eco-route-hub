"""
Dynamic Plugin Manager for Route Consumption Estimator.

Handles dynamic module discovery, class loading, dependency resolution (DAG/Topological Sort),
instantiation, and registration into the PluginRegistry.
"""

import importlib
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from route_consumption_estimator.core.plugin_registry import PluginRegistry
from route_consumption_estimator.domain.constants import (
    PLUGIN_TYPE_AMBIENT_WEATHER_PROVIDER,
    PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER,
    PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER,
    PLUGIN_TYPE_ROAD_ROUTE_PROVIDER,
    PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER,
    PLUGIN_TYPE_SPEED_PROFILE_PROVIDER,
    PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER,
    PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER,
    PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER,
)
from route_consumption_estimator.interfaces import (
    AmbientWeatherInformationProvider,
    DrivingBehaviorProvider,
    RoadInfrastructureInformationProvider,
    RoadRouteProvider,
    RouteSegmentationProvider,
    SpeedProfileProvider,
    TrafficOperationInformationProvider,
    VehicleEnergyModelProvider,
    VehicleInformationProvider,
)

logger = logging.getLogger(__name__)

PLUGIN_TYPES: Dict[str, Type[Any]] = {
    PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER: TrafficOperationInformationProvider,
    PLUGIN_TYPE_AMBIENT_WEATHER_PROVIDER: AmbientWeatherInformationProvider,
    PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER: DrivingBehaviorProvider,
    PLUGIN_TYPE_SPEED_PROFILE_PROVIDER: SpeedProfileProvider,
    PLUGIN_TYPE_ROAD_ROUTE_PROVIDER: RoadRouteProvider,
    PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER: RoadInfrastructureInformationProvider,
    PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER: RouteSegmentationProvider,
    PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER: VehicleInformationProvider,
    PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER: VehicleEnergyModelProvider,
}


class PluginManager:
    """
    Manages the lifecycle of plugins including discovery, dependency resolution, and instantiation.

    Attributes:
        config (Any): Application or system configuration containing plugin specifications.
        registry (PluginRegistry): Registry instance where loaded plugins are registered.
        plugin_classes (Dict[str, Type[Any]]): Map of plugin keys to loaded python classes.
        plugin_configs (Dict[str, Tuple[str, Any]]): Map of plugin keys to (plugin_type, config) tuples.
        instances (Dict[str, Any]): Map of plugin keys to instantiated plugin objects.
        all_attributes (List[str]): Accumulated list of micro-segment graph attributes required by plugins.
    """

    def __init__(self, config: Any) -> None:
        self.config = config
        self.registry: PluginRegistry = PluginRegistry()

        self.plugin_classes: Dict[str, Type[Any]] = {}
        self.plugin_configs: Dict[str, Tuple[str, Any]] = {}
        self.instances: Dict[str, Any] = {}
        self.all_attributes: List[str] = ["slopes", "maxspeed", "distances"]

    def load(self) -> None:
        """
        Discover, resolve dependencies for, instantiate, and register all configured plugins.

        Raises:
            ImportError: If a plugin module cannot be imported.
            AttributeError: If the target plugin class is not found within the module.
            ValueError: If missing dependencies or circular dependencies are detected.
        """
        plugins_iterable = getattr(self.config, "plugins", [])

        # Step 1: Discover and load plugin classes
        for plugin_type, plugin_configs in plugins_iterable:
            if not plugin_configs:
                continue

            configs_list = (
                plugin_configs
                if isinstance(plugin_configs, list)
                else [plugin_configs]
            )

            for cfg in configs_list:
                if isinstance(cfg, dict):
                    continue
                plugin_name = getattr(cfg, "name", "")
                class_name = getattr(cfg, "class_name", "")
                module_path = (
                    f"route_consumption_estimator.plugins.{plugin_type}.{cfg.name}"
                )

                try:
                    logger.debug(f"Importing plugin module: {module_path}")
                    module = importlib.import_module(module_path)
                    plugin_class = getattr(module, class_name)
                except (ImportError, AttributeError) as err:
                    logger.error(
                        f"Failed to load plugin '{class_name}' from '{module_path}': {err}"
                    )
                    raise

                # Optional interface validation
                expected_interface = PLUGIN_TYPES.get(plugin_type)
                if expected_interface and not issubclass(
                    plugin_class, expected_interface
                ):
                    logger.warning(
                        f"Plugin '{class_name}' does not explicitly inherit from "
                        f"{expected_interface.__name__}."
                    )

                plugin_key = f"{plugin_type}:{plugin_name}"
                self.plugin_classes[plugin_key] = plugin_class
                self.plugin_configs[plugin_key] = (plugin_type, cfg)

        # Step 2: Resolve execution/instantiation order via DAG resolution
        ordered_plugins = self._resolve_dependencies()

        # Step 3: Instantiate plugins in topological order
        for plugin_key in ordered_plugins:
            plugin_class = self.plugin_classes[plugin_key]
            plugin_type, cfg = self.plugin_configs[plugin_key]

            # Inject required dependencies from registry
            deps: Dict[str, Any] = {}
            for dep in getattr(plugin_class, "requires", []):
                dep_instance = self.registry.get(dep)
                if dep_instance is None:
                    raise ValueError(
                        f"Unresolved dependency '{dep}' for plugin class '{plugin_class.__name__}'"
                    )
                deps[dep] = dep_instance

            # Instantiate with optional config mapping
            cfg_dict = getattr(cfg, "config", None)
            if cfg_dict and isinstance(cfg_dict, dict):
                instance = plugin_class(**deps, config=cfg_dict)
                self._accumulate_graph_attributes(cfg_dict)
            else:
                instance = plugin_class(**deps)

            self.instances[plugin_key] = instance
            self.registry.register(plugin_type, cfg.name, instance)
            logger.info(
                f"Successfully registered plugin: '{cfg.name}' [{plugin_type}]"
            )

    def _accumulate_graph_attributes(self, config_dict: Dict[str, Any]) -> None:
        """Safely extend and deduplicate required graph attributes from plugin configs."""
        attribute_keys = [
            "road_attributes",
            "weather_ambient_attributes",
            "traffic_operation_attributes",
        ]
        for key in attribute_keys:
            if key in config_dict and isinstance(config_dict[key], (list, tuple)):
                for attr in config_dict[key]:
                    if attr not in self.all_attributes:
                        self.all_attributes.append(str(attr))

    def _resolve_dependencies(self) -> List[str]:
        """
        Perform topological sorting on configured plugins to resolve dependencies.

        Returns:
            List[str]: Ordered list of plugin keys safe for sequential instantiation.

        Raises:
            ValueError: If a required dependency is missing or if a cycle is detected.
        """
        visited: Set[str] = set()
        visiting: Set[str] = set()
        stack: List[str] = []

        def visit(plugin_key: str) -> None:
            if plugin_key in visiting:
                raise ValueError(
                    f"Circular dependency detected involving plugin: '{plugin_key}'"
                )

            if plugin_key not in visited:
                visiting.add(plugin_key)
                plugin_class = self.plugin_classes[plugin_key]

                for dep in getattr(plugin_class, "requires", []):
                    dep_key = self._find_plugin_key(dep)
                    if dep_key is None:
                        raise ValueError(
                            f"Dependency provider '{dep}' required by '{plugin_key}' was not configured or found."
                        )
                    visit(dep_key)

                visiting.remove(plugin_key)
                visited.add(plugin_key)
                stack.append(plugin_key)

        for key in list(self.plugin_classes.keys()):
            if key not in visited:
                visit(key)

        return stack

    def _find_plugin_key(self, plugin_type: str) -> Optional[str]:
        """
        Find the first matching registered plugin key for a given plugin type interface.

        Args:
            plugin_type (str): Target plugin type string constant.

        Returns:
            Optional[str]: Matching plugin key or None if not registered.
        """
        prefix = f"{plugin_type}:"
        for key in self.plugin_classes:
            if key.startswith(prefix):
                return key
        return None
