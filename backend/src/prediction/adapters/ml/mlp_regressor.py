import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

from src.prediction.adapters.ml.PyTorchPrediction import ConsumptionModel
from src.prediction.ports.regressor import RegressorPort


class MLPRegressor(RegressorPort):
    """Réseau de neurones dense (le modèle actuel de l'application), comparable dans le benchmark.

    Les normaliseurs sont ajustés dans `fit`, sur l'entraînement seul : aucune fuite possible
    depuis la validation ou le test.
    """

    name = "mlp"
    stochastic = True

    def __init__(
        self,
        seed: int = 42,
        max_epochs: int = 1000,
        patience: int = 50,
        batch_size: int = 512,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        verbose: bool = False,
    ):
        self.seed = seed
        self.max_epochs = max_epochs
        self.patience = patience
        self.batch_size = batch_size
        self.lr = lr
        self.weight_decay = weight_decay
        self.verbose = verbose

        self.scaler_X: MinMaxScaler | None = None
        self.scaler_Y: MinMaxScaler | None = None
        self.model: ConsumptionModel | None = None
        self.feature_names_: list[str] | None = None
        self.best_epoch_: int | None = None

    def fit(self, X_train: pd.DataFrame, y_train: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray) -> None:
        torch.manual_seed(self.seed)
        self.feature_names_ = list(X_train.columns)

        # Normalisation apprise sur l'entraînement seul
        self.scaler_X = MinMaxScaler().fit(X_train)
        self.scaler_Y = MinMaxScaler().fit(np.asarray(y_train).reshape(-1, 1))

        X_tr = torch.FloatTensor(self.scaler_X.transform(X_train))
        y_tr = torch.FloatTensor(self.scaler_Y.transform(np.asarray(y_train).reshape(-1, 1)))
        X_va = torch.FloatTensor(self.scaler_X.transform(X_val[self.feature_names_]))
        y_va = torch.FloatTensor(self.scaler_Y.transform(np.asarray(y_val).reshape(-1, 1)))

        self.model = ConsumptionModel(input_size=X_tr.shape[1])
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=50, T_mult=2, eta_min=1e-6)

        n_train = len(X_tr)
        best_val_loss = float("inf")
        best_state = None
        patience_counter = 0

        for epoch in range(self.max_epochs):
            self.model.train()
            perm = torch.randperm(n_train)
            for start in range(0, n_train, self.batch_size):
                idx = perm[start:start + self.batch_size]
                loss = criterion(self.model(X_tr[idx]), y_tr[idx])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            scheduler.step()

            self.model.eval()
            with torch.no_grad():
                val_loss = criterion(self.model(X_va), y_va).item()

            if self.verbose and epoch % 20 == 0:
                print(f"  [mlp seed={self.seed}] epoch {epoch} | val loss {val_loss:.6f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.best_epoch_ = epoch
                patience_counter = 0
                best_state = {k: v.clone() for k, v in self.model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= self.patience:
                    break

        self.model.load_state_dict(best_state)
        self.model.eval()

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Le modèle doit être entraîné (fit) avant de prédire")
        scaled = torch.FloatTensor(self.scaler_X.transform(X[self.feature_names_]))
        with torch.no_grad():
            normalized = self.model(scaled).numpy()
        return self.scaler_Y.inverse_transform(normalized).ravel()
