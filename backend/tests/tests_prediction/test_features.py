import numpy as np
import pandas as pd
import pytest

from src.prediction.domain.features import build_features


@pytest.fixture
def raw():
    return pd.DataFrame({
        "date": ["01/01/2024", "02/01/2024"],  # lundi férié, puis mardi
        "hour": [0, 6],
        "temperature_A": [10.0, -2.0],
        "wind_speed_A": [20.0, 5.0],
        "humidity_A": [70.0, 80.0],
    })


def test_colonnes_dans_l_ordre(raw):
    assert list(build_features(raw).columns) == [
        "temperature_A", "wind_speed_A", "humidity_A",
        "month", "dayofweek", "is_holiday", "hour_sin", "hour_cos",
        "temperature_A_squared",
    ]


def test_calendrier(raw):
    X = build_features(raw)
    assert X["month"].tolist() == [1, 1]
    assert X["dayofweek"].tolist() == [0, 1]
    assert X["is_holiday"].tolist() == [1, 0]


def test_heure_cyclique(raw):
    X = build_features(raw)
    assert X["hour_sin"].tolist() == pytest.approx([0.0, 1.0])
    assert X["hour_cos"].tolist() == pytest.approx([1.0, 0.0], abs=1e-12)


def test_carre_des_temperatures_seulement(raw):
    X = build_features(raw)
    assert X["temperature_A_squared"].tolist() == [100.0, 4.0]
    assert "wind_speed_A_squared" not in X.columns
    assert "humidity_A_squared" not in X.columns


def test_la_meteo_est_conservee_telle_quelle(raw):
    X = build_features(raw)
    assert X["wind_speed_A"].tolist() == [20.0, 5.0]


def test_ne_modifie_pas_l_entree_et_garde_l_index(raw):
    raw.index = [10, 20]
    before = raw.copy()
    X = build_features(raw)
    pd.testing.assert_frame_equal(raw, before)
    assert X.index.tolist() == [10, 20]


def test_plusieurs_regions_gardent_l_ordre_de_l_entree():
    raw = pd.DataFrame({
        "date": ["15/07/2024"], "hour": [12],
        "temperature_B": [25.0], "temperature_A": [20.0],
        "wind_speed_B": [3.0], "wind_speed_A": [4.0],
    })
    cols = list(build_features(raw).columns)
    assert cols[:4] == ["temperature_B", "temperature_A", "wind_speed_B", "wind_speed_A"]
    assert cols[-2:] == ["temperature_B_squared", "temperature_A_squared"]
