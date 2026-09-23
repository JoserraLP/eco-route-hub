"""
Data Access Object (DAO) database models and Marshmallow serialization schemas.

Defines the SQLAlchemy ORM entities for users, vehicles, user-vehicle associations, 
historical route executions, user statistics, and application reviews.
"""

from datetime import datetime, timezone
from typing import Optional
from route_consumption_estimator import db, ma
from route_consumption_estimator.domain.enums import MotorTypeEnum, RouteTypeEnum, FeatureTopicEnum
from route_consumption_estimator.domain.constants import GRAVITY


# -------------------------------------------------------------------------
# User Entities
# -------------------------------------------------------------------------

class UserDAO(db.Model):
    """User account entity representing a registered platform user."""

    __tablename__ = 'user'

    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(50), nullable=False, unique=True)
    Password = db.Column(db.String(255), nullable=False)
    BirthDate = db.Column(db.DateTime, nullable=True)
    Gender = db.Column(db.String(20), nullable=True)
    DrivingLicenseYear = db.Column(db.String(10), nullable=True)

    def __init__(
        self,
        Name: str,
        Email: str,
        Password: str,
        BirthDate: Optional[datetime] = None,
        Gender: Optional[str] = None,
        DrivingLicenseYear: Optional[str] = None,
        UserID: Optional[int] = None,
    ) -> None:
        if UserID is not None:
            self.UserID = UserID
        self.Name = Name
        self.Email = Email
        self.Password = Password
        self.BirthDate = BirthDate
        self.Gender = Gender
        self.DrivingLicenseYear = str(DrivingLicenseYear) if DrivingLicenseYear is not None else None

    def __repr__(self) -> str:
        return f'<User {self.UserID} {self.Name} {self.Email}>'


class UserDAOSchema(ma.Schema):
    """Serialization schema for UserDAO entity."""

    class Meta:
        fields = ('UserID', 'Name', 'Email', 'Password', 'BirthDate', 'Gender', 'DrivingLicenseYear')


# -------------------------------------------------------------------------
# Vehicle Entities
# -------------------------------------------------------------------------

class VehicleDAO(db.Model):
    """Vehicle specification entity for energy model calculations."""

    __tablename__ = 'vehicle'

    VehicleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    MotorType = db.Column(db.Enum(MotorTypeEnum), nullable=False)
    UnladenVehMass = db.Column(db.Numeric(12, 5), nullable=False)
    PMaxKw = db.Column(db.Numeric(15, 5), nullable=False)
    LitersConversion = db.Column(db.Numeric(10, 4), nullable=False)
    ResistanceFactor = db.Column(db.Numeric(20, 10), nullable=False)
    A = db.Column(db.Numeric(20, 10), nullable=False)
    B = db.Column(db.Numeric(20, 10), nullable=False)
    C = db.Column(db.Numeric(20, 10), nullable=False)
    Url = db.Column(db.String(500), nullable=True)
    ImageUrl = db.Column(db.String(500), nullable=True)

    def __init__(
        self,
        Name: str,
        MotorType: str,
        UnladenVehMass: float,
        PMaxKw: float,
        LitersConversion: float,
        ResistanceFactor: float,
        A: float,
        B: float,
        C: float,
        Url: Optional[str] = '',
        ImageUrl: Optional[str] = '',
        VehicleID: Optional[int] = None,
    ) -> None:
        if VehicleID is not None:
            self.VehicleID = VehicleID
        self.Name = Name
        self.MotorType = MotorType
        self.UnladenVehMass = UnladenVehMass
        self.PMaxKw = PMaxKw
        self.LitersConversion = LitersConversion
        self.ResistanceFactor = ResistanceFactor
        self.A = A
        self.B = B
        self.C = C
        self.Url = Url or ''
        self.ImageUrl = ImageUrl or ''

    def __repr__(self) -> str:
        return f'<Vehicle {self.VehicleID} {self.Name} {self.MotorType}>'

    def recalculate_vehicle_coefficients(self, additional_mass: float) -> None:
        """Recalculate resistance parameter A considering passenger and load mass."""
        self.A = float(self.ResistanceFactor) * (float(self.UnladenVehMass) + float(additional_mass)) * GRAVITY
        if self.B == 0.0:
            # Empirical estimation for light-duty vehicles (EPA standard conversion):
            # B is typically proportional to vehicle mass (~0.002 to 0.005 N / (m/s) per kg)
            # Or estimated from drivetrain viscous drag:
            self.B = 0.003 * (float(self.unladen_veh_mass) + float(additional_mass) / 1000)


