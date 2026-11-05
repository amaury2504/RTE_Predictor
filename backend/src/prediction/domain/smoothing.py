"""Lissage exponentiel saisonnier de type Holt-Winters (module pur).

Modèle de série temporelle : il n'utilise que la consommation passée, ni la météo ni le calendrier.
Niveau et profil hebdomadaire (une valeur par heure de la semaine, 168 au total) sont mis à jour
heure après heure par correction exponentielle de l'erreur :

    e_i      = y_i - (niveau_{i-1} + saison[h_i])
    niveau_i = niveau_{i-1} + alpha * e_i
    saison[h_i] += gamma * (1 - alpha) * e_i

Même hypothèse de prévision que la piste B (domain/level.py) : la prévision de l'heure t n'utilise que
les consommations connues jusqu'à t - delay_hours. Les heures absentes ne mettent rien à jour.
"""
import numpy as np
import pandas as pd

PERIOD_HOURS = 168
DELAY_HOURS = 48


def holt_winters_forecasts(
    utc_index: pd.DatetimeIndex,
    actual: np.ndarray,
    alpha: float,
    gamma: float,
    delay_hours: int = DELAY_HOURS,
    period: int = PERIOD_HOURS,
) -> np.ndarray:
    """Prévision de chaque point de `utc_index` (même ordre, ordre quelconque), en GW ; NaN sans historique.

    Args:
        alpha: vitesse d'adaptation du niveau (0 à 1) ; grand = suit vite un changement de niveau.
        gamma: vitesse d'adaptation du profil hebdomadaire (0 à 1).
    """
    if not (0 < alpha < 1 and 0 < gamma < 1):
        raise ValueError("alpha et gamma doivent être strictement compris entre 0 et 1")
    series = pd.Series(np.asarray(actual, dtype=float), index=utc_index)
    if series.index.has_duplicates:
        raise ValueError("Les horodatages UTC doivent être uniques")
    grid = pd.date_range(series.index.min(), series.index.max(), freq="h")
    y = series.reindex(grid).to_numpy()
    n = len(y)

    forecast = np.full(n, np.nan)
    season = np.zeros(period)
    level = None
    for i in range(n):
        if np.isnan(y[i]):
            pass                                  # heure absente : aucune mise à jour
        elif level is None:
            level = y[i]                          # initialisation sur la première valeur connue
        else:
            error = y[i] - (level + season[i % period])
            level += alpha * error
            season[i % period] += gamma * (1 - alpha) * error
        target = i + delay_hours
        if level is not None and target < n:
            forecast[target] = level + season[target % period]

    # Les premières semaines (profil non appris) ne sont pas fiables : pas de prévision avant une période pleine
    forecast[: delay_hours + period] = np.nan
    return pd.Series(forecast, index=grid).reindex(utc_index).to_numpy()
