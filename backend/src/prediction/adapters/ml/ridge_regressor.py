import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from src.prediction.ports.regressor import RegressorPort

# Variables numériques traitées comme des catégories : un modèle linéaire ne sait pas lire « mois = 7 »
# comme autre chose qu'un nombre croissant, alors que la consommation n'est pas linéaire dans le mois.
CATEGORICAL = {"month": range(1, 13), "dayofweek": range(0, 7)}


class RidgeRegressor(RegressorPort):
    """Régression linéaire régularisée (Ridge) : référence linéaire du benchmark.

    Préparation propre au modèle : mois et jour de la semaine en variables 0/1, puis normalisation
    apprise sur les données d'entraînement seules. Le coefficient de régularisation `alpha` est choisi
    sur la validation (plus petite MAE) parmi une grille, puis, si `refit_on_val`, le modèle est
    réentraîné sur entraînement + validation avec cet `alpha` (normalisation recalculée).

    Le modèle est déterministe : une seule exécution suffit.
    """

    stochastic = False

    def __init__(
        self,
        alphas: tuple[float, ...] = (0.01, 0.1, 1, 10, 100, 1000),
        refit_on_val: bool = True,
        recency_half_life_years: float | None = None,
    ):
        self.alphas = alphas
        self.refit_on_val = refit_on_val
        self.recency_half_life_years = recency_half_life_years
        self.name = "ridge_recent" if recency_half_life_years else "ridge"

        self.model: Ridge | None = None
        self.scaler: StandardScaler | None = None
        self.columns_: list[str] | None = None
        self.best_alpha_: float | None = None
        self.val_predictions_: np.ndarray | None = None

    def _design(self, X: pd.DataFrame) -> np.ndarray:
        """Matrice numérique : variables d'origine (sauf catégories) + colonnes 0/1 des catégories."""
        parts = [X.drop(columns=[c for c in CATEGORICAL if c in X.columns])]
        for column, values in CATEGORICAL.items():
            if column in X.columns:
                parts.append(pd.DataFrame(
                    {f"{column}_{v}": (X[column].to_numpy() == v).astype(float) for v in values}, index=X.index))
        design = pd.concat(parts, axis=1)
        if self.columns_ is None:
            self.columns_ = list(design.columns)
        return design[self.columns_].to_numpy(dtype=float)

    def _fit_once(self, A: np.ndarray, y: np.ndarray, w: np.ndarray | None, alpha: float) -> tuple[StandardScaler, Ridge]:
        scaler = StandardScaler().fit(A)
        model = Ridge(alpha=alpha).fit(scaler.transform(A), y, sample_weight=w)
        return scaler, model

    def fit(self, X_train, y_train, X_val, y_val, w_train=None, w_val=None) -> None:
        self.columns_ = None
        At, Av = self._design(X_train), self._design(X_val)
        yt, yv = np.asarray(y_train, dtype=float), np.asarray(y_val, dtype=float)

        # Choix d'alpha sur la validation (non pondérée, comme pour les autres modèles)
        best = None
        for alpha in self.alphas:
            scaler, model = self._fit_once(At, yt, w_train, alpha)
            pred = model.predict(scaler.transform(Av))
            mae = float(np.mean(np.abs(pred - yv)))
            if best is None or mae < best[0]:
                best = (mae, alpha, scaler, model, pred)
        _, self.best_alpha_, self.scaler, self.model, self.val_predictions_ = best

        if self.refit_on_val:
            weights = None if w_train is None or w_val is None else np.concatenate([w_train, w_val])
            self.scaler, self.model = self._fit_once(
                np.vstack([At, Av]), np.concatenate([yt, yv]), weights, self.best_alpha_)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Le modèle doit être entraîné (fit) avant de prédire")
        return self.model.predict(self.scaler.transform(self._design(X)))
