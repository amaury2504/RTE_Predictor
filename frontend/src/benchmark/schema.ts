import { z } from "zod"
import type { BenchmarkResults } from "../types/api"

/**
 * Schéma de `results.json` tel que l'expose l'API (GET /prediction/benchmark).
 * Si le format du benchmark change, la validation échoue avec un message clair
 * plutôt que d'afficher des chiffres faux.
 */
const kpi = z.number().nullable()

const KPI_KEYS = ["mae", "mae_debiased", "rmse", "mape", "wape", "bias", "p95_ae", "r2", "mase"] as const

// Un indicateur `x` et son écart entre graines/années `x_std`
const kpiShape = Object.fromEntries(
    KPI_KEYS.flatMap(key => [[key, kpi], [`${key}_std`, kpi]]),
) as Record<(typeof KPI_KEYS)[number] | `${(typeof KPI_KEYS)[number]}_std`, typeof kpi>

const row = z.looseObject({
    model: z.string(),
    runs: z.number(),
    val_mae: z.number(),
    fit_seconds: z.number(),
    predict_seconds: z.number(),
    folds: z.number().optional(),
    test_year: z.number().optional(),
    ...kpiShape,
})

export const benchmarkSchema = z.looseObject({
    generated_at: z.string(),
    protocol: z.looseObject({
        scheme: z.string(),
        test_years: z.array(z.number()),
        seeds: z.array(z.number()),
        refit_on_train_and_val: z.boolean(),
        recency_half_life_years: z.number(),
        bias_correction: z.object({ window_days: z.number(), delay_days: z.number(), min_days: z.number() }).optional(),
    }),
    summary: z.array(row).min(1),
    by_fold: z.array(row),
})

/** Valide un contenu de `results.json` ; lève une erreur lisible si le format n'est pas celui attendu. */
export function parseBenchmark(data: unknown): BenchmarkResults {
    const parsed = benchmarkSchema.safeParse(data)
    if (!parsed.success) {
        const first = parsed.error.issues[0]
        throw new Error(`Format des résultats du benchmark inattendu (${first.path.join(".") || "racine"} : ${first.message})`)
    }
    return parsed.data as unknown as BenchmarkResults
}
