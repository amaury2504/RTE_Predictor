"""Entraîne un modèle servi par l'API et l'écrit dans data/<modèle>_niveau.pkl.

Le modèle reçoit la météo, le calendrier ET le niveau récent de la consommation (piste B du benchmark) : sans lui,
les modèles surestiment la consommation de 2 à 3 GW depuis 2022 (voir DECISIONS.md).

Découpage de la dernière année du benchmark (évaluation glissante, test 2024) : entraînement jusqu'à 2022, validation
2023 (réglage, puis réentraînement sur entraînement + validation), test 2024, lu une seule fois. Les années les plus
récentes sont donc apprises par le modèle servi.

Exécution depuis backend/ : python scripts/train_regressor.py lightgbm   (ou ridge, mlp)
"""
import sys
sys.path.insert(0, ".")

import argparse

import joblib
import numpy as np

from src.prediction.adapters.datasets.csv_dataset import load_full_dataset
from src.prediction.adapters.ml.lightgbm_regressor import LightGBMRegressor
from src.prediction.adapters.ml.mlp_regressor import MLPRegressor
from src.prediction.adapters.ml.ridge_regressor import RidgeRegressor

TEST_YEAR = 2024

MODELS = {
    "lightgbm": lambda: LightGBMRegressor(seed=42),
    "ridge": lambda: RidgeRegressor(),
    "mlp": lambda: MLPRegressor(seed=42, verbose=True),
}

parser = argparse.ArgumentParser()
parser.add_argument("model", choices=sorted(MODELS))
args = parser.parse_args()

full = load_full_dataset("data/dataset_ml.csv", level_features=True)
train, val, test = (full.years <= TEST_YEAR - 2), (full.years == TEST_YEAR - 1), (full.years == TEST_YEAR)
print(f"Variables : {full.X.shape[1]} | Train: {train.sum()} | Val: {val.sum()} | Test: {test.sum()}", flush=True)

model = MODELS[args.model]()
model.fit(full.X[train], full.y[train], full.X[val], full.y[val])

pred = model.predict(full.X[test])
error = pred - full.y[test]
ape = np.abs(error) / full.y[test] * 100
print(f"Test {TEST_YEAR} : MAE {np.abs(error).mean():.2f} GW | biais {error.mean():+.2f} GW | MAPE {ape.mean():.1f} % "
      f"| heures à plus de 8 % : {(ape > 8).mean() * 100:.0f} % | consommation moyenne {full.y[test].mean():.1f} GW")

joblib.dump(model, f"data/{args.model}_niveau.pkl")
print(f"Modèle sauvegardé : data/{args.model}_niveau.pkl", flush=True)
