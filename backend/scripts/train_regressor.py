"""Entraîne un modèle du benchmark servi par l'API (météo + calendrier) et l'écrit dans data/<modèle>.pkl.

Même découpage que le MLP servi (train_model.py) : entraînement jusqu'à 2021, validation 2022 (réglage,
puis réentraînement sur entraînement + validation), test 2023 et après, lu une seule fois.
Exécution depuis backend/ : python scripts/train_regressor.py lightgbm   (ou ridge)
"""
import sys
sys.path.insert(0, ".")

import argparse

import joblib
import numpy as np
import pandas as pd

from src.prediction.adapters.ml.lightgbm_regressor import LightGBMRegressor
from src.prediction.adapters.ml.ridge_regressor import RidgeRegressor
from src.prediction.domain.features import build_features

MODELS = {"lightgbm": lambda: LightGBMRegressor(seed=42), "ridge": lambda: RidgeRegressor()}

parser = argparse.ArgumentParser()
parser.add_argument("model", choices=sorted(MODELS))
args = parser.parse_args()

df = pd.read_csv("data/dataset_ml.csv")
year = pd.to_datetime(df["date"], format="%d/%m/%Y").dt.year
X = build_features(df)
y = df["consommation"].to_numpy()

train, val, test = (year <= 2021), (year == 2022), (year >= 2023)
print(f"Train: {train.sum()} | Val: {val.sum()} | Test: {test.sum()}")

model = MODELS[args.model]()
model.fit(X[train], y[train], X[val], y[val])

pred = model.predict(X[test])
mae = float(np.abs(pred - y[test]).mean())
print(f"Erreur moyenne sur le test : {mae:.2f} GW (consommation moyenne {y[test].mean():.2f} GW)")

joblib.dump(model, f"data/{args.model}.pkl")
print(f"Modèle sauvegardé : data/{args.model}.pkl")
