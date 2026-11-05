import numpy as np
import pandas as pd
import pytest

from src.prediction.domain.level import LEVEL_COLUMNS, build_level_features


def test_lags_look_back_exactly_and_never_forward():
    idx = pd.date_range("2024-01-01", periods=24 * 40, freq="h")
    actual = np.arange(len(idx), dtype=float)
    f = build_level_features(idx, actual)
    i = 24 * 30
    assert f["conso_lag_48h"][i] == actual[i - 48]
    assert f["conso_lag_168h"][i] == actual[i - 168]
    # moyenne des 7 jours qui se terminent 48 h avant : heures i-48-167 ... i-48
    assert np.isclose(f["conso_mean_7d"][i], actual[i - 48 - 167: i - 48 + 1].mean())
    assert list(f.columns) == list(LEVEL_COLUMNS)


def test_no_leak_changing_recent_values_does_not_change_features():
    idx = pd.date_range("2024-01-01", periods=24 * 40, freq="h")
    actual = np.random.default_rng(0).normal(50, 5, len(idx))
    base = build_level_features(idx, actual)
    changed = actual.copy()
    changed[24 * 30:] += 100.0            # on bouleverse les valeurs à partir de l'heure i0
    new = build_level_features(idx, changed)
    # avant i0 + 48 h aucune variable ne peut avoir vu les valeurs modifiées
    k = 24 * 30 + 48
    assert np.allclose(base.iloc[:k].fillna(-1), new.iloc[:k].fillna(-1))


def test_unsorted_input_and_gaps_give_nan_not_wrong_values():
    idx = pd.date_range("2024-01-01", periods=24 * 20, freq="h")
    actual = np.arange(len(idx), dtype=float)
    keep = np.ones(len(idx), bool)
    keep[100] = False                                    # une heure absente
    order = np.random.default_rng(1).permutation(keep.sum())
    f = build_level_features(idx[keep][order], actual[keep][order])
    ref = build_level_features(idx[keep], actual[keep])
    assert np.allclose(f.fillna(-1).to_numpy(), ref.iloc[order].fillna(-1).to_numpy())
    j = int(np.where(idx[keep] == idx[148])[0][0])       # 148 - 48 = 100 : l'heure manquante
    assert np.isnan(ref["conso_lag_48h"][j])
    assert ref["conso_lag_168h"].isna().iloc[:100].all()  # pas d'historique au début


def test_duplicate_timestamps_rejected():
    idx = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:00"])
    with pytest.raises(ValueError):
        build_level_features(idx, np.array([1.0, 2.0]))
