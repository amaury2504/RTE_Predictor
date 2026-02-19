from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from src.auth.application.auth_use_cases import RegisterUser,LoginUser
from src.auth.adapters.persistence.sqlalchemy_repository_auth import SQLAlchemyUserRepository
from src.auth.adapters.security.bcrypt_hasher import BcryptHasher
from src.auth.adapters.security.jwt_token_provider import JWTTokenProvider
import os
from dotenv import load_dotenv
from src.auth.adapters.persistence.sqlalchemy_models_auth import Base,engine

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



# Création du premier endpoint (register)

@auth_router.post("/register")
def register_user(request:LoginRequest)->None:
    """J'appelle mon use case Register_User"""
    use_case=RegisterUser(repository,password_hasher)
    use_case.execute(request.mail,request.plain_password)
    return{"Status":"Ok"}


@auth_router.post("/login")
def login_user(request:LoginRequest)->dict:
    """Je vérifie si mon user peut se login et j'accède à sa demande si c'est le cas"""
    try:
        use_case=LoginUser(repository,password_hasher,token_provider)
        token=use_case.execute(request.mail,request.plain_password)
        return({"token" : token})
    except ValueError:
        raise HTTPException(status_code=401)