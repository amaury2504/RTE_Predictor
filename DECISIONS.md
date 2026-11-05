# Journal des décisions

Ce document explique **pourquoi** le projet est construit comme il l'est : les problèmes rencontrés, les
choix faits, ceux qui ont été écartés et ce qui reste inconnu. Les chiffres viennent de `backend/benchmark/`
(commande : `python scripts/run_benchmark.py`). Le protocole est dans `CDC.md`.

## 1. Le problème : tous les modèles se trompent dans le même sens

Dès les premiers essais, tous les modèles entraînés sur la météo et le calendrier surestiment la consommation
sur 2022-2024 (biais de +2 à +3 GW pour une consommation moyenne de 50 GW). Ni LightGBM, ni Ridge, ni le MLP
n'y échappent : ce n'est donc pas un défaut d'un modèle en particulier.

**Première réaction écartée : régler la pondération des années récentes.** Choisir la « demi-vie » qui
minimise l'erreur sur la validation aurait réduit le symptôme sans rien expliquer. Une pondération rattrape
un décalage de niveau avec retard et ne le corrige jamais complètement. Les variantes `_recent` (demi-vie de
3 ans, choisie a priori) sont gardées comme points de comparaison, sans réglage.

## 2. Le diagnostic (sur les données, avant toute correction)

Méthode : un LightGBM entraîné sur 2012-2018 (avant Covid et crise de l'énergie) prédit les années suivantes ;
on regarde où et quand la consommation réelle s'écarte de ce que la météo laissait attendre.

| Écart moyen (réel moins prédit, GW) | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|
| Année entière | −0,7 | −2,8 | −1,5 | −2,6 | −4,3 | −3,8 |
| Hiver | −0,6 | −1,9 | −1,3 | −2,7 | −5,6 | −5,1 |
| Été | −0,4 | −1,9 | −1,2 | −1,1 | −2,4 | −2,0 |
| Semaine | −0,8 | −3,1 | −1,7 | −2,8 | −4,6 | −4,3 |
| Week-end | −0,3 | −2,1 | −1,1 | −2,0 | −3,4 | −2,7 |

Ce qu'on en retient :

- **Une marche, pas une pente** : l'écart mensuel passe d'environ −1 à −2 GW en été 2022 à −4,6 en octobre
  et −6,7 en novembre 2022, puis ne revient pas. Le calendrier coïncide avec la crise de l'énergie, mais
  c'est une coïncidence de dates, pas une preuve.
- **Le même écart à toute heure** (−4,1 la nuit, −4,3 en journée en 2023) : l'autoconsommation solaire ne
  peut pas être la cause principale.
- **Un socle d'environ 2 GW présent en été et la nuit, plus un surcroît en hiver** (jusqu'à −5,6 GW) : cela
  va dans le sens d'une baisse du chauffage, sans le démontrer.
- **Plus marqué en semaine qu'en week-end** : l'activité économique ou le travail y jouent une part.
- **Ce n'est pas un artefact de données** : seule 2024 est « consolidée » chez RTE, et l'écart existe déjà en
  2023 avec des données définitives.

**Limites assumées.** Une dérive existait déjà en 2019 (−0,7 GW). Le Covid (2020) est un autre phénomène.
On sait où et quand l'écart apparaît, pas pourquoi : séparer sobriété, prix, désindustrialisation, rénovation
et télétravail demanderait des données absentes ici (prix, production industrielle, consommation par
secteur). **La cause n'est pas établie, et elle ne doit pas être présentée comme telle.**

## 3. La conséquence : un changement de régime

Aucune variable de météo ou de calendrier ne peut absorber un changement du niveau de consommation. Deux
façons d'y répondre, retenues parce qu'elles sont adaptées au problème et non à un score :

### 3.1. Correction du biais récent (`domain/bias_correction.py`)

On ajoute à chaque prédiction la moyenne des erreurs (réel moins prédit) des 28 derniers jours disponibles.

