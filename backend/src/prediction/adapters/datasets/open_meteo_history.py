import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pandas as pd

from src.prediction.ports.weather_history import WeatherHistoryPort, WeatherHistoryUnavailable

URL = "https://api.open-meteo.com/v1/forecast"

# Même chef-lieu par région que le frontend (types/api.ts) : (latitude, longitude)
REGION_COORDS: dict[str, tuple[float, float]] = {
    "Île-de-France": (48.8566, 2.3522),
    "Auvergne-Rhône-Alpes": (45.7640, 4.8357),
    "Bourgogne-Franche-Comté": (47.3220, 5.0415),
    "Bretagne": (48.1173, -1.6778),
    "Centre-Val de Loire": (47.9029, 1.9039),
    "Corse": (41.9192, 8.7386),
    "Grand Est": (48.5734, 7.7521),
    "Hauts-de-France": (50.6292, 3.0573),
    "Normandie": (49.4432, 1.0993),
    "Nouvelle-Aquitaine": (44.8378, -0.5792),
    "Occitanie": (43.6047, 1.4442),
    "Pays de la Loire": (47.2184, -1.5536),
    "Provence-Alpes-Côte d'Azur": (43.2965, 5.3698),
}


class OpenMeteoWeatherHistory(WeatherHistoryPort):
    """Météo horaire des `past_days` derniers jours, lue sur Open-Meteo (13 requêtes en parallèle, une par région).

    Mêmes variables et mêmes unités que le jeu d'entraînement (température en °C, vent en km/h, humidité en %), en UTC.
    Le résultat est gardé en mémoire `ttl_seconds` : une analyse sur 7 jours ne télécharge la météo qu'une fois.
    """

    def __init__(self, past_days: int = 45, ttl_seconds: int = 3600):
        self.past_days = past_days
        self.ttl_seconds = ttl_seconds
        self._cached: pd.DataFrame | None = None
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    def hourly(self) -> pd.DataFrame:
        with self._lock:
            if self._cached is None or time.monotonic() - self._fetched_at > self.ttl_seconds:
                try:
                    self._cached = self._fetch()
                    self._fetched_at = time.monotonic()
                except WeatherHistoryUnavailable:
                    if self._cached is None:
                        raise   # rien d'ancien à rendre : l'appelant continue sans correction du biais
                    self._fetched_at = time.monotonic() - self.ttl_seconds + 300   # on garde l'ancienne météo, nouvel essai dans 5 min
            return self._cached

    def _fetch_region(self, client: httpx.Client, region: str, lat: float, lon: float) -> pd.DataFrame:
        params = {
            "latitude": lat, "longitude": lon,
            "hourly": "temperature_2m,wind_speed_10m,relative_humidity_2m",
            "past_days": self.past_days, "forecast_days": 1,
            "wind_speed_unit": "kmh", "timezone": "UTC",
        }
        # Open-Meteo limite le débit : une requête refusée (429) est retentée après une courte pause
        for attempt in range(4):
            response = client.get(URL, params=params)
            if response.status_code != 429:
                break
            time.sleep(1.5 * (attempt + 1))
        if response.status_code != 200:
            raise WeatherHistoryUnavailable(f"Open-Meteo HTTP {response.status_code} ({region})")
        hourly = response.json()["hourly"]
        frame = pd.DataFrame({
            f"temperature_{region}": hourly["temperature_2m"],
            f"wind_speed_{region}": hourly["wind_speed_10m"],
            f"humidity_{region}": hourly["relative_humidity_2m"],
        }, index=pd.DatetimeIndex(pd.to_datetime(hourly["time"])))
        return frame

    def _fetch(self) -> pd.DataFrame:
        try:
            with httpx.Client(timeout=30) as client, ThreadPoolExecutor(max_workers=3) as pool:
                frames = list(pool.map(lambda item: self._fetch_region(client, item[0], *item[1]), REGION_COORDS.items()))
        except httpx.HTTPError as error:
            raise WeatherHistoryUnavailable(f"Open-Meteo injoignable : {error}") from error
        return pd.concat(frames, axis=1).sort_index().dropna()
