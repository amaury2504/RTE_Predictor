import numpy as np
import pandas as pd
import pytest

from src.prediction.application.benchmark import (
    evaluate_regressor, run_benchmark, run_walk_forward, summarize, summarize_by_fold,
)
from src.prediction.domain.dataset import (
    BenchmarkDataset, FullDataset, TEST_FIRST_YEAR, TRAIN_LAST_YEAR, VAL_YEAR,
    split_by_year, split_for_test_year,
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


def make_full(first_year=2018, last_year=2024, rows_per_year=30) -> FullDataset:
    """Plusieurs années de 30 heures consécutives chacune (assez pour calculer la MASE)."""
    years, timestamps = [], []
    for year in range(first_year, last_year + 1):
        for ts in pd.date_range(f"{year}-03-01", periods=rows_per_year, freq="h"):
            years.append(year)
            timestamps.append(ts.strftime("%Y-%m-%dT%H:00"))
    n = len(years)
    X = pd.DataFrame({"f": np.arange(n, dtype=float), "year": years})
    return FullDataset(X=X, y=50 + 5 * np.sin(np.arange(n) / 3), timestamps=timestamps, years=np.array(years))


class MeanRegressor(RegressorPort):
    """Prédit la moyenne de l'entraînement ; enregistre ce qu'il voit."""
    name = "mean"
    stochastic = False

    def __init__(self, journal=None):
        self.calls = []  # ("fit", nb_lignes_train, nb_lignes_val) ou ("predict", nb_lignes)
        self.journal = journal  # liste partagée optionnelle pour suivre plusieurs instances

    def fit(self, X_train, y_train, X_val, y_val, w_train=None, w_val=None):
        self.mean_ = float(np.mean(y_train))
        self.calls.append(("fit", len(X_train), len(X_val)))
        if self.journal is not None:
            self.journal.append({
                "train_years": set(X_train["year"]) if "year" in X_train else None,
                "val_years": set(X_val["year"]) if "year" in X_val else None,
            })

    def predict(self, X):
        self.calls.append(("predict", len(X)))
        if self.journal is not None and "year" in X:
            self.journal[-1].setdefault("predicted_years", []).append(set(X["year"]))
        return np.full(len(X), self.mean_)


class OffsetRegressor(RegressorPort):
    """Modèle à aléa : le décalage dépend de la graine."""
    name = "offset"
    stochastic = True

    def __init__(self, seed):
        self.seed = seed

    def fit(self, X_train, y_train, X_val, y_val, w_train=None, w_val=None):
        self.mean_ = float(np.mean(y_train))

    def predict(self, X):
        return np.full(len(X), self.mean_ + 0.5 * self.seed)


# --- découpage fixe -----------------------------------------------------------------------------

def test_decoupage_fixe_par_annee():
    data = make_dataset(n_train=48, n_val=36, n_test=36)
    assert (len(data.train.y), len(data.val.y), len(data.test.y)) == (48, 36, 36)
    all_f = np.concatenate([data.train.X["f"], data.val.X["f"], data.test.X["f"]])
    assert sorted(all_f) == list(range(120))
    assert data.train.X["f"].max() < data.val.X["f"].min() < data.test.X["f"].min()


def test_les_horodatages_suivent_les_lignes():
    data = make_dataset()
    assert len(data.test.timestamps) == len(data.test.y)
    assert data.train.timestamps[0] == "2021-12-29T00:00"


# --- découpage glissant -------------------------------------------------------------------------

def test_decoupage_glissant_annees():
    data = split_for_test_year(make_full(), 2023)
    assert set(data.train.X["year"]) == {2018, 2019, 2020, 2021}   # <= T-2
    assert set(data.val.X["year"]) == {2022}                        # T-1
    assert set(data.test.X["year"]) == {2023}                       # T


def test_decoupage_glissant_decale_avec_l_annee_de_test():
    data = split_for_test_year(make_full(), 2024)
    assert max(data.train.X["year"]) == 2022
    assert set(data.val.X["year"]) == {2023}
    assert set(data.test.X["year"]) == {2024}


def test_decoupage_glissant_aucune_ligne_perdue_ni_dupliquee_entre_parties():
    data = split_for_test_year(make_full(), 2022)
    parts = [set(data.train.X["f"]), set(data.val.X["f"]), set(data.test.X["f"])]
    assert parts[0].isdisjoint(parts[1]) and parts[0].isdisjoint(parts[2]) and parts[1].isdisjoint(parts[2])


def test_decoupage_glissant_sans_passe_suffisant_leve_une_erreur():
    with pytest.raises(ValueError):
        split_for_test_year(make_full(first_year=2018), 2019)   # pas d'entraînement <= 2017
    with pytest.raises(ValueError):
        split_for_test_year(make_full(first_year=2018, last_year=2022), 2024)  # pas de test


# --- protocole ----------------------------------------------------------------------------------

def test_le_modele_est_entraine_avant_toute_prediction_et_sans_voir_le_test():
    data = make_dataset(n_train=48, n_val=36, n_test=36)
    model = MeanRegressor()
    evaluate_regressor(model, data)
    assert model.calls[0] == ("fit", 48, 36)          # entraînement et validation seulement
    assert model.calls[1:] == [("predict", 36), ("predict", 36)]  # validation puis test, après le fit


def test_les_kpi_sont_calcules_sur_le_test():
    data = make_dataset()
    result = evaluate_regressor(MeanRegressor(), data, test_year=2023)
    assert result.test.n == len(data.test.y)
    assert result.val.n == len(data.val.y)
    assert result.test_year == 2023
    assert result.fit_seconds >= 0 and result.predict_seconds >= 0


def test_modele_deterministe_une_seule_execution():
    results = run_benchmark({"mean": lambda seed: MeanRegressor()}, make_dataset(), seeds=[0, 1, 2])
    assert len(results) == 1
    assert results[0].seed is None


def test_modele_a_alea_une_execution_par_graine():
    results = run_benchmark({"offset": lambda seed: OffsetRegressor(seed)}, make_dataset(), seeds=[0, 1, 2])
    assert [r.seed for r in results] == [0, 1, 2]


def test_on_progress_est_appele_pour_chaque_execution():
    messages = []
    run_benchmark({"offset": lambda seed: OffsetRegressor(seed)}, make_dataset(), seeds=[0, 1], on_progress=messages.append)
    assert len(messages) == 2


# --- évaluation glissante -----------------------------------------------------------------------

def test_walk_forward_une_serie_de_resultats_par_annee():
    results = run_walk_forward(
        {"mean": lambda seed: MeanRegressor(), "offset": lambda seed: OffsetRegressor(seed)},
        make_full(), test_years=[2022, 2023, 2024], seeds=[0, 1],
    )
    # 3 années x (1 exécution déterministe + 2 graines)
    assert len(results) == 9
    assert sorted({r.test_year for r in results}) == [2022, 2023, 2024]


def test_walk_forward_chaque_modele_voit_le_bon_passe_et_predit_la_bonne_annee():
    journal = []
    run_walk_forward({"mean": lambda seed: MeanRegressor(journal)}, make_full(), test_years=[2022, 2024], seeds=[0])
    first, second = journal
    assert max(first["train_years"]) == 2020 and first["val_years"] == {2021}
    assert first["predicted_years"] == [{2021}, {2022}]          # validation puis test
    assert max(second["train_years"]) == 2022 and second["val_years"] == {2023}
    assert second["predicted_years"] == [{2023}, {2024}]


def test_walk_forward_message_de_progression_indique_l_annee():
    messages = []
    run_walk_forward({"mean": lambda seed: MeanRegressor()}, make_full(), [2023], [0], on_progress=messages.append)
    assert messages == ["test 2023 · mean (graine 0)"]


# --- résumés ------------------------------------------------------------------------------------

def test_resume_par_annee_ecart_type_entre_graines():
    results = run_walk_forward(
        {"mean": lambda seed: MeanRegressor(), "offset": lambda seed: OffsetRegressor(seed)},
        make_full(), test_years=[2023], seeds=[0, 1, 2, 3],
    )
    rows = {row["model"]: row for row in summarize_by_fold(results)}
    assert rows["mean"]["runs"] == 1 and rows["mean"]["mae_std"] == 0.0
    assert rows["offset"]["runs"] == 4 and rows["offset"]["mae_std"] > 0
    assert all(row["test_year"] == 2023 for row in rows.values())


def test_resume_global_moyenne_des_annees_et_classement():
    results = run_walk_forward(
        {"mean": lambda seed: MeanRegressor(), "offset": lambda seed: OffsetRegressor(seed)},
        make_full(), test_years=[2022, 2023, 2024], seeds=[0, 1],
    )
    by_fold = summarize_by_fold(results)
    summary = summarize(results)
    by_model = {row["model"]: row for row in summary}

    assert by_model["mean"]["folds"] == 3 and by_model["mean"]["runs"] == 3
    assert by_model["offset"]["folds"] == 3 and by_model["offset"]["runs"] == 6

    # La MAE globale est la moyenne des MAE par année (chaque année pèse autant)
    mean_by_year = [r["mae"] for r in by_fold if r["model"] == "mean"]
    assert by_model["mean"]["mae"] == pytest.approx(sum(mean_by_year) / 3)
    # Son écart-type mesure la variation entre années
    assert by_model["mean"]["mae_std"] == pytest.approx(float(np.std(mean_by_year)))
    # Classé par MAE croissante
    assert [row["mae"] for row in summary] == sorted(row["mae"] for row in summary)


def test_resume_par_annee_trie_par_annee_puis_mae():
    results = run_walk_forward(
        {"mean": lambda seed: MeanRegressor(), "offset": lambda seed: OffsetRegressor(seed)},
        make_full(), test_years=[2024, 2022], seeds=[0, 1],
    )
    rows = summarize_by_fold(results)
    assert [r["test_year"] for r in rows] == [2022, 2022, 2024, 2024]


# --- pondération des années récentes et prédictions de validation ------------------------------------

class WeightRecorder(RegressorPort):
    """Enregistre les poids reçus ; sa validation « parfaite » diffère de ses prédictions réelles."""
    name = "recorder"
    stochastic = False
    recency_half_life_years = 1.0

    def fit(self, X_train, y_train, X_val, y_val, w_train=None, w_val=None):
        self.w_train, self.w_val = w_train, w_val
        self.mean_ = float(np.mean(y_train))
        self.val_predictions_ = np.asarray(y_val)  # prédictions de validation d'avant réentraînement

    def predict(self, X):
        return np.full(len(X), self.mean_)


def test_les_poids_de_recence_sont_fournis_au_modele():
    data = split_for_test_year(make_full(), 2023)
    model = WeightRecorder()
    evaluate_regressor(model, data)
    assert len(model.w_train) == len(data.train.y) and len(model.w_val) == len(data.val.y)
    assert model.w_train.max() <= 1.0 and model.w_train.min() > 0
    # Plus la donnée est récente, plus elle pèse
    assert model.w_val.mean() > model.w_train.mean()
    assert model.w_train[-1] > model.w_train[0]


def test_sans_demi_vie_aucun_poids_n_est_fourni():
    received = {}

    class Plain(MeanRegressor):
        def fit(self, X_train, y_train, X_val, y_val, w_train=None, w_val=None):
            received["w"] = (w_train, w_val)
            super().fit(X_train, y_train, X_val, y_val)

    evaluate_regressor(Plain(), make_dataset())
    assert received["w"] == (None, None)


def test_les_kpi_de_validation_utilisent_les_predictions_d_avant_reentrainement():
    result = evaluate_regressor(WeightRecorder(), split_for_test_year(make_full(), 2023))
    assert result.val.mae == pytest.approx(0.0)   # val_predictions_ parfaites
    assert result.test.mae > 0                    # le test, lui, est prédit par predict()


def test_bias_correction_adds_a_corr_row_and_removes_a_constant_offset():
    class Overestimator(MeanRegressor):
        name = "surestime"
        def predict(self, X):
            return np.full(len(X), 60.0)       # très au-dessus de la série (autour de 50)

    full = make_full(first_year=2020, last_year=2024, rows_per_year=24 * 30)
    data = split_for_test_year(full, 2024)
    plain = run_benchmark({"surestime": lambda seed: Overestimator()}, data, [0])
    corrected = run_benchmark({"surestime": lambda seed: Overestimator()}, data, [0], bias_window_days=7)
    assert [r.model for r in plain] == ["surestime"]
    assert [r.model for r in corrected] == ["surestime", "surestime_corr"]
    assert corrected[1].test.mae < corrected[0].test.mae
    assert abs(corrected[1].test.bias) < abs(corrected[0].test.bias)
    assert corrected[0].test.mae_debiased is not None


def test_run_cache_skips_finished_runs_and_survives_interruption(tmp_path):
    from src.prediction.application.run_cache import RunCache

    full = make_full(first_year=2020, last_year=2024, rows_per_year=24 * 30)
    data = split_for_test_year(full, 2024)
    cache = RunCache(str(tmp_path), "cle")
    first, second = MeanRegressor(), MeanRegressor()
    run_benchmark({"mean": lambda seed: first}, data, [0], test_year=2024, cache=cache)
    assert first.calls != []
    again = run_benchmark({"mean": lambda seed: second}, data, [0], test_year=2024, cache=cache)
    assert second.calls == []                              # rien n a ete reentraine
    assert again[0].test.mae >= 0
    next(tmp_path.rglob("*.pkl")).write_bytes(b"pas du pickle")   # fichier tronque : l execution est refaite
    third = MeanRegressor()
    run_benchmark({"mean": lambda seed: third}, data, [0], test_year=2024, cache=cache)
    assert third.calls != []


def test_run_cache_key_changes_with_settings():
    from src.prediction.application.run_cache import config_key
    assert config_key(a=1, b="x") == config_key(b="x", a=1)
    assert config_key(a=1) != config_key(a=2)
