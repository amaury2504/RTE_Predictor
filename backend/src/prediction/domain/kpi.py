"""KPI de performance d'un modèle de prévision de consommation électrique.

Module pur (pas de dépendance à un modèle ni à un framework web) : il prend des
couples (prédit, réel) horodatés et calcule les indicateurs. Il est utilisé par
l'API (onglet « Robustesse du modèle ») et pourra l'être par le benchmark.

Conventions :
- Toutes les puissances sont en GW.
- Erreur signée = prédit - réel : positive = le modèle SURESTIME, négative = il SOUS-ESTIME.
- Les pourcentages sont exprimés en % (5.0 = 5 %).
- Un indicateur non calculable (données insuffisantes, division par zéro) vaut None.
"""
from dataclasses import dataclass, field
from typing import Sequence
import math

import numpy as np
import pandas as pd

# Une journée complète compte 24 heures (23 ou 25 les jours de changement d'heure)
MIN_HOURS_FOR_DAILY_PEAK = 23
# Pas saisonnier utilisé pour la référence naïve de la MASE : même heure la veille
NAIVE_LAG_HOURS = 24


@dataclass(frozen=True)
class SegmentKpi:
    """KPI calculés sur un sous-ensemble des points (une heure du jour, un jour, ...)."""
    key: str | int
    n: int
    mae: float
    mape: float | None
    bias: float


@dataclass(frozen=True)
class KpiReport:
    # Volume et niveau moyen
    n: int
    mean_actual: float
    mean_predicted: float

    # Précision globale
    mae: float                 # Erreur absolue moyenne (GW)
    rmse: float                # Racine de l'erreur quadratique moyenne (GW), pénalise les gros écarts
    mape: float | None         # Erreur absolue moyenne en % du réel, point par point
    wape: float | None         # Somme des erreurs absolues / somme du réel (%), robuste aux faibles valeurs
    smape: float | None        # MAPE symétrique (%)
    nrmse: float | None        # RMSE / consommation moyenne réelle (%)

    # Biais et distribution de l'erreur absolue
    bias: float                # Erreur signée moyenne (GW) : > 0 surestime, < 0 sous-estime
    median_ae: float           # Erreur absolue médiane (GW)
    p95_ae: float              # 95e percentile de l'erreur absolue (GW)
    max_ae: float              # Pire erreur absolue (GW)

    # Qualité relative
    r2: float | None           # Part de variance expliquée (1 = parfait)
    mase: float | None         # MAE / MAE de la prévision naïve J-1 ; < 1 = bat la référence naïve
    within_5_pct: float | None   # % de points avec une erreur relative <= 5 %
    within_10_pct: float | None  # % de points avec une erreur relative <= 10 %

    # Pointe journalière (le pic compte pour le dimensionnement du réseau)
    peak_days: int
    peak_mae: float | None         # Erreur absolue moyenne sur la valeur du pic (GW)
    peak_bias: float | None        # Erreur signée moyenne sur la valeur du pic (GW)
    peak_hour_mae: float | None    # Décalage absolu moyen de l'heure du pic (heures)

    # Découpages
    by_hour: list[SegmentKpi] = field(default_factory=list)
    by_day: list[SegmentKpi] = field(default_factory=list)
    weekday: SegmentKpi | None = None
    weekend: SegmentKpi | None = None

    # MAE une fois le biais moyen retiré (mean |erreur - biais|) : mesure la qualité de la forme de la
    # courbe indépendamment d'un décalage de niveau (voir DECISIONS.md)
    mae_debiased: float | None = None


def _clean(value: float | None, digits: int = 4) -> float | None:
    """Arrondit et convertit NaN/inf en None (JSON-safe)."""
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return round(value, digits)


def _segment(key: str | int, y: np.ndarray, p: np.ndarray) -> SegmentKpi:
    err = p - y
    positive = y > 0
    mape = float(np.mean(np.abs(err[positive]) / y[positive] * 100)) if positive.any() else None
    return SegmentKpi(
        key=key,
        n=int(len(y)),
        mae=_clean(np.mean(np.abs(err))),
        mape=_clean(mape),
        bias=_clean(np.mean(err)),
    )


def _mase(y: np.ndarray, ts: pd.DatetimeIndex, mae: float) -> float | None:
    """MASE : MAE du modèle rapportée à celle d'une prévision naïve « même heure la veille »,
    calculée sur les mêmes données."""
    series = pd.Series(y, index=ts).groupby(level=0).mean().sort_index()
    lagged = series.shift(NAIVE_LAG_HOURS, freq="h")
    naive_errors = (series - lagged).dropna().abs()
    if naive_errors.empty:
        return None
    scale = float(naive_errors.mean())
    if scale == 0:
        return None
    return mae / scale