class VehicleDAOSchema(ma.Schema):
    """Serialization schema for VehicleDAO entity."""

    class Meta:
        fields = (
            'VehicleID', 'Name', 'MotorType', 'UnladenVehMass', 'PMaxKw',
            'LitersConversion', 'ResistanceFactor', 'A', 'B', 'C', 'Url', 'ImageUrl'
        )


# -------------------------------------------------------------------------
# User-Vehicle Association
# -------------------------------------------------------------------------

class UserVehicleDAO(db.Model):
    """Junction entity mapping users to owned or favorite vehicles."""

    __tablename__ = 'user_vehicle'

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'), nullable=False)
    VehicleID = db.Column(db.Integer, db.ForeignKey('vehicle.VehicleID', ondelete='CASCADE'), nullable=False)
    Age = db.Column(db.Integer, nullable=True)
    KmUsed = db.Column(db.Integer, nullable=True)
    IsFav = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship('UserDAO', backref=db.backref('user_vehicles', cascade='all, delete-orphan'))
    vehicle = db.relationship('VehicleDAO', backref=db.backref('vehicle_users', cascade='all, delete-orphan'))

    def __init__(
        self,
        UserID: int,
        VehicleID: int,
        Age: Optional[int] = None,
        KmUsed: Optional[int] = None,
        IsFav: int = 0,
        ID: Optional[int] = None,
    ) -> None:
        if ID is not None:
            self.ID = ID
        self.UserID = UserID
        self.VehicleID = VehicleID
        self.Age = Age
        self.KmUsed = KmUsed
        self.IsFav = IsFav

    def __repr__(self) -> str:
        return f'<UserVehicle {self.ID} User:{self.UserID} Vehicle:{self.VehicleID}>'


class UserVehicleDAOSchema(ma.Schema):
    """Serialization schema for UserVehicleDAO entity."""

    class Meta:
        fields = ('ID', 'UserID', 'VehicleID', 'Age', 'KmUsed', 'IsFav')


# -------------------------------------------------------------------------
# Route Execution & Historical Records
# -------------------------------------------------------------------------

