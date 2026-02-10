import sys
sys.path.insert(0, ".")

import pandas as pd
from src.electricity.adapters.persistence.sqlalchemy_models import SessionLocal, WeatherRecordDB, ConsumptionRecordDB

# 1. Charger les données météo et consumption depuis la base
session = SessionLocal()
weather_rows = session.query(WeatherRecordDB).all()
consumption_rows = session.query(ConsumptionRecordDB).all()

df_consumption = pd.DataFrame([
    {"date": r.date, "hour": r.hour, "consommation": r.power}
    for r in consumption_rows
])

# Convertir en DataFrame
df_weather = pd.DataFrame([
    {"date": r.date, "hour": r.hour, "region": r.region, 
     "temperature": r.temperature, "wind_speed": r.wind_speed, 
     "humidity": r.relative_humidity}
    for r in weather_rows
])

df_weather_large=pd.pivot(data=df_weather,index=["date","hour"],columns="region",values=["temperature","wind_speed","humidity"])
df_weather_large.columns = [f"{var}_{region}" for var, region in df_weather_large.columns]

df_consumption = pd.DataFrame([
    {"date": r.date, "hour": r.hour, "consommation": r.power}
    for r in consumption_rows
])

# Merge des deux dataframes

df_final=pd.merge(df_weather_large,df_consumption, on=["date","hour"])

session.close()


df_final.to_csv("data/dataset_ml.csv", index=False)
print("Dataset sauvegardé !")


