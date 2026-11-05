import numpy as np
import pytest

from src.prediction.domain.recency import recency_weights


def test_poids_de_un_a_la_date_de_reference():
    assert recency_weights(["2024-01-01T00:00"], "2024-01-01T00:00", 3.0)[0] == pytest.approx(1.0)


def test_poids_divise_par_deux_a_chaque_demi_vie():
    w = recency_weights(["2023-01-01T00:00", "2022-01-01T00:00"], "2024-01-01T00:00", 1.0)
    assert w == pytest.approx([0.5, 0.25], rel=1e-2)


def test_poids_croissants_avec_la_recence():
    ts = ["2015-06-01T12:00", "2019-06-01T12:00", "2023-06-01T12:00"]
    w = recency_weights(ts, "2024-01-01T00:00", 3.0)
    assert w[0] < w[1] < w[2] <= 1.0


def test_une_date_posterieure_a_la_reference_pese_un():
    assert recency_weights(["2025-01-01T00:00"], "2024-01-01T00:00", 3.0)[0] == pytest.approx(1.0)


def test_demi_vie_invalide():
    for bad in (0, -1):
        with pytest.raises(ValueError):
            recency_weights(["2024-01-01T00:00"], "2024-01-01T00:00", bad)
