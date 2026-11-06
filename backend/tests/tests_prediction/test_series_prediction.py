import numpy as np
import pandas as pd
import pytest

from src.prediction.adapters.ml.series_prediction import ForecastUnavailable, PredictWithHoltWinters, PredictWithTimestral
from src.prediction.domain.models_prediction import PredictionInput
from src.prediction.ports.consumption_history import ConsumptionHistoryPort


class FakeHistory(ConsumptionHistoryPort):
    """Consommation horaire synthétique : profil journalier régulier, sur `hours` heures se terminant à `end`."""
    def __init__(self, end="2026-06-10 18:00", hours=1500):
        index = pd.date_range(end=pd.Timestamp(end), periods=hours, freq="h")
        self.series = pd.Series(50 + 10 * np.sin(2 * np.pi * index.hour / 24), index=index)

    def hourly_gw(self):
        return self.series


def request(date="10/06/2026", hour=20):
    # Juin : Paris = UTC+2
    return PredictionInput(date, hour, {}, {}, {})


def test_holt_winters_prevoit_une_heure_recente_proche_du_profil():
    result = PredictWithHoltWinters(FakeHistory()).predict_item(request(hour=20))   # 18h UTC, dernière heure connue
    expected = 50 + 10 * np.sin(2 * np.pi * 18 / 24)
    assert (result.date, result.hour) == ("10/06/2026", 20)
    assert result.power == pytest.approx(expected, abs=2.5)   # une prévision plate (50) serait à 10 GW


def test_holt_winters_refuse_si_l_historique_est_trop_court():
    with pytest.raises(ForecastUnavailable):
        PredictWithHoltWinters(FakeHistory(hours=100)).predict_item(request())


class FakeForecaster:
    """Prévoit une valeur fixe et mémorise le nombre de séries demandées par appel."""
    def __init__(self):
        self.calls = []

    def forecast(self, context, prediction_length, known_covariates=None):
        self.calls.append(np.asarray(context).shape)
        median = np.full((len(context), 1, prediction_length), 55.0)
        return type("Out", (), {"median": median})()


def test_timestral_regroupe_les_heures_d_un_meme_jour_en_une_seule_prevision():
    forecaster = FakeForecaster()
    method = PredictWithTimestral(FakeHistory(), lambda: forecaster)
    # Trois heures de Paris (UTC+2) du même jour UTC, plus un autre jour
    results = method.predict_items([request(hour=8), request(hour=14), request(hour=20), request(date="09/06/2026", hour=12)])
    assert [r.power for r in results] == [55.0] * 4
    assert len(forecaster.calls) == 1 and forecaster.calls[0][0] == 2     # deux jours -> un seul lot de deux séries


def test_timestral_reduit_la_fenetre_quand_l_historique_est_court():
    forecaster = FakeForecaster()
    PredictWithTimestral(FakeHistory(hours=800), lambda: forecaster).predict_item(request(date="09/06/2026", hour=12))
    assert forecaster.calls[0][2] < 1344


def test_timestral_refuse_si_l_historique_est_trop_court():
    with pytest.raises(ForecastUnavailable):
        PredictWithTimestral(FakeHistory(hours=200), lambda: FakeForecaster()).predict_item(request(date="09/06/2026"))
