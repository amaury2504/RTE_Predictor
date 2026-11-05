import numpy as np
import pandas as pd
import pytest

from src.prediction.application.benchmark import evaluate_regressor, run_benchmark, summarize
from src.prediction.domain.dataset import (
    BenchmarkDataset, TEST_FIRST_YEAR, TRAIN_LAST_YEAR, VAL_YEAR, split_by_year,
)
from src.prediction.ports.regressor import RegressorPort


def make_dataset(n_train=48, n_val=36, n_test=36) -> BenchmarkDataset:
    """Série horaire synthétique : les n_train premières heures en 2021, puis 2022, puis 2023."""
    n = n_train + n_val + n_test
    timestamps = [t.strftime("%Y-%m-%dT%H:00") for t in pd.date_range("2021-12-29", periods=n, freq="h")]
    years = np.array([TRAIN_LAST_YEAR] * n_train + [VAL_YEAR] * n_val + [TEST_FIRST_YEAR] * n_test)
    X = pd.DataFrame({"f": np.arange(n, dtype=float)})
    y = 50 + 5 * np.sin(np.arange(n) / 3)
    return split_by_year(X, y, timestamps, years)


class MeanRegressor(RegressorPort):
    """Prédit la moyenne de l'entraînement ; enregistre ce qu'il voit."""
    name = "mean"
    stochastic = False

    def __init__(self):
        self.calls = []  # ("fit", nb_lignes_train, nb_lignes_val) ou ("predict", nb_lignes)

    def fit(self, X_train, y_train, X_val, y_val):
        self.mean_ = float(np.mean(y_train))
        self.calls.append(("fit", len(X_train), len(X_val)))

    def predict(self, X):
        self.calls.append(("predict", len(X)))
        return np.full(len(X), self.mean_)


class OffsetRegressor(RegressorPort):
    """Modèle à aléa : le décalage dépend de la graine."""
    name = "offset"
    stochastic = True

    def __init__(self, seed):
        self.seed = seed

    def fit(self, X_train, y_train, X_val, y_val):
        self.mean_ = float(np.mean(y_train))

    def predict(self, X):
        return np.full(len(X), self.mean_ + 0.5 * self.seed)


# --- découpage ----------------------------------------------------------------------------------

def test_decoupage_par_annee():
    data = make_dataset(n_train=48, n_val=36, n_test=36)
    assert (len(data.train.y), len(data.val.y), len(data.test.y)) == (48, 36, 36)
    # Les trois ensembles sont disjoints et couvrent toutes les lignes
    all_f = np.concatenate([data.train.X["f"], data.val.X["f"], data.test.X["f"]])
    assert sorted(all_f) == list(range(120))
    assert data.train.X["f"].max() < data.val.X["f"].min() < data.test.X["f"].min()


def test_les_horodatages_suivent_les_lignes():
    data = make_dataset()
    assert len(data.test.timestamps) == len(data.test.y)
    assert data.train.timestamps[0] == "2021-12-29T00:00"


# --- protocole ----------------------------------------------------------------------------------

def test_le_modele_est_entraine_avant_toute_prediction_et_sans_voir_le_test():
    data = make_dataset(n_train=48, n_val=36, n_test=36)
    model = MeanRegressor()
    evaluate_regressor(model, data)
    assert model.calls[0] == ("fit", 48, 36)          # entraînement et validation seulement
    assert model.calls[1:] == [("predict", 36), ("predict", 36)]  # validation puis test, après le fit


def test_les_kpi_sont_calcules_sur_le_test():
    data = make_dataset()
    result = evaluate_regressor(MeanRegressor(), data)
    assert result.test.n == len(data.test.y)
    assert result.val.n == len(data.val.y)
    assert result.fit_seconds >= 0 and result.predict_seconds >= 0


def test_modele_deterministe_une_seule_execution():
    data = make_dataset()
    results = run_benchmark({"mean": lambda seed: MeanRegressor()}, data, seeds=[0, 1, 2])
    assert len(results) == 1
    assert results[0].seed is None


def test_modele_a_alea_une_execution_par_graine():
    data = make_dataset()
    results = run_benchmark({"offset": lambda seed: OffsetRegressor(seed)}, data, seeds=[0, 1, 2])
    assert [r.seed for r in results] == [0, 1, 2]


def test_resume_moyenne_ecart_type_et_classement():
    data = make_dataset()
    results = run_benchmark(
        {"mean": lambda seed: MeanRegressor(), "offset": lambda seed: OffsetRegressor(seed)},
        data, seeds=[0, 1, 2, 3],
    )
    summary = summarize(results)
    by_model = {row["model"]: row for row in summary}

    assert by_model["mean"]["runs"] == 1
    assert by_model["mean"]["mae_std"] == 0.0
    assert by_model["offset"]["runs"] == 4
    assert by_model["offset"]["mae_std"] > 0
    # Classé par MAE croissante
    assert [row["mae"] for row in summary] == sorted(row["mae"] for row in summary)


def test_on_progress_est_appele_pour_chaque_execution():
    messages = []
    run_benchmark({"offset": lambda seed: OffsetRegressor(seed)}, make_dataset(), seeds=[0, 1], on_progress=messages.append)
    assert len(messages) == 2
