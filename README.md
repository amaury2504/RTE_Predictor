# RTE Predictor

Application de prédiction de la consommation électrique française, entraînée sur les données historiques RTE (2012–2024) et les données météo Open-Meteo.

## Aperçu

L'application permet de :
- **Prédire** la consommation électrique nationale (en GW) à partir de la météo de 13 régions françaises
- **Prédire en temps réel** : météo actuelle auto-remplie via Open-Meteo, comparaison avec la consommation réelle RTE
- **Évaluer la robustesse du modèle** : graphe prédiction vs réel sur les 7 derniers jours

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.14 · FastAPI 0.128 · SQLAlchemy · SQLite |
| ML | PyTorch 2.10 · scikit-learn 1.8 · réseau dense 57→256→128→64→32→1 |
| Auth | JWT (python-jose) · bcrypt |
| Frontend | React 19 · TypeScript · Vite 7 · Tailwind CSS · Recharts |
| Données | RTE eco2mix (consommation nationale) · Open-Meteo (météo historique) |

Architecture backend : **hexagonale** (domain → ports → application → adapters).

---

## Prérequis

- **Python 3.11+** et [Poetry](https://python-poetry.org/docs/#installation)
- **Node.js 18+** et npm
- Git

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/amaury2504/app_electricite_IA.git
cd app_electricite_IA
```

### 2. Backend

```bash
cd backend

# Installer les dépendances Python
poetry install

# Créer le fichier de configuration
cp .env.example .env
```

Éditer `.env` et renseigner une clé JWT :

```bash
# Générer une clé sécurisée
python -c "import secrets; print(secrets.token_hex(32))"
```

Copier le résultat dans `.env` :

```env
SECRET_KEY=<clé_générée>
DURATION_TOKEN=60
DATABASE_URL=sqlite:///./electricity.db
DATABASE_AUTH_URL=sqlite:///./auth.db
URL_WEATHER_BASE=https://archive-api.open-meteo.com/v1/archive?latitude=
URL_WEATHER_PARTIE2=&longitude=
URL_WEATHER_PARTIE3=&start_date=2012-01-01&end_date=2024-12-31&hourly=temperature_2m,wind_speed_10m,relative_humidity_2m
```

### 3. Frontend

```bash
cd ../frontend
npm install
```

---

## Générer les données et entraîner le modèle

Les fichiers `data/` (modèle, scalers, CSV) ne sont pas versionnés. Il faut les générer une fois.

> ⚠️ Les étapes 1 et 2 téléchargent plusieurs centaines de Mo de données. Compter 30–60 min selon la connexion.

Toutes les commandes suivantes s'exécutent depuis `backend/`.

#### Étape 1 — Télécharger les données de consommation RTE

Télécharger le fichier `eco2mix-national-cons-def.csv` depuis [Open Data Réseaux Énergies](https://opendata.reseaux-energies.fr/explore/dataset/eco2mix-national-cons-def) et le placer dans `backend/data/`.

Puis importer en base :

```bash
poetry run python scripts/import_data.py
```

#### Étape 2 — Télécharger les données météo (13 régions, 2012–2024)

```bash
poetry run python scripts/fetch_weather.py
```

#### Étape 3 — Construire le dataset ML

```bash
poetry run python scripts/build_dataset.py
```

#### Étape 4 — Entraîner le modèle

```bash
poetry run python scripts/train_model.py
```

À la fin, `data/model.pth`, `data/scaler_X.pkl` et `data/scaler_Y.pkl` sont créés.

---

## Lancer l'application

### Backend

```bash
cd backend
poetry run uvicorn main:app --reload
```

API disponible sur `http://localhost:8000`  
Documentation Swagger : `http://localhost:8000/docs`

### Frontend

Dans un second terminal :

```bash
cd frontend
npm run dev
```

Interface disponible sur `http://localhost:5173`

---

## Structure du projet

```
app_electricite_IA/
├── backend/
│   ├── src/
│   │   ├── auth/           # Module authentification (JWT, bcrypt)
│   │   ├── electricity/    # Module consommation électrique
│   │   └── prediction/     # Module ML (PyTorch)
│   ├── scripts/            # Import données, entraînement
│   ├── tests/
│   ├── data/               # Modèle + scalers + CSV (non versionné)
│   ├── main.py             # Point d'entrée FastAPI
│   ├── pyproject.toml
│   └── .env.example
└── frontend/
    └── src/
        ├── pages/          # LoginPage, PredictionPage, ModelPerformancePage
        ├── components/     # ResultBanner, ProtectedRoute
        ├── context/        # AuthContext (JWT)
        └── services/       # Appels API
```

---

## Modèle ML

| Paramètre | Valeur |
|-----------|--------|
| Architecture | Dense : 57 → 256 → 128 → 64 → 32 → 1 |
| Features | Heure (sin/cos), températures + T², vents, humidités (13 régions), mois, jour semaine, jour férié |
| Données d'entraînement | 2012–2021 (87 662 heures) |
| Validation | 2022 (8 759 heures) |
| Test | 2023–2024 (17 541 heures) |
| Erreur (MAPE test) | ~5.2 % |
| Unité de sortie | GW |

---

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète JWT (générer avec `secrets.token_hex(32)`) |
| `DURATION_TOKEN` | Durée de validité du token en minutes |
| `DATABASE_URL` | Chemin SQLite pour les données électricité |
| `DATABASE_AUTH_URL` | Chemin SQLite pour l'authentification |
| `URL_WEATHER_BASE/PARTIE2/PARTIE3` | URL Open-Meteo pour l'ingestion historique |

---

## Licence

Projet pédagogique — données RTE sous licence [Licence Ouverte Etalab 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence).
