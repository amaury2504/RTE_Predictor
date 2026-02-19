import os
from dotenv import load_dotenv
from sqlalchemy import create_engine,Column,Integer,String
from sqlalchemy.orm import sessionmaker,declarative_base


# Injection de l'URL de la DB

load_dotenv()

DATABASE_AUTH_URL=os.getenv(key="DATABASE_AUTH_URL")

#Engine : Connexion à la DB

engine=create_engine(url=DATABASE_AUTH_URL,connect_args={"check_same_thread": False})

# Fabrique de sessions

SessionLocal=sessionmaker(bind=engine)

Base=declarative_base()


class UserDB(Base):

    #Création de la DB

    __tablename__="user_records"

    # Colonnes : 
    id=Column(Integer,primary_key=True,autoincrement=True)
    mail=Column(String,nullable=False,unique=True)
    hashed_password=Column(String,nullable=False)


