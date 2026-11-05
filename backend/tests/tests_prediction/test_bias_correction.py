import numpy as np
import pandas as pd

from src.prediction.domain.bias_correction import rolling_bias_correction


def hourly(days=40, start="2024-01-01"):
    ts = [t.strftime("%Y-%m-%dT%H:00") for t in pd.date_range(start, periods=days * 24, freq="h")]
    return ts, np.arange(days * 24) // 24


def test_constant_bias_is_recovered_after_delay():
    ts, day = hourly()
    actual = np.full(len(ts), 50.0)
    predicted = actual + 3.0                     # le modèle surestime de 3 GW
    c = rolling_bias_correction(ts, predicted, actual, window_days=14, delay_days=2, min_days=7)
    assert np.allclose(c[day < 8], 0.0)          # pas assez d'historique : 7 jours connus (jours 0 à 6) + 1 jour de décalage
    assert np.allclose(c[day >= 8], -3.0)        # ensuite, la correction annule le biais


def test_correction_never_uses_current_or_future_days():
    ts, day = hourly()
    rng = np.random.default_rng(0)
    actual = 50 + rng.normal(0, 1, len(ts))
    predicted = np.full(len(ts), 50.0)
    base = rolling_bias_correction(ts, predicted, actual)
    changed = actual.copy()
    changed[day >= 20] += 100.0                  # on bouleverse le réel à partir du jour 20
    new = rolling_bias_correction(ts, predicted, changed)
    assert np.allclose(base[day < 22], new[day < 22])   # jours 0..21 : inchangés (délai de 2 jours)
    assert not np.allclose(base[day >= 22], new[day >= 22])


def test_correction_follows_a_level_change():
    ts, day = hourly(days=90)
    actual = np.where(day < 45, 50.0, 46.0)
    predicted = np.full(len(ts), 50.0)
    c = rolling_bias_correction(ts, predicted, actual, window_days=14, delay_days=2, min_days=7)
    assert abs(c[day == 40][0]) < 1e-9           # avant le changement : rien à corriger
    assert np.isclose(c[day == 70][0], -4.0)     # bien après : le nouveau niveau est appris


def test_order_of_rows_does_not_matter_and_gaps_are_ok():
    ts, day = hourly()
    actual = 50 + (day % 3).astype(float)
    predicted = np.full(len(ts), 50.0)
    keep = day != 12                              # un jour entièrement absent
    ts2 = np.asarray(ts)[keep]
    a, p = actual[keep], predicted[keep]
    order = np.random.default_rng(1).permutation(len(ts2))
    straight = rolling_bias_correction(list(ts2), p, a)
    shuffled = rolling_bias_correction(list(ts2[order]), p[order], a[order])
    assert np.allclose(straight[order], shuffled)


def test_invalid_parameters():
    import pytest
    with pytest.raises(ValueError):
        rolling_bias_correction(["2024-01-01T00:00"], [1.0], [1.0], window_days=0)
