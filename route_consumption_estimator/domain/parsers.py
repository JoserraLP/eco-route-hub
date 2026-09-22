"""
Domain Object Mappers / Parsers.

Provides bidirectional transformation functions between SQLAlchemy database 
models (DAOs) and domain Data Transfer Objects (DTOs).
"""

from route_consumption_estimator.domain.dao_models import (
    AppReviewDAO,
    FeatureReviewDAO,
    UserDAO,
    UserRouteDAO,
    UserStatsDAO,
    UserVehicleDAO,
    VehicleDAO,
)
from route_consumption_estimator.domain.dto_models import (
    AppReviewDTO,
    FeatureReviewDTO,
    UserDTO,
    UserRouteDTO,
    UserStatsDTO,
    UserVehicleDTO,
    VehicleDTO,
)
from route_consumption_estimator.domain.enums import (
    FeatureTopicEnum,
    MotorTypeEnum,
    RouteTypeEnum,
)


# -------------------------------------------------------------------------
# User Mappers
# -------------------------------------------------------------------------

def user_dto_to_dao(user_dto: UserDTO) -> UserDAO:
    """Convert UserDTO to UserDAO ORM entity."""
    return UserDAO(
        UserID=user_dto.user_id,
        Name=user_dto.name,
        Email=user_dto.email,
        Password=user_dto.password,
        BirthDate=user_dto.birth_date,
        Gender=user_dto.gender,
        DrivingLicenseYear=user_dto.driving_license_year,
    )


def user_dao_to_dto(user_dao: UserDAO) -> UserDTO:
    """Convert UserDAO ORM entity to UserDTO."""
    return UserDTO(
        user_id=user_dao.UserID,
        name=user_dao.Name,
        email=user_dao.Email,
        password=user_dao.Password,
        birth_date=str(user_dao.BirthDate) if user_dao.BirthDate else None,
        gender=user_dao.Gender,
        driving_license_year=user_dao.DrivingLicenseYear,
    )


# -------------------------------------------------------------------------
# Vehicle Mappers
# -------------------------------------------------------------------------

def vehicle_dto_to_dao(vehicle_dto: VehicleDTO) -> VehicleDAO:
    """Convert VehicleDTO to VehicleDAO ORM entity."""
    return VehicleDAO(
        VehicleID=vehicle_dto.vehicle_id,
        Name=vehicle_dto.name,
        MotorType=vehicle_dto.motor_type.value if isinstance(vehicle_dto.motor_type, MotorTypeEnum) else vehicle_dto.motor_type,
        UnladenVehMass=vehicle_dto.unladen_veh_mass,
        PMaxKw=vehicle_dto.p_max_kw,
        LitersConversion=vehicle_dto.liters_conversion,
        ResistanceFactor=vehicle_dto.resistance_factor,
        A=vehicle_dto.A,
        B=vehicle_dto.B,
        C=vehicle_dto.C,
        Url=vehicle_dto.url,
        ImageUrl=vehicle_dto.image_url,
    )


def vehicle_dao_to_dto(vehicle_dao: VehicleDAO) -> VehicleDTO:
    """Convert VehicleDAO ORM entity to VehicleDTO."""
    return VehicleDTO(
        vehicle_id=vehicle_dao.VehicleID,
        name=vehicle_dao.Name,
        motor_type=MotorTypeEnum(vehicle_dao.MotorType) if isinstance(vehicle_dao.MotorType, str) else vehicle_dao.MotorType,
        unladen_veh_mass=float(vehicle_dao.UnladenVehMass),
        p_max_kw=float(vehicle_dao.PMaxKw),
        liters_conversion=float(vehicle_dao.LitersConversion),
        resistance_factor=float(vehicle_dao.ResistanceFactor),
        A=float(vehicle_dao.A),
        B=float(vehicle_dao.B),
        C=float(vehicle_dao.C),
        url=vehicle_dao.Url or "",
        image_url=vehicle_dao.ImageUrl or "",
    )


