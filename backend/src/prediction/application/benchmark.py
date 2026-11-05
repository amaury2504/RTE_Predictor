"""Orchestration du benchmark : entraîne chaque modèle selon le même protocole, mesure ses KPI.

Protocole (voir CDC.md) :
- évaluation glissante : pour chaque année de test T, entraînement <= T-2, validation T-1, test T ;
- même découpage et mêmes variables pour tous les modèles ;
- le jeu de test n'est lu qu'une fois par exécution, après l'entraînement ;
- les modèles à aléa sont répétés avec plusieurs graines, les autres une seule fois.
"""
import time
from dataclasses import dataclass, replace
from statistics import mean, pstdev
from typing import Callable

import numpy as np

from src.prediction.domain.bias_correction import rolling_bias_correction
from src.prediction.domain.dataset import BenchmarkDataset, FullDataset, split_for_test_year
from src.prediction.domain.kpi import KpiReport, compute_kpis
from src.prediction.domain.recency import recency_weights
from src.prediction.ports.regressor import RegressorPort

# Indicateurs agrégés dans les tableaux de résultats (tous lus sur le jeu de test)
SUMMARY_KPIS = ("mae", "rmse", "mape", "wape", "bias", "p95_ae", "r2", "mase", "mae_debiased")


@dataclass(frozen=True)
class RunResult:
    model: str
    seed: int | None
    fit_seconds: float
    predict_seconds: float
    val: KpiReport
    test: KpiReport
    test_year: int | None = None
    # KPI de test après correction du biais récent (None si la correction n'est pas demandée)
    test_corrected: KpiReport | None = None


def evaluate_regressor(
    regressor: RegressorPort, data: BenchmarkDataset, seed: int | None = None, test_year: int | None = None,
    bias_window_days: int | None = None,
) -> RunResult:
    """Entraîne un modèle puis calcule ses KPI sur la validation et sur le test.

    Si `bias_window_days` est donné, calcule aussi les KPI du test après correction du biais récent :
    les erreurs des jours déjà écoulés du test (avec un décalage de 2 jours) corrigent les jours suivants.
    """
    # Pondération des années récentes, si le modèle en veut : âge mesuré depuis le début de l'année de test
    w_train = w_val = None
    if regressor.recency_half_life_years:
        reference = data.test.timestamps[0]
        w_train = recency_weights(data.train.timestamps, reference, regressor.recency_half_life_years)
        w_val = recency_weights(data.val.timestamps, reference, regressor.recency_half_life_years)

    t0 = time.perf_counter()
    regressor.fit(data.train.X, data.train.y, data.val.X, data.val.y, w_train, w_val)
    fit_seconds = time.perf_counter() - t0

    # Prédictions de validation faites avant un éventuel réentraînement incluant la validation
    val_pred = regressor.val_predictions_
    if val_pred is None:
        val_pred = regressor.predict(data.val.X)

    # Le test n'est lu qu'ici, une fois l'entraînement terminé
    t0 = time.perf_counter()
    test_pred = regressor.predict(data.test.X)
    predict_seconds = time.perf_counter() - t0

    test_corrected = None
    if bias_window_days:
        correction = rolling_bias_correction(data.test.timestamps, test_pred, data.test.y, bias_window_days)
        test_corrected = compute_kpis(data.test.timestamps, np.asarray(test_pred) + correction, data.test.y)

    return RunResult(
        model=regressor.name,
        seed=seed,
        fit_seconds=fit_seconds,
        predict_seconds=predict_seconds,
        val=compute_kpis(data.val.timestamps, val_pred, data.val.y),
        test=compute_kpis(data.test.timestamps, test_pred, data.test.y),
        test_year=test_year,
        test_corrected=test_corrected,
    )


