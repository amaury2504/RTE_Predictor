"""Correction du biais récent d'un modèle (module pur).

Idée : si un modèle se trompe depuis quelques semaines dans le même sens (changement de niveau de la
consommation), on ajoute à ses prédictions la moyenne de ses erreurs récentes. Contrairement à un
décalage fixe, la correction suit le niveau quand il change.

Sans fuite : la correction d'un jour D n'utilise que des jours <= D - delay_days, c'est-à-dire des
consommations déjà connues au moment de prévoir D (voir DECISIONS.md).
"""
from typing import Sequence

import numpy as np
import pandas as pd


def rolling_bias_correction(
    timestamps: Sequence[str],
    predicted: Sequence[float],
    actual: Sequence[float],
    window_days: int = 28,
    delay_days: int = 2,
    min_days: int = 7,
) -> np.ndarray:
    """Terme à ajouter à chaque prédiction : moyenne des erreurs (réel - prédit) journalières récentes.

    Args:
        timestamps: horodatages locaux "YYYY-MM-DDTHH:00", un par point (ordre quelconque).
        predicted, actual: puissances en GW, alignées sur `timestamps`.
        window_days: longueur de la fenêtre de jours utilisée pour estimer le biais.
        delay_days: décalage entre le jour à corriger D et le dernier jour utilisé (D - delay_days).
        min_days: nombre minimal de jours disponibles dans la fenêtre ; sinon, aucune correction (0).

    Returns:
        Un tableau de la même longueur que `timestamps`. Les jours sans assez d'historique valent 0.
    """
    if window_days < 1 or delay_days < 0 or min_days < 1:
        raise ValueError("window_days et min_days doivent être >= 1, delay_days >= 0")
    days = pd.DatetimeIndex(pd.to_datetime([str(t)[:10] for t in timestamps]))
    residual = pd.Series(np.asarray(actual, dtype=float) - np.asarray(predicted, dtype=float), index=days)
    daily = residual.groupby(level=0).mean()
    grid = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(grid)
    correction = daily.rolling(window_days, min_periods=min_days).mean().shift(delay_days).fillna(0.0)
    return correction.reindex(days).to_numpy()
