"""Pondération des années récentes.

Dans un contexte où le niveau de consommation dérive (choc de 2022, transition énergétique), les
données anciennes décrivent moins bien le présent. On leur donne un poids qui décroît avec l'âge.
"""
from typing import Sequence

import numpy as np
import pandas as pd

SECONDS_PER_YEAR = 365.25 * 24 * 3600


def recency_weights(timestamps: Sequence[str], reference: str, half_life_years: float) -> np.ndarray:
    """Poids de chaque ligne : 1 à la date de référence, divisé par 2 à chaque demi-vie écoulée.

    Args:
        timestamps: horodatages des lignes (ex. "2019-05-27T14:00").
        reference: date « présente » (ex. début de l'année de test). Une ligne postérieure pèse 1.
        half_life_years: durée au bout de laquelle le poids est divisé par 2.

    Raises:
        ValueError: si la demi-vie n'est pas strictement positive.
    """
    if half_life_years <= 0:
        raise ValueError("La demi-vie doit être strictement positive")
    ts = pd.DatetimeIndex(pd.to_datetime([str(t) for t in timestamps]))
    age_years = (pd.Timestamp(str(reference)) - ts).total_seconds().to_numpy() / SECONDS_PER_YEAR
    return 0.5 ** (np.clip(age_years, 0, None) / half_life_years)
