import type { BenchmarkKpiKey, BenchmarkRow } from "../types/api"

export type ModelKind = "reference" | "trackA" | "trackB" | "series"

export interface ModelInfo {
    kind: ModelKind
    label: string
    description: string
}

/** Couleur par type de modèle (trois premières teintes de la palette catégorielle, validées sur fond sombre). */
export const KIND_COLOR: Record<ModelKind, string> = {
    trackA: "#3987e5",
    reference: "#d95926",
    trackB: "#199e70",
    series: "#c98500",
}

export const KIND_LABEL: Record<ModelKind, string> = {
    trackA: "Piste A : météo et calendrier",
    trackB: "Piste B : avec la consommation récente",
    series: "Séries temporelles et modèles de fondation",
    reference: "Référence",
}

export const KIND_ORDER: ModelKind[] = ["trackA", "trackB", "series", "reference"]

const REFERENCES: Record<string, { label: string; description: string }> = {
    ref_rte_j: { label: "Prévision RTE du jour", description: "Prévision publiée par RTE le jour même. Elle dispose d'informations que ce projet n'a pas : c'est un plafond de comparaison." },
    ref_rte_j1: { label: "Prévision RTE de la veille", description: "Prévision publiée par RTE la veille. Plafond de comparaison." },
    ref_naive_j1: { label: "Naïve J-1", description: "Même heure que la veille. Utilise la consommation passée, aucun apprentissage." },
    ref_naive_j2: { label: "Naïve J-2", description: "Même heure deux jours avant : même information que la piste B." },
    ref_naive_s1: { label: "Naïve semaine", description: "Même heure la semaine précédente." },
}

const BASES: Record<string, { label: string; description: string }> = {
    ridge: { label: "Ridge", description: "Régression linéaire régularisée." },
    lightgbm: { label: "LightGBM", description: "Arbres de décision boostés." },
    mlp: { label: "MLP PyTorch", description: "Réseau de neurones dense." },
}

const SERIES: Record<string, { label: string; description: string }> = {
    ts_timestral: {
        label: "Timestral (consommation seule)",
        description: "Modèle de fondation de Mistral, sans aucun entraînement sur nos données : il lit les 8 dernières semaines de consommation (connues jusqu'à 48 h avant) et prévoit la suite.",
    },
    ts_timestral_meteo: {
        label: "Timestral + météo",
        description: "Le même modèle de fondation, avec en plus la température moyenne et les jours fériés connus à l'avance. La météo observée sert de prévision parfaite, comme pour les autres modèles.",
    },
    ts_holt_winters: {
        label: "Holt-Winters (lissage exponentiel)",
        description: "Niveau et profil hebdomadaire lissés exponentiellement, sans météo ni calendrier. Utilise la consommation connue jusqu'à 48 h avant ; ses deux paramètres sont choisis sur la validation de chaque année.",
    },
}

export function describeModel(name: string): ModelInfo {
    const series = SERIES[name]
    if (series) return { kind: "series", ...series }
    const reference = REFERENCES[name]
    if (reference) return { kind: "reference", ...reference }

    const parts = name.split("_")
    const base = BASES[parts[0]] ?? { label: parts[0], description: "" }
    const suffixes = parts.slice(1)
    const labelParts = [base.label]
    const notes = [base.description]
    if (suffixes.includes("recent")) {
        labelParts.push("années récentes")
        notes.push("Les années récentes pèsent davantage à l'entraînement.")
    }
    if (suffixes.includes("niveau")) {
        labelParts.push("niveau récent")
        notes.push("Reçoit aussi la consommation connue jusqu'à 48 h avant (même heure, moyennes sur 7 et 28 jours).")
    }
    if (suffixes.includes("corr")) {
        labelParts.push("biais corrigé")
        notes.push("Les prédictions sont corrigées par la moyenne des erreurs des 28 derniers jours.")
    }
    return {
        kind: suffixes.includes("niveau") ? "trackB" : "trackA",
        label: labelParts.join(" + "),
        description: notes.filter(Boolean).join(" "),
    }
}

export interface KpiDef {
    key: BenchmarkKpiKey
    label: string
    unit: string
    digits: number
    signed?: boolean
    hint: string
    /** Sens d'amélioration : plus petit, plus grand, ou plus proche de zéro */
    better: "lower" | "higher" | "zero"
}

export const KPI_DEFS: KpiDef[] = [
    { key: "mae", label: "MAE", unit: " GW", digits: 2, better: "lower", hint: "Erreur absolue moyenne" },
    { key: "mae_debiased", label: "MAE centrée", unit: " GW", digits: 2, better: "lower", hint: "MAE une fois le biais moyen retiré : qualité de la forme de la courbe" },
    { key: "rmse", label: "RMSE", unit: " GW", digits: 2, better: "lower", hint: "Pénalise davantage les gros écarts" },
    { key: "mape", label: "MAPE", unit: " %", digits: 2, better: "lower", hint: "Erreur relative moyenne" },
    { key: "wape", label: "WAPE", unit: " %", digits: 2, better: "lower", hint: "Erreurs cumulées rapportées à la consommation cumulée" },
    { key: "bias", label: "Biais", unit: " GW", digits: 2, signed: true, better: "zero", hint: "Positif : le modèle surestime. Négatif : il sous-estime." },
    { key: "p95_ae", label: "Erreur P95", unit: " GW", digits: 2, better: "lower", hint: "95 % des heures ont une erreur inférieure" },
    { key: "r2", label: "R²", unit: "", digits: 3, better: "higher", hint: "Part de la variance expliquée (1 = parfait)" },
    { key: "mase", label: "MASE", unit: "", digits: 2, better: "lower", hint: "Rapportée à la naïve J-1 : sous 1, bat la naïve" },
]

/** Valeur à minimiser pour classer (le biais se juge en valeur absolue). */
export function score(def: KpiDef, value: number | null): number {
    if (value == null) return Number.POSITIVE_INFINITY
    if (def.better === "higher") return -value
    if (def.better === "zero") return Math.abs(value)
    return value
}

export function formatKpi(def: KpiDef, value: number | null): string {
    if (value == null) return "—"
    const text = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: def.digits, maximumFractionDigits: def.digits }).format(value)
    return `${def.signed && value > 0 ? "+" : ""}${text}${def.unit}`
}

export function rankModels(rows: BenchmarkRow[]): string[] {
    return [...rows].sort((a, b) => (a.mae ?? Infinity) - (b.mae ?? Infinity)).map(r => r.model)
}

/** Sélection de départ de la comparaison : un exemple de chaque famille. */
export const ESSENTIAL_MODELS = ["ref_rte_j", "ref_naive_j1", "ts_holt_winters", "ridge", "lightgbm", "lightgbm_corr", "lightgbm_niveau"]
