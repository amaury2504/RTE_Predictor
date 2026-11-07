import numpy as np
import pandas as pd


MAX_GAP_HOURS = 3


def extend_history(history: pd.Series, last: pd.Timestamp) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Historique sur une grille horaire complète, prolongée jusqu'à `last` par des heures inconnues (NaN).

    Les heures à prévoir (au-delà de la dernière consommation publiée) doivent TOUTES être sur la grille : les
    prévisions et les variables de niveau sont lues à ces horodatages.

    Un trou de `MAX_GAP_HOURS` heures au plus à l'intérieur de l'historique (heure absente de la source) est comblé par
    interpolation : sinon une seule heure manquante invaliderait les retards de 48 h et de 168 h de deux heures futures.
    Les trous plus longs, et les heures après la dernière publiée, restent inconnus (NaN).
    """
    grid = pd.date_range(history.index.min(), max(history.index.max(), last), freq="h")
    filled = history.reindex(grid).interpolate(limit=MAX_GAP_HOURS, limit_area="inside")
    return grid, filled.to_numpy(dtype=float)
