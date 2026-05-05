
from route_consumption_estimator import db, ma
from route_consumption_estimator.domain.constants import GRAVITY

# Define your models and schemas here
class UserDAO(db.Model):
    __tablename__ = 'user'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(50), nullable=False)
    Password = db.Column(db.String(50), nullable=False)
    BirthDate = db.Column(db.DateTime)
    Gender = db.Column(db.String(20))
    DrivingLicenseYear = db.Column(db.String(10))

    def __init__(self, Name, Email, Password, BirthDate, Gender, DrivingLicenseYear, UserID=None):
        if UserID:
            self.UserID = UserID
        self.Name = Name
        self.Email = Email
        self.Password = Password
        self.BirthDate = BirthDate
        self.Gender = Gender
        self.DrivingLicenseYear = DrivingLicenseYear

    def __repr__(self):
        return f'<User {self.UserID} {self.Name} {self.Email}>'



# Define the User schema
class UserDAOSchema(ma.Schema):
    class Meta:
        fields = ('UserID', 'Name', 'Email', 'Password', 'BirthDate', 'Gender', 'DrivingLicenseYear')


class VehicleDAO(db.Model):
    __tablename__ = 'vehicle'
    VehicleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    MotorType = db.Column(db.Enum('ELECTRIC', 'DIESEL', 'GASOLINE', 'HYBRID'), nullable=False)
    UnladenVehMass = db.Column(db.Numeric(12, 5), nullable=False)
    PMaxKw = db.Column(db.Numeric(15, 5), nullable=False)
    LitersConversion = db.Column(db.Numeric(10, 4), nullable=False)
    ResistanceFactor = db.Column(db.Numeric(20, 10), nullable=False)
    A = db.Column(db.Numeric(20, 10), nullable=False)
    B = db.Column(db.Numeric(20, 10), nullable=False)
    C = db.Column(db.Numeric(20, 10), nullable=False)
    Url = db.Column(db.String(500))
    ImageUrl = db.Column(db.String(500))

    def __init__(self, Name, MotorType, UnladenVehMass, PMaxKw, LitersConversion, ResistanceFactor, A, B, C, Url,
                 ImageUrl, VehicleId):
        if VehicleId:
            self.VehicleID = VehicleId
        self.Name = Name
        self.MotorType = MotorType
        self.UnladenVehMass = UnladenVehMass
        self.PMaxKw = PMaxKw
        self.LitersConversion = LitersConversion
        self.ResistanceFactor = ResistanceFactor
        self.A = A
        self.B = B
        self.C = C
        self.Url = Url
        self.ImageUrl = ImageUrl

    def __repr__(self):
        return f'<Vehicle {self.VehicleID} {self.Name} {self.MotorType}>'

    def recalculate_a(self, AdditionalMass: int):
        self.A = float(self.ResistanceFactor) * (float(self.UnladenVehMass) + AdditionalMass) * GRAVITY


# Define the Vehicle schema
class VehicleDAOSchema(ma.Schema):
    class Meta:
        fields = ('VehicleID', 'Name', 'MotorType', 'UnladenVehMass', 'PMaxKw', 'LitersConversion', 'ResistanceFactor',
                  'A', 'B', 'C', 'Url', 'ImageUrl')


class UserVehicleDAO(db.Model):
    __tablename__ = 'user_vehicle'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID'), nullable=False)
    VehicleID = db.Column(db.Integer, db.ForeignKey('vehicle.VehicleID'), nullable=False)
    Age = db.Column(db.Integer)
    KmUsed = db.Column(db.Integer)
    IsFav = db.Column(db.Integer, nullable=False)
    user = db.relationship('UserDAO', backref='vehicles')
    vehicle = db.relationship('VehicleDAO', backref='users')

    def __repr__(self):
        return f'<UserVehicle {self.ID} {self.UserID} {self.VehicleID}>'

    def __init__(self, UserID, VehicleID, Age, KmUsed, IsFav):
        self.UserID = UserID
        self.VehicleID = VehicleID
        self.Age = Age
        self.KmUsed = KmUsed
        self.IsFav = IsFav


class UserVehicleDAOSchema(ma.Schema):
    class Meta:
        fields = ('ID', 'UserID', 'VehicleID', 'Age', 'KmUsed', 'IsFav')