# -------------------------------------------------------------------------
# User-Vehicle Mappers
# -------------------------------------------------------------------------

def user_vehicle_dto_to_dao(uv_dto: UserVehicleDTO) -> UserVehicleDAO:
    """Convert UserVehicleDTO to UserVehicleDAO ORM entity."""
    return UserVehicleDAO(
        ID=uv_dto.id,
        UserID=uv_dto.user_id,
        VehicleID=uv_dto.vehicle_id,
        Age=uv_dto.age,
        KmUsed=uv_dto.km_used,
        IsFav=uv_dto.is_fav,
    )


def user_vehicle_dao_to_dto(uv_dao: UserVehicleDAO) -> UserVehicleDTO:
    """Convert UserVehicleDAO ORM entity to UserVehicleDTO."""
    return UserVehicleDTO(
        id=uv_dao.ID,
        user_id=uv_dao.UserID,
        vehicle_id=uv_dao.VehicleID,
        age=uv_dao.Age,
        km_used=uv_dao.KmUsed,
        is_fav=uv_dao.IsFav,
    )


# -------------------------------------------------------------------------
# User Route Mappers
# -------------------------------------------------------------------------

def user_route_dto_to_dao(route_dto: UserRouteDTO) -> UserRouteDAO:
    """Convert UserRouteDTO to UserRouteDAO ORM entity."""
    return UserRouteDAO(
        ID=route_dto.id,
        UserID=route_dto.user_id,
        UserVehicleID=route_dto.user_vehicle_id,
        AdditionalMass=route_dto.additional_mass,
        SourceCoords=route_dto.source_coords,
        DestinationCoords=route_dto.destination_coords,
        RecordDate=route_dto.record_date,
        SelectedRoutePolyline=route_dto.selected_route_polyline,
        SelectedRouteType=route_dto.selected_route_type.value if isinstance(route_dto.selected_route_type, RouteTypeEnum) else route_dto.selected_route_type,
        SelectedRouteConsumption=route_dto.selected_route_consumption,
        SelectedRouteTime=route_dto.selected_route_time,
        SelectedRouteDistance=route_dto.selected_route_distance,
        PerformedRoutePolyline=route_dto.performed_route_polyline,
        PerformedRouteConsumption=route_dto.performed_route_consumption,
        PerformedRouteTime=route_dto.performed_route_time,
        PerformedRouteDistance=route_dto.performed_route_distance,
        PerformedRouteEstimatedConsumption=route_dto.performed_route_estimated_consumption,
        PerformedRouteEstimatedTime=route_dto.performed_route_estimated_time,
        PerformedRouteEstimatedDistance=route_dto.performed_route_estimated_distance,
        NumStopsKm=route_dto.num_stops_km,
        SpeedVariationNum=route_dto.speed_variation_num,
        DrivingAggressiveness=route_dto.driving_aggressiveness,
    )


def user_route_dao_to_dto(route_dao: UserRouteDAO) -> UserRouteDTO:
    """Convert UserRouteDAO ORM entity to UserRouteDTO."""
    return UserRouteDTO(
        id=route_dao.ID,
        user_id=route_dao.UserID,
        user_vehicle_id=route_dao.UserVehicleID,
        additional_mass=route_dao.AdditionalMass,
        source_coords=route_dao.SourceCoords,
        destination_coords=route_dao.DestinationCoords,
        record_date=route_dao.RecordDate,
        selected_route_polyline=route_dao.SelectedRoutePolyline,
        selected_route_type=RouteTypeEnum(route_dao.SelectedRouteType) if isinstance(route_dao.SelectedRouteType, str) else route_dao.SelectedRouteType,
        selected_route_consumption=float(route_dao.SelectedRouteConsumption),
        selected_route_time=route_dao.SelectedRouteTime,
        selected_route_distance=route_dao.SelectedRouteDistance,
        performed_route_polyline=route_dao.PerformedRoutePolyline,
        performed_route_consumption=float(route_dao.PerformedRouteConsumption),
        performed_route_time=route_dao.PerformedRouteTime,
        performed_route_distance=route_dao.PerformedRouteDistance,
        performed_route_estimated_consumption=float(route_dao.PerformedRouteEstimatedConsumption),
        performed_route_estimated_time=route_dao.PerformedRouteEstimatedTime,
        performed_route_estimated_distance=route_dao.PerformedRouteEstimatedDistance,
        num_stops_km=route_dao.NumStopsKm,
        speed_variation_num=route_dao.SpeedVariationNum,
        driving_aggressiveness=route_dao.DrivingAggressiveness,
    )


