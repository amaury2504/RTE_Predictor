# RTE Predictor

Prédire la consommation électrique nationale française (en GW, au pas horaire) à partir de la météo de
13 régions et du calendrier, et **comparer honnêtement plusieurs modèles** sur un protocole d'évaluation
strict. L'application web sert un modèle PyTorch ; le benchmark compare Ridge, LightGBM et des références
simples, avec et sans la consommation récente.

Projet pédagogique de bout en bout : données (RTE eco2mix 2012-2024, Open-Meteo), API FastAPI, interface
React, benchmark reproductible, 310 tests automatisés.

## Ce que ce projet montre

- **Une évaluation qui ne triche pas** : évaluation glissante (test T, validation T-1, entraînement jusqu'à
  T-2), jeu de test lu une seule fois, normalisation apprise sur l'entraînement seul, plusieurs graines avec
  écart-type. Une fuite d'information dans la première version a été trouvée et corrigée.
- **Un échec analysé plutôt que masqué** : tous les modèles surestiment la consommation de 2 à 3 GW après 2022.
  Plutôt que de régler un paramètre pour baisser le score, j'ai cherché où et quand l'écart apparaît
  (diagnostic dans [DECISIONS.md](DECISIONS.md)), puis choisi des corrections adaptées au problème.
- **Des références pour juger les modèles** : prévision naïve (même heure la veille) et prévisions publiées par
  RTE. Un modèle n'a de valeur que comparé à elles.
- **Une architecture testable** : hexagonale (domaine, ports, application, adaptateurs). Les calculs de
  variables, de KPI, de découpages et de corrections sont du code pur ; chaque modèle est un adaptateur d'un
  même contrat.

## Résultat principal

Moyenne des années de test 2022, 2023 et 2024 (LightGBM : 5 graines). L'erreur est en GW, pour une
consommation moyenne d'environ 50 GW. Le biais est positif quand le modèle surestime.

| Modèle | MAE | MAE centrée | Biais | Information utilisée |
|---|---|---|---|---|
| Prévision RTE du jour (référence) | 1,05 | 0,68 | -0,95 | prévisions RTE |
| **LightGBM + niveau récent + correction du biais** | **1,21** | 1,21 | +0,12 | météo, calendrier, consommation passée |
| Timestral 209M + météo (aucun entraînement) | 1,30 | 1,30 | -0,08 | consommation passée, température, jours fériés |
| LightGBM + niveau récent | 1,42 | 1,27 | +0,90 | météo, calendrier, consommation passée |
| LightGBM + correction du biais récent | 1,71 | 1,71 | +0,11 | météo, calendrier |
| MLP PyTorch + correction du biais récent (4 graines) | 1,90 | 1,90 | +0,11 | météo, calendrier |
| Timestral 209M, consommation seule | 2,20 | 2,20 | -0,08 | consommation passée seule |
| Lissage exponentiel (Holt-Winters) | 2,39 | 2,39 | -0,03 | consommation passée seule |
| Naïve J-1 (même heure la veille) | 2,57 | 2,57 | -0,01 | consommation passée |
| LightGBM | 2,91 | 1,92 | +2,60 | météo, calendrier |
| Ridge + correction du biais récent | 2,98 | 2,98 | +0,12 | météo, calendrier |
| MLP PyTorch (4 graines) | 3,11 | 2,04 | +2,76 | météo, calendrier |
| Ridge | 3,78 | 3,10 | +2,57 | météo, calendrier |

La « MAE centrée » est l'erreur une fois le biais moyen retiré : elle sépare la qualité de la forme de la
courbe de la justesse du niveau. Le tableau complet, année par année, est dans
[backend/benchmark/RESULTS.md](backend/benchmark/RESULTS.md).

**Ce qu'il faut retenir**

1. LightGBM comprend bien la forme de la consommation (MAE centrée 1,92 GW, contre 2,57 GW pour la naïve),
   mais il est faussé par un changement de niveau de la consommation française après 2022.
2. Ce changement est une marche, apparue à l'automne 2022 et visible à toute heure. Aucune variable de météo
   ou de calendrier ne peut l'absorber. **La cause n'est pas établie** avec ces données ; le calendrier coïncide
   avec la crise de l'énergie, sans que ce soit une preuve.
