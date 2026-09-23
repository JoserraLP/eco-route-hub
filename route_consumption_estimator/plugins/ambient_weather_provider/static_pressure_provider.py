"""
Configurable ambient weather provider implementation.

Provides constant or default atmospheric telemetry (pressure in Pa, temperature in °C)
for route coordinates without making external API requests. Useful for testing,
sensitivity analyses, and offline benchmarking.
"""

import logging
from typing import Any, Dict, List

try:
    import polyline
except ImportError:
    polyline = None

from route_consumption_estimator.domain.graph_models import Coords
from route_consumption_estimator.interfaces.ambient_weather_provider import (
    AmbientWeatherInformationProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_PRESSURE_PA: float = 101325.0  # Standard sea-level pressure (1 atm)
DEFAULT_TEMPERATURE_CELSIUS: float = 15.0  # Standard ambient temperature (15°C)
DEFAULT_WEATHER_ATTRIBUTES: List[str] = ["temp", "pressure"]


class StaticPressureProvider(AmbientWeatherInformationProvider):
    """
    Static weather provider that returns user-configured ambient pressure and temperature.

    Config parameters:
        pressure_pa (float): Atmospheric pressure in Pascals (default: 101325.0 Pa).
        pressure_hpa (float, optional): Alternative pressure input in hPa/mbar (converted to Pa).
        temperature_celsius (float): Ambient temperature in °C (default: 15.0 °C).
        ambient_weather_attributes (List[str]): Weather fields to retrieve (default: ["temp", "pressure"]).
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        endpoint = config.get("endpoint", "static://ambient_weather")
        super().__init__(endpoint=endpoint)

        self.ambient_weather_attributes: List[str] = config.get(
            "ambient_weather_attributes", DEFAULT_WEATHER_ATTRIBUTES
        )

        # Allow setting pressure either directly in Pa or conveniently in hPa
        if "pressure_hpa" in config:
            self.pressure_pa: float = float(config["pressure_hpa"]) * 100.0
        else:
            self.pressure_pa: float = float(
                config.get("pressure_pa", DEFAULT_PRESSURE_PA)
            )

        self.temperature_celsius: float = float(
            config.get("temperature_celsius", DEFAULT_TEMPERATURE_CELSIUS)
        )

    def retrieve_ambient_weather_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Generate constant atmospheric telemetry arrays matching the length of route coordinates.

        Args:
            route_coordinates (List[Coords]): Sequence of route coordinates.

        Returns:
            Dict[str, Any]: Dictionary containing telemetry lists of length N.
        """
        n_points = len(route_coordinates)

        self.ambient_weather_information = {
            "coordinates": route_coordinates,
        }

        if "temp" in self.ambient_weather_attributes:
            self.ambient_weather_information["temp"] = [
                self.temperature_celsius
            ] * n_points

        if "pressure" in self.ambient_weather_attributes:
            self.ambient_weather_information["pressure"] = [
                self.pressure_pa
            ] * n_points

        return self.ambient_weather_information

    def retrieve_ambient_weather_info_by_polyline(
        self, encoded_polyline: str
    ) -> Dict[str, Any]:
        """
        Retrieve weather info by decoding polyline.

        Args:
            encoded_polyline (str): Encoded polyline string representing path geometry.

        Returns:
            Dict[str, Any]: Weather attributes mapped along decoded route coordinates.
        """
        if polyline is None:
            raise ImportError(
                "The 'polyline' library is required to decode polylines. "
                "Install it using 'pip install polyline'."
            )

        decoded_points = polyline.decode(encoded_polyline)
        route_coordinates = [
            Coords(lat=lat, lon=lon) for lat, lon in decoded_points
        ]
        return self.retrieve_ambient_weather_info(route_coordinates)
