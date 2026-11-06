import { createSpring, cubicBezier } from "animejs"

/** Toutes les valeurs d'animation passent par ici : aucune durée ni courbe en dur dans les composants. */

/** Durées en millisecondes (l'unité d'anime.js). */
export const duration = {
    fast: 150,
    base: 250,
    slow: 450,
    hero: 800,
} as const

/** Courbe par défaut en sortie de mouvement : cubic-bezier(0.22, 1, 0.36, 1). */
export const easeOut = cubicBezier(0.22, 1, 0.36, 1)

/** Ressorts nommés (fabriques : un ressort neuf par animation). */
export const springs = {
    /** Indicateur qui glisse (onglets, élément actif de la sidebar) : rigide, peu de rebond */
    glide: () => createSpring({ stiffness: 380, damping: 32 }),
    /** Apparition « pop » (icône, coche) */
    pop: () => createSpring({ stiffness: 420, damping: 22 }),
    /** Largeur de la sidebar */
    panel: () => createSpring({ stiffness: 300, damping: 30 }),
} as const

/** Écart entre éléments qui apparaissent en cascade, plafonné pour ne pas traîner. */
export const STAGGER_MS = 40
export const STAGGER_MAX_ITEMS = 8
export const staggerDelay = (index: number) => Math.min(index, STAGGER_MAX_ITEMS) * STAGGER_MS

/** Durée d'un balayage complet du scanner de la carte (ms). Le résultat attend la fin d'un balayage. */
export const SCAN_SWEEP_MS = 2400
