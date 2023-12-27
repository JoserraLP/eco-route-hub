import webbrowser
import time
import gmplot
import pandas as pd
import networkx as nx
from pyvis.network import Network


def plot_coordinates_on_map(coordinates: list):
    """
    Plot and show all the coordinates on an HTML map

    :param coordinates: list of coordinates (lon, lat)
    :type coordinates: list
    :return:
    """
    # Coordinates are reversed
    df = pd.DataFrame(coordinates, columns=['lon', 'lat'])

    # Parse lat and lon columns to numeric
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    # Create a map plot with center the mean of the latitude and longitude with a zoom of 10
    gmap = gmplot.GoogleMapPlotter(df['lat'].mean(), df['lon'].mean(), zoom=10)
    # Insert the information into the plot
    gmap.scatter(df['lat'], df['lon'], color='red', size=40, marker=False)
    # Define file where map will be stored
    map_file = 'map.html'
    # Draw on the selected file
    gmap.draw(map_file)
    # Open the file in the browser
    webbrowser.open(map_file)


def show_graph(g: nx.MultiDiGraph):
    nt = Network()
    # populates the nodes and edges data structures
    nt.from_nx(g)
    nt.show('nx.html', notebook=False)
