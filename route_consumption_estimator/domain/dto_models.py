from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from route_consumption_estimator.domain.constants import GRAVITY


@dataclass
class UserDTO:
    user_id: int
    name: str
    email: str
    password: str
    birth_date: str
    gender: str
    driving_license_year: str


class MotorTypeEnumDTO(Enum):
    ELECTRIC = 1
    DIESEL = 2
    GASOLINE = 3
    HYBRID = 4


@dataclass
class VehicleDTO:
    vehicle_id: int
    name: str
    motor_type: MotorTypeEnumDTO
    unladen_veh_mass: float
    p_max_kw: float
    liters_conversion: float
    resistance_factor: float
    A: float
    B: float
    C: float
    url: str
    image_url: str

    def recalculate_a(self, additional_mass: int):
        self.A = float(self.resistance_factor) * (float(self.unladen_veh_mass) + additional_mass) * GRAVITY


@dataclass
class UserVehicleDTO:
    id: int
    user_id: int
    vehicle_id: int
    age: int
    km_user: int
    is_fav: int


class RouteTypeEnumDTO(Enum):
    FASTEST: 1
    SHORTEST: 2
    ECO: 3


@dataclass
class UserRouteDTO:
    id: int
    user_id: int
    user_vehicle_id: int
    additional_mass: int
    source_coords: str
    destination_coords: str
    record_date: datetime
    selected_route_polyline: str
    selected_route_type: RouteTypeEnumDTO
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
    num_stops_km: int
    speed_variation_num: int
    driving_aggressiveness: int


@dataclass
class UserStatsDTO:
    user_id: int
    consumption_saving: float
    eco_time: float
    eco_distance: float
    eco_routes_num: int
    drive_rating: float


@dataclass
class AppReviewDTO:
    app_review_id: int
    user_id: int
    global_comments: str
    global_score: float


class FeatureTopicEnumDTO(Enum):
    ACCESABILITY: 1
    RESPONSETIME: 2
    CONFIGURABILITY: 3
    USABILITY: 4
    TRUSTABILITY: 5
    ROBUSTNESS: 6
    UTILITY: 7


@dataclass
class FeatureReviewDTO:
    id: int
    app_review_id: int
    topic: FeatureTopicEnumDTO
    score: float
    comments: str
