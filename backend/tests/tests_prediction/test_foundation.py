from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.prediction.domain.foundation import HORIZON, foundation_forecasts

HOURS = pd.date_range("2024-01-01", periods=24 * 40, freq="h")


class PositionForecaster:
    """Prévoit la position du pas dans l'horizon : permet de vérifier quel pas est attribué à quelle heure."""
    def __init__(self):
        self.calls = []

    def forecast(self, context, prediction_length, known_covariates=None):
        self.calls.append((context.shape, None if known_covariates is None else known_covariates.shape))
        b = context.shape[0]
        steps = np.arange(1, prediction_length + 1, dtype=float)       # pas 1..H après l'origine
        return SimpleNamespace(median=np.tile(steps, (b, 1, 1)))


class MeanForecaster:
    """Prévoit la moyenne de l'historique (sert à contrôler quelles données sont lues)."""
    def forecast(self, context, prediction_length, known_covariates=None):
        mean = np.nanmean(context, axis=-1, keepdims=True)
        return SimpleNamespace(median=np.repeat(mean, prediction_length, axis=-1))


def test_each_hour_of_the_target_day_gets_the_right_step():
    f = PositionForecaster()
    day = pd.Timestamp("2024-01-20")
    out = foundation_forecasts(f, HOURS, np.ones(len(HOURS)), [day], context_hours=168)
    pos = {t: i for i, t in enumerate(HOURS)}
    day_slice = slice(pos[day], pos[day] + 24)
    assert np.allclose(out[day_slice], np.arange(48, 72))             # 00h -> pas +48 ... 23h -> pas +71
    assert np.isnan(out[: pos[day]]).all() and np.isnan(out[pos[day] + 24:]).all()
    assert f.calls[0][0] == (1, 1, 168) and HORIZON == 71


def test_no_leak_changing_data_after_origin_does_not_change_forecast():
    rng = np.random.default_rng(0)
    y = 50 + rng.normal(0, 1, len(HOURS))
    day = pd.Timestamp("2024-01-25")
    base = foundation_forecasts(MeanForecaster(), HOURS, y, [day], context_hours=168)
    changed = y.copy()
    origin = HOURS.get_loc(day - pd.Timedelta(hours=48))
    changed[origin + 1:] += 100.0                                     # tout ce qui suit l'origine est bouleversé
    new = foundation_forecasts(MeanForecaster(), HOURS, changed, [day], context_hours=168)
    assert np.allclose(base, new, equal_nan=True)
    changed[origin] += 100.0                                          # la dernière valeur connue, elle, compte
    assert not np.allclose(base, foundation_forecasts(MeanForecaster(), HOURS, changed, [day], context_hours=168),
                           equal_nan=True)


def test_covariates_cover_context_and_horizon_and_order_does_not_matter():
    f = PositionForecaster()
    y = np.arange(len(HOURS), dtype=float)
    cov = np.column_stack([y * 2, np.zeros(len(HOURS))])
    order = np.random.default_rng(1).permutation(len(HOURS))
    out = foundation_forecasts(f, HOURS[order], y[order], [pd.Timestamp("2024-01-20")],
                               context_hours=168, covariates=cov[order])
    assert f.calls[0][1] == (1, 2, 168 + HORIZON)
    assert np.isfinite(out).sum() == 24


def test_days_without_enough_history_or_data_are_skipped():
    f = PositionForecaster()
    out = foundation_forecasts(f, HOURS, np.ones(len(HOURS)),
                               [pd.Timestamp("2024-01-03"), pd.Timestamp("2030-01-01")], context_hours=168)
    assert np.isnan(out).all() and f.calls == []                      # historique trop court / jour hors données
    y = np.full(len(HOURS), np.nan)
    assert np.isnan(foundation_forecasts(f, HOURS, y, [pd.Timestamp("2024-01-20")], context_hours=168)).all()


def test_duplicate_timestamps_rejected():
    with pytest.raises(ValueError):
        foundation_forecasts(PositionForecaster(), pd.DatetimeIndex([HOURS[0], HOURS[0]]), np.ones(2), [HOURS[0]])
