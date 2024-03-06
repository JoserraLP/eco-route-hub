# Open Topo Data service
HEIGHT_API_URL = 'http://localhost:5000/v1/srtm30mspain?locations='

# Nominatim API URL
NOMINATIM_API_URL = 'http://localhost:8082/reverse?'
NOMINATIM_ADD_PARAMS = '&format=json&extratags=1&zoom=16'  # 16 to avoid buildings and POIs

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

# Time
DELTA_T = 1

# Space
DELTA_S = 1  # Adjust this to the length of the route

# Variables for calculating extended route (new nodes)
MAX_DISTANCE_BETWEEN_NODES = 100000000
DISTANCE_BETWEEN_NEW_NODES = 50

# Variables for calculating the slope
SLOPE_THRESHOLD = 12
SLOPE_VARIANCE_DIFFERENCE = 0.5
BATCHING_WINDOW_SIZE = 20

MAX_REQUEST_WORKERS = 4
