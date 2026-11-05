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
import time
from datetime import datetime, timezone

from src.prediction.adapters.datasets.csv_dataset import (
    load_foundation_forecasts, load_full_dataset, load_reference_forecasts, load_smoothing_candidates,
)
from src.prediction.adapters.ml.lightgbm_regressor import LightGBMRegressor
from src.prediction.adapters.ml.mlp_regressor import MLPRegressor
from src.prediction.adapters.ml.ridge_regressor import RidgeRegressor
from src.prediction.adapters.ml.timestral_loader import INSTALL_HINT, load_timestral, timestral_available
from src.prediction.application.baselines import run_baselines, run_tuned_reference
from src.prediction.application.benchmark import SUMMARY_KPIS, run_walk_forward, summarize, summarize_by_fold
from src.prediction.application.run_cache import RunCache, config_key, source_fingerprint

DEFAULT_TEST_YEARS = [2022, 2023, 2024]
# Modèles longs à entraîner : lancés en premier et avec --heavy-seeds graines
HEAVY_MODELS = ("mlp", "mlp_recent")
# Piste B : ces modèles reçoivent en plus des variables de niveau récent de la consommation (domain/level.py)
TRACK_B = ("ridge_niveau", "lightgbm_niveau")


def build_registry(max_epochs: int, patience: int, refit: bool, half_life: float) -> dict:
    """Modèles disponibles : nom -> fabrique(graine). C'est ici qu'on branche un nouveau modèle.

    Les variantes « _recent » pondèrent davantage les années récentes (demi-vie `half_life` années).
    """
    return {
        "mlp": lambda seed: MLPRegressor(seed=seed, max_epochs=max_epochs, patience=patience, refit_on_val=refit),
        "mlp_recent": lambda seed: MLPRegressor(
            seed=seed, max_epochs=max_epochs, patience=patience, refit_on_val=refit, recency_half_life_years=half_life),
        "ridge": lambda seed: RidgeRegressor(refit_on_val=refit),
        "ridge_recent": lambda seed: RidgeRegressor(refit_on_val=refit, recency_half_life_years=half_life),
        "ridge_niveau": lambda seed: RidgeRegressor(refit_on_val=refit, name="ridge_niveau"),
        "lightgbm_niveau": lambda seed: LightGBMRegressor(seed=seed, refit_on_val=refit, name="lightgbm_niveau"),
        "lightgbm": lambda seed: LightGBMRegressor(seed=seed, refit_on_val=refit),
        "lightgbm_recent": lambda seed: LightGBMRegressor(
            seed=seed, refit_on_val=refit, recency_half_life_years=half_life),
    }


def format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    return f"{minutes // 60} h {minutes % 60:02d}" if minutes >= 60 else f"{minutes} min"


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
        "| Rang | Modèle | Années | Exécutions | MAE (GW) | MAE centrée (GW) | RMSE (GW) | MAPE (%) | Biais (GW) | MASE | Entraînement (s) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rank, row in enumerate(summary, start=1):
        lines.append(
            f"| {rank} | {row['model']} | {row['folds']} | {row['runs']} | {pm(row, 'mae')} | {pm(row, 'mae_debiased')} | {pm(row, 'rmse')} "
            f"| {pm(row, 'mape')} | {pm(row, 'bias')} | {pm(row, 'mase')} | {fmt(row['fit_seconds'], 1)} |"
        )
    return "\n".join(lines)


