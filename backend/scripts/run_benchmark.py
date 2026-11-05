"""Lance le benchmark de modèles de prévision (piste A : météo et calendrier).

Évaluation glissante : pour chaque année de test T, entraînement jusqu'à T-2, validation T-1, test T.

Usage (depuis backend/, venv actif) :
    python scripts/run_benchmark.py                                  # tous les modèles, 3 années, 5 graines
    python scripts/run_benchmark.py --models lightgbm                # un seul modèle
    python scripts/run_benchmark.py --models mlp --seeds 1 --test-years 2024 --max-epochs 3 --out essai

Durée : modèles x années x graines entraînements. Le MLP est de loin le plus long.

Écrit dans le dossier --out (par défaut benchmark/) :
    results.json : protocole, résumé par modèle, détail par année, exécutions
    RESULTS.md   : classement global et détail par année de test
"""
import sys
sys.path.insert(0, ".")

import argparse
import json
import os
from datetime import datetime, timezone

from src.prediction.adapters.datasets.csv_dataset import load_full_dataset, load_reference_forecasts
from src.prediction.adapters.ml.lightgbm_regressor import LightGBMRegressor
from src.prediction.adapters.ml.mlp_regressor import MLPRegressor
from src.prediction.application.baselines import run_baselines
from src.prediction.application.benchmark import SUMMARY_KPIS, run_walk_forward, summarize, summarize_by_fold

DEFAULT_TEST_YEARS = [2022, 2023, 2024]


def build_registry(max_epochs: int, patience: int, refit: bool, half_life: float) -> dict:
    """Modèles disponibles : nom -> fabrique(graine). C'est ici qu'on branche un nouveau modèle.

    Les variantes « _recent » pondèrent davantage les années récentes (demi-vie `half_life` années).
    """
    return {
        "mlp": lambda seed: MLPRegressor(seed=seed, max_epochs=max_epochs, patience=patience, refit_on_val=refit),
        "mlp_recent": lambda seed: MLPRegressor(
            seed=seed, max_epochs=max_epochs, patience=patience, refit_on_val=refit, recency_half_life_years=half_life),
        "lightgbm": lambda seed: LightGBMRegressor(seed=seed, refit_on_val=refit),
        "lightgbm_recent": lambda seed: LightGBMRegressor(
            seed=seed, refit_on_val=refit, recency_half_life_years=half_life),
    }


def fmt(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}"


def pm(row, kpi, digits=2, show_std=True):
    """'moyenne ± écart-type' (l'écart-type n'est affiché que s'il est non nul)."""
    if row[kpi] is None:
        return "—"
    text = fmt(row[kpi], digits)
    std = row.get(f"{kpi}_std")
    if show_std and std:
        text += f" ± {fmt(std, digits)}"
    return text


def overall_table(summary: list[dict]) -> str:
    lines = [
        "| Rang | Modèle | Années | Exécutions | MAE (GW) | RMSE (GW) | MAPE (%) | Biais (GW) | MASE | Entraînement (s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rank, row in enumerate(summary, start=1):
        lines.append(
            f"| {rank} | {row['model']} | {row['folds']} | {row['runs']} | {pm(row, 'mae')} | {pm(row, 'rmse')} "
            f"| {pm(row, 'mape')} | {pm(row, 'bias')} | {pm(row, 'mase')} | {fmt(row['fit_seconds'], 1)} |"
        )
    return "\n".join(lines)


def fold_table(by_fold: list[dict]) -> str:
    lines = [
        "| Année de test | Modèle | Exécutions | MAE (GW) | RMSE (GW) | MAPE (%) | Biais (GW) | MASE | MAE validation (GW) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in by_fold:
        lines.append(
            f"| {row['test_year']} | {row['model']} | {row['runs']} | {pm(row, 'mae')} | {pm(row, 'rmse')} "
            f"| {pm(row, 'mape')} | {pm(row, 'bias')} | {pm(row, 'mase')} | {fmt(row['val_mae'])} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=None, help="modèles à lancer (défaut : tous)")
    parser.add_argument("--test-years", nargs="+", type=int, default=DEFAULT_TEST_YEARS, help="années de test")
    parser.add_argument("--seeds", type=int, default=5, help="nombre de graines pour les modèles à aléa")
    parser.add_argument("--max-epochs", type=int, default=1000)
    parser.add_argument("--patience", type=int, default=50)
    parser.add_argument("--no-refit", action="store_true",
                        help="ne pas réentraîner sur entraînement + validation après le réglage")
    parser.add_argument("--half-life", type=float, default=3.0,
                        help="demi-vie (années) de la pondération des variantes _recent")
    parser.add_argument("--no-baselines", action="store_true",
                        help="ne pas ajouter les références (prévisions naïves et prévisions RTE)")
    parser.add_argument("--data", default="data/dataset_ml.csv")
    parser.add_argument("--out", default="benchmark")
    args = parser.parse_args()

    registry = build_registry(args.max_epochs, args.patience, not args.no_refit, args.half_life)
    names = args.models or list(registry)
    unknown = [n for n in names if n not in registry]
    if unknown:
        sys.exit(f"Modèle inconnu : {unknown}. Disponibles : {list(registry)}")

    print("Chargement des données...", flush=True)
    full = load_full_dataset(args.data)
    print(f"{len(full.y)} lignes | {full.X.shape[1]} variables | années de test : {args.test_years}", flush=True)

    seeds = list(range(args.seeds))
    results = run_walk_forward(
        {n: registry[n] for n in names}, full, args.test_years, seeds,
        on_progress=lambda message: print(f"[run ] {message}", flush=True),
    )
    if not args.no_baselines:
        results += run_baselines(full, load_reference_forecasts(args.data), args.test_years)
    summary = summarize(results)
    by_fold = summarize_by_fold(results)

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": {
            "track": "A (météo et calendrier)",
            "scheme": "glissant : test T, validation T-1, entraînement <= T-2",
            "test_years": args.test_years,
            "seeds": seeds,
            "max_epochs": args.max_epochs,
            "patience": args.patience,
            "refit_on_train_and_val": not args.no_refit,
            "recency_half_life_years": args.half_life,
        },
        "summary": summary,
        "by_fold": by_fold,
        "runs": [
            {
                "model": r.model, "seed": r.seed, "test_year": r.test_year,
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
        f.write("Évaluation glissante : pour chaque année de test T, entraînement jusqu'à T-2, validation T-1, test T.\n\n")
        f.write("## Classement global\n\n")
        f.write("Moyenne des années de test (chaque année pèse autant). L'écart indiqué après ± est la variation "
                "entre années.\n\n")
        f.write(overall_table(summary) + "\n\n")
        f.write("## Détail par année de test\n\n")
        f.write("Le biais par année montre la dérive du niveau de consommation. L'écart après ± est la variation "
                "entre graines (modèles à aléa).\n\n")
        f.write(fold_table(by_fold) + "\n")

    print("\n" + overall_table(summary))
    print("\n" + fold_table(by_fold))
    print(f"\nRésultats écrits dans {args.out}/")


if __name__ == "__main__":
    main()
