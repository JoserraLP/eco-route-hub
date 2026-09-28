"""
OpenWeatherAPI plugin implementation for ambient weather provider.

Fetches weather telemetry (ambient temperature in °C and pressure in Pa)
concurrently for sampled route coordinates and interpolates across the full route geometry.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp
import numpy as np

try:
    import polyline
except ImportError:
    polyline = None

from eco_route_hub.domain.graph_models import Coords
from eco_route_hub.interfaces.ambient_weather_provider import (
    AmbientWeatherInformationProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENWEATHER_API_URL: str = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_WEATHER_ATTRIBUTES: List[str] = ["temp", "pressure"]
DEFAULT_SAMPLE_STEP: int = 50  # Fetch weather every 50 route points by default


class OpenWeatherAPI(AmbientWeatherInformationProvider):
    """
    OpenWeatherMap API implementation for fetching ambient weather telemetry.

    Attributes:
        api_key (Optional[str]): OpenWeatherMap API authentication key.
        max_concurrency (int): Maximum concurrent HTTP requests allowed.
        sample_step (int): Index interval to sample weather points along the route.
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
        self.sample_step: int = config.get("sample_step", DEFAULT_SAMPLE_STEP)

    async def _get_weather_telemetry_point(
        self,
        session: aiohttp.ClientSession,
        coords: Coords,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Dict[str, float]]:
        """Fetch current temperature (°C) and pressure (Pa) for a single coordinate point asynchronously."""
        params = {
            "lat": coords.lat,
            "lon": coords.lon,
            "appid": self.api_key,
            "units": "metric",  # Temperature in °C
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
                    main = data.get("main", {})

                    result = {}

                    # 1. Temperature in °C
                    if "temp" in main:
                        result["temp"] = float(main["temp"])

                    # 2. Pressure in Pa (1 hPa = 100 Pa)
                    hpa = main.get("grnd_level") or main.get("pressure")
                    if hpa is not None:
                        result["pressure"] = float(hpa) * 100.0

                    return result

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

    async def _get_weather_telemetry_async(
        self, coordinates: List[Coords]
    ) -> List[Optional[Dict[str, float]]]:
        """Fetch weather telemetry for multiple coordinates concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrency)
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._get_weather_telemetry_point(session, coords, semaphore)
                for coords in coordinates
            ]
            return list(await asyncio.gather(*tasks))

    def _fetch_weather_telemetry_sync(
        self, coordinates: List[Coords]
    ) -> List[Optional[Dict[str, float]]]:
        """Synchronous wrapper executing async weather collection."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(
                self._get_weather_telemetry_async(coordinates)
            )
        else:
            return asyncio.run(self._get_weather_telemetry_async(coordinates))

    def retrieve_ambient_weather_info(
        self, route_coordinates: List[Coords]
    ) -> Dict[str, Any]:
        """
        Retrieve weather metrics (temperature in °C, pressure in Pa) for route coordinates,
        sampling key points and linearly interpolating values to match full route length.

        Args:
            route_coordinates (List[Coords]): Full sequence of N route coordinates.

        Returns:
            Dict[str, Any]: Interpolated weather attributes mapped to all N coordinates.
        """
        self.ambient_weather_information = {
            "coordinates": route_coordinates,
        }

        n_points = len(route_coordinates)
        if n_points == 0:
            if "temp" in self.ambient_weather_attributes:
                self.ambient_weather_information["temp"] = []
            if "pressure" in self.ambient_weather_attributes:
                self.ambient_weather_information["pressure"] = []
            return self.ambient_weather_information

        # 1. Generate sample indices along route (e.g., [0, 50, 100, ..., N-1])
        step = max(1, self.sample_step)
        sample_indices = list(range(0, n_points, step))
        if (n_points - 1) not in sample_indices:
            sample_indices.append(n_points - 1)

        # 2. Extract sampled coordinates and query API concurrently
        sampled_coordinates = [route_coordinates[i] for i in sample_indices]
        sampled_telemetry = self._fetch_weather_telemetry_sync(sampled_coordinates)

        full_indices = np.arange(n_points)

        # 3. Process and interpolate Temperature
        if "temp" in self.ambient_weather_attributes:
            raw_temps = [
                t.get("temp") if t else None for t in sampled_telemetry
            ]
            # Fill missing/failed API calls with ISA default (15°C) before interpolating
            clean_temps = [
                val if val is not None else 15.0 for val in raw_temps
            ]

            # Interpolate linearly across all N points
            interpolated_temps = np.interp(full_indices, sample_indices, clean_temps)
            self.ambient_weather_information["temp"] = interpolated_temps.tolist()

        # 4. Process and interpolate Pressure
        if "pressure" in self.ambient_weather_attributes:
            raw_pressures = [
                p.get("pressure") if p else None for p in sampled_telemetry
            ]
            # Fill missing/failed API calls with ISA default (101325 Pa) before interpolating
            clean_pressures = [
                val if val is not None else 101325.0 for val in raw_pressures
            ]

            # Interpolate linearly across all N points
            interpolated_pressures = np.interp(full_indices, sample_indices, clean_pressures)
            self.ambient_weather_information["pressure"] = interpolated_pressures.tolist()

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