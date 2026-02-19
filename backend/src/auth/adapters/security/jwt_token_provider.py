from jose import jwt
from src.auth.ports.token_provider import TokenProvider
import datetime


# Chargement des variables d'environnements

class JWTTokenProvider(TokenProvider):
    """Classe implémentant le port TokenProvider.
    Ce qui se passe : 
        - On reçoit une clé secrète (string) une durée d'expiration en minutes
        - Si on veut créer un token, on crée un dictionnaire appelé payload
        et une date d'expiration. On encore le tour avce jwt.encode de la librairie jose.
        - verify_token : Je décode le token. Une exception est levée automatiquement. Sinon, on extrait le mail et on l'envoie"""
    

    def __init__(self,secret_key:str,duration:float):
        self.secret_key=secret_key
        self.duration=duration


    def create_token(self, mail:str)->str:
        dt=datetime.datetime.now()
        interval=datetime.timedelta(minutes=self.duration)
        exp_date=dt+interval
        payload={"sub":mail,"exp":exp_date}
        return(jwt.encode(claims=payload,key=self.secret_key,algorithm="HS256"))
    
    def verify_token(self,token_used):
        payload=jwt.decode(token=token_used,key=self.secret_key,algorithms=["HS256"])
        return(payload["sub"])
