import logging

import numpy as np
import pandas as pd

from src.prediction.adapters.ml.history_grid import extend_history
from src.prediction.adapters.ml.raw_input import raw_row_from_input, utc_timestamp
from src.prediction.domain.bias_correction import rolling_bias_correction
from src.prediction.domain.features import build_features
from src.prediction.domain.level import LEVEL_COLUMNS, build_level_features
from src.prediction.domain.models_prediction import PredictionInput, PredictionResult
from src.prediction.ports.consumption_history import ConsumptionHistoryPort, ConsumptionHistoryUnavailable
from src.prediction.ports.weather_history import WeatherHistoryPort, WeatherHistoryUnavailable
from src.prediction.ports.predict import PredictionModelPort


logger = logging.getLogger(__name__)

PARIS = "Europe/Paris"


class LevelUnavailable(Exception):
    """La consommation récente ne suffit pas pour calculer les variables de niveau de l'heure demandée."""


class PredictWithRegressor(PredictionModelPort):
    """Prédiction en ligne avec un modèle du benchmark déjà entraîné (LightGBM, Ridge, MLP).

    `regressor` est un `RegressorPort` entraîné : il connaît l'ordre de ses colonnes.

    Avec `history`, le modèle est celui de la piste B : en plus de la météo et du calendrier, il reçoit le niveau récent
    de la consommation (retards et moyennes, voir domain/level.py), calculé comme à l'entraînement avec une
    consommation connue jusqu'à 48 h avant l'heure prévue. C'est ce qui lui permet de suivre un changement de niveau
    de la consommation au lieu de le deviner à partir de la météo (les modèles bruts surestimaient de 2 à 3 GW).

    Avec en plus `weather`, la correction du biais récent du benchmark est appliquée : on prédit les dernières semaines
    (météo passée, consommation déjà publiée), on mesure l'erreur moyenne du modèle, et on l'ajoute aux prédictions
    (domain/bias_correction.py : fenêtre de 28 jours, qui s'arrête 2 jours avant le jour prévu). Sans météo passée
    disponible, la prédiction est rendue sans correction.
    """

    def __init__(self, regressor, history: ConsumptionHistoryPort | None = None, weather: WeatherHistoryPort | None = None):
        self.regressor = regressor
        self.history = history
        self.weather = weather

    def predict_item(self, input: PredictionInput) -> PredictionResult:
        return self.predict_items([input])[0]

    def predict_items(self, inputs: list[PredictionInput]) -> list[PredictionResult]:
        features = build_features(pd.DataFrame([raw_row_from_input(i) for i in inputs]))
        if self.history is not None:
            features = pd.concat([features, self._level(inputs)], axis=1)
        # Un seul appel au modèle pour tout le lot
        powers = np.asarray(self.regressor.predict(features), dtype=float)
        if self.history is not None and self.weather is not None:
            powers = powers + self._bias_correction(inputs)
        return [PredictionResult(date=i.date, hour=i.hour, power=float(p)) for i, p in zip(inputs, powers)]

    def _bias_correction(self, inputs: list[PredictionInput]) -> np.ndarray:
        """Terme à ajouter à chaque prédiction (0 si la météo ou la consommation passées manquent)."""
        try:
            weather, actual = self.weather.hourly(), self.history.hourly_gw()
        except (WeatherHistoryUnavailable, ConsumptionHistoryUnavailable) as error:
            logger.warning("Correction du biais ignorée : %s", error)
            return np.zeros(len(inputs))

        # Heures passées dont on connaît la météo ET la consommation, et dont le niveau récent est calculable
        hours = weather.index.intersection(actual.index)
        grid, values = extend_history(actual, hours.max())
        level = build_level_features(grid, values).set_index(grid).loc[hours]
        hours = hours[~level.isna().any(axis=1).to_numpy()]
        if len(hours) == 0:
            return np.zeros(len(inputs))
        raw = weather.loc[hours].copy()
        raw["date"] = hours.strftime("%d/%m/%Y")
        raw["hour"] = hours.hour
        past = pd.concat([build_features(raw.reset_index(drop=True)), level.loc[hours].reset_index(drop=True)], axis=1)
        predicted = np.asarray(self.regressor.predict(past), dtype=float)

        # Les jours à prévoir rejoignent la série sans erreur connue : la correction de chacun vient des jours antérieurs
        past_stamps = hours.tz_localize("UTC").tz_convert(PARIS).strftime("%Y-%m-%dT%H:00").tolist()
        target_days = [pd.to_datetime(i.date, format="%d/%m/%Y").strftime("%Y-%m-%dT00:00") for i in inputs]
        correction = rolling_bias_correction(
            past_stamps + target_days,
            np.concatenate([predicted, np.full(len(inputs), np.nan)]),
            np.concatenate([actual.loc[hours].to_numpy(dtype=float), np.full(len(inputs), np.nan)]),
        )
        return correction[len(past_stamps):]

    def _level(self, inputs: list[PredictionInput]) -> pd.DataFrame:
        """Variables de niveau récent de chaque heure demandée (même ordre que `inputs`)."""
        history = self.history.hourly_gw()
        wanted = [utc_timestamp(i) for i in inputs]
        grid, values = extend_history(history, max(wanted))
        level = build_level_features(grid, values).iloc[grid.get_indexer(wanted)].reset_index(drop=True)
        missing = level.isna().any(axis=1).to_numpy()
        if missing.any():
            bad = inputs[int(np.argmax(missing))]
            raise LevelUnavailable(
                f"Pas de niveau récent pour le {bad.date} à {bad.hour} h : la consommation connue ne remonte pas assez, "
                f"ou l'heure est trop éloignée (limite : 48 h après la dernière consommation publiée)")
        return level[list(LEVEL_COLUMNS)]
