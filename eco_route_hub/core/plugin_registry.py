"""
Central plugin registry module.

Stores, categorizes, and provides safe access to instantiated plugin objects.
"""

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    In-memory registry for initialized plugin instances categorized by type and name.

    Internal storage structure:
        _registry = {
            "plugin_type": {
                "plugin_name": plugin_instance,
                ...
            }
        }
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Dict[str, Any]] = {}

    def register(self, plugin_type: str, name: str, instance: Any) -> None:
        """
        Register a plugin instance under a specific plugin type category and name.

        Args:
            plugin_type (str): Plugin type/interface string constant.
            name (str): Unique plugin identifier name.
            instance (Any): Instantiated plugin object.
        """
        if plugin_type not in self._registry:
            self._registry[plugin_type] = {}

        self._registry[plugin_type][name] = instance
        logger.debug(f"Registered plugin '{name}' under category '{plugin_type}'.")

    def get(self, plugin_type: str) -> Any:
        """
        Retrieve a single registered plugin instance for a given plugin type.

        Args:
            plugin_type (str): Target plugin type string constant.

        Returns:
            Any: Registered plugin instance.

        Raises:
            KeyError: If no plugin is registered for the specified type.
            ValueError: If multiple plugins are registered for the type.
        """
        plugins_dict = self._registry.get(plugin_type, {})
        plugins = list(plugins_dict.values())

        if not plugins:
            raise KeyError(f"No plugin registered for type '{plugin_type}'.")

        if len(plugins) > 1:
            raise ValueError(
                f"Multiple plugins registered for '{plugin_type}' "
                f"({list(plugins_dict.keys())}). Use 'get_all()' or 'get_specific_plugins()'."
            )

        return plugins[0]

    def get_all(self, plugin_type: str) -> List[Any]:
        """
        Retrieve all registered plugin instances for a given plugin type.

        Args:
            plugin_type (str): Target plugin type string constant.

        Returns:
            List[Any]: List of all registered plugin instances for the type.
        """
        return list(self._registry.get(plugin_type, {}).values())

    def get_specific_plugins(
        self, plugin_type: str, names: List[str]
    ) -> List[Any]:
        """
        Retrieve plugin instances matching a specific subset of plugin names.

        Args:
            plugin_type (str): Target plugin type string constant.
            names (List[str]): List of plugin names to retrieve.

        Returns:
            List[Any]: List of matching plugin instances.
        """
        plugins_dict = self._registry.get(plugin_type, {})
        target_names: Set[str] = set(names)
        return [
            instance
            for name, instance in plugins_dict.items()
            if name in target_names
        ]

    def has(self, plugin_type: str) -> bool:
        """
        Check if at least one plugin is registered for a given plugin type.

        Args:
            plugin_type (str): Target plugin type string constant.

        Returns:
            bool: True if one or more plugins exist, False otherwise.
        """
        return bool(self._registry.get(plugin_type))

    def get_optional(self, plugin_type: str) -> Optional[Any]:
        """
        Retrieve the first registered plugin instance for a type, or None if none exist.

        Args:
            plugin_type (str): Target plugin type string constant.

        Returns:
            Optional[Any]: Plugin instance if found, otherwise None.
        """
        plugins_dict = self._registry.get(plugin_type, {})
        if not plugins_dict:
            return None
        return next(iter(plugins_dict.values()))

    def list_types(self) -> List[str]:
        """
        List all registered plugin type categories.

        Returns:
            List[str]: List of active plugin type keys.
        """
        return list(self._registry.keys())

    def clear(self) -> None:
        """Clear all registered plugins from the registry."""
        self._registry.clear()

    def __repr__(self) -> str:
        total_plugins = sum(len(p) for p in self._registry.values())
        return (
            f"<PluginRegistry(types={len(self._registry)}, "
            f"total_instances={total_plugins})>"
        )
