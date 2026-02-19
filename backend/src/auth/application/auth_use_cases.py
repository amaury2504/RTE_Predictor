from src.auth.domain.models_auth import User
from src.auth.ports.password_hasher import PasswordHasher
from src.auth.ports.token_provider import TokenProvider
from src.auth.ports.user_repository import UserRepository

class RegisterUser():
    """Classe servant à créer le use_case d'enregistrement d'utilisateur.
    Dans l'ordre :
        - L'utilisateur envoie son mail et son plain password
        - Vérification si le mail n'est pas déjà dans la base
        - Hashing du mot de passe
        - Création du User(mail,hashed_password)
        - Enregistrement de l'user dans la BDD
        """
    def __init__(self,repository:UserRepository,password_hasher:PasswordHasher):
        self.repository=repository
        self.password_hasher=password_hasher

    def execute(self,mail:str,plain_password:str)->None:
        if not self.repository.get_by_mail(mail):
            hashed_password=self.password_hasher.hash_password(plain_password)
            user_to_register=User(mail=mail,hashed_password=hashed_password)
            self.repository.store_user(user_to_register)



class LoginUser():
    """Use case pour vérifier si un client peut se login :
    
    Dans l'ordre : 
        - L'utilisateur envoie son mail et son plain password
        - On vérifie si le mail existe déjà dans la BDD des users
        - Si c'est le cas, on hash le plain_password
        - On regarde si les hash_passwords correspondent
        - On crée un token si c'est le cas
    """

    def __init__(self,repository:UserRepository,password_hasher:PasswordHasher,token_provider:TokenProvider):
        self.repository=repository
        self.password_hasher=password_hasher
        self.token_provider=token_provider

    def execute(self,mail:str,plain_password:str)->str:
        if not self.repository.get_by_mail(mail=mail):
            raise ValueError
        else:
            existing_user=self.repository.get_by_mail(mail=mail)
            if self.password_hasher.verify_password(plain_password,existing_user.hashed_password):
                return self.token_provider.create_token(mail)

