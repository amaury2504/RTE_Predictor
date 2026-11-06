import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import MinMaxScaler

from src.prediction.adapters.ml.PyTorchPrediction import ConsumptionModel
from src.prediction.ports.regressor import RegressorPort


class MLPRegressor(RegressorPort):
    """Réseau de neurones dense (le modèle actuel de l'application), comparable dans le benchmark.

    Étape 1 : entraînement avec arrêt anticipé sur la validation. Les normaliseurs sont appris sur
    l'entraînement seul. Étape 2 (si `refit_on_val`) : réentraînement depuis zéro sur entraînement +
    validation, pour le nombre d'epochs trouvé, avec des normaliseurs appris sur ces mêmes données.
    Le test n'est jamais vu pendant l'entraînement.
    """

    stochastic = True

    def __init__(
        self,
        seed: int = 42,
        max_epochs: int = 1000,
        patience: int = 50,
        batch_size: int = 512,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        refit_on_val: bool = True,
        recency_half_life_years: float | None = None,
        verbose: bool = False,
        name: str | None = None,
    ):
        self.seed = seed
        self.max_epochs = max_epochs
        self.patience = patience
        self.batch_size = batch_size
        self.lr = lr
        self.weight_decay = weight_decay
        self.refit_on_val = refit_on_val
        self.recency_half_life_years = recency_half_life_years
        self.verbose = verbose
        self.name = name or ("mlp_recent" if recency_half_life_years else "mlp")

        self.scaler_X: MinMaxScaler | None = None
        self.scaler_Y: MinMaxScaler | None = None
        self.model: ConsumptionModel | None = None
        self.feature_names_: list[str] | None = None
        self.best_epoch_: int | None = None
        self.val_predictions_: np.ndarray | None = None

    def _train(self, X_tr, y_tr, w_tr, X_va, y_va, epochs: int):
        """Entraîne un réseau. Avec une validation : arrêt anticipé et meilleur état restauré ;
        sans validation : exactement `epochs` epochs. Retourne (réseau, meilleure epoch)."""
        torch.manual_seed(self.seed)
        model = ConsumptionModel(input_size=X_tr.shape[1])
        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=50, T_mult=2, eta_min=1e-6)

        n_train = len(X_tr)
        best_val_loss, best_state, best_epoch, patience_counter = float("inf"), None, epochs - 1, 0

        for epoch in range(epochs):
            model.train()
            perm = torch.randperm(n_train)
            for start in range(0, n_train, self.batch_size):
                idx = perm[start:start + self.batch_size]
                squared_error = (model(X_tr[idx]) - y_tr[idx]).squeeze(1) ** 2
                loss = squared_error.mean() if w_tr is None else (squared_error * w_tr[idx]).mean()
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            scheduler.step()

            if X_va is None:
                continue

            model.eval()
            with torch.no_grad():
                val_loss = torch.mean((model(X_va) - y_va) ** 2).item()

            if self.verbose and epoch % 20 == 0:
                print(f"  [{self.name} seed={self.seed}] epoch {epoch} | val loss {val_loss:.6f}")

            if val_loss < best_val_loss:
                best_val_loss, best_epoch, patience_counter = val_loss, epoch, 0
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= self.patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)
        model.eval()
        return model, best_epoch

    @staticmethod
    def _weights(w) -> torch.Tensor | None:
        """Poids de moyenne 1, pour que l'échelle de la perte ne dépende pas de la pondération."""
        return None if w is None else torch.FloatTensor(np.asarray(w, dtype=float) / np.mean(w))

    def fit(self, X_train, y_train, X_val, y_val, w_train=None, w_val=None) -> None:
        self.feature_names_ = list(X_train.columns)
        y_tr = np.asarray(y_train).reshape(-1, 1)
        y_va = np.asarray(y_val).reshape(-1, 1)

        # Étape 1 : normaliseurs appris sur l'entraînement seul, arrêt anticipé sur la validation
        self.scaler_X = MinMaxScaler().fit(X_train)
        self.scaler_Y = MinMaxScaler().fit(y_tr)
        X_va_scaled = torch.FloatTensor(self.scaler_X.transform(X_val[self.feature_names_]))
        model, best_epoch = self._train(
            torch.FloatTensor(self.scaler_X.transform(X_train)),
            torch.FloatTensor(self.scaler_Y.transform(y_tr)),
            self._weights(w_train),
            X_va_scaled,
            torch.FloatTensor(self.scaler_Y.transform(y_va)),
            self.max_epochs,
        )
        self.model, self.best_epoch_ = model, best_epoch
        self.val_predictions_ = self.predict(X_val)  # avant tout réentraînement incluant la validation

        # Étape 2 : réentraînement sur entraînement + validation, pour le nombre d'epochs trouvé
        if self.refit_on_val:
            X_all = pd.concat([X_train, X_val[self.feature_names_]], ignore_index=True)
            y_all = np.concatenate([y_tr, y_va])
            w_all = None if w_train is None or w_val is None else np.concatenate([w_train, w_val])
            self.scaler_X = MinMaxScaler().fit(X_all)
            self.scaler_Y = MinMaxScaler().fit(y_all)
            self.model, _ = self._train(
                torch.FloatTensor(self.scaler_X.transform(X_all)),
                torch.FloatTensor(self.scaler_Y.transform(y_all)),
                self._weights(w_all),
                None, None,
                best_epoch + 1,
            )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Le modèle doit être entraîné (fit) avant de prédire")
        scaled = torch.FloatTensor(self.scaler_X.transform(X[self.feature_names_]))
        with torch.no_grad():
            normalized = self.model(scaled).numpy()
        return self.scaler_Y.inverse_transform(normalized).ravel()