3. Deux réponses fonctionnent : corriger le biais avec les erreurs récentes (de 2,91 à 1,71 GW, sans réentraîner),
   ou donner au modèle la consommation récente (1,42 GW). Les deux combinées donnent 1,21 GW, au niveau de la
   prévision RTE de la veille (1,21 GW).
4. Les prévisions publiées par RTE restent meilleures (1,05 à 1,21 GW), car elles disposent d'informations que ce
   projet n'a pas.
5. **Un modèle de fondation sans entraînement** (Timestral 209M de Mistral, avec température et jours fériés)
   fait 1,30 GW, mieux que tous nos modèles de la piste A corrigés. Avec la météo observée comme prévision
   parfaite, ce qui l'avantage face à RTE.
6. **Le MLP PyTorch souffre du même défaut que LightGBM** (MAE centrée 2,04 GW, proche des 1,92 GW de LightGBM) et
   il est instable d'une graine à l'autre (± 0,4 à 0,7 GW en 2023 et 2024, contre ± 0,01 pour LightGBM). Sur des
   données tabulaires, le réseau de neurones n'apporte rien de plus que les arbres boostés.

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.14 · FastAPI · SQLAlchemy · SQLite |
| ML | PyTorch · LightGBM · scikit-learn |
| Auth | JWT (python-jose) · bcrypt |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS · Recharts |
| Données | RTE eco2mix (consommation nationale) · Open-Meteo (météo historique) |

## L'application

- **Prédire** la consommation à partir de la météo de 13 régions, avec la météo actuelle remplie automatiquement.
- **Comparer** la prédiction à la consommation réelle publiée par RTE.
- **Évaluer la robustesse du modèle** : prédiction contre réel sur les 7 derniers jours, avec les KPI
  (MAE, RMSE, MAPE, biais, pointe, découpages par heure et par jour).

L'API sert le modèle MLP PyTorch ; le benchmark est un outil séparé en ligne de commande.

---

## Prérequis

