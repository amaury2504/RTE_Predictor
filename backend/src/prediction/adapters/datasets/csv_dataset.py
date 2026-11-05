import pandas as pd

from src.prediction.domain.dataset import FullDataset
from src.prediction.domain.features import build_features

PARIS_TZ = "Europe/Paris"


def load_full_dataset(path: str = "data/dataset_ml.csv") -> FullDataset:
    """Charge le jeu de données (date et heure UTC, météo par région, consommation en GW)
    et construit les variables avec le code commun. Le découpage temporel est fait ensuite
    par `split_for_test_year`.

    Les horodatages fournis aux KPI sont en heure locale de Paris, pour que « l'heure du pic »
    et le découpage semaine / week-end aient un sens métier.
    """
    raw = pd.read_csv(path, encoding="utf-8")

    X = build_features(raw)
    y = raw["consommation"].to_numpy(dtype=float)

    day = pd.to_datetime(raw["date"], format="%d/%m/%Y")
    utc = day + pd.to_timedelta(raw["hour"], unit="h")
    local = utc.dt.tz_localize("UTC").dt.tz_convert(PARIS_TZ)
    timestamps = local.dt.strftime("%Y-%m-%dT%H:00").tolist()

    return FullDataset(X=X, y=y, timestamps=timestamps, years=day.dt.year.to_numpy())
