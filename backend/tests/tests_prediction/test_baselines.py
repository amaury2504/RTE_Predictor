import numpy as np
import pandas as pd

from src.prediction.adapters.datasets.csv_dataset import load_reference_forecasts
from src.prediction.application.baselines import run_baselines
from src.prediction.domain.dataset import FullDataset


def make_full() -> FullDataset:
    ts, years = [], []
    for year in (2021, 2022, 2023):
        for t in pd.date_range(f"{year}-03-01", periods=30, freq="h"):
            ts.append(t.strftime("%Y-%m-%dT%H:00"))
            years.append(year)
    n = len(years)
    return FullDataset(X=pd.DataFrame({"f": np.arange(n)}), y=50 + np.arange(n) % 7 * 1.0,
                       timestamps=ts, years=np.array(years))


def test_baseline_perfect_reference_has_zero_error():
    full = make_full()
    results = run_baselines(full, {"ref_parfaite": np.asarray(full.y)}, [2022, 2023])
    assert [r.test_year for r in results] == [2022, 2023]
    assert all(r.test.mae == 0 and r.model == "ref_parfaite" for r in results)


def test_baseline_ignores_missing_points_and_skips_empty_years():
    full = make_full()
    pred = np.asarray(full.y) + 1.0
    pred[np.asarray(full.years) == 2023] = np.nan   # rien d'évaluable en 2023
    pred[:5] = np.nan                               # quelques trous en 2021
    results = run_baselines(full, {"ref": pred}, [2022, 2023])
    assert [r.test_year for r in results] == [2022]
    assert results[0].test.n == 30 and results[0].test.bias == 1.0
    assert results[0].val.n == 25


def test_load_reference_forecasts_alignment(tmp_path):
    hours = pd.date_range("2024-01-01", periods=200, freq="h")
    ds = tmp_path / "ds.csv"
    pd.DataFrame({"date": hours.strftime("%d/%m/%Y"), "hour": hours.hour.astype(float),
                  "consommation": np.arange(200, dtype=float)}).sample(frac=1, random_state=0).to_csv(ds, index=False)
    q = pd.date_range("2024-01-01", periods=800, freq="15min", tz="UTC").tz_convert("Europe/Paris")
    rte = tmp_path / "rte.csv"
    pd.DataFrame({"Périmètre": "France", "Nature": "x", "Date": "", "Heure": "", "Date et Heure": q.strftime("%Y-%m-%dT%H:%M:%S%z"),
                  "Consommation (MW)": 0, "Prévision J-1 (MW)": 1000, "Prévision J (MW)": 2000}).to_csv(
        rte, sep=";", index=False, encoding="utf-8-sig")
    refs = load_reference_forecasts(str(ds), str(rte))
    raw = pd.read_csv(ds)
    i = int(raw.index[raw.consommation == 190][0])          # ligne mélangée, valeur 190
    assert refs["ref_naive_j1"][i] == 166 and refs["ref_naive_s1"][i] == 22
    j = int(raw.index[raw.consommation == 5][0])
    assert np.isnan(refs["ref_naive_j1"][j]) and np.isnan(refs["ref_naive_s1"][j])   # pas de passé
    assert refs["ref_rte_j1"][i] == 1.0 and refs["ref_rte_j"][i] == 2.0