- **Pourquoi pas un décalage fixe** : un « on enlève 2,5 GW » est faux au prochain changement de niveau et
  masque la dérive au lieu de la signaler.
- **Aucune fuite** : la correction du jour D n'utilise que les jours ≤ D − 2, donc connus au moment de prévoir
  D. Un test vérifie que modifier le réel à partir d'un jour ne change aucune correction avant 2 jours plus tard.
- **Paramètres fixés a priori, non réglés** : fenêtre de 28 jours (quatre semaines complètes), décalage de
  2 jours, au moins 7 jours disponibles (sinon pas de correction). Aucun n'a été optimisé sur le test.
- **Coût** : les premiers jours de l'année de test ne sont pas corrigés ; la correction réagit avec un retard
  de quelques semaines à un changement brutal.

### 3.2. Variables de niveau récent (piste B, `domain/level.py`)

On donne au modèle la consommation récente : même heure 2 jours et 7 jours avant, moyennes des 7 et 28
jours qui se terminent 2 jours avant. Le modèle apprend « niveau récent bas, prévision basse » au lieu de le
deviner.

- **Hypothèse de prévision explicite** : la prévision de l'heure t utilise les consommations connues
  jusqu'à t − 48 h. Sans cette règle, on peut tricher sans le voir (utiliser une valeur qu'on ne connaîtrait
  pas). Des tests vérifient que changer le réel à partir de l'heure h ne modifie aucune variable avant h + 48 h.
- **Piste séparée** : ces modèles utilisent la consommation passée, ils ne sont donc pas comparés au sens
  strict aux modèles de la piste A (section 2 du CDC).
- **Référence honnête** : la naïve J-1 utilise 24 h d'information, alors que la piste B en a 48. On ajoute
  `ref_naive_j2` (même heure, 48 h avant) pour comparer à information égale.

### 3.3. Une série temporelle seule : le lissage exponentiel (`domain/smoothing.py`)

Troisième réponse au changement de niveau, sans la météo : un modèle de Holt-Winters (niveau et profil
hebdomadaire de 168 heures, lissés exponentiellement), qui suit le niveau par construction.

- **Même information que la piste B** : la prévision de l'heure t n'utilise que la consommation connue
  jusqu'à t − 48 h. Un test vérifie qu'on peut bouleverser les données récentes sans changer les prévisions
  des 48 premières heures.
- **Paramètres choisis sur la validation**, pour chaque année de test : le couple (alpha pour le niveau, gamma
  pour le profil) qui minimise la MAE de l'année T − 1. Le test ne sert jamais au choix. La première grille
  (alpha 0,003 à 0,1) donnait un meilleur couple au bord ; elle a été élargie (alpha 0,01 à 0,4, gamma 0,01 à
  0,3) sur ce seul critère de validation.
- **Un piège connu** : sur des données horaires, un alpha trop grand fait suivre au niveau le cycle
  journalier avant que le profil ne soit appris ; c'est pourquoi la grille contient surtout des alpha faibles.
- **Classement** : ni référence, ni piste A ou B. C'est une quatrième famille, « série temporelle »,
  puisqu'elle n'utilise ni météo ni calendrier mais apprend des paramètres.

### 3.4. Un modèle de fondation : Timestral (`domain/foundation.py`)

Timestral (Mistral, octobre 2026, poids ouverts) est un modèle de séries temporelles préentraîné : on ne l'entraîne
pas sur nos données, on lui donne un historique et il prévoit la suite. Deux tailles (209 M et 28 M de paramètres)
et deux variantes chacune sont évaluées : consommation seule (`ts_timestral_209m`, `ts_timestral_28m`) et avec la
température moyenne et les jours fériés (`..._meteo`). Comparer les tailles dit si le gain vaut le coût de calcul :
la variante météo de la grande taille coûte environ 5 fois plus que la variante sans météo.

