"""
Visualization utilities for mapping coordinates and rendering NetworkX graphs.
"""

import logging
import os
import webbrowser
from typing import Any, List, Optional, Tuple, Union

import networkx as nx
import pandas as pd

try:
    import gmplot
except ImportError:
    gmplot = None

try:
    from pyvis.network import Network
except ImportError:
    Network = None

from route_consumption_estimator.domain.graph_models import Coords

logger = logging.getLogger(__name__)


def plot_coordinates_on_map(
    coordinates: List[Union[Coords, List[float], Tuple[float, float]]],
    output_file: str = "map.html",
    open_browser: bool = False,
    zoom: int = 10,
) -> Optional[str]:
    """
    Render waypoint coordinates on an interactive Google Map HTML file using gmplot.

    Args:
        coordinates: List of Coords instances or (lon, lat) tuples/lists.
        output_file (str): Target output HTML filepath.
        open_browser (bool): Automatically open the generated HTML file in a web browser.
        zoom (int): Map initial zoom level.

    Returns:
        Optional[str]: Path to the generated map file or None if failed.
    """
    if gmplot is None:
        logger.error(
            "The 'gmplot' library is not installed. Install it using 'pip install gmplot'."
        )
        return None

    if not coordinates:
        logger.warning("No coordinates provided for map rendering.")
        return None

    parsed_coords = []
    for item in coordinates:
        if isinstance(item, Coords):
            parsed_coords.append({"lat": item.lat, "lon": item.lon})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            parsed_coords.append({"lon": item[0], "lat": item[1]})

    df = pd.DataFrame(parsed_coords)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    if df.empty:
        logger.warning("No valid numeric coordinates found after parsing.")
        return None

    mean_lat = float(df["lat"].mean())
    mean_lon = float(df["lon"].mean())

    gmap = gmplot.GoogleMapPlotter(mean_lat, mean_lon, zoom=zoom)
    gmap.scatter(df["lat"], df["lon"], color="red", size=40, marker=False)

    gmap.draw(output_file)
    logger.info(f"Map successfully rendered and saved to {output_file}")

    if open_browser:
        abs_path = os.path.abspath(output_file)
        webbrowser.open(f"file://{abs_path}")

    return output_file


def show_graph(
    graph: nx.Graph,
    output_file: str = "nx.html",
    notebook: bool = False,
    open_browser: bool = False,
) -> Optional[str]:
    """
    Render a NetworkX graph as an interactive 2D HTML network visualization using PyVis.

    Args:
        graph (nx.Graph): NetworkX Graph / DiGraph / MultiDiGraph.
        output_file (str): Output HTML file name.
        notebook (bool): Set to True if executing inside Jupyter Notebook environment.
        open_browser (bool): Automatically open the generated graph in a browser.

    Returns:
        Optional[str]: Path to generated HTML file or None if PyVis is unavailable.
    """
    if Network is None:
        logger.error(
            "The 'pyvis' library is not installed. Install it using 'pip install pyvis'."
        )
        return None

    if not graph or len(graph.nodes) == 0:
        logger.warning("Empty NetworkX graph provided for visualization.")
        return None

    net = Network(notebook=notebook, directed=graph.is_directed())
    net.from_nx(graph)

    # Handle PyVis API variations between write_html and show
    try:
        net.write_html(output_file)
    except AttributeError:
        net.show(output_file)

    logger.info(f"Graph visualization saved to {output_file}")

    if open_browser and not notebook:
        abs_path = os.path.abspath(output_file)
        webbrowser.open(f"file://{abs_path}")

    return output_file
