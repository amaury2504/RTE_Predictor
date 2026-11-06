import { describe, expect, it } from "vitest"
import type { BenchmarkResults, BenchmarkRow } from "../types/api"
import { bestModel, bestReference, byKind, candidates, overviewRows, primaryRows, references } from "./selectors"
import { parseBenchmark } from "./schema"

// Jeu de résultats minimal : seules les clés utilisées par les sélecteurs comptent
const row = (model: string, mae: number): BenchmarkRow => ({
    model, runs: 1, val_mae: mae, fit_seconds: 0, predict_seconds: 0,
    mae, mae_std: 0, mae_debiased: mae, mae_debiased_std: 0, rmse: mae, rmse_std: 0, mape: mae, mape_std: 0,
    wape: mae, wape_std: 0, bias: 0, bias_std: 0, p95_ae: mae, p95_ae_std: 0, r2: 0.9, r2_std: 0, mase: mae, mase_std: 0,
})

const results: BenchmarkResults = {
    generated_at: "2026-01-01",
    protocol: { scheme: "glissant", test_years: [2022, 2023, 2024], seeds: [0], refit_on_train_and_val: true, recency_half_life_years: 3 },
    summary: [
        row("ref_rte_j", 1.05), row("ref_rte_j1", 1.21), row("ref_naive_j1", 2.57),
        row("lightgbm_niveau_corr", 1.21), row("lightgbm", 2.91), row("ts_timestral_28m_meteo", 1.3),
        row("ridge", 3.78), row("mlp", 3.11),
    ],
    by_fold: [],
}

describe("sélecteurs du benchmark", () => {
    it("le meilleur modèle n'est jamais une référence, même si une référence fait mieux", () => {
        expect(bestModel(results)?.model).toBe("lightgbm_niveau_corr")
        expect(bestReference(results)?.model).toBe("ref_rte_j")
    })

    it("les candidats excluent les références et sont triés par MAE croissante", () => {
        const c = candidates(results)
        expect(c.some(r => r.model.startsWith("ref_"))).toBe(false)
        expect(c.map(r => r.mae)).toEqual([...c.map(r => r.mae)].sort((a, b) => (a ?? 0) - (b ?? 0)))
    })

    it("les références sont isolées des modèles", () => {
        expect(references(results).map(r => r.model)).toEqual(["ref_rte_j", "ref_rte_j1", "ref_naive_j1"])
    })

    it("les vues d'ensemble gardent toujours les références clés comme repères", () => {
        const models = overviewRows(results, 1).map(r => r.model)
        expect(models).toEqual(expect.arrayContaining(["ref_rte_j", "ref_rte_j1", "ref_naive_j1", "lightgbm_niveau_corr"]))
        expect(models).not.toContain("ridge")
    })

    it("sépare les pistes : la piste B (niveau récent) n'apparaît pas dans la piste A", () => {
        expect(byKind(results, "trackB").map(r => r.model)).toEqual(["lightgbm_niveau_corr"])
        expect(byKind(results, "trackA").map(r => r.model)).not.toContain("lightgbm_niveau_corr")
    })
})

describe("sélection des modèles comparés", () => {
    it("ne garde que les modèles demandés et les repères, classés par erreur, en ignorant les absents", () => {
        const rows = primaryRows(results, ["lightgbm_niveau_corr", "ts_timestral_28m_meteo", "modele_absent"], ["ref_naive_j1"])
        expect(rows.map(r => r.model)).toEqual(["lightgbm_niveau_corr", "ts_timestral_28m_meteo", "ref_naive_j1"])
    })
})

describe("validation du format", () => {
    it("accepte un résultat bien formé", () => {
        expect(parseBenchmark(results).summary).toHaveLength(8)
    })

    it("refuse un format inattendu avec un message clair", () => {
        expect(() => parseBenchmark({ ...results, summary: "x" })).toThrow(/Format des résultats/)
        expect(() => parseBenchmark({})).toThrow(/generated_at/)
    })
})
