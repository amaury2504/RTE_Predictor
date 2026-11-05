"""Références hors contrat « météo + calendrier » : prévisions naïves et prévisions publiées par RTE.

Elles servent de points de comparaison pour les modèles du benchmark. Elles utilisent la consommation
passée (ou les prévisions d'RTE) : elles sont donc rangées à part. Sur chaque année, seuls les points
où la référence existe sont évalués.
"""
import numpy as np

from src.prediction.application.benchmark import RunResult
from src.prediction.domain.dataset import FullDataset
from src.prediction.domain.kpi import compute_kpis


def _kpis_on_year(full: FullDataset, prediction: np.ndarray, year: int):
    mask = (np.asarray(full.years) == year) & np.isfinite(prediction)
    if not mask.any():
        return None
    ts = np.asarray(full.timestamps)[mask]
    return compute_kpis([str(t) for t in ts], prediction[mask], np.asarray(full.y)[mask])


def run_baselines(full: FullDataset, references: dict[str, np.ndarray], test_years: list[int]) -> list[RunResult]:
    """Une exécution par (référence, année de test) ; la validation est l'année T-1."""
    results = []
    for name, prediction in references.items():
        prediction = np.asarray(prediction, dtype=float)
        for year in test_years:
            test, val = _kpis_on_year(full, prediction, year), _kpis_on_year(full, prediction, year - 1)
            if test is None or val is None:
                continue
            results.append(RunResult(name, None, 0.0, 0.0, val, test, year))
    return results
