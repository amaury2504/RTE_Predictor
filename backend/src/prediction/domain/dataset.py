"""Découpages temporels communs à tous les modèles du benchmark.

Protocole principal : évaluation glissante (« walk-forward »). Pour une année de test T :
    - entraînement : toutes les années jusqu'à T-2
    - validation   : T-1 (réglage et arrêt anticipé)
    - test         : T  (lu une seule fois par modèle, à la fin)
Cela imite l'usage réel (réentraîner chaque année) et permet de mesurer la dérive du modèle,
la consommation française ayant changé de niveau après 2021.

Un découpage fixe (entraînement <= 2021, validation 2022, test >= 2023) reste disponible.

L'année est celle du jour UTC de la donnée.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

TRAIN_LAST_YEAR = 2021
VAL_YEAR = 2022
TEST_FIRST_YEAR = 2023


@dataclass(frozen=True)
class Split:
    X: pd.DataFrame            # variables d'entrée
    y: np.ndarray              # consommation réelle (GW)
    timestamps: list[str]      # horodatages locaux (Paris) "YYYY-MM-DDTHH:00", pour les KPI


@dataclass(frozen=True)
class BenchmarkDataset:
    train: Split
    val: Split
    test: Split


@dataclass(frozen=True)
class FullDataset:
    """Toutes les lignes, avant découpage."""
    X: pd.DataFrame
    y: np.ndarray
    timestamps: list[str]
    years: np.ndarray          # année UTC de chaque ligne


def _build(full: FullDataset, train: np.ndarray, val: np.ndarray, test: np.ndarray) -> BenchmarkDataset:
    ts = np.asarray(full.timestamps)

    def make(mask: np.ndarray) -> Split:
        return Split(X=full.X[mask].reset_index(drop=True), y=np.asarray(full.y)[mask], timestamps=list(ts[mask]))

    return BenchmarkDataset(train=make(train), val=make(val), test=make(test))


def split_for_test_year(full: FullDataset, test_year: int) -> BenchmarkDataset:
    """Découpage glissant : entraînement <= T-2, validation T-1, test T.

    Raises:
        ValueError: si une des trois parties est vide (année de test sans passé suffisant ou sans données).
    """
    years = np.asarray(full.years)
    train, val, test = years <= test_year - 2, years == test_year - 1, years == test_year
    for part, mask in (("entraînement", train), ("validation", val), ("test", test)):
        if not mask.any():
            raise ValueError(f"Année de test {test_year} : aucune donnée pour la partie {part}")
    return _build(full, train, val, test)


def split_by_year(X: pd.DataFrame, y: np.ndarray, timestamps: list[str], years: np.ndarray) -> BenchmarkDataset:
    """Découpage fixe : entraînement <= 2021, validation 2022, test >= 2023."""
    years = np.asarray(years)
    full = FullDataset(X=X, y=np.asarray(y), timestamps=timestamps, years=years)
    return _build(full, years <= TRAIN_LAST_YEAR, years == VAL_YEAR, years >= TEST_FIRST_YEAR)
