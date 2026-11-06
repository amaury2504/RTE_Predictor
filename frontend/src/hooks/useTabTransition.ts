import { useEffect, useRef, useState } from "react"
import type { RefObject } from "react"
import { animate, stagger } from "animejs"
import { duration, easeOut, STAGGER_MAX_ITEMS, STAGGER_MS } from "../design/motion"
import { useReducedMotion } from "./useReducedMotion"

const SHIFT = 10 // décalage horizontal (px) de la sortie et de l'entrée

/**
 * Transition directionnelle entre onglets : le contenu actuel sort (opacité 0, glissement de 10 px, ~140 ms),
 * PUIS React affiche le nouveau contenu, qui entre (~260 ms) avec ses enfants `[data-stagger]` en cascade
 * (40 ms d'écart, plafonnée à 8 éléments). Le sens dépend de l'ordre des onglets.
 * Retourne l'onglet réellement affiché (`shown`), qui suit `current` avec un léger retard.
 */
export function useTabTransition(current: string, order: string[], panel: RefObject<HTMLElement | null>) {
    const [shown, setShown] = useState(current)
    const direction = useRef(1)
    const reduce = useReducedMotion()

    // Sortie : se termine avant que le nouveau contenu soit monté
    useEffect(() => {
        if (shown === current) return
        direction.current = order.indexOf(current) >= order.indexOf(shown) ? 1 : -1
        const el = panel.current
        if (!el) { setShown(current); return }
        const exit = animate(el, {
            opacity: 0,
            translateX: reduce ? 0 : -direction.current * SHIFT,
            duration: reduce ? duration.fast : 140,
            ease: "inQuad",
            onComplete: () => setShown(current),
        })
        return () => { exit.pause() }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [current, shown, reduce])

    // Entrée : au montage et à chaque nouvel onglet affiché
    useEffect(() => {
        const el = panel.current
        if (!el) return
        const enter = animate(el, {
            opacity: [0, 1],
            translateX: [reduce ? 0 : direction.current * SHIFT, 0],
            duration: reduce ? duration.fast : duration.base + 10,
            ease: easeOut,
        })
        const items = Array.from(el.querySelectorAll<HTMLElement>("[data-stagger]")).slice(0, STAGGER_MAX_ITEMS)
        const cascade = reduce || items.length === 0 ? null : animate(items, {
            opacity: [0, 1],
            translateY: [12, 0],
            duration: duration.slow,
            ease: easeOut,
            delay: stagger(STAGGER_MS),
        })
        return () => { enter.revert(); cascade?.revert() }
    }, [shown, panel, reduce])

    return shown
}
