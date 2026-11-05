"""Découpage temporel commun à tous les modèles du benchmark.

- entraînement : jusqu'à 2021 inclus
- validation   : 2022
- test         : à partir de 2023 (utilisé une seule fois par modèle, à la fin)

L'année est celle du jour UTC de la donnée (même définition que l'entraînement d'origine).
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


def split_by_year(X: pd.DataFrame, y: np.ndarray, timestamps: list[str], years: np.ndarray) -> BenchmarkDataset:
    """Sépare les lignes en entraînement / validation / test selon leur année UTC."""
    years = np.asarray(years)
    masks = {
        "train": years <= TRAIN_LAST_YEAR,
        "val": years == VAL_YEAR,
        "test": years >= TEST_FIRST_YEAR,
    }
    ts = np.asarray(timestamps)

    def make(mask: np.ndarray) -> Split:
        return Split(X=X[mask].reset_index(drop=True), y=np.asarray(y)[mask], timestamps=list(ts[mask]))

    return BenchmarkDataset(train=make(masks["train"]), val=make(masks["val"]), test=make(masks["test"]))
