import pandas as pd

df=pd.read_csv("data/eco2mix-national-cons-def.csv",sep=";")

#print(df.head())
"""
for col in df.columns:
    print(col)
"""

# Affichage des 10 premières valeurs de la colonnne "Date et Heure"
"""
print(df["Date et Heure"].head(10))
print(df["Consommation (MW)"].head(10))
print(df[["Date et Heure","Consommation (MW)"]].dtypes)
"""
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

# Nombre total de lignes
print(f"Nombre de lignes : {len(df_hourly)}")

# Est-ce qu'il reste des NaN ?
print(f"NaN restants : {df_hourly.isna().sum()}")

print(f"Première date : {df_hourly["date"].iloc[0]}")
print(f"Dernière date : {df_hourly["date"].iloc[-1]}")