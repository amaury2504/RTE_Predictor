"""Variables de « niveau récent » de la consommation (piste B), module pur.

Elles décrivent la consommation DÉJÀ CONNUE au moment de prévoir : le modèle peut ainsi suivre un
changement de niveau (voir DECISIONS.md) au lieu de le deviner à partir de la météo.

Hypothèse de prévision (à fixer explicitement, sinon on triche sans le voir) : la prévision de l'heure t
est faite avec les consommations connues jusqu'à t - DELAY_HOURS. Avec 48 h, une prévision du lendemain
faite la veille en milieu de journée n'utilise jamais une valeur qu'elle ne pourrait pas connaître.
"""
import numpy as np
import pandas as pd

DELAY_HOURS = 48

LEVEL_COLUMNS = ("conso_lag_48h", "conso_lag_168h", "conso_mean_7d", "conso_mean_28d")


def build_level_features(utc_index: pd.DatetimeIndex, actual: np.ndarray, delay_hours: int = DELAY_HOURS) -> pd.DataFrame:
    """Variables de niveau récent, une ligne par point de `utc_index` (même ordre, ordre quelconque).

    - conso_lag_48h / conso_lag_168h : consommation à la même heure 2 jours / 7 jours avant
      (le 2e retard est 168 h, déjà plus ancien que le délai)
    - conso_mean_7d / conso_mean_28d : consommation moyenne des 7 / 28 jours qui se terminent
      `delay_hours` avant l'heure à prévoir
    Les valeurs sont NaN quand l'historique manque (début de série, heures absentes).
    """
    series = pd.Series(np.asarray(actual, dtype=float), index=utc_index)
    if series.index.has_duplicates:
        raise ValueError("Les horodatages UTC doivent être uniques")
    grid = pd.date_range(series.index.min(), series.index.max(), freq="h")
    hourly = series.reindex(grid)

    features = pd.DataFrame(index=grid)
    features["conso_lag_48h"] = hourly.shift(delay_hours)
    features["conso_lag_168h"] = hourly.shift(168)
    features["conso_mean_7d"] = hourly.rolling(7 * 24, min_periods=7 * 12).mean().shift(delay_hours)
    features["conso_mean_28d"] = hourly.rolling(28 * 24, min_periods=28 * 12).mean().shift(delay_hours)
    return features.reindex(utc_index).reset_index(drop=True)[list(LEVEL_COLUMNS)]
