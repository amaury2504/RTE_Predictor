"""Prévision par un modèle de fondation de séries temporelles (zéro entraînement), module pur.

Un modèle de fondation (Timestral, Chronos, TimesFM...) lit une fenêtre d'historique et prévoit la suite sans
être entraîné sur nos données. Ici, il est utilisé jour par jour, avec la même hypothèse que la piste B
(domain/level.py) : les consommations d'un jour D sont prévues avec les données connues jusqu'à D - 2 à 00h UTC.
Chaque heure du jour D est donc prévue avec un retard d'au moins 48 h (de 48 h pour 00h à 71 h pour 23h).

Le modèle est reçu par injection : n'importe quel objet qui a une méthode
`forecast(context, prediction_length, known_covariates=None)` renvoyant un objet avec `.median` de forme
(séries, variables, horizon). Cela permet de le tester sans télécharger de poids.
"""
from typing import Protocol, Sequence

import numpy as np
import pandas as pd

DELAY_HOURS = 48
DAY_HOURS = 24
HORIZON = DELAY_HOURS + DAY_HOURS - 1       # 71 pas après l'origine : de +48 h (00h du jour D) à +71 h (23h)


class Forecaster(Protocol):
    def forecast(self, context, prediction_length: int, known_covariates=None): ...


def foundation_forecasts(
    forecaster: Forecaster,
    utc_index: pd.DatetimeIndex,
    actual: np.ndarray,
    target_days: Sequence[pd.Timestamp],
    context_hours: int = 1344,
    covariates: np.ndarray | None = None,
    batch_size: int = 32,
    min_observed: float = 0.5,
) -> np.ndarray:
    """Prévision de chaque heure des jours cibles, alignée sur `utc_index` (NaN ailleurs).

    Args:
        utc_index: horodatages UTC uniques des points (ordre quelconque).
        actual: consommation en GW alignée sur `utc_index`.
        target_days: jours (UTC) à prévoir.
        context_hours: longueur de l'historique donné au modèle (1344 h = 8 semaines, fixé a priori).
        covariates: tableau (lignes, variables) aligné sur `utc_index`, connu à l'avance (ex. température
            observée, utilisée comme prévision parfaite de la météo, comme pour les autres modèles).
        min_observed: part minimale d'heures connues dans l'historique ; sinon le jour est ignoré.
    """
    series = pd.Series(np.asarray(actual, dtype=float), index=utc_index)
    if series.index.has_duplicates:
        raise ValueError("Les horodatages UTC doivent être uniques")
    grid = pd.date_range(series.index.min(), series.index.max(), freq="h")
    y = series.reindex(grid).to_numpy()
    n = len(grid)

    cov = None
    if covariates is not None:
        cov_frame = pd.DataFrame(np.asarray(covariates, dtype=float), index=utc_index).reindex(grid)
        cov = cov_frame.to_numpy().T                     # (variables, temps)

    forecast_grid = np.full(n, np.nan)
    jobs: list[tuple[int, np.ndarray, np.ndarray | None]] = []
    for day in target_days:
        origin_time = pd.Timestamp(day).normalize() - pd.Timedelta(hours=DELAY_HOURS)
        if origin_time not in grid:
            continue
        origin = int(grid.get_loc(origin_time))
        start = origin - context_hours + 1
        if start < 0:
            continue
        context = y[start: origin + 1]
        if np.isfinite(context).mean() < min_observed:
            continue
        known = None
        if cov is not None:
            window = np.full((cov.shape[0], context_hours + HORIZON), np.nan)
            stop = min(origin + HORIZON + 1, n)
            window[:, : stop - start] = cov[:, start:stop]
            known = window
        jobs.append((origin, context, known))

    for i in range(0, len(jobs), batch_size):
        batch = jobs[i: i + batch_size]
        context = np.stack([c for _, c, _ in batch])[:, None, :]            # (B, 1, T)
        known = np.stack([k for _, _, k in batch]) if cov is not None else None
        kwargs = {"known_covariates": known} if known is not None else {}
        median = np.asarray(forecaster.forecast(context, prediction_length=HORIZON, **kwargs).median)
        for (origin, _, _), values in zip(batch, median[:, 0, :]):
            first = origin + DELAY_HOURS
            for hour in range(DAY_HOURS):
                if first + hour < n:
                    forecast_grid[first + hour] = values[DELAY_HOURS - 1 + hour]   # pas k=48+hour -> position k-1

    return pd.Series(forecast_grid, index=grid).reindex(utc_index).to_numpy()
