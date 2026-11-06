import { useEffect } from "react"
import type { RefObject } from "react"
import { animate, createScope, utils } from "animejs"
import type { Timeline } from "animejs"
import { duration, easeOut } from "../design/motion"

/** Sélectionne des éléments SVG dans la racine du visuel (les animations ciblent des listes d'éléments). */
export type Query = (selector: string) => SVGElement[]

/**
 * Anime un visuel SVG en boucle, mais seulement tant qu'il est à l'écran (pause hors écran : aucun coût CPU
 * pour les visuels que l'on ne voit pas). En mouvement réduit, rien n'est animé : le SVG reste dans son état
 * final, qui est donc toujours complet et lisible.
 *
 * `build` crée la timeline (elle est mise en pause tout de suite, puis lancée à l'apparition).
 */
export function useInViewLoop(root: RefObject<SVGSVGElement | null>, build: (q: Query) => Timeline, reduce: boolean) {
    useEffect(() => {
        const el = root.current
        if (!el || reduce) return
        const q: Query = selector => Array.from(el.querySelectorAll<SVGElement>(selector))
        const scope = createScope({ root: el })
        let timeline: Timeline | undefined
        scope.add(() => {
            timeline = build(q)
            timeline.pause()
        })
        const observer = new IntersectionObserver(
            entries => {
                if (entries.some(e => e.isIntersecting)) timeline?.play()
                else timeline?.pause()
            },
            { threshold: 0.25 },
        )
        observer.observe(el)
        return () => {
            observer.disconnect()
            scope.revert()
        }
        // `build` est recréé à chaque rendu : seul le mouvement réduit doit relancer l'effet
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [reduce])
}

/**
 * Apparition d'un bloc quand il entre à l'écran (fondu et léger glissement), une seule fois.
 * Masqué avant son apparition ; en mouvement réduit, il reste visible tel quel.
 */
export function useReveal(root: RefObject<HTMLElement | null>, reduce: boolean) {
    useEffect(() => {
        const el = root.current
        if (!el || reduce) return
        utils.set(el, { opacity: 0 })
        let anim: ReturnType<typeof animate> | undefined
        const observer = new IntersectionObserver(
            entries => {
                if (!entries.some(e => e.isIntersecting)) return
                observer.disconnect()
                anim = animate(el, { opacity: [0, 1], translateY: [24, 0], duration: duration.slow, ease: easeOut })
            },
            { threshold: 0.12 },
        )
        observer.observe(el)
        return () => {
            observer.disconnect()
            anim?.revert()
            utils.set(el, { opacity: 1 })
        }
    }, [root, reduce])
}
