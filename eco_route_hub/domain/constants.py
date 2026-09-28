"""
Domain-level physical constants and plugin type identifiers.

Defines physical values used across energy estimation algorithms and 
string literal constants representing supported domain plugin provider types.
"""

from typing import Final

# -------------------------------------------------------------------------
# Physical Constants
# -------------------------------------------------------------------------

GRAVITY: Final[float] = 9.81
"""Standard acceleration due to gravity in m/s²."""

EARTH_RADIUS: Final[int] = 6371000
"""Earth's mean radius in meters (used in Haversine/geospatial calculations)."""


# -------------------------------------------------------------------------
# Plugin Type Identifiers
# -------------------------------------------------------------------------

PLUGIN_TYPE_ROAD_INFRASTRUCTURE_PROVIDER: Final[str] = "road_infrastructure_provider"
PLUGIN_TYPE_TRAFFIC_OPERATION_PROVIDER: Final[str] = "traffic_operation_provider"
PLUGIN_TYPE_AMBIENT_WEATHER_PROVIDER: Final[str] = "ambient_weather_provider"
PLUGIN_TYPE_ROAD_ROUTE_PROVIDER: Final[str] = "road_route_provider"
PLUGIN_TYPE_DRIVING_BEHAVIOR_PROVIDER: Final[str] = "driving_behavior_provider"
PLUGIN_TYPE_SPEED_PROFILE_PROVIDER: Final[str] = "speed_profile_provider"
PLUGIN_TYPE_ROUTE_SEGMENTATION_PROVIDER: Final[str] = "route_segmentation_provider"
PLUGIN_TYPE_VEHICLE_ENERGY_MODEL_PROVIDER: Final[str] = "vehicle_energy_model_provider"
PLUGIN_TYPE_VEHICLE_INFORMATION_PROVIDER: Final[str] = "vehicle_information_provider"