from abc import ABC,abstractmethod

class TokenProvider(ABC):
    """Classe servant à gérer les tokens. Un token sert à reconnaitre un utilisateur sur plusieurs requêtes HTTPS."""

    @abstractmethod
    def create_token(self,mail:str)->str:
        """Créer un token après une authentification réussie"""
        pass
    @abstractmethod
    def verify_token(self,token_used:str)->str:
        """Extraire les informations du token, 
        pour voir s'il appartient à la bonne personne et s'il est toujours valide.
        Si le token est valide, il renvoie le mail de la personne."""
        pass
        
