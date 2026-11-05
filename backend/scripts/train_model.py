import sys
sys.path.insert(0, ".")  # exécution depuis backend/

import time
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
import joblib

from src.prediction.domain.features import build_features

torch.manual_seed(42)

# Import de la base de données pour le ML
df=pd.read_csv("data/dataset_ml.csv")

dt=pd.to_datetime(df["date"], format="%d/%m/%Y")

# Création des features avec le code commun (calendrier, heure cyclique, carrés de température),
# identique à celui du benchmark et de l'API
X=build_features(df)

# Création de l'array de la target
Y=df["consommation"]

# Création des sous-ensembles

# Indices de chaque période
train_mask = dt.dt.year <= 2021
val_mask = dt.dt.year == 2022
test_mask = dt.dt.year >= 2023

# Normalisation : les échelles (min/max) sont apprises sur l'ENTRAÎNEMENT SEUL,
# puis appliquées à tout. Les ajuster sur toutes les données ferait fuiter de
# l'information du jeu de test (data leakage).
scaler_X=MinMaxScaler()
scaler_Y=MinMaxScaler()

scaler_X.fit(X[train_mask])
scaler_Y.fit(Y[train_mask].values.reshape(-1,1))

X_scaled=scaler_X.transform(X)
Y_scaled=scaler_Y.transform(Y.values.reshape(-1,1))

# Split X
X_train = X_scaled[train_mask]
X_val = X_scaled[val_mask]
X_test = X_scaled[test_mask]

# Split Y
Y_train = Y_scaled[train_mask]
Y_val = Y_scaled[val_mask]
Y_test = Y_scaled[test_mask]

print(f"Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")


class ConsumptionModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.LeakyReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.LeakyReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.LeakyReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.network(x)


# Conversion en tenseurs PyTorch
X_train_tensor = torch.FloatTensor(X_train)
Y_train_tensor = torch.FloatTensor(Y_train)
X_val_tensor = torch.FloatTensor(X_val)
Y_val_tensor = torch.FloatTensor(Y_val)

# Mini-batchs construits directement depuis les tenseurs (plus rapide qu'un DataLoader
# pour un petit réseau : pas de surcoût Python par lot)
BATCH_SIZE = 512
n_train = len(X_train_tensor)

# Instanciation
input_size = X_train.shape[1]
model = ConsumptionModel(input_size)

criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
# Relance le LR tous les 50 epochs, puis tous les 100, 200... → s'échappe des minima locaux
scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=50, T_mult=2, eta_min=1e-6)

print(model)

# Entrainement avec early stopping
best_val_loss = float('inf')
best_state = None
patience = 50
patience_counter = 0

best_epoch = 0
t_start = time.perf_counter()

# Ctrl+C interrompt proprement l'entraînement : on garde le meilleur modèle trouvé
# jusque-là et le script passe à l'évaluation et à la sauvegarde.
try:
    for epoch in range(1000):
        model.train()
        perm = torch.randperm(n_train)
        for start in range(0, n_train, BATCH_SIZE):
            idx = perm[start:start + BATCH_SIZE]
            X_batch, Y_batch = X_train_tensor[idx], Y_train_tensor[idx]
            Y_pred = model(X_batch)
            loss = criterion(Y_pred, Y_batch)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        scheduler.step()
        current_lr = optimizer.param_groups[0]['lr']

        # Validation
        model.eval()
        with torch.no_grad():
            Y_val_pred = model(X_val_tensor)
            val_loss = criterion(Y_val_pred, Y_val_tensor).item()

        if epoch % 20 == 0:
            elapsed = time.perf_counter() - t_start
            print(f"Epoch {epoch} | Val loss: {val_loss:.6f} | LR: {current_lr:.2e} "
                  f"| meilleur: {best_val_loss:.6f} (epoch {best_epoch}) | {elapsed:.0f} s")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping à epoch {epoch}")
                break
except KeyboardInterrupt:
    print(f"\nInterrompu à l'epoch {epoch} : on garde le meilleur modèle (epoch {best_epoch}).")

# Recharger le meilleur modèle (gardé en mémoire) et l'écrire une seule fois sur disque
model.load_state_dict(best_state)
torch.save(best_state, "data/best_model.pth")

# Évaluation sur le jeu de test
model.eval()
with torch.no_grad():
    X_test_tensor = torch.FloatTensor(X_test)
    Y_test_pred = model(X_test_tensor).numpy()

# Reconvertir en GW (dé-normaliser)
Y_test_real = scaler_Y.inverse_transform(Y_test)
Y_test_pred_real = scaler_Y.inverse_transform(Y_test_pred)

# Calcul de l'erreur moyenne en GW
mae = abs(Y_test_real - Y_test_pred_real).mean()
print(f"\nErreur moyenne sur le test : {mae:.2f} GW")
print(f"Consommation moyenne réelle : {Y_test_real.mean():.2f} GW")
print(f"Erreur relative : {mae / Y_test_real.mean() * 100:.1f}%")

# Sauvegarder le modèle et les scalers
torch.save(model.state_dict(), "data/model.pth")
joblib.dump(scaler_X, "data/scaler_X.pkl")
joblib.dump(scaler_Y, "data/scaler_Y.pkl")
print("Modèle et scalers sauvegardés !")
