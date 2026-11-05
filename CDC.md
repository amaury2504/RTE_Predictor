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
- **Découpage temporel glissant (« walk-forward ») :** pour chaque année de test T (2022, 2023, 2024) :
  entraînement jusqu'à T-2, validation T-1, test T. Cela imite un réentraînement annuel et mesure la dérive
  du niveau de consommation, qui a changé après 2021. Les résultats sont donnés par année et en moyenne.
- **Jeu de test :** utilisé une seule fois par modèle, à la fin. Aucun réglage dessus.
- **Normalisation :** apprise sur l'entraînement seul (pas de fuite vers validation/test).
- **Variables d'entrée :** identiques pour tous les modèles d'une même piste, construites par un code commun.
- **Réglage :** budget identique pour chaque modèle (même nombre d'essais), évalué sur la validation.
- **Réentraînement :** après le réglage sur la validation, chaque modèle se réentraîne sur entraînement +
  validation avec le budget trouvé (nombre d'arbres, d'epochs). Les KPI de validation restent calculés
  avant ce réentraînement.
- **Variantes `_recent` :** pondération des lignes selon leur âge (demi-vie en années), pour tester
  l'effet d'une consommation qui dérive. Ce sont des modèles distincts dans le classement.
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
- [x] LightGBM (`adapters/ml/lightgbm_regressor.py`), dépendance ajoutée via Poetry.
- [x] Évaluation glissante sur 3 années de test (`split_for_test_year`, `run_walk_forward`), résultats globaux et par année.
- [x] Réentraînement sur entraînement + validation (LightGBM, MLP) et variantes `_recent` (poids selon l'âge).
- [ ] Lancement complet (5 graines) des modèles et enregistrement des résultats dans `benchmark/`.
- [x] Références (`ref_naive_j1`, `ref_naive_s1`, `ref_rte_j1`, `ref_rte_j`), classées à part car elles utilisent la consommation passée ou les prévisions d'RTE.
- [x] Ridge (`adapters/ml/ridge_regressor.py`) : mois et jour en 0/1, `alpha` choisi sur la validation, variantes `ridge` et `ridge_recent`.
- [x] Diagnostic du biais de niveau et correction du biais récent (`domain/bias_correction.py`, lignes `*_corr`), MAE centrée (`mae_debiased`). Voir `DECISIONS.md`.
- [x] Lissage exponentiel saisonnier (`domain/smoothing.py`, modèle `ts_holt_winters`) : consommation seule, paramètres choisis sur la validation de chaque année.
- [x] Piste B, premiers modèles : `ridge_niveau` et `lightgbm_niveau` avec variables de niveau récent (`domain/level.py`, prévision faite avec les données connues jusqu'à t - 48 h) et référence `ref_naive_j2`.

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
- Budget de réglage identique pour tous les modèles (section 3) : pour l'instant le MLP et LightGBM
  utilisent des hyperparamètres fixes, sans recherche. À uniformiser.
- Biais de niveau (surestimation systématique). Essai LightGBM, 1 graine, évaluation glissante :
  biais +1,9 GW (test 2022), +3,6 (2023), +3,1 (2024) pour une MAE de 2,5, 3,7 et 3,3 GW. À météo
  comparable, la consommation de 2024 est environ 3,7 GW sous celle de 2019. Le glissement mesure la dérive
  mais ne la corrige pas. Un réentraînement incluant l'année de validation réduit peu le biais
  (+3,4 en 2023, +2,6 en 2024). Pistes restantes : pondérer les années récentes, fenêtre d'entraînement
  plus courte, indicateur de niveau récent (consommation moyenne des 365 derniers jours : utilise le passé
  de la consommation, à classer avec la piste B), ou prédire un rapport au niveau récent.
  Résultat obtenu : réentraînement sur entraînement + validation et pondération des années récentes
  (demi-vie 3 ans) font passer LightGBM de MAE 3,14 à 2,65 GW et de biais +2,87 à +2,24 GW (moyenne des
  3 années de test, 1 graine). Le biais reste présent.
  Mise à jour : le biais est un changement de régime après 2022 (diagnostic et cause non établie dans
  `DECISIONS.md`). Correction du biais récent et variables de niveau récent (piste B) le traitent ; combiner
  les deux reste à tester.
- Demi-vie de la pondération (3 ans) : conservée telle quelle, sans réglage (décision : ne pas optimiser un
  symptôme, voir `DECISIONS.md`).
- Le MLP n'a pas encore de résultat 5 graines sur le protocole complet.
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
