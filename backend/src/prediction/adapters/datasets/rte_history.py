import threading
import time
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd

from src.prediction.ports.consumption_history import ConsumptionHistoryPort, ConsumptionHistoryUnavailable

URL = "https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets/eco2mix-national-tr/exports/json"


class RteConsumptionHistory(ConsumptionHistoryPort):
    """Consommation horaire des dernières semaines, lue sur l'open data RTE (eco2mix temps réel, ~2 mois d'historique).

    Le résultat est gardé en mémoire `ttl_seconds` : une analyse sur 7 jours ne télécharge l'historique qu'une fois.
    """

    def __init__(self, hours: int = 1700, ttl_seconds: int = 1800):
        self.hours = hours
        self.ttl_seconds = ttl_seconds
        self._cached: pd.Series | None = None
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    def hourly_gw(self) -> pd.Series:
        with self._lock:
            if self._cached is None or time.monotonic() - self._fetched_at > self.ttl_seconds:
                self._cached = self._fetch()
                self._fetched_at = time.monotonic()
            return self._cached

    def _fetch(self) -> pd.Series:
        start = datetime.now(timezone.utc) - timedelta(hours=self.hours)
        params = {
            "select": "date_heure,consommation",
            "order_by": "date_heure asc",
            "where": f'date_heure >= "{start:%Y-%m-%dT%H:%M:%SZ}" AND consommation is not null AND minute(date_heure)=0',
        }
        try:
            response = httpx.get(URL, params=params, timeout=60, verify=False, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
        except httpx.HTTPError as error:
            raise ConsumptionHistoryUnavailable(f"RTE connexion impossible : {error}") from error
        if response.status_code != 200:
            raise ConsumptionHistoryUnavailable(f"RTE HTTP {response.status_code}")
        records = response.json()
        if not records:
            raise ConsumptionHistoryUnavailable("RTE n'a renvoyé aucune consommation récente")
        index = pd.DatetimeIndex([pd.Timestamp(r["date_heure"]).tz_convert("UTC").tz_localize(None) for r in records])
        series = pd.Series([r["consommation"] / 1000 for r in records], index=index).sort_index()
        return series[~series.index.duplicated()]