def fold_table(by_fold: list[dict]) -> str:
    lines = [
        "| Année de test | Modèle | Exécutions | MAE (GW) | MAE centrée (GW) | RMSE (GW) | MAPE (%) | Biais (GW) | MASE | MAE validation (GW) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in by_fold:
        lines.append(
            f"| {row['test_year']} | {row['model']} | {row['runs']} | {pm(row, 'mae')} | {pm(row, 'mae_debiased')} | {pm(row, 'rmse')} "
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
    parser.add_argument("--bias-window", type=int, default=28,
                        help="fenêtre (jours) de la correction du biais récent ; 0 = pas de variante _corr")
    parser.add_argument("--no-baselines", action="store_true",
                        help="ne pas ajouter les références (prévisions naïves et prévisions RTE)")
    parser.add_argument("--heavy-seeds", type=int, default=None,
                        help="nombre de graines pour les modèles longs (MLP) ; défaut : même valeur que --seeds")
    parser.add_argument("--no-timestral", action="store_true", help="ne pas évaluer Timestral (modèle de fondation)")
    parser.add_argument("--timestral-model", default="mistralai/Timestral-209M",
                        help="identifiant Hugging Face du modèle Timestral")
    parser.add_argument("--no-cache", action="store_true",
                        help="ne pas sauvegarder ni relire les exécutions terminées")
    parser.add_argument("--cache-dir", default="benchmark_cache")
    parser.add_argument("--data", default="data/dataset_ml.csv")
    parser.add_argument("--out", default="benchmark")
    args = parser.parse_args()

    registry = build_registry(args.max_epochs, args.patience, not args.no_refit, args.half_life)
    names = args.models or list(registry)
    unknown = [n for n in names if n not in registry]
    if unknown:
        sys.exit(f"Modèle inconnu : {unknown}. Disponibles : {list(registry)}")

    print("Chargement des données...", flush=True)
    seeds = list(range(args.seeds))
    heavy_seeds = list(range(args.seeds if args.heavy_seeds is None else args.heavy_seeds))

    # Sauvegarde de chaque exécution terminée : relancer la même commande reprend là où elle s'est arrêtée.
    # La clé change dès que le code du dossier src/prediction, les données ou un réglage change.
    cache = None
    if not args.no_cache:
        data_file = os.stat(args.data)
        cache = RunCache(args.cache_dir, config_key(
            code=source_fingerprint("src/prediction"), data=f"{data_file.st_size}-{int(data_file.st_mtime)}",
            max_epochs=args.max_epochs, patience=args.patience, refit=not args.no_refit,
            half_life=args.half_life, bias_window=args.bias_window,
        ))
        print(f"Sauvegarde des exécutions : {cache.directory}", flush=True)

    results = []
    smoothing_choices: dict = {}
    timestral_model = None
    started = time.time()

    # 1. Références, lissage exponentiel et Timestral : rapides. Une erreur apparaît tout de suite,
    #    et non après des heures d'entraînement.
    full_a = load_full_dataset(args.data)
    if not args.no_baselines:
        results += run_baselines(full_a, load_reference_forecasts(args.data), args.test_years)
        # Série temporelle seule (lissage exponentiel) : paramètres choisis sur la validation de chaque année
        print("Lissage exponentiel (Holt-Winters)...", flush=True)
        smoothing, smoothing_choices = run_tuned_reference(
            full_a, load_smoothing_candidates(args.data), args.test_years, "ts_holt_winters")
        results += smoothing

        # Modèle de fondation : aucun entraînement, il lit l'historique et prévoit (téléchargement des poids au 1er appel)
        if not args.no_timestral:
            if timestral_available():
                print(f"Timestral ({args.timestral_model})...", flush=True)
                forecaster = load_timestral(args.timestral_model)
                years = sorted({y for t in args.test_years for y in (t - 1, t)})
                foundation = load_foundation_forecasts(forecaster, years, args.data)
                results += run_baselines(full_a, foundation, args.test_years)
                timestral_model = args.timestral_model
            else:
                print(f"Timestral n'est pas installé : ignoré ({INSTALL_HINT})", flush=True)

    # 2. Modèles entraînés. Le MLP (long) passe en premier, puis le reste. Piste A (météo + calendrier)
    #    et piste B (avec niveau récent) n'ont pas les mêmes variables d'entrée.
    groups = []
    for track in ("A", "B"):
        track_names = [n for n in names if (n in TRACK_B) == (track == "B")]
        heavy = [n for n in track_names if n in HEAVY_MODELS]
        light = [n for n in track_names if n not in HEAVY_MODELS]
        if heavy:
            groups.append((track, heavy, heavy_seeds))
        if light:
            groups.append((track, light, seeds))

    # Nombre total d'exécutions prévues, pour estimer le temps restant
    total = sum(
        len(args.test_years) * sum(len(group_seeds) if registry[n](0).stochastic else 1 for n in group_names)
        for _, group_names, group_seeds in groups
    )
    done = [0]

    def progress(track: str, message: str) -> None:
        done[0] += 1
        elapsed = time.time() - started
        remaining = elapsed / done[0] * (total - done[0])
        print(f"[run {track}] {done[0]}/{total} | écoulé {format_duration(elapsed)} | "
              f"reste ~{format_duration(remaining)} | {message}", flush=True)

    full_by_track = {"A": full_a}
    for track, group_names, group_seeds in groups:
        if track not in full_by_track:
            full_by_track[track] = load_full_dataset(args.data, level_features=(track == "B"))
        full = full_by_track[track]
        print(f"Piste {track} : {', '.join(group_names)} | {len(full.y)} lignes | {full.X.shape[1]} variables | "
              f"{len(group_seeds)} graine(s) | années de test : {args.test_years}", flush=True)
        results += run_walk_forward(
            {n: registry[n] for n in group_names}, full, args.test_years, group_seeds,
            on_progress=lambda message, track=track: progress(track, message),
            # La correction du biais n'a pas de sens pour la piste B, qui voit déjà le niveau récent
            bias_window_days=(args.bias_window or None) if track == "A" else None,
            cache=cache,
        )
    summary = summarize(results)
    by_fold = summarize_by_fold(results)

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": {
            "tracks": {"A": "météo et calendrier", "B": "météo, calendrier et niveau récent de la consommation"},
            "scheme": "glissant : test T, validation T-1, entraînement <= T-2",
            "test_years": args.test_years,
            "seeds": seeds,
            "seeds_heavy_models": heavy_seeds,
            "timestral_model": timestral_model,
            "max_epochs": args.max_epochs,
            "patience": args.patience,
            "refit_on_train_and_val": not args.no_refit,
            "holt_winters_choices": {str(y): c for y, c in smoothing_choices.items()},
            "bias_correction": {"window_days": args.bias_window, "delay_days": 2, "min_days": 7},
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
        f.write("Les lignes `ref_*` sont des références, pas des modèles de la piste A : elles utilisent la "
                "consommation passée (`ref_naive_j1` : même heure la veille ; `ref_naive_j2` : 48 h avant ; "
                "`ref_naive_s1` : la semaine précédente) ou les prévisions publiées par RTE (`ref_rte_j1`, "
                "`ref_rte_j`). `ts_holt_winters` est une série temporelle seule (lissage exponentiel saisonnier "
                "hebdomadaire, consommation connue jusqu'à 48 h avant, sans météo) ; ses paramètres sont choisis "
                "sur la validation de chaque année.\n\n")
        f.write("## Détail par année de test\n\n")
        f.write("Le biais par année montre la dérive du niveau de consommation. L'écart après ± est la variation "
                "entre graines (modèles à aléa).\n\n")
        f.write(fold_table(by_fold) + "\n")

    print("\n" + overall_table(summary))
    print("\n" + fold_table(by_fold))
    print(f"\nRésultats écrits dans {args.out}/")


if __name__ == "__main__":
    main()
