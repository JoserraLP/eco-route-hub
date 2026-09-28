"""
Data Transfer Objects (DTOs) for application domain boundaries.

Defines decoupled in-memory representations for entities transferred between 
API routes, domain services, and external calculation plugins.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from eco_route_hub.domain.constants import GRAVITY
from eco_route_hub.domain.enums import (
    DrivingBehaviorEnum,
    FeatureTopicEnum,
    MotorTypeEnum,
    RouteTypeEnum,
)


@dataclass
class UserDTO:
    """In-memory representation of user profile data."""
    name: str
    email: str
    password: str
    user_id: Optional[int] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    driving_license_year: Optional[str] = None


@dataclass
class VehicleDTO:
    """In-memory representation of vehicle physical parameters."""
    name: str
    motor_type: MotorTypeEnum
    unladen_veh_mass: float
    p_max_kw: float
    liters_conversion: float
    resistance_factor: float
    A: float
    B: float
    C: float
    vehicle_id: Optional[int] = None
    url: Optional[str] = ""
    image_url: Optional[str] = ""

    def recalculate_vehicle_coefficients(self, additional_mass: float) -> None:
        """Recalculate resistance parameter A with added passenger/payload mass."""
        self.A = float(self.resistance_factor) * (float(self.unladen_veh_mass) + float(additional_mass)) * GRAVITY
        if self.B == 0.0:
            # Empirical estimation for light-duty vehicles (EPA standard conversion):
            # B is typically proportional to vehicle mass (~0.002 to 0.005 N / (m/s) per kg)
            # Or estimated from drivetrain viscous drag:
            self.B = 0.003 * (float(self.unladen_veh_mass) + float(additional_mass) / 1000.0)


@dataclass
class UserVehicleDTO:
    """Association object linking a user to a vehicle profile."""
    user_id: int
    vehicle_id: int
    id: Optional[int] = None
    age: Optional[int] = None
    km_used: Optional[int] = None  # Fixed typo: km_user -> km_used
    is_fav: int = 0


@dataclass
class UserRouteDTO:
    """Telemetry data record for route calculation queries and actual trips."""
    user_id: int
    user_vehicle_id: Optional[int]
    additional_mass: int
    source_coords: str
    destination_coords: str
    selected_route_polyline: str
    selected_route_type: RouteTypeEnum
    selected_route_consumption: float
    selected_route_time: int
    selected_route_distance: int
    performed_route_polyline: str
    performed_route_consumption: float
    performed_route_time: int
    performed_route_distance: int
    performed_route_estimated_consumption: float
    performed_route_estimated_time: int
    performed_route_estimated_distance: int
    id: Optional[int] = None
    record_date: Optional[datetime] = None
    num_stops_km: int = 0
    speed_variation_num: int = 0
    driving_aggressiveness: int = 0
    driving_behavior: Optional[DrivingBehaviorEnum] = None


@dataclass
class UserStatsDTO:
    """Summary metrics of user eco-driving savings."""
    user_id: int
    consumption_saving: float = 0.0
    eco_time: float = 0.0
    eco_distance: float = 0.0
    eco_routes_num: int = 0
    drive_rating: float = 0.0


@dataclass
class AppReviewDTO:
    """Overall user review score and feedback."""
    user_id: int
    global_comments: str
    global_score: float
    app_review_id: Optional[int] = None


@dataclass
class FeatureReviewDTO:
    """Feature-specific evaluation review entry."""
    app_review_id: int
    topic: FeatureTopicEnum
    score: float
    comments: str
    id: Optional[int] = None
