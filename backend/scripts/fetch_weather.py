import sys
sys.path.insert(0, ".")
import time
import requests
import json
import os
from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm
from src.electricity.adapters.persistence.sqlalchemy_models import WeatherRecordDB, SessionLocal, Base, engine

# Import des variables d'environnement

load_dotenv()
URL_WEATHER_BASE=os.getenv("URL_WEATHER_BASE")
URL_WEATHER_PARTIE2=os.getenv("URL_WEATHER_PARTIE2")
URL_WEATHER_PARTIE3=os.getenv("URL_WEATHER_PARTIE3")

"""
# Création de la requête requests
response=request(method="get",url="https://archive-api.open-meteo.com/v1/archive?latitude=48.86&longitude=2.35&start_date=2012-01-01&end_date=2012-01-02&hourly=temperature_2m,wind_speed_10m,relative_humidity_2m")

# Mise en JSON
data=response.json()
print(data)

"""

# Construction du dictionnaire de coordonnés des chefs lieux des régions
# Format des coordonnés : (latitude,longitude)
dictionnaire_regions={"Île-de-France":{"lat":48.866667,"lon":2.333333},                
                      "Auvergne-Rhône-Alpes": {"lat":45.752975,"lon":4.839223},
                      "Bourgogne-Franche-Comté": {"lat":47.316667,"lon":5.016667},
                      "Bretagne" :{"lat":48.111979,"lon":-1.681864},
                      "Centre-Val de Loire":{"lat":47.90289,"lon":1.90389},
                      "Corse":{"lat":41.916672,"lon":8.73333},
                      "Grand Est":{"lat":48.58392,"lon":7.74553},
                      "Hauts-de-France":{"lat":50.633333,"lon":3.066667},
                      "Normandie":{"lat":49.433331,"lon":1.08333},
                      "Nouvelle-Aquitaine":{"lat":44.833328,"lon":-0.56667},
                      "Occitanie":{"lat":43.60426,"lon":1.44367},
                      "Pays de la Loire":{"lat":47.2382,"lon":-1.5603},
                      "Provence-Alpes-Côte d'Azur": {"lat":43.296398,"lon":5.370000}}


# Création du constructeur dynamique d'URL

class DynamicConstructorURLOpenMeteo():
    """Cette classe permet de créer dynamiquement un URL prêt à l'envoi vers Open Meteo avec longitude et latitude adaptée.
    """
    def __init__(self,URL_WEATHER_BASE:str,URL_WEATHER_PARTIE2:str,URL_WEATHER_PARTIE3:str):
        self.url_base=URL_WEATHER_BASE
        self.url_middle=URL_WEATHER_PARTIE2
        self.url_end=URL_WEATHER_PARTIE3

    def build_url_with_coordinates(self,lat:float,lon:float)->str:
        return(f"{self.url_base}{lat}{self.url_middle}{lon}{self.url_end}")
    


# Création de la fonction qui retourne le json le dataframe avec les données météo

