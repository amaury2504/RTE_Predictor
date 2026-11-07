"""Prédiction en ligne par des modèles de séries temporelles (Holt-Winters, Timestral).

Ces modèles n'utilisent pas la météo : ils prévoient l'heure demandée à partir de la consommation passée,
connue jusqu'à 48 h avant (même hypothèse que dans le benchmark). L'historique vient d'un `ConsumptionHistoryPort`.
"""
import numpy as np
import pandas as pd

from src.prediction.adapters.ml.history_grid import extend_history
from src.prediction.adapters.ml.raw_input import utc_timestamp
from src.prediction.domain.foundation import DELAY_HOURS, foundation_forecasts
from src.prediction.domain.models_prediction import PredictionInput, PredictionResult
from src.prediction.domain.smoothing import holt_winters_forecasts
from src.prediction.ports.consumption_history import ConsumptionHistoryPort
from src.prediction.ports.predict import PredictionModelPort

# Couple (alpha, gamma) du benchmark (grille de lissage) qui apprend le plus vite le profil hebdomadaire. L'historique
# en ligne ne couvre que ~9 semaines : avec gamma = 0,1 (choix 2023-2024, sur des années d'historique), chaque heure
# de la semaine n'est vue que 9 fois et le profil n'a pas le temps de se former.
HOLT_WINTERS_ALPHA = 0.2
HOLT_WINTERS_GAMMA = 0.3
TIMESTRAL_CONTEXT_HOURS = 1344  # 8 semaines, comme dans le benchmark
MIN_CONTEXT_HOURS = 24 * 14


class ForecastUnavailable(Exception):
    """L'historique ne suffit pas pour prévoir l'heure demandée (trop lointaine, ou historique trop court)."""


def _results(inputs: list[PredictionInput], wanted: list[pd.Timestamp], forecast: pd.Series) -> list[PredictionResult]:
    results = []
    for item, when in zip(inputs, wanted):
        power = forecast.get(when, np.nan)
        if not np.isfinite(power):
            raise ForecastUnavailable(f"Pas de prévision possible pour le {item.date} à {item.hour} h : historique insuffisant")
        results.append(PredictionResult(date=item.date, hour=item.hour, power=float(power)))
    return results


class PredictWithHoltWinters(PredictionModelPort):
    """Lissage exponentiel saisonnier (niveau + profil hebdomadaire), appliqué à la consommation récente."""

    def __init__(self, history: ConsumptionHistoryPort, alpha: float = HOLT_WINTERS_ALPHA, gamma: float = HOLT_WINTERS_GAMMA):
        self.history = history
        self.alpha = alpha
        self.gamma = gamma

    def predict_item(self, input: PredictionInput) -> PredictionResult:
        return self.predict_items([input])[0]

    def predict_items(self, inputs: list[PredictionInput]) -> list[PredictionResult]:
        history = self.history.hourly_gw()
        wanted = [utc_timestamp(i) for i in inputs]
        index, values = extend_history(history, max(wanted))
        forecast = pd.Series(holt_winters_forecasts(index, values, self.alpha, self.gamma), index=index)
        return _results(inputs, wanted, forecast)


class PredictWithTimestral(PredictionModelPort):
    """Timestral (modèle de fondation, aucun entraînement), consommation passée seule.

    Un calcul par jour UTC demandé : une analyse sur 7 jours en fait 8, regroupés en un seul lot.
    `loader` rend le modèle (chargé une fois, au premier appel).
    """

    def __init__(self, history: ConsumptionHistoryPort, loader):
        self.history = history
        self.loader = loader

    def predict_item(self, input: PredictionInput) -> PredictionResult:
        return self.predict_items([input])[0]

    def predict_items(self, inputs: list[PredictionInput]) -> list[PredictionResult]:
        history = self.history.hourly_gw()
        wanted = [utc_timestamp(i) for i in inputs]
        days = sorted({w.normalize() for w in wanted})
        # L'historique disponible (~2 mois) peut être plus court que 8 semaines + délai : on réduit alors la fenêtre
        earliest_origin = days[0] - pd.Timedelta(hours=DELAY_HOURS)
        available = int((earliest_origin - history.index.min()) / pd.Timedelta(hours=1)) + 1
        context_hours = min(TIMESTRAL_CONTEXT_HOURS, available)
        if context_hours < MIN_CONTEXT_HOURS:
            raise ForecastUnavailable("Historique de consommation insuffisant pour Timestral")
        index, values = extend_history(history, max(wanted).normalize() + pd.Timedelta(hours=23))
        forecast = pd.Series(
            foundation_forecasts(self.loader(), index, values, days, context_hours=context_hours), index=index)
        return _results(inputs, wanted, forecast)
