import os

from route_consumption_estimator.routers.graphhopper import GraphHopper
from route_consumption_estimator.routers.ors import OpenRouteService
from route_consumption_estimator.routers.osrm import OSRM

OSRM_QUERY_PARAMS = {
    "alternatives": 0,
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

OPENROUTESERVICE_QUERY_PARAMS = {"share_factor": 0.6, "target_count": 1, "weight_factor": 0.8}


def get_routes_osrm(coords: list):
    osrm = OSRM(params=OSRM_QUERY_PARAMS)

    return osrm.get_routes(coords)


def get_routes_graphhopper(coords: list):
    # Append coords to query params
    GRAPHHOPPER_QUERY_PARAMS['point'] = [f"{coord.lat},{coord.lon}" for coord in coords]

    graphhopper = GraphHopper(params=GRAPHHOPPER_QUERY_PARAMS)

    return graphhopper.get_routes()


def get_routes_ors(coords: list):
    ors = OpenRouteService(params=OPENROUTESERVICE_QUERY_PARAMS)

    return ors.get_routes(coords)
