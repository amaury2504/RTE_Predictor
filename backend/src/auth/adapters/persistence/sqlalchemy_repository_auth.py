from src.auth.ports.user_repository import UserRepository
from src.auth.domain.models_auth import User
from src.auth.adapters.persistence.sqlalchemy_models_auth import SessionLocal,UserDB

class SQLAlchemyUserRepository(UserRepository):
    
    def store_user(self,user:User)->None:
        #Conversion de User vers UserDB
        user_db=UserDB(mail=user.mail,hashed_password=user.hashed_password)


        #Ouverture de la session

        session=SessionLocal()

        #Ajout de l'objet dans la DB

        session.add(user_db)

        #Commit

        session.commit()

        #Fermeture de session :
        session.close()

    
    def get_by_mail(self,mail:str)->User|None:

        session=SessionLocal()

        user_extracted=session.query(UserDB).filter(UserDB.mail==mail).first()

        if not user_extracted:
            session.close()
            return None
        else:
            user=User(user_extracted.mail,user_extracted.hashed_password)
            session.close()
            return(user)