import os

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


# ------------------------
# System Configuration
# ------------------------

class SystemConfig(BaseModel):
    delta_s: int = Field(default=1, ge=1)  # Adjust this to the length of the route
    delta_s_max: int = Field(default=50, le=50)  # meters
    delta_s_min_interval_distance: int = Field(default=50000, ge=50000)  # 50km
    delta_s_max_interval_distance: int = Field(default=1000000, le=1000000)  # 1000km
    distance_between_nodes: int = Field(default=50, ge=1)  # meters
    slope_threshold: int = Field(default=12, ge=-12, le=12)  # maximum degrees
    slope_variance_difference: float = Field(default=0.5, ge=0.0, le=1.0)
    batching_window_size: int = Field(default=20, ge=1, le=100)
    polyline_precision: int = Field(default=6, ge=1, le=8)
    smoothing_factor_alpha: float = Field(default=0.3, ge=0.0, le=1.0)
    default_passenger_additional_mass: int = Field(default=70, ge=1)
    api_key: str = Field(default=os.environ.get("API_KEY"))
    vehicle_default_rf: float = Field(default=0.015, ge=0.0)
    vehicle_default_cx: float = Field(default=0.30, ge=0.0)
    vehicle_default_b: float = Field(default=0.0, ge=0.0)
    vehicle_default_gasoline_conversion: float = Field(default=9.2, ge=0.1)
    vehicle_default_diesel_conversion: float = Field(default=10.96, ge=0.1)
    database: dict = Field(default={
        "sqlalchemy_database_uri": "${DATABASE_URI}",
        "sqlalchemy_track_modifications": False})


# ------------------------
# Plugin Configuration
# ------------------------

class SinglePluginConfig(BaseModel):
    name: str
    class_name: str = Field(alias="class")
    config: Dict[str, Any] = Field(default_factory=dict)


class PluginsConfig(BaseModel):
    road_routing_services: Optional[List[SinglePluginConfig]] = None
    road_information: Optional[List[SinglePluginConfig]] = None
    vehicle_information: Optional[List[SinglePluginConfig]] = None
    vehicle_engine_model: Optional[List[SinglePluginConfig]] = None


# ------------------------
# Root App Config
# ------------------------

class AppConfig(BaseModel):
    system: SystemConfig = SystemConfig()
    plugins: PluginsConfig = PluginsConfig()
