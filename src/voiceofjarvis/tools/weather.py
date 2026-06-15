"""Weather via Open-Meteo — free, no API key needed."""

import logging

import requests

log = logging.getLogger(__name__)

# Default location — Bangkok
DEFAULT_LAT = 13.7563
DEFAULT_LON = 100.5018
DEFAULT_CITY = "Bangkok"


def get_weather(city: str | None = None) -> str | None:
    try:
        lat, lon, name = _resolve_location(city)
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={  # type: ignore[arg-type]  # requests stubs over-constrain mixed-type params
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=6,
        )
        data = r.json().get("current", {})
        temp = data.get("temperature_2m")
        humidity = data.get("relative_humidity_2m")
        wind = data.get("wind_speed_10m")
        condition = _wmo_to_text(data.get("weather_code", 0))
        return f"{name}: {condition}, {temp}°C, humidity {humidity}%, wind {wind} km/h"
    except Exception as e:
        log.warning(f"Weather fetch failed: {e}")
        return None


def _resolve_location(city: str | None) -> tuple[float, float, str]:
    if not city:
        return DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},  # type: ignore[arg-type]
            timeout=5,
        )
        results = r.json().get("results", [])
        if results:
            loc = results[0]
            return loc["latitude"], loc["longitude"], loc["name"]
    except Exception:
        pass
    return DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY


def _wmo_to_text(code: int) -> str:
    table = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 61: "Light rain",
        63: "Moderate rain", 65: "Heavy rain", 71: "Light snow", 80: "Rain showers",
        95: "Thunderstorm",
    }
    for k in sorted(table.keys(), reverse=True):
        if code >= k:
            return table[k]
    return "Unknown"
