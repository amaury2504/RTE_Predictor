import pytest

from src.prediction.domain.kpi import compute_kpis
from src.prediction.application.use_cases_prediction import ComputeKpisUseCase


def hourly_timestamps(start_day: str, hours: int) -> list[str]:
    """Horodatages horaires consécutifs à partir de start_day (format YYYY-MM-DD)."""
    import pandas as pd
    return [t.strftime("%Y-%m-%dT%H:00") for t in pd.date_range(start_day, periods=hours, freq="h")]


# Cas de référence calculé à la main : 4 points
Y = [10.0, 20.0, 30.0, 40.0]
P = [13.0, 17.0, 31.0, 38.5]
TS = hourly_timestamps("2026-01-05", 4)  # un lundi


def test_kpis_de_precision_globale():
    k = compute_kpis(TS, P, Y)
    assert k.n == 4
    assert k.mean_actual == pytest.approx(25.0)
    assert k.mae == pytest.approx(2.125)
    assert k.rmse == pytest.approx(2.30489, abs=1e-4)
    assert k.mape == pytest.approx(13.0208, abs=1e-3)
    assert k.wape == pytest.approx(8.5)
    assert k.nrmse == pytest.approx(2.30489 / 25 * 100, abs=1e-3)


def test_kpis_de_biais_et_distribution():
    k = compute_kpis(TS, P, Y)
    assert k.bias == pytest.approx(-0.125)   # légère sous-estimation moyenne
    assert k.median_ae == pytest.approx(2.25)
    assert k.p95_ae == pytest.approx(3.0)
    assert k.max_ae == pytest.approx(3.0)


def test_kpis_de_qualite_relative():
    k = compute_kpis(TS, P, Y)
    assert k.r2 == pytest.approx(0.9575, abs=1e-4)
    assert k.within_5_pct == pytest.approx(50.0)
    assert k.within_10_pct == pytest.approx(50.0)


def test_modele_parfait():
    k = compute_kpis(TS, Y, Y)
    assert k.mae == 0
    assert k.rmse == 0
    assert k.bias == 0
    assert k.r2 == pytest.approx(1.0)
    assert k.within_5_pct == pytest.approx(100.0)


def test_signe_du_biais_surestimation():
    k = compute_kpis(TS, [y + 2 for y in Y], Y)
    assert k.bias == pytest.approx(2.0)


def test_mase_indisponible_sans_historique_de_24h():
    assert compute_kpis(TS, P, Y).mase is None


# Série de 48 h : le jour 2 vaut le jour 1 + 2 GW. La prévision naïve J-1 se trompe donc de 2 GW
# partout ; un modèle qui se trompe de 1 GW a une MASE de 0.5.
def two_days():
    ts = hourly_timestamps("2026-01-05", 48)
    y = [50.0 + (i % 24) + (2.0 if i >= 24 else 0.0) for i in range(48)]
    return ts, y


def test_mase_inferieure_a_1_quand_le_modele_bat_la_reference_naive():
    ts, y = two_days()
    k = compute_kpis(ts, [v + 1 for v in y], y)
    assert k.mae == pytest.approx(1.0)
    assert k.mase == pytest.approx(0.5)


def test_pointe_journaliere():
    ts, y = two_days()
    k = compute_kpis(ts, [v + 1 for v in y], y)
    assert k.peak_days == 2
    assert k.peak_mae == pytest.approx(1.0)
    assert k.peak_bias == pytest.approx(1.0)
    assert k.peak_hour_mae == pytest.approx(0.0)


def test_decalage_de_l_heure_de_pointe():
    ts, y = two_days()
    # Le modèle place le pic à 22h au lieu de 23h chaque jour
    p = list(y)
    for day in (0, 1):
        p[day * 24 + 22] = y[day * 24 + 23] + 5
    k = compute_kpis(ts, p, y)
    assert k.peak_hour_mae == pytest.approx(1.0)


def test_pointe_ignoree_si_journee_incomplete():
    k = compute_kpis(TS, P, Y)  # 4 heures seulement
    assert k.peak_days == 0
    assert k.peak_mae is None


def test_decoupages_par_heure_et_par_jour():
    ts, y = two_days()
    k = compute_kpis(ts, [v + 1 for v in y], y)
    assert len(k.by_hour) == 24
    assert all(s.n == 2 for s in k.by_hour)
    assert [s.key for s in k.by_day] == ["2026-01-05", "2026-01-06"]
    assert all(s.bias == pytest.approx(1.0) for s in k.by_day)


def test_semaine_et_weekend():
    ts, y = two_days()  # lundi et mardi
    k = compute_kpis(ts, y, y)
    assert k.weekday.n == 48
    assert k.weekend is None

    ts_we = hourly_timestamps("2026-01-10", 24)  # samedi
    k2 = compute_kpis(ts_we, [50.0] * 24, [50.0] * 24)
    assert k2.weekend.n == 24
    assert k2.weekday is None


def test_reel_nul_rend_les_pourcentages_indisponibles():
    k = compute_kpis(TS[:2], [1.0, 1.0], [0.0, 0.0])
    assert k.mape is None
    assert k.wape is None
    assert k.r2 is None
    assert k.mae == pytest.approx(1.0)


def test_longueurs_differentes():
    with pytest.raises(ValueError):
        compute_kpis(TS, P[:3], Y)


def test_serie_vide():
    with pytest.raises(ValueError):
        compute_kpis([], [], [])


def test_valeurs_non_finies():
    with pytest.raises(ValueError):
        compute_kpis(TS, [1.0, float("nan"), 3.0, 4.0], Y)


def test_use_case_delegue_au_domaine():
    report = ComputeKpisUseCase(TS, P, Y).execute()
    assert report.mae == pytest.approx(2.125)
