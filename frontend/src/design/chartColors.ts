/** Palette des graphiques du benchmark : du bleu au gris, et l'orange réservé au meilleur modèle. */
export const CHART = {
    model: "#3987e5",
    reference: "#5b6c8a",
    best: "#ff9a3d",
    grid: "#172640",
    axis: "#8a9bb8",
    text: "#e8eef8",
} as const

export type BarKind = "best" | "model" | "reference"

export const KIND_FILL: Record<BarKind, string> = {
    best: CHART.best,
    model: CHART.model,
    reference: CHART.reference,
}
