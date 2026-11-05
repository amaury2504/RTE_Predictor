from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from src.auth.application.auth_use_cases import RegisterUser,LoginUser,LoginGuest
from src.auth.adapters.persistence.sqlalchemy_repository_auth import SQLAlchemyUserRepository
from src.auth.adapters.security.bcrypt_hasher import BcryptHasher
from src.auth.adapters.security.jwt_token_provider import JWTTokenProvider
import os
from dotenv import load_dotenv
from src.auth.adapters.persistence.sqlalchemy_models_auth import Base,engine
from src.auth.adapters.api.auth_dependency import CheckAuthorization
from src.auth.domain.exceptions import InvalidCredentialsError,UserAlreadyExistsError
import logging
logger = logging.getLogger(__name__)

# Importation des variables d'environnements :
load_dotenv()

SECRET_KEY=os.getenv("SECRET_KEY")
DURATION_TOKEN=float(os.getenv("DURATION_TOKEN"))


# Structures immuables

Base.metadata.create_all(engine) #Création de la DBUser
repository=SQLAlchemyUserRepository()
password_hasher=BcryptHasher()
token_provider=JWTTokenProvider(SECRET_KEY,DURATION_TOKEN)


# Création du router avec un préfix

auth_router=APIRouter(prefix="/auth")

# BaseModel :

class LoginRequest(BaseModel):
    mail:str
    plain_password:str

class StatusResponse(BaseModel):
    status:str

class TokenResponse(BaseModel):
    token:str

checker=CheckAuthorization(token_provider)

# Création du premier endpoint (register)

@auth_router.post("/register",response_model=StatusResponse)
def register_user(request:LoginRequest)->StatusResponse:
    """J'appelle mon use case Register_User"""
    try:
        use_case=RegisterUser(repository,password_hasher)
        use_case.execute(request.mail,request.plain_password)
        logger.info("Utilisateur enregistré : %s", request.mail)
        return(StatusResponse(status="Ok"))
        
    except UserAlreadyExistsError:
        logger.warning("Tentative d'inscription échouée : %s", request.mail)
        raise HTTPException(status_code=401,detail="Cet email est déjà enregistré")

@auth_router.post("/login",response_model=TokenResponse)
def login_user(request:LoginRequest)->TokenResponse:
    """Je vérifie si mon user peut se login et j'accède à sa demande si c'est le cas"""
    try:
        use_case=LoginUser(repository,password_hasher,token_provider)
        token=use_case.execute(request.mail,request.plain_password)
        logger.info("Login réussi : %s", request.mail)
        return(TokenResponse(token=token))
    except InvalidCredentialsError:
        logger.warning("Tentative de login échouée : %s", request.mail)
        raise HTTPException(status_code=401,detail="Identifiant ou mot de passe incorrect")

@auth_router.post("/guest",response_model=TokenResponse)
def login_guest()->TokenResponse:
    """Mode démo : délivre un token de profil invité, sans identifiant ni mot de passe"""
    use_case=LoginGuest(token_provider)
    token=use_case.execute()
    logger.info("Connexion en profil invité")
    return(TokenResponse(token=token))