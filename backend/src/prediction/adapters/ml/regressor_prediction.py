import pandas as pd

from src.prediction.adapters.ml.raw_input import raw_row_from_input
from src.prediction.domain.features import build_features
from src.prediction.domain.models_prediction import PredictionInput, PredictionResult
from src.prediction.ports.predict import PredictionModelPort


class PredictWithRegressor(PredictionModelPort):
    """Prédiction en ligne avec un modèle du benchmark déjà entraîné (LightGBM, Ridge) : météo + calendrier.

    `regressor` est un `RegressorPort` entraîné : il connaît l'ordre de ses colonnes.
    """

    def __init__(self, regressor):
        self.regressor = regressor

    def predict_item(self, input: PredictionInput) -> PredictionResult:
        return self.predict_items([input])[0]

    def predict_items(self, inputs: list[PredictionInput]) -> list[PredictionResult]:
        # Un seul appel au modèle pour tout le lot
        features = build_features(pd.DataFrame([raw_row_from_input(i) for i in inputs]))
        powers = self.regressor.predict(features)
        return [PredictionResult(date=i.date, hour=i.hour, power=float(p)) for i, p in zip(inputs, powers)]
