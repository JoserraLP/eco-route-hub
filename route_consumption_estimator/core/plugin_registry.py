class PluginRegistry:

    def __init__(self):
        self._registry = {}

    # ---------------------------------
    # REGISTER PLUGIN
    # ---------------------------------
    def register(self, plugin_type, name, instance):

        if plugin_type not in self._registry:
            self._registry[plugin_type] = {}

        self._registry[plugin_type][name] = instance

    # ---------------------------------
    # GET SINGLE PLUGIN
    # ---------------------------------
    def get(self, plugin_type):

        plugins = self._registry.get(plugin_type).values()

        if not plugins:
            raise KeyError(f"No plugin registered for type '{plugin_type}'")

        if len(plugins) > 1:
            raise ValueError(
                f"Multiple plugins registered for '{plugin_type}', use get_all()"
            )

        return next(iter(plugins))

    # ---------------------------------
    # GET ALL PLUGINS
    # ---------------------------------
    def get_all(self, plugin_type):
        return [v for v in self._registry.get(plugin_type, {}).values()]

    def get_specific_plugins(self, plugin_type, names):
        return [v for k, v in self._registry.get(plugin_type, {}).items() if k in names]

    # ---------------------------------
    # CHECK IF PLUGIN EXISTS
    # ---------------------------------
    def has(self, plugin_type):

        return plugin_type in self._registry and len(self._registry[plugin_type]) > 0

    # ---------------------------------
    # GET FIRST OR NONE
    # ---------------------------------
    def get_optional(self, plugin_type):

        plugins = self._registry.get(plugin_type)

        if not plugins:
            return None

        return plugins[0]

    # ---------------------------------
    # DEBUG / LIST
    # ---------------------------------
    def list_types(self):

        return list(self._registry.keys())
