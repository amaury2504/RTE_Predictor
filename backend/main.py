from fastapi import FastAPI
from pydantic import BaseModel
from src.electricity.adapters.persistence.in_memory_repository import InMemoryConsumptionRepository
from src.electricity.domain.models import ConsumptionRecord
from src.electricity.application.use_cases import StoreConsumption

app=FastAPI()

# WIRING : Créé une seule fois au démarrage
repository=InMemoryConsumptionRepository()
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

    

