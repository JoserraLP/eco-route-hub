from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Segment:
    """ OpenStreetMap road relation between two nodes """
    max_speed: int
    segment_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    """
    Additional information examples (included in extra)

    distance: float
    slope: float 
    lanes: int 
    highway: str
    name: str 
    surface: str
    congestion: int
    """


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
