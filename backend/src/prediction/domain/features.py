"""Construction des variables d'entrée (features), COMMUNE à l'entraînement, au benchmark et à l'API.

Un seul code pour tous : c'est la condition pour que les modèles soient comparés sur les mêmes
entrées et pour qu'un modèle entraîné reçoive en production exactement ce qu'il a vu à l'entraînement.

Entrée : un DataFrame « brut » avec
    - date : jour UTC au format "JJ/MM/AAAA"
    - hour : heure UTC (0-23)
    - temperature_<région>, wind_speed_<région>, humidity_<région> (une colonne par région)
Sortie : un DataFrame de variables numériques, même index que l'entrée, colonnes dans l'ordre :
    météo brute (ordre de l'entrée), calendrier, heure cyclique, carrés des températures.
"""
import holidays
import numpy as np
import pandas as pd

WEATHER_PREFIXES = ("temperature_", "wind_speed_", "humidity_")


def _is_holiday(dates: pd.Series) -> pd.Series:
    """1 si le jour est férié en France, 0 sinon (calcul par jour distinct, pas par ligne)."""
    fr_holidays = holidays.France()
    days = dates.dt.date
    lookup = {d: int(d in fr_holidays) for d in days.unique()}
    return days.map(lookup)


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Transforme les données brutes en variables d'entrée des modèles."""
    dates = pd.to_datetime(raw["date"], format="%d/%m/%Y")
    weather_cols = [c for c in raw.columns if c.startswith(WEATHER_PREFIXES)]

    features = raw[weather_cols].copy()

    # Calendrier (jour UTC)
    features["month"] = dates.dt.month
    features["dayofweek"] = dates.dt.dayofweek
    features["is_holiday"] = _is_holiday(dates)

    # Heure encodée de façon cyclique (23h est proche de 0h)
    features["hour_sin"] = np.sin(2 * np.pi * raw["hour"] / 24)
    features["hour_cos"] = np.cos(2 * np.pi * raw["hour"] / 24)

    # Carré de chaque température (relation non linéaire chauffage / climatisation)
    for col in weather_cols:
        if col.startswith("temperature_"):
            features[col + "_squared"] = features[col] ** 2

    return features
