import importlib

from route_consumption_estimator.domain.constants import PLUGIN_TYPE_ROAD_INFORMATION, PLUGIN_TYPE_VEHICLE_INFORMATION, \
    PLUGIN_TYPE_ROAD_ROUTING, PLUGIN_TYPE_VEHICLE_ENGINE_MODEL
from route_consumption_estimator.core.plugin_registry import PluginRegistry
from route_consumption_estimator.interfaces import RoadInformationProvider, RoadRoutingServiceProvider, \
    VehicleEngineModelProvider, VehicleInformationProvider

PLUGIN_TYPES = {
    PLUGIN_TYPE_ROAD_INFORMATION: RoadInformationProvider,
    PLUGIN_TYPE_ROAD_ROUTING: RoadRoutingServiceProvider,
    PLUGIN_TYPE_VEHICLE_ENGINE_MODEL: VehicleEngineModelProvider,
    PLUGIN_TYPE_VEHICLE_INFORMATION: VehicleInformationProvider,
}


class PluginManager:

    def __init__(self, config):
        self.config = config
        self.registry = PluginRegistry()

        self.plugin_classes = {}
        self.plugin_configs = {}
        self.instances = {}

    # ---------------------------------
    # LOAD PLUGIN CLASSES
    # ---------------------------------
    def load(self):

        # discover plugin classes
        for plugin_type, plugin_configs in self.config.plugins:

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
            else:
                instance = plugin_class(**deps)

            # store instance
            self.instances[plugin_key] = instance

            # register plugin
            self.registry.register(plugin_type, instance)

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

""" TODO Previous version
    def load(self):
        for plugin_type, plugin_configs in self.config.plugins:

            # ensure list
            if not isinstance(plugin_configs, list):
                plugin_configs = [plugin_configs]

            for cfg in plugin_configs:
                module_path = f"route_consumption_estimator.plugins.{plugin_type}.{cfg.name}"
                module = importlib.import_module(module_path)

                plugin_class = getattr(module, cfg.class_name)
                print(plugin_type)
                print(cfg.config)
                if cfg.config:
                    instance = plugin_class(cfg.config)
                else:
                    instance = plugin_class()

                self.registry.register(plugin_type, instance)
"""