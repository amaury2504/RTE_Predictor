import { useEffect, useRef } from "react"
import { animate } from "animejs"
import { duration, easeOut } from "../../design/motion"
import { useReducedMotion } from "../../hooks/useReducedMotion"

interface AnimatedNumberProps {
    value: number
    digits?: number
    unit?: string
}

const format = (v: number, digits: number) =>
    new Intl.NumberFormat("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v)

/**
 * Compteur animé à l'apparition et à chaque changement de valeur (~700 ms).
 * Chiffres tabulaires : le texte ne « saute » pas. Mouvement réduit : la valeur s'affiche directement.
 * Le texte est écrit directement dans le nœud (pas de rendu React à chaque image).
 */
export default function AnimatedNumber({ value, digits = 2, unit = "" }: AnimatedNumberProps) {
    const ref = useRef<HTMLSpanElement>(null)
    const shown = useRef(0)
    const reduce = useReducedMotion()

    useEffect(() => {
        const node = ref.current
        if (!node) return
        if (reduce) {
            node.textContent = `${format(value, digits)}${unit}`
            shown.current = value
            return
        }
        const state = { v: shown.current }
        const animation = animate(state, {
            v: value,
            duration: duration.hero - 100,
            ease: easeOut,
            onUpdate: () => {
                shown.current = state.v
                node.textContent = `${format(state.v, digits)}${unit}`
            },
        })
        return () => { animation.revert() }
    }, [value, digits, unit, reduce])

    // Texte initial : la valeur finale (lecteurs d'écran, avant le premier rendu animé)
    return <span ref={ref} className="tabular">{format(value, digits)}{unit}</span>
}
