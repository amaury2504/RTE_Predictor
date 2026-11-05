import lightgbm as lgb
import numpy as np
import pandas as pd

from src.prediction.ports.regressor import RegressorPort


def _normalize(weights: np.ndarray | None) -> np.ndarray | None:
    """Poids de moyenne 1 (leur échelle ne doit pas influencer la régularisation de LightGBM)."""
    return None if weights is None else np.asarray(weights, dtype=float) / np.mean(weights)


class LightGBMRegressor(RegressorPort):
    """Arbres de décision boostés (LightGBM), comparables dans le benchmark.

    Les arbres n'ont pas besoin de normalisation : les variables sont utilisées telles quelles.
    Étape 1 : entraînement avec arrêt anticipé sur la validation (on garde le nombre d'arbres qui
    minimise la MAE de validation). Étape 2 (si `refit_on_val`) : réentraînement sur entraînement +
    validation avec ce nombre d'arbres, pour que le modèle apprenne aussi l'année la plus récente.
    Le test n'est jamais vu pendant l'entraînement.

    L'échantillonnage des lignes et des variables dépend de la graine, d'où `stochastic = True`.
    """

    stochastic = True

    def __init__(
        self,
        seed: int = 42,
        n_estimators: int = 5000,
        learning_rate: float = 0.05,
        num_leaves: int = 63,
        min_child_samples: int = 20,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        early_stopping_rounds: int = 100,
        refit_on_val: bool = True,
        recency_half_life_years: float | None = None,
        name: str | None = None,
    ):
        self.seed = seed
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.early_stopping_rounds = early_stopping_rounds
        self.refit_on_val = refit_on_val
        self.recency_half_life_years = recency_half_life_years
        self.name = name or ("lightgbm_recent" if recency_half_life_years else "lightgbm")

        self.model: lgb.LGBMRegressor | None = None
        self.feature_names_: list[str] | None = None
        self.best_iteration_: int | None = None
        self.val_predictions_: np.ndarray | None = None

    def _new_model(self, n_estimators: int) -> lgb.LGBMRegressor:
        return lgb.LGBMRegressor(
            objective="regression",
            n_estimators=n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            min_child_samples=self.min_child_samples,
            subsample=self.subsample,
            subsample_freq=1,  # active l'échantillonnage des lignes à chaque arbre
            colsample_bytree=self.colsample_bytree,
            random_state=self.seed,
            deterministic=True,
            force_row_wise=True,
            verbose=-1,
        )

    def fit(self, X_train, y_train, X_val, y_val, w_train=None, w_val=None) -> None:
        self.feature_names_ = list(X_train.columns)
        # Tableaux numpy : l'ordre des colonnes est celui de l'entraînement, sans dépendre des noms
        Xt = X_train[self.feature_names_].to_numpy()
        Xv = X_val[self.feature_names_].to_numpy()
        yt, yv = np.asarray(y_train), np.asarray(y_val)

        # Étape 1 : entraînement, arrêt anticipé sur la validation (non pondérée)
        self.model = self._new_model(self.n_estimators)
        self.model.fit(
            Xt, yt,
            sample_weight=_normalize(w_train),
            eval_X=Xv, eval_y=yv,
            eval_metric="l1",
            callbacks=[lgb.early_stopping(self.early_stopping_rounds, verbose=False)],
        )
        self.best_iteration_ = self.model.best_iteration_
        self.val_predictions_ = self.model.predict(Xv)  # avant tout réentraînement incluant la validation

        # Étape 2 : réentraînement sur entraînement + validation, avec le nombre d'arbres trouvé
        if self.refit_on_val:
            weights = None if w_train is None or w_val is None else _normalize(np.concatenate([w_train, w_val]))
            self.model = self._new_model(max(1, self.best_iteration_))
            self.model.fit(np.vstack([Xt, Xv]), np.concatenate([yt, yv]), sample_weight=weights)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Le modèle doit être entraîné (fit) avant de prédire")
        return self.model.predict(X[self.feature_names_].to_numpy())
