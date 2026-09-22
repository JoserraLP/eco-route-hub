import uuid

import networkx as nx
from flask import current_app

from route_consumption_estimator.domain import Coords, Node, Segment

# Default values for ways info and maximum speeds
DEFAULT_WAYS_VALUES = {
    'distances': 0.0,
    'slopes': 0.0,
    'maxspeed': 50.0,
    'lanes': 1,
    'highway': '',
    'name': '',
    'surface': '',
    'congestion': None
}

class GraphEngine:

    def __init__(self, routes: list = None):
        # Initialize graph db and memory graph as directed graph
        self._graph = nx.DiGraph()

        # Initialize routes
        self._routes = routes

        # Create a dict with the coordinates and a related identifier
        self._coordinates_ids = {}

        # Last identifier used
        self._last_id = 0

        # Get all stored attributes from configuration
        self._all_graph_attributes = current_app.config.get("ALL_ATTRIBUTES")

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
        self._graph.add_edge(source_id, destination_id, **{'maxspeed': segment_info.maxspeed} | segment_info.extra)

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

                # Create the segment info with additional information
                extra_info = {k: route[k][idx] for k in self._all_graph_attributes}

                segment_info = Segment(maxspeed=route['maxspeed'][idx], segment_id=uuid.uuid4(), extra=extra_info)
                # Store the relation between them
                self.create_relation(source_id, destination_id, segment_info)

    def extend_graph_info(self):
        """
        Extend graph information related to ways such as congestion, maxspeed, lanes, type of highway, name or surface
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
                if key != 'segment_id' and key != 'congestion' and key != 'distance' and key != 'slope':
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
            if key != 'segment_id' and key != 'congestion':
                if key in DEFAULT_WAYS_VALUES and value == DEFAULT_WAYS_VALUES[key]:
                    if key in previous_relation:
                        relation[key] = previous_relation[key]
            else:
                # Remain the same the way id
                relation[key] = value

        return relation

    def get_routes_information(self, avg_route_distance: float):
        """
        Get the routes information divided by delta_s segments

        :param avg_route_distance: average distance of the routes to calculate delta_s
        :type avg_route_distance: float

        :return:
        """
        current_app_config = current_app.config["APP_CONFIG"].system
        delta_s = current_app_config.delta_s
        # If it is greater than the first threshold
        if avg_route_distance > current_app_config.delta_s_min_interval_distance:
            # Calculate the specified delta_s value (must be integer)
            delta_s = int(current_app_config.delta_s_max * avg_route_distance /
                          current_app_config.delta_s_max_interval_distance)

        routes_information = []
        # Get source and target (there should be only one of each)
        sources = [x for x in self._graph.nodes() if self._graph.in_degree(x) == 0]
        targets = [x for x in self._graph.nodes() if self._graph.out_degree(x) == 0]
        # Key error maxspeed
        # Iterate all possible simple paths between source and destination
        simple_paths = nx.all_simple_paths(self._graph, source=sources[0], target=targets[0])
        # Get the attributes
        for simple_path in simple_paths:
            # Define dict for information
            simple_path_info = {k: [] for k in self._all_graph_attributes}

            # Iterate over the edges data
            for edge_data in self._graph.edges(simple_path, data=True):
                for attribute in self._all_graph_attributes:
                    simple_path_info[attribute].append(edge_data[2][attribute])

            # Append the data
            routes_information.append(simple_path_info)

        attributes = set()

        for _, _, data in self._graph.edges(data=True):
            attributes.update(data.keys())

        print(f"Graph edges attributes: {attributes}")

        micro_segments_route_information = []
        # Calculate the values for micro segments for each route
        for route_info in routes_information:
            # Define segment start point for the route
            segment_start_point = [0]
            acc_distance = 0
            # Get the length of the segments e.g. from 'distances' which is mandatory
            for i in range(1, len(route_info['distances'])):
                # Increase the accumulated distance with previous value
                acc_distance += route_info['distances'][i - 1]
                # Add accumulated distance
                segment_start_point.append(acc_distance)

            # Do not consider heights as they are used in nodes (not segments)
            micro_segments_info = {k: [] for k in route_info.keys() if k != 'heights'}

            # Iterate over for getting the micro segments
            for i, distance in enumerate(route_info['distances']):
                # Define instant speed and slope lists
                instant_info = {k: [] for k in route_info.keys() if k not in ['heights', 'distances']}

                # Calculate num micro segments
                num_micro_segments = int(distance // delta_s) + 1

                # Iterate over the number of micro segments to store the speeds and processed slopes
                for _ in range(num_micro_segments):
                    for k, v in route_info.items():
                        if k == 'distances' or k == 'heights':
                            continue
                        elif k == 'slopes':
                            instant_info[k].append(v[i]/100)
                        else:
                            instant_info[k].append(v[i])

                for k in instant_info.keys():
                    micro_segments_info[k].append(instant_info[k])

            # Calculate micro segments of distance with delta_s
            # First create a list with delta_s for all segments
            micro_segment_distances = [[delta_s for _ in range(int(distance // delta_s))] for i, distance in
                                       enumerate(route_info['distances'])]
            # Iterate over the upper segments and add one new element if there is decimals
            for i, micro_segment in enumerate(micro_segment_distances):
                # If there are decimals, append the new value
                if route_info['distances'][i] % delta_s != 0:
                    micro_segment.append(route_info['distances'][i] % delta_s)

            # Flatten internal info and distances
            for k, v in micro_segments_info.items():
                micro_segments_info[k] = [item for sublist in v for item in sublist]

            micro_segment_distances = [item for sublist in micro_segment_distances for item in sublist]

            # Store the start micro segment points
            micro_segment_start_points = [0]
            acc_distance = 0
            for i in range(len(micro_segment_distances) - 1):
                acc_distance += micro_segment_distances[i]
                micro_segment_start_points.append(acc_distance)

            # Append micro segment information
            micro_segments_route_information.append({'start_points': micro_segment_start_points} | micro_segments_info)

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
