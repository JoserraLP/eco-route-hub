import importlib

from route_consumption_estimator.core.plugin_registry import PluginRegistry
from route_consumption_estimator.domain.constants import PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER, \
    PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER, PLUGIN_TYPE_AMBIENT_WEATHER_PROVIDER, PLUGIN_TYPE_ROAD_ROUTE_PROVIDER, \
    PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER, PLUGIN_TYPE_SPEED_PROFILE_PROVIDER, PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER, \
    PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER, PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER
from route_consumption_estimator.interfaces import RoadInfrastructureInformationProvider, RoadRouteProvider, \
    VehicleEnergyModelProvider, VehicleInformationProvider, SpeedProfileProvider, AmbientWeatherInformationProvider, \
    TrafficOperationInformationProvider, DrivingBehaviorProvider, RouteSegmentationProvider

PLUGIN_TYPES = {
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

    def __init__(self, config):
        self.config = config
        self.registry = PluginRegistry()

        self.plugin_classes = {}
        self.plugin_configs = {}
        self.instances = {}
        self.all_attributes = ['slopes', 'distances']

    # ---------------------------------
    # LOAD PLUGIN CLASSES
    # ---------------------------------
    def load(self):

        # discover plugin classes
        for plugin_type, plugin_configs in self.config.plugins:

            if plugin_configs:
                if not isinstance(plugin_configs, list):
                    plugin_configs = [plugin_configs]

                for cfg in plugin_configs:
                    module_path = f"route_consumption_estimator.plugins.{plugin_type}.{cfg.name}"
                    module = importlib.import_module(module_path)

                    plugin_class = getattr(module, cfg.class_name)

                    plugin_key = f"{plugin_type}:{cfg.name}"

                    self.plugin_classes[plugin_key] = plugin_class
                    self.plugin_configs[plugin_key] = (plugin_type, cfg)

        # 2️⃣ resolve dependencies
        ordered_plugins = self._resolve_dependencies()

        # instantiate plugins
        for plugin_key in ordered_plugins:

            plugin_class = self.plugin_classes[plugin_key]
            plugin_type, cfg = self.plugin_configs[plugin_key]

            deps = {}

            for dep in getattr(plugin_class, "requires", []):
                deps[dep] = self.registry.get(dep)

            # instantiate plugin
            if cfg.config:
                instance = plugin_class(**deps, config=cfg.config)
                if 'road_attributes' in cfg.config:
                    self.all_attributes.extend([x for x in cfg.config['road_attributes']])

                if 'weather_ambient_attributes' in cfg.config:
                    self.all_attributes.extend([x for x in cfg.config['weather_ambient_attributes']])

                if 'traffic_operation_attributes' in cfg.config:
                    self.all_attributes.extend([x for x in cfg.config['traffic_operation_attributes']])
            else:
                instance = plugin_class(**deps)

            # store instance
            self.instances[plugin_key] = instance

            # register plugin
            self.registry.register(plugin_type, cfg.name, instance)

    # ---------------------------------
    # DEPENDENCY RESOLUTION
    # ---------------------------------
    def _resolve_dependencies(self):

        visited = set()
        stack = []

        def visit(plugin_key):

            if plugin_key in visited:
                return

            visited.add(plugin_key)

            plugin_class = self.plugin_classes[plugin_key]
            for dep in getattr(plugin_class, "requires", []):

                dep_key = self._find_plugin_key(dep)

                if dep_key is None:
                    raise Exception(f"Dependency {dep} not found")

                visit(dep_key)

            stack.append(plugin_key)

        for plugin_key in self.plugin_classes:
            visit(plugin_key)

        return stack

    # ---------------------------------
    # FIND PLUGIN BY TYPE
    # ---------------------------------
    def _find_plugin_key(self, plugin_type):

        for key in self.plugin_classes:
            if key.startswith(plugin_type + ":"):
                return key

        return None
