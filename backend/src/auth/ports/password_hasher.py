from abc import ABC,abstractmethod

class PasswordHasher(ABC):
    """Cette classe sert à hasher des password et vérifier si le password est le bon"""

    @abstractmethod
    def hash_password(self,plain_password:str)->str:
        """Fonction consistant à hasher un password."""
        pass

    @abstractmethod
    def verify_password(self,plain_password:str,hashed_password:str)->bool:
        """Fonction pour vérifier si un password est correct.
        Retourne True si c'est le cas, et False dans le cas contraire."""
        pass
