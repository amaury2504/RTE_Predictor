"""Import de l'historique de consommation éco2mix (RTE) dans la base SQL.

Usage (depuis le dossier backend, venv actif) :
    python scripts/import_data.py

Entrée  : data/eco2mix-national-cons-def.csv (séparateur ';', colonnes
          "Date et Heure" et "Consommation (MW)", pas de 15/30 min).
Sortie  : table `consumption_records` (date "JJ/MM/AAAA", hour 0-23, power en GW),
          dans la base définie par DATABASE_URL (.env).

Traitement : agrégation à l'heure (moyenne), conversion MW -> GW, puis insertion
par lots de CHUNK_SIZE avec un commit par lot.

Attention :
- Le script n'est pas idempotent : le relancer sur une table non vide crée des
  doublons. Vider la table avant (voir vider.py).
- Un commit par lot : si le script est interrompu, les lots déjà commités restent
  en base (import partiel). Vider la table puis relancer.
"""
import sys
import time
sys.path.insert(0, ".")  # exécution depuis backend/

import pandas as pd
from tqdm import tqdm
from src.electricity.domain.models import ConsumptionRecord
from src.electricity.adapters.persistence.sqlalchemy_repository import SQLAlchemyConsumptionRepository
from src.electricity.adapters.persistence.sqlalchemy_models import Base, engine

# Nombre de lignes insérées par commit (compromis vitesse / granularité de la barre)
CHUNK_SIZE=10_000

# Créer la table si elle n'existe pas
Base.metadata.create_all(engine)


# Création du dataframe
df=pd.read_csv("data/eco2mix-national-cons-def.csv",sep=";")


# Conversion du format Date et Heure en datetime

df["datetime"]=pd.to_datetime(df["Date et Heure"],utc=True)

df["hour"]=df["datetime"].dt.hour

# Formatage de la date avec dt.strftime
df["date"]=df["datetime"].dt.strftime("%d/%m/%Y")

# Alignement de la consommation électrique au pas horaire
df_hourly=df.groupby(["date","hour"])["Consommation (MW)"].mean().reset_index()

# Renommer la colonne Consommation (MW)

df_hourly=df_hourly.rename(columns={"Consommation (MW)":"power_mw"})

# Conversion en GW

df_hourly["power_gw"]=df_hourly["power_mw"]/1000

# Création du repository
db_object=SQLAlchemyConsumptionRepository()

# Création des objets ConsumptionRecord (sans iterrows, beaucoup plus rapide)
records=[
    ConsumptionRecord(date,hour,power)
    for date,hour,power in zip(df_hourly["date"],df_hourly["hour"],df_hourly["power_gw"])
]

# Enregistrement par lots : un commit par lot (et non un par ligne).
# La barre tqdm affiche l'avancement, le temps écoulé, le temps restant estimé (ETA)
# et la vitesse. L'ETA devient fiable après le 1er lot.
total=len(records)
print(f"Lignes CSV lues : {len(df)} | enregistrements horaires à insérer : {total} "
      f"| taille de lot : {CHUNK_SIZE} ({-(-total//CHUNK_SIZE)} lots)")

start=time.perf_counter()
with tqdm(total=total, desc="Import en base", unit="ligne") as bar:
    for i in range(0,total,CHUNK_SIZE):
        chunk=records[i:i+CHUNK_SIZE]
        db_object.save_many(chunk)
        bar.update(len(chunk))

elapsed=time.perf_counter()-start
print(f"{total} enregistrements importés en {elapsed:.1f} s ({total/elapsed:.0f} lignes/s)")



