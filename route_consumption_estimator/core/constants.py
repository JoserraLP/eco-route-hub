import os

GRAVITY = 9.81  # Gravity

# Aerodynamic effect
RO = 1.225  # Air density in kg/m^3
CX = 0.28  # Aerodynamic coefficient

# Consumption constants
R2 = 0.252
R1 = 1 - R2
CEXP = 0.35
BEXP = 0.203

# Idling consumption = ralenti
IDLING_CONSUMPTION = 0.7

# Max acceleration limit
ACC_LIMIT_PROPORTION = 0.7*GRAVITY

# Area factor -> Defined by hand
AREA_FACTOR = 0.8

# Percentage value of maximum power for performance calculation according to FASTSIM
POWER_PERCENTAGE = [0, 0.5, 1.5, 4, 6, 10, 14, 20, 40, 60, 80, 100]

# Performance value according to FASTSIM
ENGINE_PERFORMANCE = [10, 14, 20, 26, 32, 39, 41, 42, 41, 38, 36, 34]

DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

# Open Topo Data service
HEIGHT_API_URL = 'http://localhost:5000/v1/srtm30mspain?locations='

# Nominatim API URL
NOMINATIM_API_URL = 'http://localhost:8082/reverse?'
NOMINATIM_ADD_PARAMS = '&format=json&extratags=1&zoom=16'  # 16 to avoid buildings and POIs

NOMINATIM_ROAD_ATTRIBUTES = ["maxspeed"]

# Congestion distance
CONGESTION_DISTANCE = 500

# R script directory
R_SCRIPT_DIRECTORY = '../googletraffic/main.R'

# Congestion related data
CONGESTION_DICT = {
    "low": 0,
    "moderate": 1,
    "heavy": 2,
    "severe": 3
}

CONGESTION_DATA_DIR = '../congestion_data/'

# Default values for ways info and maximum speeds
DEFAULT_WAYS_VALUES = {
    'distance': 0.0,
    'slope': 0.0,
    'max_speed': 50.0,
    'lanes': 1,
    'highway': '',
    'name': '',
    'surface': '',
    'congestion': None
}

DEFAULT_MAX_SPEED_VALUES = {
    'pedestrian': 20.0,
    '1': 30.0,
    '2': 50.0,
    'motorway': 120.0,
    'motorway_link': 70.0
}

# Earth radius
EARTH_RADIUS = 6371000

# Time
DELTA_T = 1

# Space
DELTA_S = 1  # Adjust this to the length of the route
DELTA_S_MAX = 50  # meters
DELTA_S_MIN_INTERVAL_DISTANCE = 50000  # 50km
DELTA_S_MAX_INTERVAL_DISTANCE = 1000000  # 1000km

# Variables for calculating extended route (new nodes)
MAX_DISTANCE_BETWEEN_NODES = 100000000
DISTANCE_BETWEEN_NEW_NODES = 50

# Variables for calculating the slope
SLOPE_THRESHOLD = 12
SLOPE_VARIANCE_DIFFERENCE = 0.5
BATCHING_WINDOW_SIZE = 20

MAX_REQUEST_WORKERS = 4

DEFAULT_POLYLINE_PRECISION = 6
DEFAULT_MAX_SPEED = 50

SMOOTHING_FACTOR_ALPHA = 0.3

DEFAULT_USER_ROUTE_ADDITIONAL_MASS = 70
DEFAULT_VEHICLE_RF = 0.015
DEFAULT_VEHICLE_CX = 0.30

DEFAULT_VEHICLE_B = 0

DEFAULT_GASOLINE_CONVERSION = 9.2
DEFAULT_DIESEL_CONVERSION = 10.96

# Max is 3
OSRM_QUERY_PARAMS = {
    "alternatives": 3,
    "geometries": "geojson",
    "annotations": "nodes",
    "overview": "full"  # More precise routing coordinates
}

GRAPHHOPPER_QUERY_PARAMS = {
    "profile": "car",
    "point": '',
    "locale": "en",
    "elevation": "false",
    "optimize": "false",
    "instructions": "true",
    "calc_points": "true",
    "debug": "false",
    "points_encoded": "false",
    "ch.disable": "true",
    "heading": "0",
    "heading_penalty": "120",
    "pass_through": "false",
    "round_trip.distance": "10000",
    "round_trip.seed": "0",
    "key": os.environ.get("GRAPHHOPPER_KEY")
}
# Max is 3
OPENROUTESERVICE_QUERY_PARAMS = {"share_factor": 0.6, "target_count": 3, "weight_factor": 0.8}


API_KEY = "K4CH0P0-Eco-Traffic-App-Testing"