class UserRouteDAO(db.Model):
    """Record of route planning queries and actual performed route consumption telemetry."""

    __tablename__ = 'user_route'

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'), nullable=False)
    UserVehicleID = db.Column(db.Integer, db.ForeignKey('user_vehicle.ID', ondelete='SET NULL'), nullable=True)
    AdditionalMass = db.Column(db.Integer, nullable=False, default=0)
    SourceCoords = db.Column(db.String(200), nullable=False)
    DestinationCoords = db.Column(db.String(200), nullable=False)
    RecordDate = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    SelectedRoutePolyline = db.Column(db.Text, nullable=False)
    SelectedRouteType = db.Column(db.Enum(RouteTypeEnum), nullable=False)
    SelectedRouteConsumption = db.Column(db.Numeric(10, 3), nullable=False)
    SelectedRouteTime = db.Column(db.Integer, nullable=False)
    SelectedRouteDistance = db.Column(db.Integer, nullable=False)
    PerformedRoutePolyline = db.Column(db.Text, nullable=False)
    PerformedRouteConsumption = db.Column(db.Numeric(10, 3), nullable=False)
    PerformedRouteTime = db.Column(db.Integer, nullable=False)
    PerformedRouteDistance = db.Column(db.Integer, nullable=False)
    PerformedRouteEstimatedConsumption = db.Column(db.Numeric(10, 3), nullable=False)
    PerformedRouteEstimatedTime = db.Column(db.Integer, nullable=False)
    PerformedRouteEstimatedDistance = db.Column(db.Integer, nullable=False)
    NumStopsKm = db.Column(db.Integer, nullable=False, default=0)
    SpeedVariationNum = db.Column(db.Integer, nullable=False, default=0)
    DrivingAggressiveness = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship('UserDAO', backref=db.backref('routes', cascade='all, delete-orphan'))

    def __init__(
        self,
        UserID: int,
        UserVehicleID: Optional[int],
        AdditionalMass: int,
        SourceCoords: str,
        DestinationCoords: str,
        SelectedRoutePolyline: str,
        SelectedRouteType: str,
        SelectedRouteConsumption: float,
        SelectedRouteTime: int,
        SelectedRouteDistance: int,
        PerformedRoutePolyline: str,
        PerformedRouteConsumption: float,
        PerformedRouteTime: int,
        PerformedRouteDistance: int,
        PerformedRouteEstimatedConsumption: float,
        PerformedRouteEstimatedTime: int,
        PerformedRouteEstimatedDistance: int,
        NumStopsKm: int = 0,
        SpeedVariationNum: int = 0,
        DrivingAggressiveness: int = 0,
        RecordDate: Optional[datetime] = None,
        ID: Optional[int] = None,
    ) -> None:
        if ID is not None:
            self.ID = ID
        self.UserID = UserID
        self.UserVehicleID = UserVehicleID
        self.AdditionalMass = AdditionalMass
        self.SourceCoords = SourceCoords
        self.DestinationCoords = DestinationCoords
        self.RecordDate = RecordDate or datetime.now(timezone.utc)
        self.SelectedRoutePolyline = SelectedRoutePolyline
        self.SelectedRouteType = SelectedRouteType
        self.SelectedRouteConsumption = SelectedRouteConsumption
        self.SelectedRouteTime = SelectedRouteTime
        self.SelectedRouteDistance = SelectedRouteDistance
        self.PerformedRoutePolyline = PerformedRoutePolyline
        self.PerformedRouteConsumption = PerformedRouteConsumption
        self.PerformedRouteTime = PerformedRouteTime
        self.PerformedRouteDistance = PerformedRouteDistance
        self.PerformedRouteEstimatedConsumption = PerformedRouteEstimatedConsumption
        self.PerformedRouteEstimatedTime = PerformedRouteEstimatedTime
        self.PerformedRouteEstimatedDistance = PerformedRouteEstimatedDistance
        self.NumStopsKm = NumStopsKm
        self.SpeedVariationNum = SpeedVariationNum
        self.DrivingAggressiveness = DrivingAggressiveness

    def __repr__(self) -> str:
        return f'<UserRoute {self.ID} User:{self.UserID} Type:{self.SelectedRouteType}>'


class UserRouteDAOSchema(ma.Schema):
    """Serialization schema for UserRouteDAO entity."""

    class Meta:
        fields = (
            'ID', 'UserID', 'UserVehicleID', 'AdditionalMass', 'SourceCoords', 'DestinationCoords',
            'RecordDate', 'SelectedRoutePolyline', 'SelectedRouteType', 'SelectedRouteConsumption',
            'SelectedRouteTime', 'SelectedRouteDistance', 'PerformedRoutePolyline',
            'PerformedRouteConsumption', 'PerformedRouteTime', 'PerformedRouteDistance',
            'PerformedRouteEstimatedConsumption', 'PerformedRouteEstimatedTime',
            'PerformedRouteEstimatedDistance', 'NumStopsKm', 'SpeedVariationNum', 'DrivingAggressiveness'
        )


# -------------------------------------------------------------------------
# User Statistics & Ratings
# -------------------------------------------------------------------------

