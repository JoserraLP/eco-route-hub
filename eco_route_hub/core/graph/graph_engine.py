"""
Graph Engine for Route Consumption Estimator.

Constructs, processes, and queries NetworkX directed graphs representing vehicle routes,
nodes (waypoints), edges (segments), and associated telemetry attributes.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Set

import networkx as nx
from flask import current_app

from eco_route_hub.domain.graph_models import Coords, Node, Segment

logger = logging.getLogger(__name__)

# Default values for OSM/Provider road attributes
DEFAULT_WAYS_VALUES: Dict[str, Any] = {
    "distances": 0.0,
    "slopes": 0.0,
    "maxspeed": 50.0,
    "lanes": 1,
    "highway": "",
    "name": "",
    "surface": "",
    "congestion": None,
}

DEFAULT_GRAPH_ATTRIBUTES: List[str] = [
    "distances",
    "slopes",
    "maxspeed"
]


class GraphEngine:
    """
    In-memory directed graph engine for storing, enriching, and micro-segmenting routes.

    Attributes:
        routes (List[Dict[str, Any]]): Raw segmented route payloads.
        all_graph_attributes (List[str]): List of edge attributes stored in graph relations.
    """

    def __init__(
            self,
            routes: Optional[List[Dict[str, Any]]] = None,
            all_graph_attributes: Optional[List[str]] = None,
            config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self.routes: List[Dict[str, Any]] = routes or []
        self.coordinates_ids: Dict[str, int] = {}
        self.last_id: int = 0

        self.all_graph_attributes: List[str] = (
                all_graph_attributes or DEFAULT_GRAPH_ATTRIBUTES
        )
        self.config: Dict[str, Any] = config or {}

    def get_coordinates_id(self, coords: Coords) -> str:
        """
        Generate or retrieve a unique string identifier for a pair of coordinates.

        Args:
            coords (Coords): Waypoint coordinate object.

        Returns:
            str: String representation of internal node ID.
        """
        coords_str = f'{coords.lat};{coords.lon}'  # ID = lat;lon

        # Retrieve the node id if exists, otherwise calculate it and store it
        if coords_str in self.coordinates_ids:
            coords_id = self.coordinates_ids[coords_str]
        else:
            coords_id = self.last_id
            self.coordinates_ids[coords_str] = coords_id
            self.last_id += 1

        return str(coords_id)

    def create_node(self, node_info: Node) -> None:
        """
        Add a waypoint node to the directed graph if it does not exist.

        Args:
            node_info (Node): Domain Node model containing location and height.
        """
        if node_info.node_id not in self.graph.nodes:
            self.graph.add_node(
                node_info.node_id,
                lat=node_info.lat,
                lon=node_info.lon,
                height=node_info.height,
            )

    def create_relation(
            self, source_id: str, destination_id: str, segment_info: Segment
    ) -> None:
        """
            Create a directed edge relation between two graph nodes with telemetry attributes.

            Args:
                source_id (str): Source node identifier.
                destination_id (str): Destination node identifier.
                segment_info (Segment): Domain Segment model carrying telemetry attributes.
            """
        # Store relation
        edge_data = {"maxspeed": segment_info.maxspeed, **segment_info.extra}
        self.graph.add_edge(source_id, destination_id, **edge_data)

    def store_routes_graph(self) -> None:
        """
        Parse stored routes and construct graph nodes and edges for each path.
        """
        for route_id, route in enumerate(self.routes):
            segments = route.get("segments", [])
            heights = route.get("heights", [])
            maxspeeds = route.get("maxspeed", [])

            if len(segments) < 2:
                continue

            for idx, (source, destination) in enumerate(zip(segments, segments[1:])):
                # Assign dedicated source and destination IDs per route
                if idx == 0:
                    source_id = "source"
                    destination_id = f"{self.get_coordinates_id(destination)}-r{route_id}"
                elif idx == len(segments) - 2:
                    source_id = f"{self.get_coordinates_id(source)}-r{route_id}"
                    destination_id = "destination"
                else:
                    source_id = f"{self.get_coordinates_id(source)}-r{route_id}"
                    destination_id = f"{self.get_coordinates_id(destination)}-r{route_id}"

                source_height = heights[idx] if idx < len(heights) else 0.0
                dest_height = heights[idx + 1] if (idx + 1) < len(heights) else 0.0

                source_node = Node(
                    node_id=source_id,
                    lat=source.lat,
                    lon=source.lon,
                    height=source_height,
                )
                destination_node = Node(
                    node_id=destination_id,
                    lat=destination.lat,
                    lon=destination.lon,
                    height=dest_height,
                )

                self.create_node(node_info=source_node)
                self.create_node(node_info=destination_node)

                # Extract extra attributes safely
                extra_info = {}
                for key in self.all_graph_attributes:
                    if key in route and idx < len(route[key]):
                        extra_info[key] = route[key][idx]

                maxspeed_val = maxspeeds[idx] if idx < len(maxspeeds) else 50.0

                segment_info = Segment(
                    maxspeed=maxspeed_val,
                    segment_id=uuid.uuid4(),
                    extra=extra_info,
                )
                self.create_relation(source_id, destination_id, segment_info)

    def extend_graph_info(self) -> None:
        """
        Propagate road telemetry attributes along connected edges if unassigned or default.
        """
        self.extend_initial_empty_nodes()

        previous_relation: Dict[str, Any] = {}
        for u, v in self.graph.edges():
            relation = self.extend_relation_info(u, v, previous_relation)
            self.graph.add_edge(u, v, **relation)
            previous_relation = relation

    def extend_initial_empty_nodes(self):
        """
        Search forward in graph successors to fill initial node missing attribute values.
        """
        last_relation: Dict[str, Any] = {}
        passed_nodes: List[str] = []

        for u, v in self.graph.edges():
            passed_nodes.append(u)
            relation = self.graph.get_edge_data(u, v) or {}

            # Check if all relation properties carry default values
            is_default = all(
                relation.get(k) == v_def
                for k, v_def in DEFAULT_WAYS_VALUES.items()
                if k in relation
            )

            visited = set()
            curr_v = v
            while is_default and curr_v not in visited:
                visited.add(curr_v)
                successors = list(self.graph.successors(curr_v))
                # There are successors
                if successors:
                    next_v = successors[0]
                    relation = self.graph.get_edge_data(curr_v, next_v) or {}
                    passed_nodes.append(curr_v)
                    last_relation = relation
                    curr_v = next_v

                    is_default = all(
                        relation.get(k) == v_def
                        for k, v_def in DEFAULT_WAYS_VALUES.items()
                        if k in relation
                    )
            # Once a node with non-default values is achieved, stop searching
            break

        # Iterate over the passed nodes
        if last_relation and len(passed_nodes) > 1:
            for u_node, v_node in zip(passed_nodes[:-1], passed_nodes[1:]):
                rel = self.graph.get_edge_data(u_node, v_node) or {}
                for key, val in rel.items():
                    if key not in ("segment_id", "congestion", "distance", "slope", "slopes"):
                        rel[key] = last_relation.get(key, val)
                self.graph.add_edge(u_node, v_node, **rel)

    def extend_relation_info(
            self, source: str, target: str, previous_relation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fill missing edge attributes using data from the preceding edge relation.
        """
        relation = dict(self.graph.get_edge_data(source, target) or {})

        for key, value in relation.items():
            if key not in ("segment_id", "congestion"):
                if key in DEFAULT_WAYS_VALUES and value == DEFAULT_WAYS_VALUES[key]:
                    if key in previous_relation:
                        relation[key] = previous_relation[key]

        return relation

    def get_routes_information(
            self,
            avg_route_distance: float,
            delta_s_default: int = 1,
            delta_s_min_interval_distance: float = 50000.0,
            delta_s_max_interval_distance: float = 1000000.0,
            delta_s_max: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Process graph simple paths and split segments into spatial micro-segments (delta_s).

        Args:
            avg_route_distance (float): Mean route length in meters.
            delta_s_default (int): Default micro-segment length step in meters.
            delta_s_min_interval_distance (float): Distance threshold to scale delta_s.
            delta_s_max_interval_distance (float): Upper limit for delta_s scaling.
            delta_s_max (int): Maximum cap for micro-segment step size.

        Returns:
            List[Dict[str, Any]]: Segmented route information enriched with micro-steps.
        """
        delta_s = delta_s_default
        if avg_route_distance > delta_s_min_interval_distance:
            delta_s = int(
                (delta_s_max * avg_route_distance) / delta_s_max_interval_distance
            )
            delta_s = max(1, min(delta_s, delta_s_max))

        sources = [x for x in self.graph.nodes() if self.graph.in_degree(x) == 0]
        targets = [x for x in self.graph.nodes() if self.graph.out_degree(x) == 0]

        if not sources or not targets:
            logger.warning("Graph has no valid source or target nodes.")
            return []

        routes_information: List[Dict[str, List[Any]]] = []

        try:
            simple_paths = list(
                nx.all_simple_paths(self.graph, source=sources[0], target=targets[0])
            )
        except (nx.NetworkXError, IndexError) as e:
            logger.error(f"Error computing simple paths in graph: {e}")
            return []

        # Extract path edge attributes in strict sequential order
        for simple_path in simple_paths:
            path_info: Dict[str, List[Any]] = {
                k: [] for k in self.all_graph_attributes
            }

            for u, v in zip(simple_path, simple_path[1:]):
                edge_data = self.graph.get_edge_data(u, v) or {}
                for attribute in self.all_graph_attributes:
                    path_info[attribute].append(edge_data.get(attribute))

            routes_information.append(path_info)

        detected_attrs: Set[str] = set()
        for _, _, data in self.graph.edges(data=True):
            detected_attrs.update(data.keys())

        logger.debug(f"Graph edges attributes detected: {detected_attrs}")

        micro_segments_route_information: List[Dict[str, Any]] = []

        for route_info in routes_information:
            distances = route_info.get("distances", [])
            if not distances:
                continue

            micro_segments_info: Dict[str, List[Any]] = {
                k: [] for k in route_info.keys() if k != "heights"
            }

            for i, distance in enumerate(distances):
                if distance is None or distance <= 0:
                    distance = float(delta_s)

                instant_info: Dict[str, List[Any]] = {
                    k: []
                    for k in route_info.keys()
                    if k not in ("heights", "distances")
                }

                num_micro_segments = int(distance // delta_s) + 1

                for _ in range(num_micro_segments):
                    for k, v in route_info.items():
                        if k in ("distances", "heights"):
                            continue
                        elif k in ("slopes", "slope"):
                            val = v[i] if i < len(v) and v[i] is not None else 0.0
                            instant_info[k].append(val / 100.0)
                        else:
                            val = v[i] if i < len(v) else None
                            instant_info[k].append(val)

                for k, v_list in instant_info.items():
                    micro_segments_info[k].append(v_list)

            # Calculate micro-segment spatial steps
            micro_segment_distances: List[List[float]] = [
                [float(delta_s) for _ in range(int((d or delta_s) // delta_s))]
                for d in distances
            ]
            for i, micro_seg in enumerate(micro_segment_distances):
                d_val = distances[i] or delta_s
                if d_val % delta_s != 0:
                    micro_seg.append(float(d_val % delta_s))

            # Flatten micro-segments lists
            for k, v in micro_segments_info.items():
                micro_segments_info[k] = [
                    item for sublist in v for item in sublist
                ]

            flat_distances = [
                item for sublist in micro_segment_distances for item in sublist
            ]

            # Calculate micro-segment start coordinates/distances
            micro_segment_start_points = [0.0]
            acc_distance = 0.0
            for i in range(len(flat_distances) - 1):
                acc_distance += flat_distances[i]
                micro_segment_start_points.append(acc_distance)

            micro_segments_route_information.append(
                {"start_points": micro_segment_start_points, **micro_segments_info}
            )

        return micro_segments_route_information

    def restart_graph(self) -> None:
        """Clear all graph edges, nodes, and coordinate mapping caches."""
        self.graph.clear()
        self.coordinates_ids.clear()
        self.last_id = 0
