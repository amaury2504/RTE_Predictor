import json
from pathlib import Path

DEFAULT_RESULTS_PATH = "benchmark/results.json"


def load_benchmark_results(path: str = DEFAULT_RESULTS_PATH) -> dict:
    """Lit les résultats écrits par `scripts/run_benchmark.py`.

    Raises:
        FileNotFoundError: si le benchmark n'a pas encore été lancé.
        ValueError: si le fichier n'a pas le format attendu.
    """
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Résultats introuvables : {path}")
    data = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not {"protocol", "summary", "by_fold"} <= data.keys():
        raise ValueError("Format de résultats inattendu (protocol, summary et by_fold attendus)")
    return data