- **Python 3.11+** et [Poetry](https://python-poetry.org/docs/#installation)
- **Node.js 18+** et npm
- Git

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/amaury2504/RTE_Predictor.git
cd RTE_Predictor
```

### 2. Backend

```bash
cd backend
poetry install
cp .env.example .env
```

Éditer `.env` et renseigner une clé JWT :

```bash
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

## Générer les données

Les fichiers `data/` (CSV, modèle) ne sont pas versionnés. Il faut les générer une fois. Les étapes 1 et 2
téléchargent plusieurs centaines de Mo ; compter 30 à 60 minutes selon la connexion.
Toutes les commandes s'exécutent depuis `backend/`.

1. **Consommation RTE** : télécharger `eco2mix-national-cons-def.csv` depuis
   [Open Data Réseaux Énergies](https://opendata.reseaux-energies.fr/explore/dataset/eco2mix-national-cons-def),
   le placer dans `backend/data/`, puis `poetry run python scripts/import_data.py`.
2. **Météo (13 régions, 2012-2024)** : `poetry run python scripts/fetch_weather.py`
3. **Jeu de données** : `poetry run python scripts/build_dataset.py` (crée `data/dataset_ml.csv`)
4. **Modèle de l'API** : `poetry run python scripts/train_model.py` (crée `data/model.pth` et les normaliseurs)

## Lancer l'application

```bash
# Terminal 1
cd backend
poetry run uvicorn main:app --reload      # http://localhost:8000 (Swagger : /docs)

# Terminal 2
cd frontend
npm run dev                               # http://localhost:5173
```

## Lancer le benchmark

Depuis `backend/` (nécessite `data/dataset_ml.csv` et `data/eco2mix-national-cons-def.csv`) :

```bash
python scripts/run_benchmark.py                                   # tous les modèles, 3 années de test, 5 graines
python scripts/run_benchmark.py --models lightgbm lightgbm_niveau --seeds 3
python scripts/run_benchmark.py --models mlp --seeds 1 --test-years 2024 --max-epochs 3 --out essai
```

Les résultats sont écrits dans `benchmark/` (`results.json` et `RESULTS.md`). Les modèles disponibles :

| Nom | Description |
|---|---|
| `ridge`, `lightgbm`, `mlp` | Piste A : météo et calendrier |
| `*_recent` | Idem, avec les années récentes pondérées (demi-vie de 3 ans, choisie a priori, non réglée) |
| `*_corr` (ajoutés automatiquement) | Idem, avec correction du biais des 28 derniers jours |
| `ridge_niveau`, `lightgbm_niveau` | Piste B : en plus, la consommation récente connue jusqu'à 48 h avant |
| `ts_holt_winters` (ajouté automatiquement) | Série temporelle seule : lissage exponentiel saisonnier hebdomadaire, paramètres choisis sur la validation |
| `ts_timestral_209m`, `ts_timestral_28m` et leurs variantes `_meteo` (ajoutés si le paquet est installé) | Modèle de fondation de Mistral (209 M ou 28 M de paramètres), sans entraînement : consommation seule, ou avec température et jours fériés |
| `ref_*` (ajoutés automatiquement) | Références : naïves (J-1, J-2, semaine) et prévisions RTE |

**Tout lancer d'une traite** (par exemple la nuit) : `powershell -ExecutionPolicy Bypass -File backend\scripts\run_night.ps1`.
Le MLP passe en premier (4 graines), puis le reste. Chaque exécution terminée est sauvegardée dans
`backend/benchmark_cache/` : après une interruption, relancer la même commande reprend là où elle s'est arrêtée.

**Timestral** (facultatif) : `pip install git+https://github.com/mistralai/timestral.git` dans l'environnement
du backend. Sans lui, le benchmark ignore ces deux lignes et le signale.

Les tests : `cd backend && python -m pytest tests -q` (310 tests).

---

## Structure du projet

```
RTE_Predictor/
├── CDC.md                  # Cahier des charges : protocole, avancement, points ouverts
├── DECISIONS.md            # Journal des décisions : diagnostic, choix, limites, résultats
├── backend/
│   ├── src/
│   │   ├── auth/           # Authentification (JWT, bcrypt)
│   │   ├── electricity/    # Données de consommation
│   │   └── prediction/
│   │       ├── domain/         # Variables, découpages, KPI, correction du biais, niveau récent, lissage
│   │       ├── ports/          # Contrat d'un modèle (RegressorPort)
│   │       ├── application/    # Benchmark, références
│   │       └── adapters/       # Modèles (Ridge, LightGBM, MLP), chargement des données
│   ├── scripts/            # Données, entraînement, run_benchmark.py
│   ├── benchmark/          # Résultats du benchmark
│   ├── tests/
│   └── main.py             # Point d'entrée FastAPI
└── frontend/
    └── src/                # Pages, composants, contexte d'authentification, services d'API
```

## Déploiement

Une configuration Docker prête à l'emploi est dans [deploy/](deploy/README.md) : API, frontend, reverse proxy
commun avec HTTPS automatique, volume pour le modèle et les bases. Un serveur de 2 vCPU et 4 Go de RAM suffit.

## Limites connues

- Le modèle de l'API est le MLP initial ; les modèles du benchmark ne sont pas encore servis par l'API.
- Le mode invité (`POST /auth/guest`) délivre un jeton sans identifiants : voulu pour la démo. Il peut lire et
  prédire mais pas écrire, les tentatives sont limitées par adresse IP, et `GUEST_ENABLED=false` le coupe.
- Les fichiers de déploiement (Docker, reverse proxy) sont écrits mais pas encore éprouvés sur un vrai serveur.
- La cause du changement de niveau de la consommation après 2022 n'est pas établie.

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète JWT (générer avec `secrets.token_hex(32)`) |
| `DURATION_TOKEN` | Durée de validité du token en minutes |
| `DATABASE_URL` | Chemin SQLite pour les données électricité |
| `DATABASE_AUTH_URL` | Chemin SQLite pour l'authentification |
| `URL_WEATHER_BASE/PARTIE2/PARTIE3` | URL Open-Meteo pour l'ingestion historique |

## Licence

Projet pédagogique. Données RTE sous [Licence Ouverte Etalab 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence).
