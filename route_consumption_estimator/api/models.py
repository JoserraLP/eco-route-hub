from route_consumption_estimator import db, ma
from route_consumption_estimator.api.constants import DEFAULT_VEHICLE_RF, GRAVITY


# Define your models and schemas here
class User(db.Model):
    __tableName__ = 'user'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(50), nullable=False)
    Password = db.Column(db.String(50), nullable=False)
    BirthDate = db.Column(db.DateTime)
    Gender = db.Column(db.String(20))
    DrivingLicenseDate = db.Column(db.DateTime)

    def __init__(self, Name, Email, Password, BirthDate, Gender, DrivingLicenseDate):
        self.Name = Name
        self.Email = Email
        self.Password = Password
        self.BirthDate = BirthDate
        self.Gender = Gender
        self.DrivingLicenseDate = DrivingLicenseDate

    def __repr__(self):
        return f'<User {self.UserID} {self.Name} {self.Email}>'


# Define the User schema
class UserSchema(ma.Schema):
    class Meta:
        fields = ('UserID', 'Name', 'Email', 'Password', 'BirthDate', 'Gender', 'DrivingLicenseDate')


class Vehicle(db.Model):
    __tableName__ = 'vehicle'
    VehicleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    MotorType = db.Column(db.Enum('ELECTRIC', 'DIESEL', 'GASOLINE', 'HYBRID'), nullable=False)
    UnladenVehMass = db.Column(db.Integer, nullable=False)
    PMaxKw = db.Column(db.Integer, nullable=False)
    AvgConsumption = db.Column(db.Numeric(10, 1), nullable=False)
    ResistanceFactor = db.Column(db.Numeric(6, 4), nullable=False)
    A = db.Column(db.Numeric(10, 3), nullable=False)
    B = db.Column(db.Numeric(10, 3), nullable=False)
    C = db.Column(db.Numeric(10, 3), nullable=False)
    Url = db.Column(db.String(500))
    ImageUrl = db.Column(db.String(500))

    def __init__(self, Name, MotorType, UnladenVehMass, PMaxKw, AvgConsumption, ResistanceFactor,
                 A, B, C, Url, ImageUrl):
        self.Name = Name
        self.MotorType = MotorType
        self.UnladenVehMass = UnladenVehMass
        self.PMaxKw = PMaxKw
        self.AvgConsumption = AvgConsumption
        self.ResistanceFactor = ResistanceFactor
        self.A = A
        self.B = B
        self.C = C
        self.Url = Url
        self.ImageUrl = ImageUrl

    def __repr__(self):
        return f'<Vehicle {self.VehicleID} {self.Name} {self.MotorType}>'

    def recalculate_a(self, AdditionalMass: int):
        self.A = float(self.ResistanceFactor)*(float(self.UnladenVehMass) + AdditionalMass)*GRAVITY


# Define the Vehicle schema
class VehicleSchema(ma.Schema):
    class Meta:
        fields = ('VehicleID', 'Name', 'MotorType', 'UnladenVehMass', 'PMaxKw', 'AvgConsumption', 'ResistanceFactor',
                  'A', 'B', 'C', 'Url', 'ImageUrl')


class UserVehicle(db.Model):
    __tableName__ = 'user_vehicle'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID'), nullable=False)
    VehicleID = db.Column(db.Integer, db.ForeignKey('vehicle.VehicleID'), nullable=False)
    Age = db.Column(db.Integer)
    KmUsed = db.Column(db.Integer)
    IsFav = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', backref='vehicles')
    vehicle = db.relationship('Vehicle', backref='users')

    def __repr__(self):
        return f'<UserVehicle {self.ID} {self.UserID} {self.VehicleID}>'

    def __init__(self, UserID, VehicleID, Age, KmUsed, IsFav):
        self.UserID = UserID
        self.VehicleID = VehicleID
        self.Age = Age
        self.KmUsed = KmUsed
        self.IsFav = IsFav


class UserVehicleSchema(ma.Schema):
    class Meta:
        fields = ('ID', 'UserID', 'VehicleID', 'Age', 'KmUsed', 'IsFav')


