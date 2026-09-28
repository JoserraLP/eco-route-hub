"""
Graph domain data models.

Defines in-memory dataclass entities for representing geospatial coordinates, 
OpenStreetMap nodes, road segments/edges, segment pairs, and evaluated routes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Coords:
    """Geospatial coordinates representation (Latitude and Longitude)."""

    lat: float
    lon: float

    def to_tuple(self) -> Tuple[float, float]:
        """Return coordinates as a (latitude, longitude) tuple."""
        return self.lat, self.lon


@dataclass
class Node:
    """OpenStreetMap node entity containing spatial coordinates and elevation."""

    node_id: str
    lat: float
    lon: float
    height: float = 0.0

    @property
    def coords(self) -> Coords:
        """Get coordinates as a Coords instance."""
        return Coords(lat=self.lat, lon=self.lon)


@dataclass
class Segment:
    """
    OpenStreetMap road segment / relation connecting two nodes.

    Attributes:
        maxspeed (Optional[int]): Speed limit in km/h.
        segment_id (str): Unique segment identifier.
        extra (Dict[str, Any]): Additional metadata associated with the segment.
            Common keys in 'extra':
                - distance (float): Length in meters.
                - slope (float): Inclination angle or percentage.
                - lanes (int): Number of driving lanes.
                - highway (str): OSM highway type classification (e.g., 'motorway').
                - name (str): Road name.
                - surface (str): Road surface material (e.g., 'asphalt').
                - congestion (int): Traffic congestion level index.
    """

    maxspeed: Optional[int] = None
    segment_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SegmentNodes:
    """Directed segment bounded by source and destination coordinates."""

    source: Coords
    destination: Coords
    segment: Segment


@dataclass
class Route:
    """
    Calculated route containing geometric nodes, attributes, and total estimated metrics.

    Attributes:
        total_distance (float): Total route length in meters.
        ett (float): Estimated Travel Time in seconds.
        efc (float): Estimated Fuel/Energy Consumption.
        nodes (List[Node]): Ordered sequence of route spatial nodes.
        segments (List[Segment]): Sequence of road segments along the route.
    """

    total_distance: float = 0.0
    ett: float = 0.0
    efc: float = 0.0
    nodes: List[Node] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)

    @property
    def num_nodes(self) -> int:
        """Return total number of nodes in the route."""
        return len(self.nodes)

    @property
    def num_segments(self) -> int:
        """Return total number of segments in the route."""
        return len(self.segments)
