# Déploiement sur un serveur

Objectif : RTE Predictor en ligne sur un petit serveur (VPS Linux), à côté d'autres projets, avec HTTPS.

```
Internet ──► Caddy commun (ports 80/443, HTTPS) ──► rte-predictor-web ──► /api ──► rte-predictor-api
                                   ├────────────► autre projet 1
                                   └────────────► autre projet 2
```

- Un seul reverse proxy (Caddy) reçoit tout le trafic, obtient les certificats HTTPS et route par nom de domaine.
- Chaque projet est un `docker compose` indépendant, rattaché au réseau Docker `proxy`.
- Le frontend appelle l'API sur le même domaine (`/api`) : pas de CORS à configurer.

## Serveur conseillé

Pour trois petits projets et une dizaine de visites : 2 vCPU, 4 Go de RAM, 40 Go de disque, Ubuntu 24.04 LTS.
Si un des autres projets embarque une base de graphes (Neo4j) ou des modèles locaux, prévoir 8 Go.
Ajouter 2 Go de swap pour absorber les pointes de mémoire (voir plus bas).

## 1. Préparer le serveur (une fois)

```bash
# Accès par clé SSH uniquement, puis pare-feu
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable

# Docker (dépôt officiel) : https://docs.docker.com/engine/install/ubuntu/
# Puis le réseau commun :
docker network create proxy

# Swap de 2 Go
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Noms de domaine

Créer un enregistrement DNS `A` par projet (ex. `rte.mondomaine.fr`) vers l'adresse IPv4 du serveur.
Le certificat HTTPS ne peut être obtenu qu'une fois le DNS propagé.

## 3. Reverse proxy commun (une fois)

```bash
git clone https://github.com/amaury2504/RTE_Predictor.git
cd RTE_Predictor/deploy/server
cp Caddyfile.example Caddyfile      # remplacer les domaines
docker compose up -d
```

## 4. RTE Predictor

```bash
cd RTE_Predictor/deploy
cp .env.example .env                # renseigner SECRET_KEY (voir le fichier)
mkdir -p data
```

**Fichiers du modèle** : ils ne sont pas dans git (ils pèsent peu, mais dépendent de l'entraînement).
Depuis le poste où le modèle a été entraîné :

```bash
scp backend/data/model.pth backend/data/scaler_X.pkl backend/data/scaler_Y.pkl backend/data/mlp_niveau.pkl backend/data/lightgbm_niveau.pkl backend/data/ridge_niveau.pkl utilisateur@serveur:~/RTE_Predictor/deploy/data/
```

Puis, sur le serveur :

```bash
docker compose up -d --build
docker compose ps                   # api : "healthy"
curl -fsS https://rte.mondomaine.fr/api/health
```

Si l'API ne démarre pas, `docker compose logs api` : la cause la plus fréquente est un fichier du modèle manquant
dans `deploy/data/` ou une `SECRET_KEY` absente ou trop courte (moins de 32 caractères).

## Mise à jour

```bash
cd RTE_Predictor && git pull && cd deploy && docker compose up -d --build
```

Les bases SQLite et le modèle sont dans `deploy/data/` (volume) : ils ne sont pas touchés par une mise à jour.
Les résultats du benchmark (`backend/benchmark/`) sont versionnés et copiés dans l'image : relancer le benchmark,
commiter, puis reconstruire.

## Ce qui protège la démo

- Les connexions sont limitées par adresse IP : 10 essais par minute, 5 inscriptions par heure, 60 profils invités par heure.
- Le profil invité peut lire et prédire, mais pas écrire dans la base (route `/electricity/consumption`).
- `GUEST_ENABLED=false` dans `.env` coupe le profil invité (comptes obligatoires).
- L'API refuse de démarrer en production sans `SECRET_KEY` solide.
- Le conteneur de l'API tourne sans droits administrateur et est limité à 1 Go de mémoire.

## Limites connues

- Les limites de tentatives sont en mémoire : un redémarrage les remet à zéro, et elles ne se partagent pas entre
  plusieurs instances (inutile ici, il n'y en a qu'une).
- Les appels à RTE passent avec la vérification TLS désactivée dans le code (`verify=False` dans
  `prediction_routes.py`) : à corriger avant tout usage au-delà de la démo.
- L'image et le déploiement ont été écrits sans pouvoir les construire sur le poste de développement
  (Docker n'y était pas démarré) : le premier `docker compose up --build` est la vraie vérification.