# -------------------------------------------------------------------------
# User Stats Mappers
# -------------------------------------------------------------------------

def user_stats_dto_to_dao(stats_dto: UserStatsDTO) -> UserStatsDAO:
    """Convert UserStatsDTO to UserStatsDAO ORM entity."""
    return UserStatsDAO(
        UserID=stats_dto.user_id,
        ConsumptionSaving=stats_dto.consumption_saving,
        EcoTime=stats_dto.eco_time,
        EcoDistance=stats_dto.eco_distance,
        EcoRoutesNum=stats_dto.eco_routes_num,
        DriveRating=stats_dto.drive_rating,
    )


def user_stats_dao_to_dto(stats_dao: UserStatsDAO) -> UserStatsDTO:
    """Convert UserStatsDAO ORM entity to UserStatsDTO."""
    return UserStatsDTO(
        user_id=stats_dao.UserID,
        consumption_saving=float(stats_dao.ConsumptionSaving),
        eco_time=float(stats_dao.EcoTime),
        eco_distance=float(stats_dao.EcoDistance),
        eco_routes_num=stats_dao.EcoRoutesNum,
        drive_rating=float(stats_dao.DriveRating),
    )


# -------------------------------------------------------------------------
# Review Mappers
# -------------------------------------------------------------------------

def app_review_dto_to_dao(review_dto: AppReviewDTO) -> AppReviewDAO:
    """Convert AppReviewDTO to AppReviewDAO ORM entity."""
    return AppReviewDAO(
        AppReviewID=review_dto.app_review_id,
        UserID=review_dto.user_id,
        GlobalComments=review_dto.global_comments,
        GlobalScore=review_dto.global_score,
    )


def app_review_dao_to_dto(review_dao: AppReviewDAO) -> AppReviewDTO:
    """Convert AppReviewDAO ORM entity to AppReviewDTO."""
    return AppReviewDTO(
        app_review_id=review_dao.AppReviewID,
        user_id=review_dao.UserID,
        global_comments=review_dao.GlobalComments,
        global_score=float(review_dao.GlobalScore),
    )


def feature_review_dto_to_dao(feature_dto: FeatureReviewDTO) -> FeatureReviewDAO:
    """Convert FeatureReviewDTO to FeatureReviewDAO ORM entity."""
    return FeatureReviewDAO(
        ID=feature_dto.id,
        AppReviewID=feature_dto.app_review_id,
        Topic=feature_dto.topic.value if isinstance(feature_dto.topic, FeatureTopicEnum) else feature_dto.topic,
        Score=feature_dto.score,
        Comments=feature_dto.comments,
    )


def feature_review_dao_to_dto(feature_dao: FeatureReviewDAO) -> FeatureReviewDTO:
    """Convert FeatureReviewDAO ORM entity to FeatureReviewDTO."""
    return FeatureReviewDTO(
        id=feature_dao.ID,
        app_review_id=feature_dao.AppReviewID,
        topic=FeatureTopicEnum(feature_dao.Topic) if isinstance(feature_dao.Topic, str) else feature_dao.Topic,
        score=float(feature_dao.Score),
        comments=feature_dao.Comments,
    )
