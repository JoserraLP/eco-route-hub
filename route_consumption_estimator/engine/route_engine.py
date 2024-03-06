import networkx as nx

from route_consumption_estimator.graph.models import Node, Segment, Coords
from route_consumption_estimator.static.constants import *


class EcoTrafficEngine:
    """
    Engine of the EcoTraffic APP
    """

    def __init__(self, routes: list):
        # Initialize graph db and memory graph as directed graph
        self._graph = nx.DiGraph()

        # Initialize routes
        self._routes = routes

        # Create a dict with the coordinates and a related identifier
        self._coordinates_ids = {}

        # Last identifier used
        self._last_id = 0

    def get_coordinates_id(self, coords: Coords) -> str:
        """
        Get coordinates id for the graph based on its latitude and longitude
        :param coords:
        :return:
        """
        coords_str = f'{coords.lat};{coords.lon}'  # ID = lat;lon

        # Retrieve the node id if exists, otherwise calculate it and store it
        if coords_str in self._coordinates_ids:
            coords_id = self._coordinates_ids[coords_str]
        else:
            self._coordinates_ids[coords_str] = coords_id = self._last_id
            self._last_id += 1

        return str(coords_id)

    def create_node(self, node_info: Node) -> None:
        """
        Create a node in the memory graph

        :param node_info: Node information
        :type node_info: Node
        :return: None
        """
        # Check if node exists
        if node_info.node_id not in self._graph.nodes:
            # Add node
            self._graph.add_node(node_info.node_id, lat=node_info.lat, lon=node_info.lon, height=node_info.height)

    def create_relation(self, source_id: str, destination_id: str, segment_info: Segment) -> None:
        """
        Create a relation between source and destination nodes in the memory graph and/or graph database

        :param source_id: source node identifier
        :type source_id: str
        :param destination_id: destination node identifier
        :type destination_id: Node
        :param segment_info: segment information
        :type segment_info: Segment
        :return: None
        """
        # Store relation
        self._graph.add_edge(source_id, destination_id, slope=segment_info.slope, distance=segment_info.distance,
                             congestion=segment_info.congestion, max_speed=segment_info.max_speed,
                             lanes=segment_info.lanes, highway=segment_info.highway, name=segment_info.name,
                             surface=segment_info.surface, way_id=segment_info.way_id)

    def store_routes_graph(self):
        """
        Process all the routes and store them into the graphs

        :return:
        """
        # Changed to be single routes each path and not connecting them
        for i, route in enumerate(self._routes):
            # Define route id
            route_id = i
            # Retrieve segments
            segments = route['segments']

            # Iterate over pairs of coordinates creating only destination nodes
            for idx, (source, destination) in enumerate(zip(segments, segments[1:])):
                # Source and destination nodes has the same ID
                if idx == 0:
                    source_id = 'source'
                    destination_id = f"{self.get_coordinates_id(destination)}-r{route_id}"
                elif idx == len(segments) - 2:
                    source_id = f"{self.get_coordinates_id(source)}-r{route_id}"
                    destination_id = 'destination'
                else:
                    # Append new identifier with route
                    source_id = f"{self.get_coordinates_id(source)}-r{route_id}"
                    destination_id = f"{self.get_coordinates_id(destination)}-r{route_id}"

                # Create the destination node info
                source_node = Node(node_id=source_id, lat=source.lat, lon=source.lon, height=route['heights'][idx])
                destination_node = Node(node_id=destination_id, lat=destination.lat, lon=destination.lon,
                                        height=route['heights'][idx + 1])

                # Store the source and destination nodes
                self.create_node(node_info=source_node)
                self.create_node(node_info=destination_node)

                # Create the segment info
                segment_info = Segment(slope=route['slopes'][idx], distance=route['distances'][idx],
                                       max_speed=route['max_speed'][idx], congestion=None, lanes=0, highway="",
                                       name="", surface="", way_id="")
                # Store the relation between them
                self.create_relation(source_id, destination_id, segment_info)

    def extend_graph_info(self):
        """
        Extend graph information related to ways such as congestion, max_speed, lanes, type of highway, name or surface
        if not set previously.

        :return:
        """
        # Define previous node info
        previous_relation = {}

        # First check if first node have information, otherwise search for it on its successors
        self.extend_initial_empty_nodes()

        # Iterate over the graph by source-destination pair
        for u, v in self._graph.edges:
            # Extend relation info
            relation = self.extend_relation_info(u, v, previous_relation)

            # Update relation data
            self._graph.add_edge(u, v, **relation)

    def extend_initial_empty_nodes(self):
        """
        Iterate over the first node to check if it has information, if do not, search for it on its successors

        :return:
        """
        last_relation = {}
        passed_nodes = []
        # Iterate over the graph by source-destination pair
        for u, v in self._graph.edges:
            # Append the source node
            passed_nodes.append(u)
            # Retrieve relation information
            relation = self._graph.get_edge_data(u, v)
            # Check non-default values of the relation
            default_keys = [k for k, v in relation.items() if k in DEFAULT_WAYS_VALUES and
                            v == DEFAULT_WAYS_VALUES[k]]
            # Check default keys -> If there are the ones specified it means it is unchanged
            while default_keys == ['slope', 'maxspeed', 'lanes', 'highway', 'name', 'surface']:
                # Retrieve new successor
                successors = list(self._graph.successors(v))
                # There are successors
                if successors:
                    # Get new relation value
                    relation = self._graph.get_edge_data(v, successors[0])
                    # Check non-default values of the relation
                    default_keys = [k for k, v in relation.items() if k in DEFAULT_WAYS_VALUES and
                                    v == DEFAULT_WAYS_VALUES[k]]
                # Append target to passed nodes
                passed_nodes.append(v)
                # Update last_relation variable
                last_relation = relation
                # Update target to its successor
                v = successors[0]
            # Once a node with non-default values is achieved, stop searching
            break

        # Iterate over the passed nodes
        for u, v in zip(passed_nodes[:-1], passed_nodes[1:]):
            relation = self._graph.get_edge_data(u, v)
            # Get those attributes that are empty or with default values and update from previous
            for key, value in relation.items():
                # Way ID, distance, congestion and slope are not copied
                if key != 'way_id' and key != 'congestion' and key != 'distance' and key != 'slope':
                    relation[key] = last_relation[key]
                else:
                    # Remain the same value as previous
                    relation[key] = value

            # Update relation data
            self._graph.add_edge(u, v, **relation)

    def extend_relation_info(self, source, target, previous_relation: dict) -> dict:
        """
        Extend relation information based on the previous relation

        :param source: source node
        :param target: target node
        :param previous_relation: previous relation information
        :type previous_relation: dict
        :return: updated relation information
        :rtype: dict
        """
        # Retrieve relation information
        relation = self._graph.get_edge_data(source, target)

        # Get those attributes that are empty or with default values and update from previous
        for key, value in relation.items():
            # Way ID not processed and congestion will be processed afterwards
            if key != 'way_id' and key != 'congestion':
                if value == DEFAULT_WAYS_VALUES[key]:
                    if key in previous_relation:
                        relation[key] = previous_relation[key]
            else:
                # Remain the same the way id
                relation[key] = value

        return relation

    def get_routes_information(self):
        """
        Get the routes information divided by delta_s segments

        :return:
        """
        routes_information = []
        # Get source and target (there should be only one of each)
        sources = [x for x in self._graph.nodes() if self._graph.in_degree(x) == 0]
        targets = [x for x in self._graph.nodes() if self._graph.out_degree(x) == 0]

        # Iterate all possible simple paths between source and destination
        simple_paths = nx.all_simple_paths(self._graph, source=sources[0], target=targets[0])
        # Get the required attributes (max_speed, slope and distance)
        for simple_path in simple_paths:
            # Define dict for information
            simple_path_info = {'max_speed': [], 'slope': [], 'distance': []}

            # Iterate over the edges data
            for edge_data in self._graph.edges(simple_path, data=True):
                simple_path_info['max_speed'].append(edge_data[2]['max_speed'])
                simple_path_info['slope'].append(edge_data[2]['slope'])
                simple_path_info['distance'].append(edge_data[2]['distance'])

            # Append the data
            routes_information.append(simple_path_info)

        micro_segments_route_information = []
        # Calculate the values for micro segments for each route
        for route_info in routes_information:
            # Define variables of route info
            max_speeds, slopes, distances = route_info['max_speed'], route_info['slope'], route_info['distance']

            # Define segment start point for the route
            segment_start_point = [0]
            acc_distance = 0
            # Get the length of the segments e.g. from 'distance'
            for i in range(1, len(route_info['distance'])):
                # Increase the accumulated distance with previous value
                acc_distance += route_info['distance'][i - 1]
                # Add accumulated distance
                segment_start_point.append(acc_distance)

            micro_segment_speeds, micro_segment_slopes, micro_segment_distances = [], [], []
            # Iterate over for getting the micro segments
            for i, distance in enumerate(distances):
                # Define instant speed and slope lists
                instant_speed, instant_slope = [], []

                # Calculate num micro segments
                num_micro_segments = int(distance // DELTA_S) + 1

                # Iterate over the number of micro segments to store the speeds and processed slopes
                for _ in range(num_micro_segments):
                    instant_speed.append(max_speeds[i])
                    instant_slope.append(slopes[i] / 100)

                micro_segment_speeds.append(instant_speed)
                micro_segment_slopes.append(instant_slope)

            # Calculate the accumulated of the slopes
            micro_segment_slopes_acc = []
            for slopes_i in micro_segment_slopes:
                micro_segment_slopes_acc.append(sum(slopes_i))

            # Calculate micro segments of distance with DELTA_S
            # First create a list with DELTA_S for all segments
            micro_segment_distances = [[DELTA_S for _ in range(int(distance // DELTA_S))] for i, distance in
                                       enumerate(distances)]
            # Iterate over the upper segments and add one new element if there is decimals
            for i, micro_segment in enumerate(micro_segment_distances):
                # If there are decimals, append the new value
                if distances[i] % DELTA_S != 0:
                    micro_segment.append(distances[i] % DELTA_S)

            # Flatten micro segment speeds, slopes and distances
            micro_segment_speeds = [item for sublist in micro_segment_speeds for item in sublist]
            micro_segment_slopes = [item for sublist in micro_segment_slopes for item in sublist]
            micro_segment_distances = [item for sublist in micro_segment_distances for item in sublist]

            # Store the start micro segment points
            micro_segment_start_points = [0]
            acc_distance = 0
            for i in range(len(micro_segment_distances) - 1):
                acc_distance += micro_segment_distances[i]
                micro_segment_start_points.append(acc_distance)

            # Append micro segment information
            micro_segments_route_information.append({'start_points': micro_segment_start_points,
                                                     'max_speeds': micro_segment_speeds,
                                                     'slopes': micro_segment_slopes})
        return micro_segments_route_information

    def restart_graph(self):
        """
        Stop engine connections

        :return: None
        """
        self._graph.clear()

    @property
    def routes(self):
        """
        Getter of routes

        :return: routes
        """
        return self._routes

    @routes.setter
    def routes(self, routes: list):
        """
        Setter of routes

        :param routes: routes
        :return:
        """
        self._routes = routes
