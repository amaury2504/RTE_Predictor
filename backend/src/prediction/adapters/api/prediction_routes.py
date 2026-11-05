from dataclasses import asdict
from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.prediction.adapters.ml.PyTorchPrediction import ConsumptionModel
from src.auth.adapters.api.auth_routes import checker
from src.prediction.domain.models_prediction import PredictionInput, PredictionResult
from src.prediction.application.use_cases_prediction import PredictConsumptionUseCase, ComputeKpisUseCase
from src.prediction.adapters.ml.PyTorchPrediction import PredictWithPytorch
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import torch
import joblib
import logging
import httpx

logger = logging.getLogger(__name__)

prediction_router = APIRouter(prefix="/prediction")

PARIS_TZ = ZoneInfo("Europe/Paris")


class PredictionRequest(BaseModel):
    date: str
    hour: int | float
    temperatures: dict[str, float]
    wind_speeds: dict[str, float]
    humidities: dict[str, float]


class PredictionResponse(BaseModel):
    date: str
    hour: int
    power: int | float


class BatchPredictionRequest(BaseModel):
    items: list[PredictionRequest]


class BatchPredictionResponse(BaseModel):
    items: list[PredictionResponse]


class KpiPointRequest(BaseModel):
    datetime: str           # horodatage local, ex. "2026-05-27T14:00"
    predicted: float        # GW
    actual: float           # GW


class KpiRequest(BaseModel):
    points: list[KpiPointRequest] = Field(min_length=1, max_length=5000)


class SegmentKpiResponse(BaseModel):
    key: str | int
    n: int
    mae: float
    mape: float | None
    bias: float


class KpiResponse(BaseModel):
    n: int
    mean_actual: float
    mean_predicted: float
    mae: float
    rmse: float
    mape: float | None
    wape: float | None
    smape: float | None
    nrmse: float | None
    bias: float
    median_ae: float
    p95_ae: float
    max_ae: float
    r2: float | None
    mase: float | None
    within_5_pct: float | None
    within_10_pct: float | None
    peak_days: int
    peak_mae: float | None
    peak_bias: float | None
    peak_hour_mae: float | None
    by_hour: list[SegmentKpiResponse]
    by_day: list[SegmentKpiResponse]
    weekday: SegmentKpiResponse | None
    weekend: SegmentKpiResponse | None


class RTEDataPoint(BaseModel):
    datetime: str
    consumption: int


class RTEWeekResponse(BaseModel):
    data: list[RTEDataPoint]


# Charger le modèle
model = ConsumptionModel(input_size=57)
model.load_state_dict(torch.load("data/model.pth"))
model.eval()

scaler_X = joblib.load("data/scaler_X.pkl")
scaler_Y = joblib.load("data/scaler_Y.pkl")


class RTEConsumptionResponse(BaseModel):
    consumption_mw: int


