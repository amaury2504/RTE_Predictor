import { describe, expect, it } from "vitest"
import { gbCycleMs, gbStageState } from "./lightgbmTimeline"

const COUNT = 3
const visible = (t: number) => Array.from({ length: COUNT }, (_, i) => gbStageState(i, t, COUNT).stroke)

describe("chronologie LightGBM", () => {
    it("n'affiche jamais deux étapes en même temps de façon marquée, à aucun instant du cycle", () => {
        for (let t = 0; t <= gbCycleMs(COUNT); t += 10) {
            const strong = visible(t).filter(v => v > 0.6)
            expect(strong.length, `t=${t}`).toBeLessThanOrEqual(1)
        }
    })

    it("part de rien et finit sans rien d'affiché : le cycle suivant ne retrouve aucun tracé", () => {
        expect(visible(0)).toEqual([0, 0, 0])
        expect(visible(gbCycleMs(COUNT)).every(v => v === 0)).toBe(true)
    })

    it("donne le même état au même instant, quel que soit le chemin pour y arriver", () => {
        const direct = visible(2000)
        visible(4000); visible(100); visible(3300)          // allers-retours (pause hors écran, retour en arrière)
        expect(visible(2000)).toEqual(direct)
    })

    it("dessine progressivement l'étape qui commence", () => {
        expect(gbStageState(1, 1250 + 350, COUNT).draw).toBeGreaterThan(0.5)
        expect(gbStageState(1, 1250 + 700, COUNT).draw).toBe(1)
    })
})
