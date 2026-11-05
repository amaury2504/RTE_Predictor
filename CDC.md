# Cahier des charges : benchmark de modèles de prédiction

## 1. Objectif

Disposer d'un benchmark reproductible pour comparer plusieurs modèles sur un même cas d'usage :
prédire la consommation électrique nationale française (en GW, au pas horaire).

À terme, pouvoir affirmer, chiffres à l'appui, quel modèle est le meilleur et dans quelles conditions.
Une affirmation n'est recevable que si elle repose sur le protocole de la section 3.

## 2. Pistes de comparaison

Les modèles ne sont comparés qu'à l'intérieur d'une même piste (les entrées diffèrent).

| Piste | Entrées | Statut |
|---|---|---|
| A | Météo (13 régions) et calendrier | Sprint 1 |
| B | Piste A + historique de consommation (variables retardées, séquences) | Sprint 2 |

## 3. Protocole d'évaluation (commun à tous les modèles)

- **Données :** `eco2mix-national-cons-def.csv` agrégé à l'heure (GW) et météo Open-Meteo, 13 régions.
- **Découpage temporel :** entraînement jusqu'à 2021 inclus, validation 2022, test à partir de 2023.
- **Jeu de test :** utilisé une seule fois par modèle, à la fin. Aucun réglage dessus.
- **Normalisation :** apprise sur l'entraînement seul (pas de fuite vers validation/test).
- **Variables d'entrée :** identiques pour tous les modèles d'une même piste, construites par un code commun.
- **Réglage :** budget identique pour chaque modèle (même nombre d'essais), évalué sur la validation.
- **Aléa :** modèles à initialisation aléatoire exécutés avec 5 graines. On publie la moyenne et l'écart-type.
- **Métriques :** MAE (GW), RMSE (GW), MAPE (%), temps d'entraînement, temps de prédiction.
- **Reproductibilité :** une commande relance l'ensemble et régénère le tableau de résultats.

## 4. Modèles du sprint 1 (piste A)

| # | Modèle | Rôle |
|---|---|---|
| 1 | Prévision naïve (même heure, semaine précédente) | Référence plancher, classée à part : elle utilise la consommation passée |
| 2 | Ridge | Référence linéaire |
| 3 | LightGBM | Arbres boostés |
| 4 | MLP PyTorch (modèle actuel) | 5 graines |

Avancement : un modèle à la fois. Un modèle est terminé quand il est évalué selon le protocole et que
ses résultats figurent dans le tableau.

- [x] Base commune : variables d'entrée (`domain/features.py`), découpage (`domain/dataset.py`), KPI (`domain/kpi.py`),
      contrat de modèle (`ports/regressor.py`), orchestration (`application/benchmark.py`), lancement
      (`scripts/run_benchmark.py`).
- [x] MLP PyTorch branché sur la base commune (normalisation apprise dans `fit`, sur l'entraînement seul).
- [ ] Lancement complet du MLP (5 graines) et enregistrement des résultats dans `benchmark/`.
- [ ] Prévision naïve (référence), Ridge, LightGBM.

## 5. Architecture (hexagonale, conservée)

Le module `src/prediction` garde ses couches :

- `domain/` : objets métier (`PredictionInput`, `PredictionResult`, `ModelMetrics`). Indépendant de tout modèle.
- `ports/` : contrats (`PredictionModelPort`, `EvaluateModelPort`) et, pour le benchmark, un contrat
  d'entraînement. Aucun détail propre à un modèle.
- `application/` : cas d'usage, qui orchestrent via les ports.
- `adapters/ml/` : **un adaptateur par modèle** (naïf, Ridge, LightGBM, PyTorch). Chacun gère ses propres
  artefacts (fichiers sauvegardés) et sa propre façon de prédire.

Règles :
- Le domaine et les ports ne dépendent d'aucune bibliothèque de modèle.
- La construction des variables d'entrée est **partagée** entre les modèles, pour que la comparaison soit équitable.
- Le modèle naïf a besoin de l'historique de consommation : il passe par un port d'accès à l'historique,
  pas par `PredictionInput`.

## 6. Livrables du sprint 1

- Code commun du benchmark (chargement, découpage, variables, métriques, mesure du temps).
- Un adaptateur par modèle, avec sa configuration.
- Un script de lancement unique et un fichier de résultats (CSV ou JSON) versionné.
- Un test vérifiant qu'aucune donnée de validation ou de test n'est utilisée à l'entraînement.
- Un tableau de classement dans le README, avec la commande pour reproduire.

## 7. Définition de « terminé »

Une seule commande relance les quatre modèles et produit un classement identique d'une exécution à l'autre
(à l'écart-type près pour les modèles à graine).

## 8. Hors périmètre du sprint 1

- Piste B et modèles de séquence (GRU, CNN 1D, TCN, PatchTST).
- Modèles de fondation (Timestral, Chronos, TimesFM), zero-shot puis ajustés.
- Page de classement dans le frontend.
- Suivi d'expériences (MLflow), intégration continue.
- Déploiement d'une démo en ligne et conteneurisation (voir section 10).

## 9. Points ouverts

- Vérifier le comportement de `EvaluateWithPytorch` (il applique le scaler directement à des `PredictionInput`).
- Réentraîner le modèle avec la normalisation corrigée et noter le score de référence.
- Ajouter LightGBM aux dépendances du projet.
- Décider si les variantes de réseaux de neurones comptent comme des modèles distincts dans le classement.

## 10. Déploiement d'une démo en ligne (à planifier)

Objectif : qu'un visiteur puisse essayer l'application sans rien installer. Le profil invité
(`POST /auth/guest`) permet déjà d'entrer sans compte.

Pistes :
- Frontend statique chez un hébergeur de sites (Vercel, Netlify, Cloudflare Pages, GitHub Pages).
- Backend sur un hébergeur d'applications (Render, Railway, Fly.io, Space Hugging Face en Docker).
- `docker-compose.yml` pour tout lancer en une commande en local.
- README : lien de la démo en haut, captures d'écran ou GIF en secours.

Points bloquants identifiés :
- L'adresse du backend est écrite en dur dans le frontend (`http://localhost:8000`) et l'origine
  autorisée par CORS l'est dans le backend (`http://localhost:5173`) : à passer en variables d'environnement.
- Les fichiers du modèle (`data/model.pth`, `scaler_X.pkl`, `scaler_Y.pkl`) sont ignorés par git :
  prévoir comment les fournir au serveur (fichier versionné à part, release GitHub ou étape de construction).
- La base SQLite est réinitialisée au redémarrage sur la plupart des offres gratuites :
  volume persistant ou base hébergée si les comptes doivent survivre.
- PyTorch est lourd par rapport aux offres gratuites (mémoire limitée, à vérifier) :
  version CPU seule ou export du modèle en ONNX.
- Le profil invité ouvre les routes à toute personne qui joint le backend : ajouter une limitation
  du nombre de requêtes avant une exposition publique.
- Démarrage à froid sur les offres gratuites : le signaler dans le README.
- Les secrets (`.env`, clé de signature des jetons) restent hors de git et se configurent chez l'hébergeur.

Ordre prévu : variables d'environnement, puis Dockerfile et docker-compose, puis guide dans le README,
puis déploiement (les comptes chez l'hébergeur sont à créer par le propriétaire du projet).
