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
    model = MLPRegressor(max_epochs=1, batch_size=32, refit_on_val=False)
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


# --- réentraînement sur entraînement + validation -------------------------------------------------

def fit_with(data, **kwargs):
    model = MLPRegressor(seed=0, max_epochs=3, patience=50, batch_size=32, **kwargs)
    X_tr, y_tr, X_va, y_va = data
    model.fit(X_tr, y_tr, X_va, y_va)
    return model


def test_le_reentrainement_integre_la_validation_dans_les_normaliseurs(data):
    X_tr, y_tr, X_va, y_va = data
    model = MLPRegressor(seed=0, max_epochs=1, batch_size=32, refit_on_val=True)
    model.fit(X_tr, y_tr, X_va * 1000, y_va * 1000)
    # Après réentraînement, l'échelle couvre aussi la validation
    assert model.scaler_X.data_max_.max() > 100 * X_tr.max().max()


def test_les_predictions_de_validation_sont_celles_d_avant_reentrainement(data):
    X_va = data[2]
    sans = fit_with(data, refit_on_val=False)
    avec = fit_with(data, refit_on_val=True)
    # Mêmes graine et étape 1 : les prédictions de validation conservées sont identiques
    assert np.allclose(avec.val_predictions_, sans.val_predictions_)
    # Mais le modèle final, réentraîné avec la validation, prédit autre chose
    assert not np.allclose(avec.predict(X_va), avec.val_predictions_)


def test_sans_reentrainement_les_predictions_de_validation_sont_celles_du_modele(data):
    model = fit_with(data, refit_on_val=False)
    assert np.allclose(model.predict(data[2]), model.val_predictions_)


def test_les_poids_changent_le_resultat(data):
    X_tr, y_tr, X_va, y_va = data
    w_tr = np.linspace(0.1, 1.0, len(X_tr))
    w_va = np.ones(len(X_va))
    plain = MLPRegressor(seed=0, max_epochs=3, batch_size=32, refit_on_val=False)
    weighted = MLPRegressor(seed=0, max_epochs=3, batch_size=32, refit_on_val=False, recency_half_life_years=2.0)
    plain.fit(X_tr, y_tr, X_va, y_va)
    weighted.fit(X_tr, y_tr, X_va, y_va, w_tr, w_va)
    assert not np.allclose(plain.predict(X_va), weighted.predict(X_va))


def test_nom_de_la_variante_ponderee():
    assert MLPRegressor().name == "mlp"
    assert MLPRegressor(recency_half_life_years=3.0).name == "mlp_recent"
