from dataclasses import dataclass

from route_consumption_estimator.static.constants import DEFAULT_WAYS_VALUES


@dataclass
class Segment:
    """ OpenStreetMap road relation between two nodes """
    way_id: str = ""
    distance: float = DEFAULT_WAYS_VALUES['distance']
    slope: float = DEFAULT_WAYS_VALUES['slope']
    max_speed: float = DEFAULT_WAYS_VALUES['max_speed']
    lanes: int = DEFAULT_WAYS_VALUES['lanes']
    highway: str = DEFAULT_WAYS_VALUES['highway']
    name: str = DEFAULT_WAYS_VALUES['name']
    surface: str = DEFAULT_WAYS_VALUES['surface']
    congestion: int = DEFAULT_WAYS_VALUES['congestion']


@dataclass
class Node:
    """ OpenStreetMap node information """
    node_id: str
    lat: float
    lon: float
    height: float


@dataclass
class Coords:
    """ Coordinates information """
    lat: float
    lon: float


@dataclass
class SegmentNodes:
    source: Coords
    destination: Coords
    segment: Segment


@dataclass
class Route:
    total_distance: float
    ett: float
    efc: float
    nodes: list[Node]
    segments: list[Segment]
