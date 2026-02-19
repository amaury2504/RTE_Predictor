

class User():
    """Classe servant à définir ce qu'est un user valide dans mon application.
    """    

    def __init__(self,mail:str,hashed_password:str):
        """Vérification et initialisation des paramètres
        
        Args : 
            - mail : Adresse email de l'utilisateur. C'est une string non vide composée d'un @ et d'un .
            - hashed_password : Mot de passe de l'utilisateur : c'est une string non vide
        """

        # Vérification des types 

        if not isinstance(mail,str):
            raise TypeError("L'adresse mail doit être une string")
        
        if not isinstance(hashed_password,str):
            raise TypeError("Le password doit être une string")


        # Vérification des valeurs

        if not mail:
            raise ValueError("L'adresse mail ne peut être vide.")
        
        if not mail.strip():
            raise ValueError("L'adresse email ne peut être vide.")
        
        if "@" not in mail:
            raise ValueError("Format d'adresse mail incorrecte, il manque @")
        

        if "." not in mail: 
            raise ValueError("Format d'adresse mail incorrecte, il manque .")
        
        dot_after_arobase=mail.split("@")[1]
        if "." not in dot_after_arobase:
            raise ValueError("Format mail incorrect : Il doit y avoir un . derrière @")
        

        if not hashed_password:
            raise ValueError("Le password ne peut être vide")
        
        
        if not hashed_password.strip():
            raise ValueError("Le password ne peut être vide")
        
        #Initialisation des attributs

        self.mail=mail
        self.hashed_password=hashed_password

        
  