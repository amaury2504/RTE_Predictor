import numpy as np
import pandas as pd
import pytest

from src.prediction.adapters.ml.mlp_regressor import MLPRegressor


@pytest.fixture
def data():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.uniform(0, 10, size=(240, 3)), columns=["a", "b", "c"])
    y = 20 + 2 * X["a"].to_numpy() - X["b"].to_numpy()
    return X.iloc[:160], y[:160], X.iloc[160:], y[160:]


def fit_small(seed, data):
    model = MLPRegressor(seed=seed, max_epochs=3, patience=50, batch_size=32)
    X_tr, y_tr, X_va, y_va = data
    model.fit(X_tr, y_tr, X_va, y_va)
    return model


def test_predict_avant_fit_leve_une_erreur(data):
    with pytest.raises(RuntimeError):
        MLPRegressor().predict(data[0])


def test_predictions_de_la_bonne_forme_et_finies(data):
    model = fit_small(0, data)
    pred = model.predict(data[2])
    assert pred.shape == (len(data[2]),)
    assert np.isfinite(pred).all()


def test_les_normaliseurs_sont_ajustes_sur_l_entrainement_seul(data):
    X_tr, y_tr, X_va, y_va = data
    # Une validation aux valeurs extrêmes ne doit PAS modifier les échelles apprises
    X_va_extreme = X_va.copy() * 1000
    model = MLPRegressor(max_epochs=1, batch_size=32)
    model.fit(X_tr, y_tr, X_va_extreme, y_va * 1000)

    assert model.scaler_X.data_max_.tolist() == pytest.approx(X_tr.max().tolist())
    assert model.scaler_Y.data_max_[0] == pytest.approx(y_tr.max())


def test_meme_graine_meme_resultat(data):
    a = fit_small(7, data).predict(data[2])
    b = fit_small(7, data).predict(data[2])
    assert np.allclose(a, b)


def test_graines_differentes_resultats_differents(data):
    a = fit_small(1, data).predict(data[2])
    b = fit_small(2, data).predict(data[2])
    assert not np.allclose(a, b)


def test_meilleure_epoch_enregistree(data):
    assert fit_small(0, data).best_epoch_ in (0, 1, 2)


def test_predict_utilise_les_colonnes_dans_l_ordre_d_entrainement(data):
    model = fit_small(0, data)
    X_va = data[2]
    shuffled = X_va[["c", "a", "b"]]
    assert np.allclose(model.predict(X_va), model.predict(shuffled))