@prediction_router.get("/rte-now", dependencies=[Depends(checker.authorized_request)], response_model=RTEConsumptionResponse)
async def get_rte_now(date: str, hour: int):
    """Retourne la consommation RTE pour une date/heure locale Paris (date au format DD/MM/YYYY)."""
    local_date = datetime.strptime(date, "%d/%m/%Y")
    local_dt = datetime(local_date.year, local_date.month, local_date.day, hour, 0, 0, tzinfo=PARIS_TZ)
    utc_dt = local_dt.astimezone(timezone.utc)
    utc_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fenêtre : de 2h avant jusqu'à l'heure demandée → on prend le point le plus récent disponible
    window_start = (utc_dt - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    url = (
        "https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets"
        "/eco2mix-national-tr/records"
    )
    params = {
        "limit": 10,
        "order_by": "date_heure desc",
        "select": "date_heure,consommation",
        "where": f'date_heure <= "{utc_str}" AND date_heure >= "{window_start}" AND consommation is not null',
    }
    try:
        async with httpx.AsyncClient(timeout=15, verify=False, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RTE connexion impossible : {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"RTE HTTP {resp.status_code}")

    records = resp.json().get("results", [])
    if not records:
        raise HTTPException(status_code=404, detail="Données RTE indisponibles pour cette heure")

    return RTEConsumptionResponse(consumption_mw=int(records[0]["consommation"]))


@prediction_router.post("/predict", dependencies=[Depends(checker.authorized_request)], response_model=PredictionResponse)
def predict_consumption(data: PredictionRequest):
    domain_input = PredictionInput(data.date, data.hour, data.temperatures, data.wind_speeds, data.humidities)
    method = PredictWithPytorch(model, scaler_X, scaler_Y)
    use_case = PredictConsumptionUseCase(domain_input, method)
    response = use_case.execute_prediction_item()
    result = PredictionResult(response.date, response.hour, response.power)
    logger.info("Prédiction demandée pour le %s à %sh", data.date, data.hour)
    return PredictionResponse(date=result.date, hour=result.hour, power=result.power)


@prediction_router.post("/batch-predict", dependencies=[Depends(checker.authorized_request)], response_model=BatchPredictionResponse)
def batch_predict(data: BatchPredictionRequest):
    method = PredictWithPytorch(model, scaler_X, scaler_Y)
    results = []
    for item in data.items:
        domain_input = PredictionInput(item.date, item.hour, item.temperatures, item.wind_speeds, item.humidities)
        use_case = PredictConsumptionUseCase(domain_input, method)
        resp = use_case.execute_prediction_item()
        result = PredictionResult(resp.date, resp.hour, resp.power)
        results.append(PredictionResponse(date=result.date, hour=result.hour, power=result.power))
    logger.info("Batch predict : %d prédictions exécutées", len(results))
    return BatchPredictionResponse(items=results)


@prediction_router.post("/kpis", dependencies=[Depends(checker.authorized_request)], response_model=KpiResponse)
def compute_model_kpis(data: KpiRequest):
    """Calcule les KPI de performance à partir de couples (prédit, réel) horodatés, en GW."""
    use_case = ComputeKpisUseCase(
        timestamps=[p.datetime for p in data.points],
        predicted=[p.predicted for p in data.points],
        actual=[p.actual for p in data.points],
    )
    try:
        report = use_case.execute()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    logger.info("KPI calculés sur %d points", report.n)
    return KpiResponse.model_validate(asdict(report))


@prediction_router.get("/rte-week",dependencies=[Depends(checker.authorized_request)], response_model=RTEWeekResponse)
async def get_rte_week():
    now = datetime.now(timezone.utc)
    end_dt = (now - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(hours=167)

    start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    base_url = (
        "https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets"
        "/eco2mix-national-tr/records"
    )

    all_records = []
    offset = 0

    async with httpx.AsyncClient(timeout=30, verify=False, follow_redirects=True) as client:
        while len(all_records) < 800:
            params = {
                "limit": 100,
                "offset": offset,
                "order_by": "date_heure asc",
                "select": "date_heure,consommation",
                "where": f'date_heure >= "{start_str}" AND date_heure <= "{end_str}" AND consommation is not null',
            }
            try:
                resp = await client.get(base_url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"RTE connexion impossible : {e}")

            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"RTE HTTP {resp.status_code} : {resp.text[:200]}")

            records = resp.json().get("results", [])
            all_records.extend(records)
            if len(records) < 100:
                break
            offset += 100

    hourly = []
    for r in all_records:
        try:
            dt_paris = datetime.fromisoformat(r["date_heure"]).astimezone(PARIS_TZ)
            if dt_paris.minute == 0:
                hourly.append(RTEDataPoint(
                    datetime=dt_paris.strftime("%Y-%m-%dT%H:00"),
                    consumption=int(r["consommation"]),
                ))
        except Exception:
            continue

    hourly.sort(key=lambda x: x.datetime)
    logger.info("RTE semaine : %d points horaires retournés", len(hourly))
    return RTEWeekResponse(data=hourly)
