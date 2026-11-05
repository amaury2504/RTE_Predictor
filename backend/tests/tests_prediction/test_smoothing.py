import numpy as np
import pandas as pd
import pytest

from src.prediction.domain.smoothing import holt_winters_forecasts

HOURS = pd.date_range("2024-01-01", periods=24 * 7 * 12, freq="h")


def weekly(level=50.0):
    return level + 5 * np.sin(2 * np.pi * np.arange(len(HOURS)) / 24) + (np.arange(len(HOURS)) % 168 > 120) * -3


def test_periodic_series_is_forecast_almost_exactly_after_burn_in():
    y = weekly()
    f = holt_winters_forecasts(HOURS, y, alpha=0.01, gamma=0.9)
    ok = np.isfinite(f)
    assert ok[24 * 7 * 6:].all()
    assert np.abs(f[24 * 7 * 8:] - y[24 * 7 * 8:]).max() < 0.05


def test_follows_a_level_shift():
    y = weekly()
    y[24 * 7 * 6:] -= 4.0                       # le niveau baisse de 4 GW à la 7e semaine
    f = holt_winters_forecasts(HOURS, y, alpha=0.03, gamma=0.5)
    late = slice(24 * 7 * 10, None)
    assert abs(np.mean(f[late] - y[late])) < 0.5


def test_no_leak_forecast_only_uses_data_known_48h_before():
    rng = np.random.default_rng(0)
    y = weekly() + rng.normal(0, 0.3, len(HOURS))
    base = holt_winters_forecasts(HOURS, y, 0.1, 0.1)
    k = 24 * 7 * 8
    changed = y.copy()
    changed[k:] += 100.0
    new = holt_winters_forecasts(HOURS, changed, 0.1, 0.1)
    assert np.allclose(base[: k + 48], new[: k + 48], equal_nan=True)   # jusqu'à k + 47 inclus
    assert not np.allclose(base[k + 48:], new[k + 48:], equal_nan=True)


def test_unsorted_input_and_missing_hours():
    y = weekly()
    keep = np.ones(len(HOURS), bool)
    keep[500:520] = False
    idx, vals = HOURS[keep], y[keep]
    order = np.random.default_rng(1).permutation(len(idx))
    straight = holt_winters_forecasts(idx, vals, 0.1, 0.1)
    shuffled = holt_winters_forecasts(idx[order], vals[order], 0.1, 0.1)
    assert np.allclose(straight[order], shuffled, equal_nan=True)
    assert np.isfinite(straight[24 * 7 * 6:]).all()


def test_invalid_parameters_and_duplicates():
    with pytest.raises(ValueError):
        holt_winters_forecasts(HOURS, weekly(), alpha=0.0, gamma=0.1)
    with pytest.raises(ValueError):
        holt_winters_forecasts(pd.DatetimeIndex([HOURS[0], HOURS[0]]), np.array([1.0, 2.0]), 0.1, 0.1)
