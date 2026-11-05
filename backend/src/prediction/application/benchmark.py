"""Orchestration du benchmark : entraîne chaque modèle selon le même protocole, mesure ses KPI.

Protocole (voir CDC.md) :
- même découpage temporel et mêmes variables pour tous les modèles ;
- le jeu de test n'est lu qu'une fois par exécution, après l'entraînement ;
- les modèles à aléa sont répétés avec plusieurs graines, les autres une seule fois.
"""
import time
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Callable

from src.prediction.domain.dataset import BenchmarkDataset
from src.prediction.domain.kpi import KpiReport, compute_kpis
from src.prediction.ports.regressor import RegressorPort

# Indicateurs agrégés dans le tableau de classement (tous lus sur le jeu de test)
SUMMARY_KPIS = ("mae", "rmse", "mape", "wape", "bias", "p95_ae", "r2", "mase")


@dataclass(frozen=True)
class RunResult:
    model: str
    seed: int | None
    fit_seconds: float
    predict_seconds: float
    val: KpiReport
    test: KpiReport


def evaluate_regressor(regressor: RegressorPort, data: BenchmarkDataset, seed: int | None = None) -> RunResult:
    """Entraîne un modèle puis calcule ses KPI sur la validation et sur le test."""
    t0 = time.perf_counter()
    regressor.fit(data.train.X, data.train.y, data.val.X, data.val.y)
    fit_seconds = time.perf_counter() - t0

    val_pred = regressor.predict(data.val.X)

    # Le test n'est lu qu'ici, une fois l'entraînement terminé
    t0 = time.perf_counter()
    test_pred = regressor.predict(data.test.X)
    predict_seconds = time.perf_counter() - t0

    return RunResult(
        model=regressor.name,
        seed=seed,
        fit_seconds=fit_seconds,
        predict_seconds=predict_seconds,
        val=compute_kpis(data.val.timestamps, val_pred, data.val.y),
        test=compute_kpis(data.test.timestamps, test_pred, data.test.y),
    )


def run_benchmark(
    factories: dict[str, Callable[[int], RegressorPort]],
    data: BenchmarkDataset,
    seeds: list[int],
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[RunResult]:
    """Exécute chaque modèle : une fois par graine s'il est stochastique, une seule fois sinon."""
    results: list[RunResult] = []
    for name, factory in factories.items():
        for i, seed in enumerate(seeds):
            regressor = factory(seed)
            if i > 0 and not regressor.stochastic:
                break
            on_progress(f"{name} (graine {seed})")
            results.append(evaluate_regressor(regressor, data, seed if regressor.stochastic else None))
    return results


def summarize(results: list[RunResult]) -> list[dict]:
    """Moyenne et écart-type par modèle, triés par MAE de test croissante."""
    by_model: dict[str, list[RunResult]] = {}
    for r in results:
        by_model.setdefault(r.model, []).append(r)

    rows = []
    for model, runs in by_model.items():
        row: dict = {"model": model, "runs": len(runs)}
        for kpi in SUMMARY_KPIS:
            values = [getattr(r.test, kpi) for r in runs if getattr(r.test, kpi) is not None]
            row[kpi] = mean(values) if values else None
            if not values:
                row[f"{kpi}_std"] = None
            else:
                row[f"{kpi}_std"] = pstdev(values) if len(values) > 1 else 0.0
        row["val_mae"] = mean(r.val.mae for r in runs)
        row["fit_seconds"] = mean(r.fit_seconds for r in runs)
        row["predict_seconds"] = mean(r.predict_seconds for r in runs)
        rows.append(row)
    return sorted(rows, key=lambda row: row["mae"])
