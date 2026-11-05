from src.auth.application.auth_use_cases import GUEST_SUBJECT
from src.auth.ports.token_provider import TokenProvider
from typing import Annotated
from fastapi import HTTPException, Header
from jose import JWTError


class CheckAuthorization():
    """Cette classe sert à protéger les routes internes de l'outil, celles soumises à autorisation."""
    def __init__(self,token_provider:TokenProvider):
        
        self.token_provider=token_provider


    def authorized_request(self,authorization:Annotated[str,Header()])->str:
        
        if authorization.startswith("Bearer "):
            token=authorization.split(" ")[1]
        else:
            raise HTTPException(status_code=401,detail="Format d'autorisation invalide : Utilisez 'Bearer <token>'")
        try: 
            response=self.token_provider.verify_token(token)
            return(response)
        except JWTError:
            raise HTTPException(status_code=401,detail="Token invalide ou expiré")

    def registered_request(self,authorization:Annotated[str,Header()])->str:
        """Comme authorized_request, mais refuse le profil invité (routes qui écrivent des données)."""
        subject=self.authorized_request(authorization)
        if subject==GUEST_SUBJECT:
            raise HTTPException(status_code=403,detail="Cette action nécessite un compte, pas le profil invité")
        return(subject)
            