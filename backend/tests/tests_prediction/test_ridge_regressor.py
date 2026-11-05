import numpy as np
import pandas as pd
import pytest

from src.prediction.adapters.ml.ridge_regressor import RidgeRegressor


def make_xy(n=300, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({
        "temperature_A": rng.normal(10, 5, n),
        "month": rng.integers(1, 13, n),
        "dayofweek": rng.integers(0, 7, n),
    })
    y = 60 - 1.5 * X["temperature_A"] + (X["dayofweek"] >= 5) * -4 + rng.normal(0, 0.1, n)
    return X, y.to_numpy()


def test_ridge_learns_linear_relation_and_weekend_effect():
    X, y = make_xy()
    model = RidgeRegressor()
    model.fit(X[:200], y[:200], X[200:250], y[200:250])
    pred = model.predict(X[250:])
    assert np.mean(np.abs(pred - y[250:])) < 0.3


def test_ridge_val_predictions_and_alpha_are_chosen_on_validation():
    X, y = make_xy()
    model = RidgeRegressor(alphas=(0.01, 1e6))
    model.fit(X[:200], y[:200], X[200:250], y[200:250])
    assert model.best_alpha_ == 0.01          # un alpha énorme écrase le modèle
    assert model.val_predictions_.shape == (50,)


def test_ridge_refit_keeps_val_predictions_from_before_refit():
    X, y = make_xy()
    a = RidgeRegressor(refit_on_val=False)
    b = RidgeRegressor(refit_on_val=True)
    for m in (a, b):
        m.fit(X[:200], y[:200], X[200:250], y[200:250])
    assert np.allclose(a.val_predictions_, b.val_predictions_)
    assert not np.allclose(a.predict(X[250:]), b.predict(X[250:]))


def test_ridge_accepts_weights_and_unseen_column_order():
    X, y = make_xy()
    w = np.linspace(0.2, 1, 200), np.ones(50)
    model = RidgeRegressor(recency_half_life_years=3.0)
    model.fit(X[:200], y[:200], X[200:250], y[200:250], *w)
    assert model.name == "ridge_recent"
    shuffled = X[250:][["dayofweek", "month", "temperature_A"]]
    assert np.allclose(model.predict(shuffled), model.predict(X[250:]))


def test_ridge_predict_before_fit_raises():
    with pytest.raises(RuntimeError):
        RidgeRegressor().predict(pd.DataFrame({"month": [1]}))
