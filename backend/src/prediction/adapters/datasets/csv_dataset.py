import numpy as np
import pandas as pd

from src.prediction.domain.dataset import FullDataset
from src.prediction.domain.features import build_features
from src.prediction.domain.foundation import foundation_forecasts
from src.prediction.domain.level import build_level_features
from src.prediction.domain.smoothing import holt_winters_forecasts

PARIS_TZ = "Europe/Paris"


def load_full_dataset(path: str = "data/dataset_ml.csv", level_features: bool = False) -> FullDataset:
    """Charge le jeu de données (date et heure UTC, météo par région, consommation en GW)
    et construit les variables avec le code commun. Le découpage temporel est fait ensuite
    par `split_for_test_year`.

    Avec `level_features=True` (piste B), les variables de niveau récent de la consommation sont ajoutées
    (voir domain/level.py) ; sinon seules la météo et le calendrier sont fournis (piste A).

    Les horodatages fournis aux KPI sont en heure locale de Paris, pour que « l'heure du pic »
    et le découpage semaine / week-end aient un sens métier.
    """
    raw = pd.read_csv(path, encoding="utf-8")

    X = build_features(raw)
    y = raw["consommation"].to_numpy(dtype=float)

    day = pd.to_datetime(raw["date"], format="%d/%m/%Y")
    utc = day + pd.to_timedelta(raw["hour"], unit="h")
    if level_features:
        X = pd.concat([X, build_level_features(pd.DatetimeIndex(utc), y)], axis=1)
    local = utc.dt.tz_localize("UTC").dt.tz_convert(PARIS_TZ)
    timestamps = local.dt.strftime("%Y-%m-%dT%H:00").tolist()

    return FullDataset(X=X, y=y, timestamps=timestamps, years=day.dt.year.to_numpy())


RTE_PATH = "data/eco2mix-national-cons-def.csv"


def load_reference_forecasts(dataset_path: str = "data/dataset_ml.csv", rte_path: str = RTE_PATH) -> dict[str, np.ndarray]:
    """Prévisions de référence alignées ligne à ligne sur `load_full_dataset` (GW ; NaN si indisponible).

    Ces références utilisent la consommation passée (ou les prévisions d'RTE) : elles ne respectent
    pas le contrat des modèles météo + calendrier et sont classées à part.

    - ref_naive_j1   : consommation observée 24 h plus tôt
    - ref_naive_j2   : consommation observée 48 h plus tôt (même information disponible que la piste B)
    - ref_naive_s1   : consommation observée 168 h plus tôt (même heure, semaine précédente)
    - ref_rte_j1     : prévision J-1 publiée par RTE (moyenne horaire des pas de 15 min)
    - ref_rte_j      : prévision J (jour même) publiée par RTE ; les valeurs 0 sont des trous
    """
    raw = pd.read_csv(dataset_path, encoding="utf-8", usecols=["date", "hour", "consommation"])
    utc = pd.DatetimeIndex(pd.to_datetime(raw["date"], format="%d/%m/%Y") + pd.to_timedelta(raw["hour"], unit="h"))
    actual = pd.Series(raw["consommation"].to_numpy(dtype=float), index=utc)

    refs = {
        "ref_naive_j1": actual.reindex(utc - pd.Timedelta(hours=24)).to_numpy(),
        "ref_naive_j2": actual.reindex(utc - pd.Timedelta(hours=48)).to_numpy(),
        "ref_naive_s1": actual.reindex(utc - pd.Timedelta(hours=168)).to_numpy(),
    }

    rte = pd.read_csv(rte_path, sep=";", encoding="utf-8-sig", usecols=[4, 6, 7])
    rte.columns = ["datetime", "j1", "j"]
    rte["t"] = pd.to_datetime(rte["datetime"], utc=True).dt.tz_localize(None)
    rte = rte.drop_duplicates("t").set_index("t").drop(columns="datetime")
    rte["j"] = rte["j"].replace(0, np.nan)
    hourly = rte.groupby(rte.index.floor("h")).mean() / 1000.0  # MW -> GW
    refs["ref_rte_j1"] = hourly["j1"].reindex(utc).to_numpy()
    refs["ref_rte_j"] = hourly["j"].reindex(utc).to_numpy()
    return refs


# Grille de lissage, élargie une fois parce que le meilleur couple de validation touchait le bord de la première grille
SMOOTHING_ALPHAS = (0.01, 0.03, 0.1, 0.2, 0.4)
SMOOTHING_GAMMAS = (0.01, 0.03, 0.1, 0.3)


def load_smoothing_candidates(
    dataset_path: str = "data/dataset_ml.csv",
    alphas: tuple[float, ...] = SMOOTHING_ALPHAS,
    gammas: tuple[float, ...] = SMOOTHING_GAMMAS,
) -> dict[str, np.ndarray]:
    """Prévisions Holt-Winters (consommation seule) pour chaque couple (alpha, gamma), alignées sur `load_full_dataset`.

    Le choix du couple se fait ensuite, année par année, sur la validation (voir application/baselines.py).
    """
    raw = pd.read_csv(dataset_path, encoding="utf-8", usecols=["date", "hour", "consommation"])
    utc = pd.DatetimeIndex(pd.to_datetime(raw["date"], format="%d/%m/%Y") + pd.to_timedelta(raw["hour"], unit="h"))
    actual = raw["consommation"].to_numpy(dtype=float)
    return {
        f"alpha={a},gamma={g}": holt_winters_forecasts(utc, actual, a, g)
        for a in alphas for g in gammas
    }


def load_foundation_forecasts(
    forecaster,
    years: list[int],
    dataset_path: str = "data/dataset_ml.csv",
    context_hours: int = 1344,
    with_weather: bool = True,
    on_progress=None,
    prefix: str = "ts_timestral",
) -> dict[str, np.ndarray]:
    """Prévisions d'un modèle de fondation pour tous les jours des `years`, alignées sur `load_full_dataset`.

    - <prefix>        : consommation seule (historique connu jusqu'à 48 h avant)
    - <prefix>_meteo  : en plus, température nationale moyenne et jour férié, connus à l'avance
      (la météo observée sert de prévision parfaite, comme pour les modèles de la piste A)
    `prefix` contient la taille du modèle (ex. ts_timestral_28m) pour distinguer plusieurs tailles.
    """
    raw = pd.read_csv(dataset_path, encoding="utf-8")
    days_utc = pd.to_datetime(raw["date"], format="%d/%m/%Y")
    utc = pd.DatetimeIndex(days_utc + pd.to_timedelta(raw["hour"], unit="h"))
    actual = raw["consommation"].to_numpy(dtype=float)
    wanted = set(years)
    target_days = sorted(d for d in days_utc.unique() if pd.Timestamp(d).year in wanted)

    def report(name: str):
        return (lambda done, total: on_progress(name, done, total)) if on_progress else None

    refs = {prefix: foundation_forecasts(
        forecaster, utc, actual, target_days, context_hours, on_progress=report(prefix))}
    if with_weather:
        features = build_features(raw)
        temperature_cols = [c for c in features.columns if c.startswith("temperature_") and not c.endswith("_squared")]
        covariates = np.column_stack([features[temperature_cols].mean(axis=1), features["is_holiday"]])
        refs[f"{prefix}_meteo"] = foundation_forecasts(
            forecaster, utc, actual, target_days, context_hours, covariates=covariates,
            on_progress=report(f"{prefix}_meteo"))
    return refs
