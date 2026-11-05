import numpy as np
import pandas as pd
import pytest

from src.prediction.adapters.ml.lightgbm_regressor import LightGBMRegressor


@pytest.fixture
def data():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.uniform(0, 10, size=(400, 3)), columns=["a", "b", "c"])
    y = 20 + 2 * X["a"].to_numpy() - X["b"].to_numpy()
    return X.iloc[:280], y[:280], X.iloc[280:], y[280:]


def fit_small(seed, data):
    model = LightGBMRegressor(seed=seed, n_estimators=60, num_leaves=8, min_child_samples=5, early_stopping_rounds=20)
    X_tr, y_tr, X_va, y_va = data
    model.fit(X_tr, y_tr, X_va, y_va)
    return model


def test_predict_avant_fit_leve_une_erreur(data):
    with pytest.raises(RuntimeError):
        LightGBMRegressor().predict(data[0])


def test_predictions_de_la_bonne_forme_et_finies(data):
    pred = fit_small(0, data).predict(data[2])
    assert pred.shape == (len(data[2]),)
    assert np.isfinite(pred).all()


def test_le_modele_apprend_mieux_que_la_moyenne(data):
    _, y_tr, X_va, y_va = data
    pred = fit_small(0, data).predict(X_va)
    mae_model = np.mean(np.abs(pred - y_va))
    mae_mean = np.mean(np.abs(y_tr.mean() - y_va))
    assert mae_model < mae_mean / 2


def test_meme_graine_meme_resultat(data):
    a = fit_small(3, data).predict(data[2])
    b = fit_small(3, data).predict(data[2])
    assert np.allclose(a, b)


def test_graines_differentes_resultats_differents(data):
    a = fit_small(1, data).predict(data[2])
    b = fit_small(2, data).predict(data[2])
    assert not np.allclose(a, b)


def test_arret_anticipe_respecte_le_maximum_d_arbres(data):
    model = fit_small(0, data)
    assert 1 <= model.best_iteration_ <= 60


def test_predict_utilise_les_colonnes_dans_l_ordre_d_entrainement(data):
    model = fit_small(0, data)
    X_va = data[2]
    assert np.allclose(model.predict(X_va), model.predict(X_va[["c", "a", "b"]]))


# --- réentraînement sur entraînement + validation -------------------------------------------------

def fit_with(data, **kwargs):
    model = LightGBMRegressor(seed=0, n_estimators=60, num_leaves=8, min_child_samples=5,
                              early_stopping_rounds=20, **kwargs)
    X_tr, y_tr, X_va, y_va = data
    model.fit(X_tr, y_tr, X_va, y_va)
    return model


def test_le_reentrainement_utilise_le_nombre_d_arbres_trouve(data):
    model = fit_with(data, refit_on_val=True)
    assert model.model.n_estimators == max(1, model.best_iteration_)


def test_les_predictions_de_validation_sont_celles_d_avant_reentrainement(data):
    X_va = data[2]
    sans = fit_with(data, refit_on_val=False)
    avec = fit_with(data, refit_on_val=True)
    assert np.allclose(avec.val_predictions_, sans.val_predictions_)
    assert not np.allclose(avec.predict(X_va), avec.val_predictions_)


def test_sans_reentrainement_les_predictions_de_validation_sont_celles_du_modele(data):
    model = fit_with(data, refit_on_val=False)
    assert np.allclose(model.predict(data[2]), model.val_predictions_)


def test_les_poids_changent_le_resultat(data):
    X_tr, y_tr, X_va, y_va = data
    plain = fit_with(data, refit_on_val=False)
    weighted = LightGBMRegressor(seed=0, n_estimators=60, num_leaves=8, min_child_samples=5,
                                 early_stopping_rounds=20, refit_on_val=False, recency_half_life_years=2.0)
    weighted.fit(X_tr, y_tr, X_va, y_va, np.linspace(0.05, 1.0, len(X_tr)), np.ones(len(X_va)))
    assert not np.allclose(plain.predict(X_va), weighted.predict(X_va))


def test_nom_de_la_variante_ponderee():
    assert LightGBMRegressor().name == "lightgbm"
    assert LightGBMRegressor(recency_half_life_years=3.0).name == "lightgbm_recent"