def _daily_peak_kpis(df: pd.DataFrame) -> tuple[int, float | None, float | None, float | None]:
    value_errors, hour_errors = [], []
    for _, day in df.groupby("date"):
        if len(day) < MIN_HOURS_FOR_DAILY_PEAK:
            continue
        actual_peak = day.loc[day["y"].idxmax()]
        predicted_peak = day.loc[day["p"].idxmax()]
        value_errors.append(day["p"].max() - day["y"].max())
        hour_errors.append(abs(int(predicted_peak["hour"]) - int(actual_peak["hour"])))
    if not value_errors:
        return 0, None, None, None
    value_errors = np.asarray(value_errors)
    return (
        len(value_errors),
        float(np.mean(np.abs(value_errors))),
        float(np.mean(value_errors)),
        float(np.mean(hour_errors)),
    )


def compute_kpis(
    timestamps: Sequence[str],
    predicted: Sequence[float],
    actual: Sequence[float],
) -> KpiReport:
    """Calcule tous les KPI à partir de séries horaires alignées.

    Args:
        timestamps: horodatages locaux (ex. "2026-05-27T14:00"), un par point.
        predicted: puissance prédite en GW.
        actual: puissance réelle en GW.

    Raises:
        ValueError: longueurs différentes, série vide ou valeurs non finies.
    """
    if not (len(timestamps) == len(predicted) == len(actual)):
        raise ValueError("timestamps, predicted et actual doivent avoir la même longueur")
    if len(actual) == 0:
        raise ValueError("Au moins un point est nécessaire pour calculer les KPI")

    y = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if not (np.isfinite(y).all() and np.isfinite(p).all()):
        raise ValueError("predicted et actual ne doivent contenir que des valeurs finies")

    ts = pd.DatetimeIndex(pd.to_datetime(list(timestamps)))

    err = p - y
    abs_err = np.abs(err)
    positive = y > 0

    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mean_actual = float(np.mean(y))

    rel_err = abs_err[positive] / y[positive] * 100
    mape = float(np.mean(rel_err)) if positive.any() else None
    wape = float(abs_err.sum() / y.sum() * 100) if y.sum() > 0 else None
    denom = np.abs(y) + np.abs(p)
    smape = float(np.mean(2 * abs_err[denom > 0] / denom[denom > 0] * 100)) if (denom > 0).any() else None
    nrmse = rmse / mean_actual * 100 if mean_actual > 0 else None

    ss_tot = float(np.sum((y - mean_actual) ** 2))
    r2 = 1 - float(np.sum(err ** 2)) / ss_tot if ss_tot > 0 else None

    within_5 = float(np.mean(rel_err <= 5) * 100) if positive.any() else None
    within_10 = float(np.mean(rel_err <= 10) * 100) if positive.any() else None

    df = pd.DataFrame({"y": y, "p": p, "date": ts.strftime("%Y-%m-%d"), "hour": ts.hour, "dow": ts.dayofweek})

    peak_days, peak_mae, peak_bias, peak_hour_mae = _daily_peak_kpis(df)

    by_hour = [_segment(int(h), g["y"].to_numpy(), g["p"].to_numpy()) for h, g in df.groupby("hour")]
    by_day = [_segment(str(d), g["y"].to_numpy(), g["p"].to_numpy()) for d, g in df.groupby("date")]

    weekday_df, weekend_df = df[df["dow"] < 5], df[df["dow"] >= 5]
    weekday = _segment("semaine", weekday_df["y"].to_numpy(), weekday_df["p"].to_numpy()) if len(weekday_df) else None
    weekend = _segment("week-end", weekend_df["y"].to_numpy(), weekend_df["p"].to_numpy()) if len(weekend_df) else None

    return KpiReport(
        n=int(len(y)),
        mean_actual=_clean(mean_actual),
        mean_predicted=_clean(np.mean(p)),
        mae=_clean(mae),
        rmse=_clean(rmse),
        mape=_clean(mape),
        wape=_clean(wape),
        smape=_clean(smape),
        nrmse=_clean(nrmse),
        bias=_clean(np.mean(err)),
        median_ae=_clean(np.median(abs_err)),
        p95_ae=_clean(np.percentile(abs_err, 95)),
        max_ae=_clean(np.max(abs_err)),
        r2=_clean(r2),
        mase=_clean(_mase(y, ts, mae)),
        within_5_pct=_clean(within_5, 2),
        within_10_pct=_clean(within_10, 2),
        peak_days=peak_days,
        peak_mae=_clean(peak_mae),
        peak_bias=_clean(peak_bias),
        peak_hour_mae=_clean(peak_hour_mae, 2),
        by_hour=by_hour,
        by_day=by_day,
        weekday=weekday,
        weekend=weekend,
        mae_debiased=_clean(np.mean(np.abs(err - np.mean(err)))),
    )
