import os

from route_consumption_estimator.graph.models import Coords
from route_consumption_estimator.routers.graphhopper import GraphHopper
from route_consumption_estimator.routers.ors import OpenRouteService
from route_consumption_estimator.routers.osrm import OSRM

OSRM_QUERY_PARAMS = {
    "alternatives": 2,
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

OPENROUTESERVICE_QUERY_PARAMS = {"share_factor": 0.6, "target_count": 2, "weight_factor": 0.8}


def get_routes_osrm(coords: list, common_source: Coords, common_target: Coords):
    osrm = OSRM(params=OSRM_QUERY_PARAMS)

    return osrm.get_routes(coords, common_source=common_source, common_target=common_target)


def get_routes_graphhopper(coords: list, common_source: Coords, common_target: Coords):
    # Append coords to query params
    GRAPHHOPPER_QUERY_PARAMS['point'] = [f"{coord.lat},{coord.lon}" for coord in coords]

    graphhopper = GraphHopper(params=GRAPHHOPPER_QUERY_PARAMS)

    return graphhopper.get_routes(common_source=common_source, common_target=common_target)


def get_routes_ors(coords: list, common_source: Coords, common_target: Coords):
    ors = OpenRouteService(params=OPENROUTESERVICE_QUERY_PARAMS)

    return ors.get_routes(coords, common_source=common_source, common_target=common_target)