def run_benchmark(
    factories: dict[str, Callable[[int], RegressorPort]],
    data: BenchmarkDataset,
    seeds: list[int],
    on_progress: Callable[[str], None] = lambda message: None,
    test_year: int | None = None,
    bias_window_days: int | None = None,
) -> list[RunResult]:
    """Exécute chaque modèle sur un découpage : une fois par graine s'il est stochastique, une fois sinon.

    Avec `bias_window_days`, chaque modèle produit une ligne de plus, « <nom>_corr », avec le biais récent corrigé.
    """
    results: list[RunResult] = []
    for name, factory in factories.items():
        for i, seed in enumerate(seeds):
            regressor = factory(seed)
            if i > 0 and not regressor.stochastic:
                break
            on_progress(f"{name} (graine {seed})")
            result = evaluate_regressor(
                regressor, data, seed if regressor.stochastic else None, test_year, bias_window_days)
            results.append(result)
            if result.test_corrected is not None:
                results.append(replace(
                    result, model=f"{result.model}_corr", test=result.test_corrected, test_corrected=None))
    return results


def run_walk_forward(
    factories: dict[str, Callable[[int], RegressorPort]],
    full: FullDataset,
    test_years: list[int],
    seeds: list[int],
    on_progress: Callable[[str], None] = lambda message: None,
    bias_window_days: int | None = None,
) -> list[RunResult]:
    """Évaluation glissante : refait tout le protocole pour chaque année de test."""
    results: list[RunResult] = []
    for year in test_years:
        data = split_for_test_year(full, year)
        results += run_benchmark(
            factories, data, seeds,
            on_progress=lambda message, year=year: on_progress(f"test {year} · {message}"),
            test_year=year,
            bias_window_days=bias_window_days,
        )
    return results


def _aggregate(runs: list[RunResult]) -> dict:
    """Moyenne et écart-type (entre exécutions) des KPI de test."""
    row: dict = {"runs": len(runs)}
    for kpi in SUMMARY_KPIS:
        values = [getattr(r.test, kpi) for r in runs if getattr(r.test, kpi) is not None]
        row[kpi] = mean(values) if values else None
        row[f"{kpi}_std"] = None if not values else (pstdev(values) if len(values) > 1 else 0.0)
    row["val_mae"] = mean(r.val.mae for r in runs)
    row["fit_seconds"] = mean(r.fit_seconds for r in runs)
    row["predict_seconds"] = mean(r.predict_seconds for r in runs)
    return row


def summarize_by_fold(results: list[RunResult]) -> list[dict]:
    """Une ligne par (année de test, modèle) : moyenne et écart-type entre graines. Triées par année puis MAE."""
    groups: dict[tuple[int | None, str], list[RunResult]] = {}
    for r in results:
        groups.setdefault((r.test_year, r.model), []).append(r)
    rows = [{"test_year": year, "model": model, **_aggregate(runs)} for (year, model), runs in groups.items()]
    return sorted(rows, key=lambda row: (row["test_year"] or 0, row["mae"]))


def summarize(results: list[RunResult]) -> list[dict]:
    """Une ligne par modèle sur l'ensemble des années de test, triées par MAE croissante.

    Chaque KPI est la moyenne des moyennes par année (chaque année pèse autant) ; son écart-type
    mesure la variation ENTRE ANNÉES (0 s'il n'y a qu'une année). La variation entre graines
    est dans `summarize_by_fold`.
    """
    by_model: dict[str, list[dict]] = {}
    for fold_row in summarize_by_fold(results):
        by_model.setdefault(fold_row["model"], []).append(fold_row)

    rows = []
    for model, folds in by_model.items():
        row: dict = {"model": model, "folds": len(folds), "runs": sum(f["runs"] for f in folds)}
        for kpi in SUMMARY_KPIS:
            values = [f[kpi] for f in folds if f[kpi] is not None]
            row[kpi] = mean(values) if values else None
            row[f"{kpi}_std"] = None if not values else (pstdev(values) if len(values) > 1 else 0.0)
        for key in ("val_mae", "fit_seconds", "predict_seconds"):
            row[key] = mean(f[key] for f in folds)
        rows.append(row)
    return sorted(rows, key=lambda row: row["mae"])
