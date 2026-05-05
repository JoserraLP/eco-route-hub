class PluginRegistry:

    def __init__(self):
        self._registry = {}

    # ---------------------------------
    # REGISTER PLUGIN
    # ---------------------------------
    def register(self, plugin_type, instance):

        if plugin_type not in self._registry:
            self._registry[plugin_type] = []

        self._registry[plugin_type].append(instance)

    # ---------------------------------
    # GET SINGLE PLUGIN
    # ---------------------------------
    def get(self, plugin_type):

        plugins = self._registry.get(plugin_type)

        if not plugins:
            raise KeyError(f"No plugin registered for type '{plugin_type}'")

        if len(plugins) > 1:
            raise ValueError(
                f"Multiple plugins registered for '{plugin_type}', use get_all()"
            )

        return plugins[0]

    # ---------------------------------
    # GET ALL PLUGINS
    # ---------------------------------
    def get_all(self, plugin_type):

        return self._registry.get(plugin_type, [])

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