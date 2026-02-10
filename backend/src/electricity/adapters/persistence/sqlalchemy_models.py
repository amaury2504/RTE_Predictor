from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL=os.getenv("DATABASE_URL")

# Engine = Connexion à la DB
engine =create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


# Fabrique de sessions
SessionLocal=sessionmaker(bind=engine)

# Classe de base pour les modèles 
Base = declarative_base()

class ConsumptionRecordDB(Base):
    #Création de la DB

    __tablename__="consumption_records" #Nom de la DB

    # Colonnes = Attributs de classe
    id=Column(Integer, primary_key=True,autoincrement=True)
    date=Column(String, nullable=False)
    hour=Column(Float,nullable=False)
    power=Column(Float,nullable=False)

class WeatherRecordDB(Base):
    # Création de la DB

    __tablename__="Weather_records_by_region" # Nom de la DB

    # Colonnes = Attributs de classe

    id=Column(Integer,primary_key=True,autoincrement=True)
    date=Column(String,nullable=False) # Colonne date : Format "JJ/MM/AAAA"
    hour=Column(Float,nullable=False) # Colonne heure : Format 0-23
    region=Column(String, nullable=False) # Colonne région
    temperature=Column(Float,nullable=False) # Colonne température (en °C)
    wind_speed=Column(Float,nullable=False) # Colonne wind_speed (en km/h)
    relative_humidity=Column(Float,nullable=False) # Colonne relative_humidity (en %)