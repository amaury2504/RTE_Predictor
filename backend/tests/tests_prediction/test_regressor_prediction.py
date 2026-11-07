import numpy as np
import pandas as pd
import pytest

from src.prediction.adapters.ml.regressor_prediction import LevelUnavailable, PredictWithRegressor
from src.prediction.domain.level import LEVEL_COLUMNS
from src.prediction.ports.consumption_history import ConsumptionHistoryPort
from src.prediction.ports.weather_history import WeatherHistoryPort, WeatherHistoryUnavailable
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
    result = PredictWithRegressor(stub).predict_item(make_input(hour=14))
    assert (result.date, result.hour, result.power) == ("15/01/2026", 14, 42.5)
    assert len(stub.seen) == 1


class RampHistory(ConsumptionHistoryPort):
    """Consommation qui vaut 100 + (numéro de l'heure) : chaque retard et chaque moyenne se calcule à la main."""
    def __init__(self, end="2026-06-10 18:00", hours=1500):
        index = pd.date_range(end=pd.Timestamp(end), periods=hours, freq="h")
        self.series = pd.Series(100.0 + np.arange(hours), index=index)

    def hourly_gw(self):
        return self.series


class RecordingRegressor:
    """Mémorise les variables reçues et rend une valeur par ligne."""
    def __init__(self):
        self.seen = None

    def predict(self, X):
        self.seen = X
        return np.full(len(X), 42.5)


def test_avec_historique_le_modele_recoit_le_niveau_recent_calcule_comme_a_l_entrainement():
    history, regressor = RampHistory(), RecordingRegressor()
    # 14 h Paris (UTC+2) le 10/06 = 12 h UTC, soit 6 h avant la dernière heure connue (18 h UTC)
    PredictWithRegressor(regressor, history).predict_item(make_input(hour=14).__class__("10/06/2026", 14, {}, {}, {}))
    level = regressor.seen[list(LEVEL_COLUMNS)].iloc[0]
    at = history.series.index.get_loc(pd.Timestamp("2026-06-10 12:00"))
    assert level["conso_lag_48h"] == history.series.iloc[at - 48]        # même heure, 2 jours avant
    assert level["conso_lag_168h"] == history.series.iloc[at - 168]       # même heure, 7 jours avant
    assert level["conso_mean_7d"] == pytest.approx(history.series.iloc[at - 48 - 167: at - 48 + 1].mean())


def test_sans_historique_le_modele_ne_recoit_pas_de_niveau():
    regressor = RecordingRegressor()
    PredictWithRegressor(regressor).predict_item(make_input())
    assert not set(LEVEL_COLUMNS) & set(regressor.seen.columns)


def test_une_heure_trop_eloignee_de_la_derniere_consommation_est_refusee():
    # Plus de 48 h après la dernière heure connue : le retard de 48 h n'existe pas encore
    with pytest.raises(LevelUnavailable):
        PredictWithRegressor(RecordingRegressor(), RampHistory()).predict_item(
            make_input().__class__("14/06/2026", 14, {}, {}, {}))


def test_les_heures_futures_proches_sont_prevues_en_un_seul_lot():
    regressor = RecordingRegressor()
    inputs = [make_input().__class__("10/06/2026", h, {}, {}, {}) for h in (20, 22)] +              [make_input().__class__("11/06/2026", 10, {}, {}, {})]
    results = PredictWithRegressor(regressor, RampHistory()).predict_items(inputs)
    assert [r.power for r in results] == [42.5] * 3 and len(regressor.seen) == 3


class FlatWeather(WeatherHistoryPort):
    """Météo constante sur les 600 dernières heures de RampHistory (le modèle bouchon ignore la météo)."""
    def __init__(self, end="2026-06-10 18:00", hours=600, unavailable=False):
        self.unavailable = unavailable
        index = pd.date_range(end=pd.Timestamp(end), periods=hours, freq="h")
        self.frame = pd.DataFrame({f"temperature_{r}": 5.0 for r in REGIONS} | {f"wind_speed_{r}": 10.0 for r in REGIONS}
                                  | {f"humidity_{r}": 80.0 for r in REGIONS}, index=index)

    def hourly(self):
        if self.unavailable:
            raise WeatherHistoryUnavailable("injoignable")
        return self.frame


class FlatHistory(RampHistory):
    """Consommation constante de 60 GW."""
    def __init__(self):
        super().__init__()
        self.series[:] = 60.0


class ConstantRegressor:
    """Prédit toujours 50 GW : le modèle sous-estime de 10 GW depuis des semaines."""
    def predict(self, X):
        return np.full(len(X), 50.0)


def test_la_correction_du_biais_ajoute_l_erreur_moyenne_recente_du_modele():
    item = make_input().__class__("10/06/2026", 20, {}, {}, {})
    raw = PredictWithRegressor(ConstantRegressor(), FlatHistory()).predict_item(item)
    corrected = PredictWithRegressor(ConstantRegressor(), FlatHistory(), FlatWeather()).predict_item(item)
    assert raw.power == 50.0
    assert corrected.power == pytest.approx(60.0, abs=0.01)     # 50 + 10 d'erreur moyenne récente


def test_sans_meteo_passee_la_prediction_est_rendue_sans_correction():
    item = make_input().__class__("10/06/2026", 20, {}, {}, {})
    result = PredictWithRegressor(ConstantRegressor(), FlatHistory(), FlatWeather(unavailable=True)).predict_item(item)
    assert result.power == 50.0
