from pydantic import BaseModel
from fastapi import APIRouter,Depends

from src.electricity.domain.models import ConsumptionRecord
from src.electricity.application.use_cases import StoreConsumption
from src.electricity.adapters.persistence.sqlalchemy_models import Base,engine
from src.electricity.adapters.persistence.sqlalchemy_repository import SQLAlchemyConsumptionRepository

from src.auth.adapters.api.auth_routes import checker
import logging
logger = logging.getLogger(__name__)
# WIRING : Créé une seule fois au démarrage

Base.metadata.create_all(engine)
repository=SQLAlchemyConsumptionRepository()
store_use_case=StoreConsumption(repository)


# Création de electricity_router
electricity_router=APIRouter(prefix="/electricity")

class ConsumptionRequest(BaseModel):
    date: str
    hour: int|float
    power: float


class StatusResponse(BaseModel):
    status:str

@electricity_router.post("/consumption",dependencies=[Depends(checker.authorized_request)],response_model=StatusResponse)
def store_consumption(data:ConsumptionRequest):
    record=ConsumptionRecord(data.date,data.hour,data.power)
    store_use_case.execute(record)
    logger.info("Consommation enregistrée : %s", record)
    return(StatusResponse(status="Ok"))