- **Même hypothèse que la piste B** : l'historique s'arrête 48 h avant le début du jour prévu, donc chaque
  heure est prévue avec un retard d'au moins 48 h (de 48 h à 71 h). Un test vérifie que modifier les données
  postérieures à l'origine ne change pas la prévision.
- **Réglages fixés a priori, non optimisés** : historique de 8 semaines (1344 h), prévision médiane
  (quantile 0,5) comme prévision ponctuelle.
- **La météo est « parfaite »** : la météo observée sert de prévision de météo, comme pour tous les autres
  modèles du projet qui utilisent la météo. Un usage réel recevrait une vraie prévision, moins exacte. **Cela
  avantage tous nos modèles météo face aux prévisions d'RTE**, qui reposent sur une météo prévue : la comparaison
  avec `ref_rte_j` et `ref_rte_j1` est donc plutôt favorable à nos modèles.
- **Premier résultat (taille 209 M, essai isolé)** : Timestral avec météo fait 1,30 GW de MAE (biais −0,08 GW),
  sans aucun entraînement sur nos données ; sans météo, 2,20 GW. À confirmer par le lancement complet, avec le 28 M.
- **Dépendance optionnelle** : `pip install git+https://github.com/mistralai/timestral.git` (absente de
  `pyproject.toml` pour ne pas alourdir l'image de l'API). Sans elle, le benchmark ignore Timestral et le dit.
- **Licence** : poids sous licence MIT modifiée (interdiction d'usage au-delà de 20 M$ de revenu mensuel pour
  l'entreprise de l'utilisateur) : sans objet pour un projet personnel, mais à connaître.
- **Les résultats annoncés par Mistral** (premier rang sur plusieurs classements publics) sont ceux de
  Mistral, sur d'autres données. Ce qui compte ici est la mesure sur notre protocole : **non encore mesurée**.

## 4. Nouvelle métrique : la MAE centrée

`mae_debiased` = MAE une fois le biais moyen retiré. Elle sépare deux questions que la MAE brute mélange :
le modèle comprend-il la forme de la consommation (météo, heures, jours) et sait-il où est le niveau ? Une
MAE centrée proche de la MAE brute indique un modèle sans biais.

## 5. Résultats (moyenne des années de test 2022, 2023 et 2024 ; 5 graines pour LightGBM)

Voir `backend/benchmark/RESULTS.md` pour le détail par année. Les lignes `ref_*` sont des références, pas des
modèles de la piste A.

| Modèle | MAE (GW) | MAE centrée (GW) | Biais (GW) |
|---|---|---|---|
| ref_rte_j (prévision RTE du jour) | 1,05 | 0,68 | −0,95 |
| ref_rte_j1 (prévision RTE de la veille) | 1,21 | 0,93 | −0,92 |
| **Piste B** lightgbm_niveau | 1,42 | 1,27 | +0,90 |
| **Piste B** ridge_niveau | 2,02 | 1,82 | +1,01 |
| **Piste A** lightgbm_corr | 1,71 | 1,71 | +0,11 |
| **Piste A** lightgbm_recent_corr | 1,75 | 1,75 | +0,11 |
| **Série temporelle** ts_holt_winters | 2,39 | 2,39 | −0,03 |
| ref_naive_j1 | 2,57 | 2,57 | −0,01 |
| **Piste A** lightgbm_recent | 2,65 | 1,92 | +2,24 |
| **Piste A** lightgbm | 2,91 | 1,92 | +2,60 |
| **Piste A** ridge_corr | 2,98 | 2,98 | +0,12 |
| **Piste A** ridge_recent | 3,49 | 3,05 | +2,07 |
| **Piste A** ridge | 3,78 | 3,10 | +2,57 |
| ref_naive_j2 | 4,18 | 4,18 | −0,02 |

Ce que cela dit, et ce que cela ne dit pas :

