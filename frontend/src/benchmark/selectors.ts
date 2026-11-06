import type { BenchmarkResults, BenchmarkRow } from "../types/api"
import { describeModel } from "../lib/benchmarkModels"

/** Références toujours présentes dans les vues d'ensemble : le plancher (naïve) et le plafond (RTE). */
export const KEY_REFERENCES = ["ref_rte_j", "ref_rte_j1", "ref_naive_j1"]

const byMae = (a: BenchmarkRow, b: BenchmarkRow) => (a.mae ?? Infinity) - (b.mae ?? Infinity)

/** Modèles réellement candidats : tout sauf les références, classés par MAE croissante. */
export function candidates(results: BenchmarkResults): BenchmarkRow[] {
    return results.summary.filter(r => describeModel(r.model).kind !== "reference").sort(byMae)
}

/** Le meilleur modèle candidat selon la MAE moyenne (null si aucun résultat). */
export function bestModel(results: BenchmarkResults): BenchmarkRow | null {
    return candidates(results)[0] ?? null
}

export function rowOf(results: BenchmarkResults, model: string): BenchmarkRow | undefined {
    return results.summary.find(r => r.model === model)
}

/** Sélection par défaut des vues d'ensemble : les `top` meilleurs candidats + les références clés. */
export function overviewRows(results: BenchmarkResults, top = 8): BenchmarkRow[] {
    const picked = new Set([...candidates(results).slice(0, top).map(r => r.model), ...KEY_REFERENCES])
    return results.summary.filter(r => picked.has(r.model)).sort(byMae)
}

/** Les références (naïves, prévisions RTE) : toujours présentées à part des modèles. */
export function references(results: BenchmarkResults): BenchmarkRow[] {
    return results.summary.filter(r => describeModel(r.model).kind === "reference").sort(byMae)
}

/** La meilleure référence (en pratique, la prévision RTE du jour). */
export function bestReference(results: BenchmarkResults): BenchmarkRow | null {
    return references(results)[0] ?? null
}

/** Les modèles d'une famille donnée (piste A, piste B, série temporelle/fondation, référence), classés par MAE. */
export function byKind(results: BenchmarkResults, kind: ReturnType<typeof describeModel>["kind"]): BenchmarkRow[] {
    return results.summary.filter(r => describeModel(r.model).kind === kind).sort(byMae)
}

/** Les modèles comparés dans les vues principales, plus les deux repères, classés par MAE. Ignore ceux qui manquent. */
export function primaryRows(results: BenchmarkResults, primary: string[], references: string[]): BenchmarkRow[] {
    const wanted = new Set([...primary, ...references])
    return results.summary.filter(r => wanted.has(r.model)).sort(byMae)
}
