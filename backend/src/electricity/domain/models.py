from datetime import datetime


class ConsumptionRecord():
    """Classe qui définit ce qu'est un bon enregistrement de consommation électrique
    """

    def __init__(self,date:str,hour:int|float,power:float):
        """Initialisation des paramètres

        Args :
            - date : Date d'enregistrement de la consommation (format DD/MM/AAAA)
            - hour : Heure d'enregistrement de la consommation (format int)
            - power : Puissance électrique consommée (en GW)
        """
        # Vérification du type des instances
        if not isinstance(date,str):
            raise TypeError("Le type de la date est incorrect")
        if not isinstance(hour,(int,float)):
            raise TypeError("Le type de l'heure est invalide")
        if not isinstance(power,(int,float)):
            raise TypeError("Le type de la puissance est invalide")

        # Vérification du format de la date

        date_correcte=datetime.strptime(date, "%d/%m/%Y")

        annee_reference=datetime.now().year
        if date_correcte.year>annee_reference+1:
            raise ValueError("Année incohérente")

        # Vérification de l'heure :

        if hour<0 or hour>23:
            raise ValueError("La valeur de l'heure est incohérente")
        
        # Vérification de la puissance :

        if power<0 or power >170: # Puissance installée maximale (en GW) : 155 GW fin décembre 2025
            raise ValueError("La valeur de la puissance de la puissance électrique mobilisée est incohérente")
        
        # Initialisation des attributs :
        self.date=date
        self.hour=hour
        self.power=power