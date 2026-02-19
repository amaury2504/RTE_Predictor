from passlib.context import CryptContext
from src.auth.ports.password_hasher import PasswordHasher


class BcryptHasher(PasswordHasher):
    def __init__(self):
        hasher=CryptContext(["bcrypt"])
        self.hasher=hasher
    
    
    def hash_password(self, plain_password:str)->str:
        hashed_password=self.hasher.hash(secret=plain_password)
        return(hashed_password)
    
    def verify_password(self, plain_password:str, hashed_password:str):
        return(self.hasher.verify(plain_password,hashed_password))
        