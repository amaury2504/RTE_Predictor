from abc import ABC, abstractmethod

import pandas as pd


class WeatherHistoryUnavailable(Exception):
    """La météo passée n'a pas pu être obtenue."""


class WeatherHistoryPort(ABC):
    """Météo horaire des dernières semaines, pour mesurer l'erreur récente d'un modèle (correction du biais)."""

    @abstractmethod
    def hourly(self) -> pd.DataFrame:
        """Une ligne par heure UTC (index sans fuseau, trié), colonnes `temperature_<région>`, `wind_speed_<région>`
        et `humidity_<région>`, comme les entrées de l'API de prédiction.

        Raises:
            WeatherHistoryUnavailable: si la source est injoignable ou incomplète.
        """
