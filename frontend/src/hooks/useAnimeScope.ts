import { useEffect } from "react"
import type { RefObject } from "react"
import { createScope } from "animejs"
import type { Scope } from "animejs"

/**
 * Exécute des animations anime.js dans un `createScope` lié à un élément racine, et les annule au démontage.
 * Indispensable avec le StrictMode de React 19 (double montage en développement) : `scope.revert()` retire
 * les animations et les styles posés, donc rien n'est doublé ni orphelin.
 *
 * `build` est relancé quand `deps` change. Il ne doit animer que des éléments stables (propriétés de style),
 * pas ceux que React monte ou démonte en même temps.
 */
export function useAnimeScope(root: RefObject<HTMLElement | SVGElement | null>, build: (scope: Scope) => void, deps: unknown[] = []) {
    useEffect(() => {
        if (!root.current) return
        const scope: Scope = createScope({ root: root.current })
        scope.add(() => build(scope))
        return () => scope.revert()
        // `build` est volontairement exclu : il est recréé à chaque rendu, seules les `deps` relancent l'animation
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps)
}
