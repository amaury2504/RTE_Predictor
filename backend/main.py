from fastapi import FastAPI
from pydantic import BaseModel
from src.electricity.adapters.persistence.sqlalchemy_repository import SQLAlchemyConsumptionRepository
from src.electricity.adapters.persistence.sqlalchemy_models import Base,engine
from src.electricity.domain.models import ConsumptionRecord
from src.electricity.application.use_cases import StoreConsumption
from src.prediction.adapters.ml.PyTorchPrediction import PredictWithPytorch
from src.prediction.application.use_cases_prediction import PredictConsumptionUseCase
from src.prediction.domain.models_prediction import PredictionResult, PredictionInput
from src.prediction.adapters.ml.PyTorchPrediction import ConsumptionModel
from src.auth.adapters.api.auth_routes import auth_router

import torch
import joblib


app=FastAPI()

Base.metadata.create_all(engine)

# WIRING : Créé une seule fois au démarrage
repository=SQLAlchemyConsumptionRepository()
store_use_case=StoreConsumption(repository)

@app.get("/")
def root():
    return {"message": "API Electricité"}

class ConsumptionRequest(BaseModel):
    date: str
    hour: int|float
    power: float


@app.post("/consumption")
def store_consumption(data:ConsumptionRequest):
    record=ConsumptionRecord(data.date,data.hour,data.power)
    store_use_case.execute(record)
    return {"Status":"Ok"}

    
class PredictionRequest(BaseModel):
    date:str
    hour:int|float
    temperatures:dict[str,float]
    wind_speeds:dict[str, float]
    humidities:dict[str,float]



# Charger le modèle
model=ConsumptionModel(input_size=56)
model.load_state_dict(torch.load("data/model.pth"))
model.eval()

# Charger les scalers
scaler_X=joblib.load("data/scaler_X.pkl")
scaler_Y=joblib.load("data/scaler_Y.pkl")


@app.post("/predict")
def predict_consumption(data:PredictionRequest):
    domain_input=PredictionInput(data.date,data.hour,data.temperatures,data.wind_speeds,data.humidities)
    method=PredictWithPytorch(model,scaler_X,scaler_Y)
    use_case_prediction=PredictConsumptionUseCase(domain_input,method)
    response=use_case_prediction.execute_prediction_item()
    resultat=PredictionResult(response.date,response.hour,response.power)
    return(resultat)


app.include_router(router=auth_router)