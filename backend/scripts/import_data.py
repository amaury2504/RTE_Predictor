import sys
sys.path.insert(0, ".")  # ou sys.path.insert(0, ".")

import pandas as pd
from src.electricity.domain.models import ConsumptionRecord
from src.electricity.adapters.persistence.sqlalchemy_repository import SQLAlchemyConsumptionRepository
from src.electricity.adapters.persistence.sqlalchemy_models import Base, engine

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
j=0
for index, row in df_hourly.iterrows():
    date=row["date"]
    hour=row["hour"]
    power=row["power_gw"]
    
# Création de l'objet ConsumptionRecord et de l'objet SQLAlchemyConsumptionRepository
    record=ConsumptionRecord(date,hour,power)
    j+=1
    print(j)

# Enregistrement du record
    db_object.save_record(record)