class UserRouteDAO(db.Model):
    __tablename__ = 'user_route'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'))
    UserVehicleID = db.Column(db.Integer, db.ForeignKey('user_vehicle.ID', ondelete='CASCADE'))
    AdditionalMass = db.Column(db.Integer, nullable=False)
    SourceCoords = db.Column(db.String(200), nullable=False)
    DestinationCoords = db.Column(db.String(200), nullable=False)
    RecordDate = db.Column(db.DateTime, nullable=False)
    SelectedRoutePolyline = db.Column(db.Text, nullable=False)
    SelectedRouteType = db.Column(db.Enum('FASTEST', 'SHORTEST', 'ECO'), nullable=False)
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
    NumStopsKm = db.Column(db.Integer, nullable=False)
    SpeedVariationNum = db.Column(db.Integer, nullable=False)
    DrivingAggressiveness = db.Column(db.Integer, nullable=False)
    user = db.relationship('UserDAO', backref='route')

    def __repr__(self):
        return f'<UserRoute {self.ID} {self.UserID} {self.SelectedRouteType}>'

    def __init__(self, UserID, UserVehicleID, AdditionalMass, SourceCoords, DestinationCoords, SelectedRoutePolyline,
                 SelectedRouteType, SelectedRouteConsumption, SelectedRouteTime, SelectedRouteDistance,
                 PerformedRoutePolyline, PerformedRouteConsumption, PerformedRouteTime, PerformedRouteDistance,
                 PerformedRouteEstimatedConsumption, PerformedRouteEstimatedTime, PerformedRouteEstimatedDistance,
                 NumStopsKm, SpeedVariationNum, DrivingAggressiveness, RecordDate=None):
        self.UserID = UserID
        self.UserVehicleID = UserVehicleID
        self.AdditionalMass = AdditionalMass
        self.SourceCoords = SourceCoords
        self.DestinationCoords = DestinationCoords
        self.RecordDate = RecordDate
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


class UserRouteDAOSchema(ma.Schema):
    class Meta:
        fields = ('ID', 'UserID', 'UserVehicleID', 'AdditionalMass', 'SourceCoords', 'DestinationCoords', 'RecordDate',
                  'SelectedRoutePolyline',
                  'SelectedRouteType', 'SelectedRouteConsumption', 'SelectedRouteTime', 'SelectedRouteDistance',
                  'PerformedRoutePolyline', 'PerformedRouteConsumption', 'PerformedRouteTime', 'PerformedRouteDistance',
                  'PerformedRouteEstimatedConsumption', 'PerformedRouteEstimatedTime',
                  'PerformedRouteEstimatedDistance', 'NumStopsKm', 'SpeedVariationNum', 'DrivingAggressiveness')


class UserStatsDAO(db.Model):
    __tablename__ = 'user_stats'
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'), primary_key=True)
    ConsumptionSaving = db.Column(db.Numeric(10, 2), nullable=False)
    EcoTime = db.Column(db.Numeric(10, 2), nullable=False)
    EcoDistance = db.Column(db.Numeric(10, 2), nullable=False)
    EcoRoutesNum = db.Column(db.Integer, nullable=False)
    DriveRating = db.Column(db.Numeric(3, 2), nullable=False)
    user = db.relationship('UserDAO', backref='stats', uselist=False)

    def __repr__(self):
        return f'<UserStats {self.UserID} {self.ConsumptionSaving} {self.EcoTime}>'

    def __init__(self, UserID, ConsumptionSaving, EcoTime, EcoDistance, EcoRoutesNum, DriveRating):
        self.UserID = UserID
        self.ConsumptionSaving = ConsumptionSaving
        self.EcoTime = EcoTime
        self.EcoDistance = EcoDistance
        self.EcoRoutesNum = EcoRoutesNum
        self.DriveRating = DriveRating


class UserStatsDAOSchema(ma.Schema):
    class Meta:
        fields = ('UserID', 'ConsumptionSaving', 'EcoTime', 'EcoDistance', 'EcoRoutesNum', 'DriveRating')


class AppReviewDAO(db.Model):
    __tablename__ = 'app_review'
    AppReviewID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID', ondelete='CASCADE'))
    GlobalComments = db.Column(db.String(2000), nullable=False)
    GlobalScore = db.Column(db.Numeric(3, 2), nullable=False)
    user = db.relationship('UserDAO', backref='reviews')
    features = db.relationship('FeatureReviewDAO', backref='app_review')

    def __repr__(self):
        return f'<AppReview {self.AppReviewID} {self.UserID} {self.GlobalScore}>'

    def __init__(self, UserID, GlobalComments, GlobalScore):
        self.UserID = UserID
        self.GlobalComments = GlobalComments
        self.GlobalScore = GlobalScore


class AppReviewDAOSchema(ma.Schema):
    class Meta:
        fields = ('AppReviewID', 'UserID', 'GlobalComments', 'GlobalScore')


class FeatureReviewDAO(db.Model):
    __tablename__ = 'feature_review'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AppReviewID = db.Column(db.Integer, db.ForeignKey('app_review.AppReviewID', ondelete='CASCADE'), nullable=False)
    Topic = db.Column(
        db.Enum('ACCESABILITY', 'RESPONSETIME', 'CONFIGURABILITY', 'USABILITY', 'TRUSTABILITY', 'ROBUSTNESS',
             'UTILITY'), nullable=False)
    Score = db.Column(db.Numeric(3, 2), nullable=False)
    Comments = db.Column(db.String(2000), nullable=False)

    def __repr__(self):
        return f'<FeatureReview {self.ID} {self.AppReviewID} {self.Topic} {self.Score}>'

    def __init__(self, AppReviewID, Topic, Score, Comments):
        self.AppReviewID = AppReviewID
        self.Topic = Topic
        self.Score = Score
        self.Comments = Comments


class FeatureReviewDAOSchema(ma.Schema):
    class Meta:
        fields = ('ID', 'AppReviewID', 'Topic', 'Score', 'Comments')
