import asyncio
import os
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import aiohttp

from route_consumption_estimator.domain.graph_models import Coords
from route_consumption_estimator.interfaces import AmbientWeatherInformationProvider

OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")


async def get_temperature(
        session: aiohttp.ClientSession,
        coords: Coords,
        semaphore: asyncio.Semaphore,
) -> float:
    """
    Get the current temperature for a coordinate.
    """

    params = {
        "lat": coords.lat,
        "lon": coords.lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }

    async with semaphore:
        try:
            async with session.get(OPENWEATHER_API_URL, params=params) as response:
                if response.status != 200:
                    print(
                        f"Error {response.status} "
                        f"para {coords.lat}, {coords.lon}"
                    )
                    return None

                data = await response.json()

                return data["main"]["temp"]

        except aiohttp.ClientError as e:
            print(
                f"Error de conexión para "
                f"{coords.lat}, {coords.lon}: {e}"
            )
            return None


async def get_temperatures(
        coordinates: List[Coords],
        max_concurrency: int = 10,
) -> List[float]:
    """
    Get temperatures for many coordinates concurrently.
    """

    # Limita el número de peticiones simultáneas
    semaphore = asyncio.Semaphore(max_concurrency)

    # Reutilizamos una única conexión HTTP
    async with aiohttp.ClientSession() as session:
        tasks = [
            get_temperature(
                session,
                coords,
                semaphore,
            )
            for coords in coordinates
        ]

        return await asyncio.gather(*tasks)


def fetch_temperatures(
        coordinates: List[Coords],
        max_concurrency: int = 10,
) -> List[float]:
    """
    Synchronous wrapper.
    """
    return asyncio.run(
        get_temperatures(
            coordinates,
            max_concurrency,
        )
    )

OPENWEATHER_ATTRIBUTES = ["temp"]
class OpenWeatherAPI(AmbientWeatherInformationProvider):

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config.get("endpoint", OPENWEATHER_API_URL))
        self._ambient_weather_attributes = config.get("ambient_weather_attributes", OPENWEATHER_ATTRIBUTES)

    def retrieve_ambient_weather_info(self, route_coordinates: list[Coords]) -> list:
        """
        Retrieve extra info values of the input route coordinates

        :param route_coordinates: input route coordinates
        :type route_coordinates: list[Coords]
        :return: list with associated extra road info
        :rtype: list
        """
        self.ambient_weather_information = {
                                     "coordinates": route_coordinates,
        }

        if 'temp' in self._ambient_weather_attributes:
            self.ambient_weather_information.update({"temp": fetch_temperatures(coordinates=route_coordinates)})

        return self.ambient_weather_information

    def retrieve_ambient_weather_info_by_polyline(self, encoded_polyline: str) -> dict:
        pass
