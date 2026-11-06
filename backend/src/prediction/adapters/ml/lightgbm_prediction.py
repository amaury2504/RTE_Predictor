import pandas as pd

from src.prediction.adapters.ml.raw_input import raw_row_from_input
from src.prediction.domain.features import build_features
from src.prediction.domain.models_prediction import PredictionInput, PredictionResult
from src.prediction.ports.predict import PredictionModelPort


class PredictWithLightGBM(PredictionModelPort):
    """Prédiction en ligne avec un LightGBM entraîné (météo + calendrier, comme le MLP servi).

    `regressor` est un `LightGBMRegressor` déjà entraîné : il connaît l'ordre de ses colonnes.
    """

    def __init__(self, regressor):
        self.regressor = regressor

    def predict_item(self, input: PredictionInput) -> PredictionResult:
        features = build_features(pd.DataFrame([raw_row_from_input(input)]))
        power = float(self.regressor.predict(features)[0])
        return PredictionResult(date=input.date, hour=input.hour, power=power)
