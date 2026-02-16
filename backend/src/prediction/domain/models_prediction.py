import pandas as pd

class PredictionResult():
    """Classe représentant ce qu'est une prédiction valide"""

    def __init__(self,date:str,hour:int|float,power:int|float):
        """Vérification des instances et initialisation des attributs :

        Args:
        - date : Format "DD/MM/AAAA" str
        - hour : Format [0-23] int|float
        - power : Format [0-169] float (en GW) 
        """
        # Vérification des types :

        if not isinstance(date,str):
            raise TypeError("Le format de la date n'est pas une string")
        
        if not isinstance(hour,int|float):
            raise TypeError("Le format de l'heure n'est pas un int ou float")
        
        if not isinstance(power,int|float):
            raise TypeError("Le format de power n'est pas un float")

        # Vérification des valeurs des paramètres
        if not date:
            raise ValueError("La date ne peut être vide.")
        
        if not date.strip():
            raise ValueError("La date ne peut pas être uniquement composée d'espaces")
        
        if hour<0 or hour>23:
            raise ValueError(f"L'heure doit être comprise dans [0-23] : hour = {hour}")
        
        if power <0 or power > 169:
            raise ValueError(f"Erreur : power doit être compris dans [0-169] : power = {power}")
        
        try:
            pd.to_datetime(date,format="%d/%m/%Y")
        except ValueError:
            raise ValueError("La date doit être au format JJ/MM/AAAA")
        
        # Initialisation des paramètres :
        date_formate=pd.to_datetime(date,format="%d/%m/%Y").strftime("%d/%m/%Y")


        self.date=date_formate
        self.hour=hour
        self.power=power


    def __str__(self):
        return(f"Le {self.date} à {self.hour}, la production électrique française devrait être de {self.power} GW.")


class ModelMetrics():
    mae: float    # Erreur Absolue Moyenne
    rmse: float   # Root Mean Square Error
    mape: float   # Mean Absolute Percentage Error

    def __init__(self,mae:float,rmse:float,mape:float):
        
        # Vérification des types des paramètres

        if not isinstance(mae,float):
            raise TypeError("Type incorrect : mae n'est pas un float")
        
        if not isinstance(rmse,float):
            raise TypeError("Type incorrect : rmse n'est pas un float")
        
        if not isinstance(mape,float):
            raise TypeError("Type incorrect : mape n'est pas un float")


        # Vérification des paramètres

        if mae<0:
            raise ValueError(f"La valeur de mae ne peut être négative : mae actuel {mae}.")
        
        if rmse<0:
            raise ValueError(f"La valeur de rmse ne peut être négative : rmse actuel {rmse}.")
        
        if mape<0:
            raise ValueError(f"La valeur de mape ne peut être négative : mape actuel {mape}.")
        
        # Initialisation des attributs 

        self.mae=mae
        self.rmse=rmse
        self.mape=mape


TOUTES_LES_REGIONS=["Île-de-France",
                    "Auvergne-Rhône-Alpes",
                    "Bourgogne-Franche-Comté",
                    "Bretagne",
                    "Centre-Val de Loire",
                    "Corse",
                    "Grand Est",
                    "Hauts-de-France",
                    "Normandie",
                    "Nouvelle-Aquitaine",
                    "Occitanie",
                    "Pays de la Loire",
                    "Provence-Alpes-Côte d'Azur"]


class PredictionInput():
    """Cette classe sert à vérifier les paramètres et indiquer ce qu'est un input valide pour demander une requête utilisateur"""

    def __init__(self,date:str,hour:int|float,temp_regions:dict[str,int|float],wind_regions:dict[str,int|float],humidity_regions:dict[str,int|float]):
        # Vérification des paramètres

        # Vérification des types des paramètres
        
        if not isinstance(date,str):
            raise TypeError("Le type de la date est invalide. Ce n'est pas une str")

        if not isinstance(hour,int|float):
            raise TypeError("Le type de hour est invalide. Ce n'est ni un int, ni un float")

        if not isinstance(temp_regions,dict):
            raise TypeError("Le type de temp_regions est invalide. Ce n'est pas un dict.")

        if not isinstance(wind_regions,dict):
            raise TypeError("Le type de wind_regions est invalide. Ce n'est pas un dict.")

        if not isinstance(humidity_regions,dict):
            raise TypeError("Le type de humidity_regions est invalide. Ce n'est pas un dict.")

        # Vérification de Valeurs : 

            # Vérification de la date :

        if not date:
            raise ValueError("La date ne peut être vide")

        if not date.strip():
            raise ValueError("La date ne peut être composée uniquement d'espaces.")

        try:
            pd.to_datetime(date,format="%d/%m/%Y").strftime("%d/%m/%Y")
        except ValueError:
            raise ValueError("La date doit être au format DD/MM/AAAA")
        

            # Vérification de l'heure

        if hour<0 or hour>23:
            raise ValueError(f"L'heure indiquée n'est pas valide. Elle doit être comprise entre 0 et 23. Heure : {hour}")
        
            # Vérification de temp_regions
        
        for region in temp_regions.keys():
            if not isinstance(region,str):
                raise TypeError("Les régions ne sont pas des str")

        for region in temp_regions.keys():
            if region not in TOUTES_LES_REGIONS:
                raise ValueError("Les régions ne sont pas correctes.")
            
        for temp in temp_regions.values():
            if not isinstance(temp,int|float):
                raise TypeError("Les températures ne sont pas du type int ou float.")
            
        for temp in temp_regions.values():
            if temp <-40 or temp > 75:
                raise ValueError(f"Les températures sont incohérentes. Elles doivent être comprises dans [-40°C,75°C]. Température trouvée : {temp}")
            

            # Vérification de temp_wind
        
        for region in wind_regions.keys():
            if not isinstance(region,str):
                raise TypeError("Les régions ne sont pas des str")

        for region in wind_regions.keys():
            if region not in TOUTES_LES_REGIONS:
                raise ValueError("Les régions ne sont pas correctes.")
            
        for wind_speed in wind_regions.values():
            if not isinstance(wind_speed,int|float):
                raise TypeError("Les wind_speed ne sont pas du type int ou float.")
            
        for wind_speed in wind_regions.values():
            if wind_speed <0 or wind_speed > 200:
                raise ValueError(f"Les wind_speed sont incohérentes. Elles doivent être comprises dans [0 km/h,200 km/h]. Wind_speed trouvée : {wind_speed}")
            
            # Vérification de humidity_regions
        
        for region in humidity_regions.keys():
            if not isinstance(region,str):
                raise TypeError("Les régions ne sont pas des str")

        for region in humidity_regions.keys():
            if region not in TOUTES_LES_REGIONS:
                raise ValueError("Les régions ne sont pas correctes.")
            
        for humidity in humidity_regions.values():
            if not isinstance(humidity,int|float):
                raise TypeError("Les valeurs humidity ne sont pas du type int ou float.")
            
        for humidity in humidity_regions.values():
            if humidity <0 or humidity > 100:
                raise ValueError(f"Les valeurs humidity sont incohérentes. Elles doivent être comprises dans [0%, 100%]. Valeur d'humidity trouvée : {humidity}")
            

    # Initialisation des paramètres

        self.date=pd.to_datetime(date,format="%d/%m/%Y").strftime(format="%d/%m/%Y")
        self.hour=hour
        self.temp_regions=temp_regions
        self.wind_regions=wind_regions
        self.humidity_regions=humidity_regions