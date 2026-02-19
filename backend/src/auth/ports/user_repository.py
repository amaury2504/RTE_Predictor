from src.auth.domain.models_auth import User
from abc import ABC , abstractmethod


class UserRepository(ABC):
    """Port servant à définir les actions à réaliser sur la base de données des utilisateurs.
    
    Il y a deux usages identifiés sur cette base : 
        - Stocker les données d'un nouvel utilisateur
        - Obtenir le mot de passe d'un utilisateur lorsqu'il se connecte """


    @abstractmethod
    def store_user(self,user:User)->None:
        """Fonction pour stocker les données d'un utilisateur"""
        pass

    @abstractmethod
    def get_by_mail(self,mail:str)->User:
        """Fonction pour récupérer le mot de passe d'un mail dans le repository."""
        pass
