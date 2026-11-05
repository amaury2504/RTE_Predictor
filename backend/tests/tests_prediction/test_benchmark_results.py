import json

import pytest

from src.prediction.adapters.datasets.benchmark_results import load_benchmark_results


def test_load_benchmark_results_reads_file(tmp_path):
    payload = {"protocol": {}, "summary": [{"model": "a"}], "by_fold": []}
    f = tmp_path / "results.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    assert load_benchmark_results(str(f)) == payload


def test_load_benchmark_results_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_benchmark_results(str(tmp_path / "absent.json"))


def test_load_benchmark_results_rejects_unexpected_format(tmp_path):
    f = tmp_path / "results.json"
    f.write_text(json.dumps({"summary": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_benchmark_results(str(f))
