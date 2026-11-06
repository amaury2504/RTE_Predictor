from abc import ABC, abstractmethod

import pandas as pd


class ConsumptionHistoryUnavailable(Exception):
    """La consommation passée n'a pas pu être obtenue."""


class ConsumptionHistoryPort(ABC):
    """Historique récent de la consommation nationale, nécessaire aux modèles de séries temporelles."""

    @abstractmethod
    def hourly_gw(self) -> pd.Series:
        """Consommation horaire en GW, indexée par l'heure UTC (sans fuseau), triée. Les heures absentes sont omises.

        Raises:
            ConsumptionHistoryUnavailable: si la source est injoignable ou vide.
        """
