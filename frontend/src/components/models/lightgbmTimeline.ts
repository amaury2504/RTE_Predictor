/*
 * Chronologie de l'illustration LightGBM (ms). Chaque étape (« Arbre 1 », « Arbres 1 à 3 »...) se dessine en 700 ms,
 * reste affichée, puis s'efface quand la suivante arrive ; la dernière s'efface à la fin du cycle.
 */
const STEP = 1250
const DRAW = 700
const HOLD_UNTIL = 1050     // l'étape commence à s'effacer 1050 ms après son début
const FADE = 300
const LABEL_FADE = 250
const LAST_HOLD = 1500
const LAST_FADE = 450

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const easeOutCubic = (x: number) => 1 - (1 - x) ** 3

/** Durée d'un cycle complet, pour `count` étapes. */
export const gbCycleMs = (count: number) => (count - 1) * STEP + LAST_HOLD + LAST_FADE

/**
 * État de l'étape `i` (sur `count`) à l'instant `t` du cycle : tracé dessiné (0 à 1), opacité du tracé et du libellé.
 * Fonction pure du temps : une seule étape est visible à la fois, quel que soit l'historique (pause hors écran,
 * retour en arrière). Une timeline d'animations par étape gardait l'état laissé par les passages précédents,
 * et les tracés orange s'accumulaient.
 */
export function gbStageState(i: number, t: number, count: number) {
    const at = i * STEP
    const last = i === count - 1
    const draw = easeOutCubic(clamp01((t - at) / DRAW))
    const out = last ? clamp01((t - ((count - 1) * STEP + LAST_HOLD)) / LAST_FADE) : clamp01((t - (at + HOLD_UNTIL)) / FADE)
    const labelOut = last ? out : clamp01((t - (at + HOLD_UNTIL)) / LABEL_FADE)
    return {
        draw,
        stroke: draw * (1 - out),
        label: easeOutCubic(clamp01((t - at) / LABEL_FADE)) * (1 - labelOut),
    }
}
