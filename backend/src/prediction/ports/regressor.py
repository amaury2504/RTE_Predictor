from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class RegressorPort(ABC):
    """Contrat d'un modèle comparable dans le benchmark.

    Chaque modèle est un adaptateur qui gère SA propre préparation des données
    (normalisation, etc.) à l'intérieur de `fit`, uniquement à partir de l'entraînement.
    Le benchmark ne fait que lui fournir les mêmes variables et le même découpage.
    """

    name: str = "regressor"
    # True si le résultat dépend d'un aléa (initialisation, mélange) : le benchmark répète alors
    # l'exécution avec plusieurs graines.
    stochastic: bool = False

    @abstractmethod
    def fit(self, X_train: pd.DataFrame, y_train: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray) -> None:
        """Entraîne le modèle. La validation sert au réglage et à l'arrêt anticipé, jamais le test."""

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Retourne les prédictions en GW, une par ligne de X."""