class UserRoute(db.Model):
    __tableName__ = 'user_route'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'))
    UserVehicleID = db.Column(db.Integer, db.ForeignKey('user_vehicle.ID', ondelete='CASCADE'))
    AdditionalMass = db.Column(db.Integer, nullable=False)
    RoutePolyline = db.Column(db.String(1000), nullable=False)
    RouteType = db.Column(db.Enum('FASTEST', 'SHORTEST', 'ECO'), nullable=False)
    EstimatedConsumption = db.Column(db.Numeric(6, 2), nullable=False)
    EstimatedTimeSeconds = db.Column(db.Integer, nullable=False)
    EstimatedDistanceMeters = db.Column(db.Integer, nullable=False)
    RecordDate = db.Column(db.TIMESTAMP, nullable=False)
    ActualConsumption = db.Column(db.Numeric(6, 2), nullable=False)
    ActualTimeSeconds = db.Column(db.Integer, nullable=False)
    ActualDistanceMeters = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', backref='route')

    def __repr__(self):
        return f'<UserRoute {self.ID} {self.UserID} {self.RouteType}>'

    def __init__(self, UserID, UserVehicleID, AdditionalMass, RoutePolyline, RouteType, EstimatedConsumption,
                 EstimatedTimeSeconds, EstimatedDistanceMeters, RecordDate, ActualConsumption, ActualTimeSeconds,
                 ActualDistanceMeters):
        self.UserID = UserID
        self.UserVehicleID = UserVehicleID
        self.AdditionalMass = AdditionalMass
        self.RoutePolyline = RoutePolyline
        self.RouteType = RouteType
        self.EstimatedConsumption = EstimatedConsumption
        self.EstimatedTimeSeconds = EstimatedTimeSeconds
        self.EstimatedDistanceMeters = EstimatedDistanceMeters
        self.RecordDate = RecordDate
        self.ActualConsumption = ActualConsumption
        self.ActualTimeSeconds = ActualTimeSeconds
        self.ActualDistanceMeters = ActualDistanceMeters


class UserRouteSchema(ma.Schema):
    class Meta:
        fields = ('ID', 'UserID', 'UserVehicleID', 'AdditionalMass', 'RoutePolyline', 'RouteType',
                  'EstimatedConsumption', 'EstimatedTimeSeconds', 'EstimatedDistanceMeters', 'RecordDate',
                  'ActualConsumption', 'ActualTimeSeconds', 'ActualDistanceMeters')


class UserStats(db.Model):
    __tableName__ = 'user_stats'
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'), primary_key=True)
    ConsumptionSaving = db.Column(db.Numeric(10, 2), nullable=False)
    EcoTime = db.Column(db.Numeric(10, 2), nullable=False)
    EcoDistance = db.Column(db.Numeric(10, 2), nullable=False)
    EcoRoutesNum = db.Column(db.Integer, nullable=False)
    DriveRating = db.Column(db.Numeric(3, 2), nullable=False)
    CarbonFootprint = db.Column(db.Numeric(5, 2), nullable=False)
    user = db.relationship('User', backref='stats', uselist=False)

    def __repr__(self):
        return f'<UserStats {self.UserID} {self.ConsumptionSaving} {self.EcoTime}>'

    def __init__(self, UserID, ConsumptionSaving, EcoTime, EcoDistance, EcoRoutesNum, DriveRating,
                 CarbonFootprint):
        self.UserID = UserID
        self.ConsumptionSaving = ConsumptionSaving
        self.EcoTime = EcoTime
        self.EcoDistance = EcoDistance
        self.EcoRoutesNum = EcoRoutesNum
        self.DriveRating = DriveRating
        self.CarbonFootprint = CarbonFootprint


class UserStatsSchema(ma.Schema):
    class Meta:
        fields = ('UserID', 'ConsumptionSaving', 'EcoTime', 'EcoDistance', 'EcoRoutesNum', 'DriveRating',
                  'CarbonFootprint')


class AppReview(db.Model):
    __tableName__ = 'app_review'
    AppReviewID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'))
    GlobalComments = db.Column(db.String(200), nullable=False)
    GlobalScore = db.Column(db.Numeric(3, 2), nullable=False)
    user = db.relationship('User', backref='reviews')
    features = db.relationship('FeatureReview', backref='app_review')

    def __repr__(self):
        return f'<AppReview {self.AppReviewID} {self.UserID} {self.GlobalScore}>'

    def __init__(self, UserID, GlobalComments, GlobalScore):
        self.UserID = UserID
        self.GlobalComments = GlobalComments
        self.GlobalScore = GlobalScore


class AppReviewSchema(ma.Schema):
    class Meta:
        fields = ('AppReviewID', 'UserID', 'GlobalComments', 'GlobalScore')


class FeatureReview(db.Model):
    __tableName__ = 'feature_review'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AppReviewID = db.Column(db.Integer, db.ForeignKey('app_review.AppReviewID', ondelete='CASCADE'), nullable=False)
    Topic = db.Column(
        db.Enum('ACCESABILITY', 'RESPONSETIME', 'CONFIGURABILITY', 'USABILITY', 'TRUSTABILITY', 'ROBUSTNESS',
                'UTILITY'), nullable=False)
    Score = db.Column(db.Numeric(3, 2), nullable=False)
    Comments = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<FeatureReview {self.ID} {self.AppReviewID} {self.Topic} {self.Score}>'

    def __init__(self, AppReviewID, Topic, Score, Comments):
        self.AppReviewID = AppReviewID
        self.Topic = Topic
        self.Score = Score
        self.Comments = Comments


class FeatureReviewSchema(ma.Schema):
    class Meta:
        fields = ('ID', 'AppReviewID', 'Topic', 'Score', 'Comments')
