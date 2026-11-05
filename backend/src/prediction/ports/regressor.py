from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class RegressorPort(ABC):
    """Contrat d'un modèle comparable dans le benchmark.

    Chaque modèle est un adaptateur qui gère SA propre préparation des données
    (normalisation, etc.) à l'intérieur de `fit`, uniquement à partir des données fournies.
    Le benchmark ne fait que lui fournir les mêmes variables et le même découpage.
    """

    name: str = "regressor"
    # True si le résultat dépend d'un aléa (initialisation, mélange) : le benchmark répète alors
    # l'exécution avec plusieurs graines.
    stochastic: bool = False
    # Demi-vie (en années) de la pondération des années récentes ; None = toutes les lignes pèsent pareil.
    # Le benchmark calcule les poids et les fournit à `fit` ; c'est le modèle qui déclare en vouloir.
    recency_half_life_years: float | None = None
    # Prédictions sur la validation faites AVANT un éventuel réentraînement qui inclurait la validation.
    # Le benchmark les utilise pour les KPI de validation (sinon ils seraient mesurés sur des données apprises).
    val_predictions_: np.ndarray | None = None

    @abstractmethod
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame,
        y_val: np.ndarray,
        w_train: np.ndarray | None = None,
        w_val: np.ndarray | None = None,
    ) -> None:
        """Entraîne le modèle.

        La validation sert au réglage et à l'arrêt anticipé, jamais le test. Un modèle peut ensuite se
        réentraîner sur entraînement + validation avec le budget trouvé (nombre d'arbres, d'epochs...).
        `w_train` et `w_val` sont des poids d'échantillons optionnels (pondération des années récentes).
        """

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Retourne les prédictions en GW, une par ligne de X."""
