from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from src.prediction.domain.models_prediction import PredictionInput

PARIS_TZ = ZoneInfo("Europe/Paris")


def raw_row_from_input(input: PredictionInput) -> dict:
    """Ligne brute au format du jeu d'entraînement (jour et heure UTC, météo par région).

    L'API reçoit une heure locale de Paris ; les données d'entraînement sont en UTC. Partagé par tous les
    modèles servis, pour qu'ils reçoivent exactement les mêmes entrées.
    """
    local_date = pd.to_datetime(input.date, format="%d/%m/%Y")
    local_dt = datetime(
        local_date.year, local_date.month, local_date.day,
        int(input.hour), 0, 0, tzinfo=PARIS_TZ
    )
    utc_dt = local_dt.astimezone(timezone.utc)

    raw = {"date": utc_dt.strftime("%d/%m/%Y"), "hour": utc_dt.hour}
    for region, temp in input.temp_regions.items():
        raw[f"temperature_{region}"] = temp
    for region, wind_speed in input.wind_regions.items():
        raw[f"wind_speed_{region}"] = wind_speed
    for region, humidity in input.humidity_regions.items():
        raw[f"humidity_{region}"] = humidity
    return raw
