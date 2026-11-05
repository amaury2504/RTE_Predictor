"""Lance le benchmark de modèles de prévision (piste A : météo et calendrier).

Usage (depuis backend/, venv actif) :
    python scripts/run_benchmark.py                        # tous les modèles, 5 graines
    python scripts/run_benchmark.py --models mlp --seeds 3
    python scripts/run_benchmark.py --models mlp --seeds 1 --max-epochs 3 --out essai_benchmark

Écrit dans le dossier --out (par défaut benchmark/) :
    results.json : protocole, résultats par exécution et résumé par modèle
    RESULTS.md   : tableau de classement
"""
import sys
sys.path.insert(0, ".")

import argparse
import json
import os
from datetime import datetime, timezone

from src.prediction.adapters.data.csv_dataset import load_benchmark_dataset
from src.prediction.adapters.ml.mlp_regressor import MLPRegressor
from src.prediction.application.benchmark import SUMMARY_KPIS, run_benchmark, summarize
from src.prediction.domain.dataset import TEST_FIRST_YEAR, TRAIN_LAST_YEAR, VAL_YEAR


def build_registry(max_epochs: int, patience: int) -> dict:
    """Modèles disponibles : nom -> fabrique(graine). C'est ici qu'on branche un nouveau modèle."""
    return {
        "mlp": lambda seed: MLPRegressor(seed=seed, max_epochs=max_epochs, patience=patience),
    }


def fmt(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}"


def pm(row, kpi, digits=2):
    """'moyenne ± écart-type' (l'écart-type n'est affiché que s'il y a plusieurs exécutions)."""
    if row[kpi] is None:
        return "—"
    text = fmt(row[kpi], digits)
    if row["runs"] > 1:
        text += f" ± {fmt(row[f'{kpi}_std'], digits)}"
    return text


def markdown_table(summary: list[dict]) -> str:
    lines = [
        "| Rang | Modèle | Exécutions | MAE (GW) | RMSE (GW) | MAPE (%) | WAPE (%) | Biais (GW) | MASE | Entraînement (s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rank, row in enumerate(summary, start=1):
        lines.append(
            f"| {rank} | {row['model']} | {row['runs']} | {pm(row, 'mae')} | {pm(row, 'rmse')} | {pm(row, 'mape')} "
            f"| {pm(row, 'wape')} | {pm(row, 'bias')} | {pm(row, 'mase')} | {fmt(row['fit_seconds'], 1)} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=None, help="modèles à lancer (défaut : tous)")
    parser.add_argument("--seeds", type=int, default=5, help="nombre de graines pour les modèles à aléa")
    parser.add_argument("--max-epochs", type=int, default=1000)
    parser.add_argument("--patience", type=int, default=50)
    parser.add_argument("--data", default="data/dataset_ml.csv")
    parser.add_argument("--out", default="benchmark")
    args = parser.parse_args()

    registry = build_registry(args.max_epochs, args.patience)
    names = args.models or list(registry)
    unknown = [n for n in names if n not in registry]
    if unknown:
        sys.exit(f"Modèle inconnu : {unknown}. Disponibles : {list(registry)}")

    print("Chargement des données...", flush=True)
    data = load_benchmark_dataset(args.data)
    print(f"Entraînement : {len(data.train.y)} | Validation : {len(data.val.y)} | Test : {len(data.test.y)} "
          f"| Variables : {data.train.X.shape[1]}", flush=True)

    seeds = list(range(args.seeds))
    results = run_benchmark(
        {n: registry[n] for n in names}, data, seeds,
        on_progress=lambda message: print(f"[run ] {message}", flush=True),
    )
    summary = summarize(results)

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": {
            "track": "A (météo et calendrier)",
            "train_last_year": TRAIN_LAST_YEAR,
            "val_year": VAL_YEAR,
            "test_first_year": TEST_FIRST_YEAR,
            "rows": {"train": len(data.train.y), "val": len(data.val.y), "test": len(data.test.y)},
            "seeds": seeds,
            "max_epochs": args.max_epochs,
            "patience": args.patience,
        },
        "summary": summary,
        "runs": [
            {
                "model": r.model, "seed": r.seed,
                "fit_seconds": round(r.fit_seconds, 2), "predict_seconds": round(r.predict_seconds, 3),
                "val_mae": r.val.mae,
                "test": {k: getattr(r.test, k) for k in SUMMARY_KPIS},
            }
            for r in results
        ],
    }
    with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("# Résultats du benchmark (piste A)\n\n")
        f.write(f"Test : années ≥ {TEST_FIRST_YEAR}. Valeurs : moyenne ± écart-type sur les graines.\n\n")
        f.write(markdown_table(summary) + "\n")

    print("\n" + markdown_table(summary))
    print(f"\nRésultats écrits dans {args.out}/")


if __name__ == "__main__":
    main()