1. **Une grande part de l'erreur de LightGBM sur la piste A (2,91 GW) était du biais.** Une fois le biais retiré
   (MAE centrée), elle tombe à 1,92 GW, loin de la naïve J-1 (2,57 GW). Notre première lecture, « LightGBM
   fait comme la naïve », était trompeuse : c'était le décalage de niveau qui masquait la qualité du modèle.
2. **La correction du biais récent ramène l'erreur de LightGBM de 2,91 à 1,71 GW** (biais +0,11 GW), sans
   réentraîner.
3. **Le niveau récent comme variable donne 1,42 GW** (piste B), mieux que la correction (1,71 GW) mais avec
   un biais résiduel (+0,90 GW) : le modèle voit le niveau, mais apprend sa relation à la consommation sur des
   années où le niveau était différent. **Les deux approches se combinent** : avec la correction du biais en plus, LightGBM
   tombe à **1,21 GW** (biais +0,12 GW, MASE 0,47, ± 0,08 GW entre graines), au niveau de la prévision RTE de la veille
   (1,21 GW), et le Ridge à 1,79 GW. Premier essai isolé, régénéré dans les résultats officiels par le lancement complet.
4. **Les prévisions d'RTE restent meilleures** (1,05 à 1,21 GW) : elles disposent d'informations qu'on n'a
   pas. Elles sont un plafond de comparaison, pas un concurrent.
5. **Le Ridge est derrière LightGBM dans toutes les conditions**, y compris avec le niveau récent : la relation
   entre météo et consommation n'est pas linéaire.
6. **Le lissage exponentiel, sans météo, fait 2,39 GW** avec un biais quasi nul : mieux que la naïve J-1 (2,57 GW)
   et que LightGBM brut (2,91 GW), car il suit le niveau. Mais il reste derrière LightGBM corrigé (1,71 GW) et
   LightGBM avec niveau récent (1,42 GW) : la météo apporte environ 1 GW de plus. Cet écart n'est valable
   que pour ce protocole et ce modèle de série temporelle ; un SARIMAX ou un réseau de séquence pourraient faire mieux.
7. **Non mesuré** : le MLP PyTorch sur ce protocole complet (son lancement complet est prévu à part). Dans
   `RESULTS.md`, le « ± » du classement global est l'écart entre années de test ; l'écart entre graines (LightGBM)
   est dans le détail par année. Le Ridge, déterministe, n'en a pas.

## 6. Choix transverses

- **Architecture hexagonale** (domaine, ports, application, adaptateurs) : le calcul des variables, des
  KPI, des découpages et des corrections est du code pur, testable sans framework ni modèle ; chaque modèle
  est un adaptateur d'un même contrat (`RegressorPort`).
- **Un seul code pour construire les variables** (API, entraînement, benchmark) : un modèle en production reçoit
  exactement ce qu'il a vu à l'entraînement.
- **Évaluation glissante** (test T, validation T − 1, entraînement ≤ T − 2) plutôt qu'un découpage fixe :
  elle imite un réentraînement annuel et permet de voir la dérive.
- **Le jeu de test n'est lu qu'une fois par modèle**, après l'entraînement. La normalisation et l'imputation
  des valeurs manquantes sont apprises sur l'entraînement seul (une fuite de ce type a été corrigée dans la
  première version).
- **Références classées à part** (`ref_*`) : elles utilisent la consommation passée ou les prévisions d'RTE.

## 7. Ce qui reste à faire

- Lancement complet du MLP et des variantes avec 5 graines.
- Combiner niveau récent et correction du biais, et mesurer ce que la combinaison apporte.
- Autres séries temporelles et modèles de séquence (SARIMAX, GRU, CNN 1D, TCN) puis modèles de fondation (Chronos, TimesFM).
- Surveiller le biais glissant en production et réentraîner au-delà d'un seuil (non commencé).
- Déploiement d'une démo (section 10 du CDC).
