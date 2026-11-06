import { describeModel } from "./benchmarkModels"

/** Noms courts affichés dans les vues principales. Le détail (variantes, pistes) reste dans « Détails ». */
const SHORT: Record<string, string> = {
    lightgbm: "LightGBM",
    lightgbm_corr: "LightGBM",
    lightgbm_niveau_corr: "LightGBM",
    mlp: "MLP",
    mlp_corr: "MLP",
    mlp_niveau_corr: "MLP",
    ridge: "Ridge",
    ridge_corr: "Ridge",
    ridge_niveau_corr: "Ridge",
    ts_timestral_28m_meteo: "Timestral 28M",
    ts_holt_winters: "Holt-Winters",
    ref_rte_j1: "RTE (veille)",
    ref_rte_j: "RTE (jour)",
    ref_naive_j1: "Naïve (veille)",
}

export const shortName = (model: string): string => SHORT[model] ?? describeModel(model).label

/** Les cinq modèles comparés : tous avec leurs meilleures conditions (correction du biais, consommation récente). */
export const PRIMARY_MODELS = [
    "lightgbm_niveau_corr",
    "ts_timestral_28m_meteo",
    "mlp_niveau_corr",
    "ridge_niveau_corr",
    "ts_holt_winters",
]

/** Repères : la prévision RTE de la veille (plafond) et la naïve (plancher). */
export const REFERENCE_MODELS = ["ref_rte_j1", "ref_naive_j1"]

/** Les trois familles dont on montre l'effet des décisions (brut, correction, consommation récente). */
export const FAMILIES = [
    { id: "lightgbm", label: "LightGBM" },
    { id: "mlp", label: "MLP" },
    { id: "ridge", label: "Ridge" },
] as const