class UserStatsDAO(db.Model):
    """Aggregated eco-driving efficiency metrics for a user."""

    __tablename__ = 'user_stats'

    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'), primary_key=True)
    ConsumptionSaving = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    EcoTime = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    EcoDistance = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    EcoRoutesNum = db.Column(db.Integer, nullable=False, default=0)
    DriveRating = db.Column(db.Numeric(3, 2), nullable=False, default=0.0)

    user = db.relationship('UserDAO', backref=db.backref('stats', uselist=False, cascade='all, delete-orphan'))

    def __init__(
        self,
        UserID: int,
        ConsumptionSaving: float = 0.0,
        EcoTime: float = 0.0,
        EcoDistance: float = 0.0,
        EcoRoutesNum: int = 0,
        DriveRating: float = 0.0,
    ) -> None:
        self.UserID = UserID
        self.ConsumptionSaving = ConsumptionSaving
        self.EcoTime = EcoTime
        self.EcoDistance = EcoDistance
        self.EcoRoutesNum = EcoRoutesNum
        self.DriveRating = DriveRating

    def __repr__(self) -> str:
        return f'<UserStats User:{self.UserID} Saving:{self.ConsumptionSaving} EcoTime:{self.EcoTime}>'


class UserStatsDAOSchema(ma.Schema):
    """Serialization schema for UserStatsDAO entity."""

    class Meta:
        fields = ('UserID', 'ConsumptionSaving', 'EcoTime', 'EcoDistance', 'EcoRoutesNum', 'DriveRating')


# -------------------------------------------------------------------------
# User Feedback & Reviews
# -------------------------------------------------------------------------

class AppReviewDAO(db.Model):
    """Global feedback review submitted by a user."""

    __tablename__ = 'app_review'

    AppReviewID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'), nullable=False)
    GlobalComments = db.Column(db.String(2000), nullable=False)
    GlobalScore = db.Column(db.Numeric(3, 2), nullable=False)

    user = db.relationship('UserDAO', backref=db.backref('reviews', cascade='all, delete-orphan'))

    def __init__(
        self,
        UserID: int,
        GlobalComments: str,
        GlobalScore: float,
        AppReviewID: Optional[int] = None,
    ) -> None:
        if AppReviewID is not None:
            self.AppReviewID = AppReviewID
        self.UserID = UserID
        self.GlobalComments = GlobalComments
        self.GlobalScore = GlobalScore

    def __repr__(self) -> str:
        return f'<AppReview {self.AppReviewID} User:{self.UserID} Score:{self.GlobalScore}>'


class AppReviewDAOSchema(ma.Schema):
    """Serialization schema for AppReviewDAO entity."""

    class Meta:
        fields = ('AppReviewID', 'UserID', 'GlobalComments', 'GlobalScore')


class FeatureReviewDAO(db.Model):
    """Specific feature aspect rating associated with an overall app review."""

    __tablename__ = 'feature_review'

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AppReviewID = db.Column(db.Integer, db.ForeignKey('app_review.AppReviewID', ondelete='CASCADE'), nullable=False)
    Topic = db.Column(db.Enum(FeatureTopicEnum), nullable=False)
    Score = db.Column(db.Numeric(3, 2), nullable=False)
    Comments = db.Column(db.String(2000), nullable=False)

    app_review = db.relationship('AppReviewDAO', backref=db.backref('features', cascade='all, delete-orphan'))

    def __init__(
        self,
        AppReviewID: int,
        Topic: str,
        Score: float,
        Comments: str,
        ID: Optional[int] = None,
    ) -> None:
        if ID is not None:
            self.ID = ID
        self.AppReviewID = AppReviewID
        self.Topic = Topic
        self.Score = Score
        self.Comments = Comments

    def __repr__(self) -> str:
        return f'<FeatureReview {self.ID} AppReview:{self.AppReviewID} Topic:{self.Topic}>'


class FeatureReviewDAOSchema(ma.Schema):
    """Serialization schema for FeatureReviewDAO entity."""

    class Meta:
        fields = ('ID', 'AppReviewID', 'Topic', 'Score', 'Comments')
