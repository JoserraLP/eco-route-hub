from route_consumption_estimator.domain import *


def user_dto_to_dao(user_dto: UserDTO):
    return UserDAO(
        UserID=user_dto.user_id,
        Name=user_dto.name,
        Email=user_dto.email,
        Password=user_dto.password,
        BirthDate=user_dto.birth_date,
        Gender=user_dto.gender,
        DrivingLicenseYear=user_dto.driving_license_year)


def user_dao_to_dto(user_dao: UserDAO):
    return UserDTO(
        user_id=user_dao.UserID,
        name=user_dao.Name,
        email=user_dao.Email,
        password=user_dao.Password,
        birth_date=user_dao.BirthDate,
        gender=user_dao.Gender,
        driving_license_year=user_dao.DrivingLicenseYear)


def vehicle_dao_to_dto(vehicle_dao: VehicleDAO):
    return VehicleDTO(
        vehicle_id=vehicle_dao.VehicleID,
        name=vehicle_dao.Name,
        motor_type=vehicle_dao.MotorType,
        unladen_veh_mass=vehicle_dao.UnladenVehMass,
        p_max_kw=vehicle_dao.PMaxKw,
        liters_conversion=vehicle_dao.LitersConversion,
        resistance_factor=vehicle_dao.ResistanceFactor,
        A=vehicle_dao.A,
        B=vehicle_dao.B,
        C=vehicle_dao.C,
        url=vehicle_dao.Url,
        image_url=vehicle_dao.ImageUrl,
    )