class ImportJsonAndFormateDataframe():
    def __init__(self,timeout:int|float):
        self.timeout=timeout
        

    def request_data(self,region:str)->json:
        """ Cette fonction permet de construire l'URL pour envoyer la requête HTTP via requests
        
        Returns:
            La réponse HTTP sous forme de json

        Raises:
            ValueError : Si les données du json sont incorrects
            ConnectionError :
                - Si l'API ne fonctionne pas
                - Si la requête met trop de temps à s'envoyer
        """
        
        # Vérification des paramètres

        if not region or not region.strip():
            raise ValueError("Le nom de la région ne peut être vide")
        
        if region not in dictionnaire_regions.keys():
            raise ValueError(f"Le nom de la région est invalide. Il doit figurer parmi les noms suivants : {dictionnaire_regions.keys()}")

        # Recherche des coordonnées de la région :

        lat=dictionnaire_regions[region]["lat"]
        lon=dictionnaire_regions[region]["lon"]


        # Construction de l'URL
        url_to_be_built=DynamicConstructorURLOpenMeteo(URL_WEATHER_BASE,URL_WEATHER_PARTIE2,URL_WEATHER_PARTIE3)
        url_ready_to_request=url_to_be_built.build_url_with_coordinates(lat,lon)

        # Vérification de l'URL

        if not url_ready_to_request or not url_ready_to_request.strip():
            raise ValueError("L'URL ne peut être vide")

        try:
            # Lancement de la requête HTTP
            response=requests.get(url=url_ready_to_request,timeout=self.timeout)
            response.raise_for_status()
            
            # Parse JSON
            data=response.json()
            
            # Vérification des données :

            if not data or "hourly" not in data \
                or "time" not in data["hourly"] \
                or "temperature_2m" not in data["hourly"] \
                or "wind_speed_10m" not in data["hourly"] \
                or "relative_humidity_2m" not in data["hourly"]:
                raise ValueError("Le format du json est invalide") 
                  
            return(data)
        
        except requests.Timeout:
            raise ConnectionError(f"L'API ne répond pas après {self.timeout} secondes.")
        
        except requests.ConnectionError as e:
            raise ConnectionError(f"Impossible de connecter l'API : {e}")
        
        except requests.HTTPError as e:
            raise ConnectionError(f"Erreur {e.response.status_code} : {e}")
        
        except requests.RequestException as e:
            raise ConnectionError(f"Erreur lors de la requête : {e}")
        
        except (KeyError,IndexError) as e:
            raise ValueError(f"Format de l'API innatendu : {e}")
        
        except (ValueError,TypeError) as e:
            raise ValueError(f"Format de données invalides : {e}")
    

    def format_dataframe(self,data:json,region:str):
        """
        Cette fonction permet de convertir le json en dataframe à l'aide de pandas

        Args:
            Le json

        Returns : 
            Un dataframe Pandas avec les colonnes "date", "heure", "temperature", "wind_speed", "relative_humidity"

        """

        # Création du dataframe
        df=pd.DataFrame()

        # Création de la colonne date
        date=data["hourly"]["time"]
        df["date et heure"]=date
        df["datetime"]=pd.to_datetime(df["date et heure"],utc=True)
        df["date"]=df["datetime"].dt.strftime("%d/%m/%Y")

        # Création de la colonne heure
        df["hour"]=df["datetime"].dt.hour

        # Création de la colonne "temperature"
        temperature=data["hourly"]["temperature_2m"]
        df["temperature"]=temperature

        # Création de la colonne "wind_speed"
        wind_speed=data["hourly"]["wind_speed_10m"]
        df["wind_speed"]=wind_speed

        # Création de la colonne "relative_humidity_10m"
        relative_humidity=data["hourly"]["relative_humidity_2m"]
        df["relative_humidity"]=relative_humidity

        # Création de la colonne "region"
        df["region"]=region

        # Suppresion des colonnes intermédiaires
        df=df.drop(columns=["date et heure","datetime"])

        return(df)

# --- Exécution ---

Base.metadata.create_all(engine)
session = SessionLocal()
session.query(WeatherRecordDB).delete()
session.commit()

# 1. Fetch des 13 régions
fetcher = ImportJsonAndFormateDataframe(timeout=60)
all_dataframes = []

for region in tqdm(dictionnaire_regions, desc="Fetch météo"):
    data = fetcher.request_data(region)
    df = fetcher.format_dataframe(data, region)
    all_dataframes.append(df)
    time.sleep(10) # Attend 10 secondes avant la prochaine requête
df_total = pd.concat(all_dataframes, ignore_index=True)
print(f"Total : {len(df_total)} lignes")


for index, row in tqdm(df_total.iterrows(), total=len(df_total), desc="Import en base"):
    record = WeatherRecordDB(
        date=row["date"],
        hour=row["hour"],
        region=row["region"],
        temperature=row["temperature"],
        wind_speed=row["wind_speed"],
        relative_humidity=row["relative_humidity"]
    )
    session.add(record)

session.commit()
session.close()
print("Import terminé !")