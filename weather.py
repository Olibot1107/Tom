import json
import threading
import time
from urllib.request import urlopen
from urllib.parse import urlencode
from config_state import get_config

WEATHER_CODES = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm hail",
    99: "Thunderstorm hail",
}


class WeatherProvider:
    def __init__(self):
        self._lock = threading.Lock()
        self._summary = "Weather: --"
        self._last_update = 0
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _set_summary(self, text):
        with self._lock:
            self._summary = text

    def get_summary(self):
        with self._lock:
            return self._summary

    def _run(self):
        while not self._stop.is_set():
            cfg = get_config()
            weather_cfg = cfg["weather"]

            if not weather_cfg.get("enabled", True):
                self._set_summary("Weather: off")
                time.sleep(5)
                continue

            now = time.time()
            if now - self._last_update >= weather_cfg.get("refresh_s", 300):
                summary = self._fetch_weather(weather_cfg)
                self._set_summary(summary)
                self._last_update = now

            time.sleep(5)

    def _fetch_weather(self, weather_cfg):
        try:
            lat = weather_cfg.get("latitude")
            lon = weather_cfg.get("longitude")
            units = weather_cfg.get("units", "imperial")

            temp_unit = "fahrenheit" if units == "imperial" else "celsius"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "temperature_unit": temp_unit,
                "timezone": "auto",
            }
            url = f"https://api.open-meteo.com/v1/forecast?{urlencode(params)}"

            with urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            temp = None
            code = None

            if "current_weather" in data:
                temp = data["current_weather"].get("temperature")
                code = data["current_weather"].get("weathercode")
            elif "current" in data:
                temp = data["current"].get("temperature_2m")
                code = data["current"].get("weather_code")

            if temp is None:
                return "Weather: --"

            unit_symbol = "°F" if units == "imperial" else "°C"
            desc = WEATHER_CODES.get(code, "Weather")
            return f"{temp:.0f}{unit_symbol} {desc}"
        except Exception:
            return "Weather: --"
