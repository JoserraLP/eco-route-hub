import zipfile

from fastkml import kml
from pygeoif.geometry import LineString

from route_consumption_estimator.graph.models import Coords


def extract_coordinates(geometry):
    if isinstance(geometry, LineString):
        # Do not return height
        return list(geometry.coords)
    else:
        return []


def kmz_to_coordinates(file_path) -> list[Coords]:
    kmz = zipfile.ZipFile(file_path, 'r')
    kml_file = kmz.open('doc.kml', 'r')

    k = kml.KML()
    k.from_string(kml_file.read())

    coordinates_list = []

    def extract_placemark(placemark):
        coordinates_list.extend(extract_coordinates(placemark.geometry))

    def traverse_feature(feature):
        for subfeature in feature.features():

            if isinstance(subfeature, kml.Placemark):
                extract_placemark(subfeature)
            elif isinstance(subfeature, kml.Folder):
                traverse_feature(subfeature)

    for feature in k.features():
        traverse_feature(feature)

    # Remove the third field (height)
    coordinates_list = [coordinates[:2] for coordinates in coordinates_list]

    # Parse to coords object
    coordinates_list = [Coords(lat=coordinates[1], lon=coordinates[0]) for coordinates in coordinates_list]

    return coordinates_list


def get_kmz_filter(city, route):
    filter_value = 100
    if city == 'caceres':
        # Caceres
        if route == 1:
            # Route 1
            filter_value = 100
    elif city == 'madrid':
        # Madrid
        if route == 1:
            # Route 1
            filter_value = 45

    # TODO Add the remaining routes filter
    return filter_value
