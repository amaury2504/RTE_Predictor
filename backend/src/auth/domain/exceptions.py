class UserAlreadyExistsError(Exception):

    def __init__(self,mail:str):
        super().__init__(f"Le mail est déjà enregistré dans la base : {mail}")

class InvalidCredentialsError(Exception):
    def __init__(self):
        super().__init__("Les identifiants sont invalides")