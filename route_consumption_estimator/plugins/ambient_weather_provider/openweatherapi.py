"""
OpenWeatherAPI plugin implementation for ambient weather provider.

Fetches weather telemetry (e.g., ambient temperature) concurrently for route 
coordinates using OpenWeatherMap API and aiohttp.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp

try:
    import polyline
except ImportError:
    polyline = None

from route_consumption_estimator.domain.graph_models import Coords
from route_consumption_estimator.interfaces.ambient_weather_provider import (
    AmbientWeatherInformationProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENWEATHER_API_URL: str = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_WEATHER_ATTRIBUTES: List[str] = ["temp"]


class OpenWeatherAPI(AmbientWeatherInformationProvider):
    """
    OpenWeatherMap API implementation for fetching ambient weather telemetry.

    Attributes:
        api_key (Optional[str]): OpenWeatherMap API authentication key.
        max_concurrency (int): Maximum concurrent HTTP requests allowed.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        endpoint = config.get("endpoint", DEFAULT_OPENWEATHER_API_URL)
        super().__init__(endpoint=endpoint)

        self.api_key: Optional[str] = config.get("api_key") or os.environ.get(
            "OPENWEATHER_API_KEY"
        )
        self.ambient_weather_attributes: List[str] = config.get(
            "ambient_weather_attributes", DEFAULT_WEATHER_ATTRIBUTES
        )
        self.max_concurrency: int = config.get("max_concurrency", 10)

    async def _get_temperature(
        self,
        session: aiohttp.ClientSession,
        coords: Coords,
        semaphore: asyncio.Semaphore,
    ) -> Optional[float]:
        """Fetch current temperature for a single coordinate point asynchronously."""
        params = {
            "lat": coords.lat,
            "lon": coords.lon,
            "appid": self.api_key,
            "units": "metric",
        }

        async with semaphore:
            try:
                async with session.get(self.endpoint, params=params) as response:
                    if response.status != 200:
                        logger.warning(
                            f"OpenWeatherAPI status {response.status} for coords "
                            f"({coords.lat}, {coords.lon})"
                        )
                        return None

                    data = await response.json()
                    return data.get("main", {}).get("temp")

            except aiohttp.ClientError as e:
                logger.error(
                    f"Connection error requesting weather for ({coords.lat}, {coords.lon}): {e}"
                )
                return None
            except Exception as e:
                logger.error(
                    f"Unexpected error parsing weather for ({coords.lat}, {coords.lon}): {e}"
                )
                return None

    async def _get_temperatures_async(
        self, coordinates: List[Coords]
    ) -> List[Optional[float]]:
        """Fetch temperatures for multiple coordinates concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrency)
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._get_temperature(session, coords, semaphore)
                for coords in coordinates
            ]
            return list(await asyncio.gather(*tasks))

    def _fetch_temperatures_sync(
        self, coordinates: List[Coords]
    ) -> List[Optional[float]]:
        """Synchronous wrapper executing async temperature collection."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(
                self._get_temperatures_async(coordinates)
            )
        else:
            return asyncio.run(self._get_temperatures_async(coordinates))

    def retrieve_ambient_weather_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Retrieve weather metrics for a list of route coordinates.

        Args:
            route_coordinates (List[Coords]): Sequence of route coordinates.

        Returns:
            Dict[str, Any]: Weather attributes mapped along coordinates.
        """
        self.ambient_weather_information = {
            "coordinates": route_coordinates,
        }

        if "temp" in self.ambient_weather_attributes:
            temperatures = self._fetch_temperatures_sync(route_coordinates)
            self.ambient_weather_information["temp"] = temperatures

        return self.ambient_weather_information

    def retrieve_ambient_weather_info_by_polyline(
        self, encoded_polyline: str
    ) -> Dict[str, Any]:
        """
        Retrieve ambient weather info by decoding an encoded polyline string.

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
