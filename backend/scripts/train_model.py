import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
import holidays
from torch.utils.data import TensorDataset, DataLoader
import joblib

torch.manual_seed(42)

# Import de la base de données pour le ML
df=pd.read_csv("data/dataset_ml.csv")

# Retrouver les features du mois et des jours de la semaine
dt=pd.to_datetime(df["date"], format="%d/%m/%Y")

df["month"]=dt.dt.month
df["dayofweek"]=dt.dt.dayofweek

# Ajout de features
fr_holidays=holidays.France()
df["is_holiday"]=dt.apply(lambda x:1 if x in fr_holidays else 0)

# Encodage cyclique de l'heure (remplace le raw hour)
df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
df = df.drop(columns=["hour"])

# Pour chaque colonne de température, créer son carré
for col in df.columns:
    if col.startswith("temperature_"):
        df[col + "_squared"] = df[col] ** 2

# Création de l'array des features
X=df.drop(columns=["date","consommation"])

# Création de l'array de la target
Y=df["consommation"]

scaler_X=MinMaxScaler()
scaler_Y=MinMaxScaler()

X_scaled=scaler_X.fit_transform(X)
Y_scaled=scaler_Y.fit_transform(Y.values.reshape(-1,1))

# Création des sous-ensembles

# Indices de chaque période
train_mask = dt.dt.year <= 2021
val_mask = dt.dt.year == 2022
test_mask = dt.dt.year >= 2023

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

# DataLoader
train_dataset = TensorDataset(X_train_tensor, Y_train_tensor)
train_loader = DataLoader(train_dataset, batch_size=512, shuffle=True)

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
patience = 150
patience_counter = 0

for epoch in range(1000):
    model.train()
    for X_batch, Y_batch in train_loader:
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
        print(f"Epoch {epoch} | Val loss: {val_loss:.6f} | LR: {current_lr:.2e}")

    # Early stopping
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        patience_counter = 0
        torch.save(model.state_dict(), "data/best_model.pth")
    else:
        patience_counter += 1
        if patience_counter >= patience:
            print(f"Early stopping à epoch {epoch}")
            break

# Recharger le meilleur modèle
model.load_state_dict(torch.load("data/best_model.pth"))

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
