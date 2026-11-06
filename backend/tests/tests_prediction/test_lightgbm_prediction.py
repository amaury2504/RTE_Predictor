import numpy as np

from src.prediction.adapters.ml.lightgbm_prediction import PredictWithLightGBM
from src.prediction.adapters.ml.raw_input import raw_row_from_input
from src.prediction.domain.models_prediction import PredictionInput

REGIONS = ["Bretagne", "Occitanie"]


def make_input(hour=14):
    return PredictionInput(
        "15/01/2026", hour,
        {r: 5.0 for r in REGIONS}, {r: 10.0 for r in REGIONS}, {r: 80.0 for r in REGIONS},
    )


class StubRegressor:
    """Mémorise les variables reçues et renvoie une valeur fixe."""
    def __init__(self):
        self.seen = None

    def predict(self, X):
        self.seen = X
        return np.array([42.5])


def test_raw_row_convertit_l_heure_de_paris_en_utc():
    # Janvier : Paris = UTC+1
    raw = raw_row_from_input(make_input(hour=14))
    assert raw["date"] == "15/01/2026" and raw["hour"] == 13
    assert raw["temperature_Bretagne"] == 5.0 and raw["wind_speed_Occitanie"] == 10.0 and raw["humidity_Bretagne"] == 80.0


def test_predict_item_renvoie_la_puissance_du_regresseur_avec_la_date_et_l_heure_d_origine():
    stub = StubRegressor()
    result = PredictWithLightGBM(stub).predict_item(make_input(hour=14))
    assert (result.date, result.hour, result.power) == ("15/01/2026", 14, 42.5)
    assert len(stub.seen) == 1
