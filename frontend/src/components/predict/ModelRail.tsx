import { useRef } from "react"
import type { KeyboardEvent } from "react"
import { animate } from "animejs"
import { duration, springs } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import type { PredictModel } from "../../lib/predictModels"

const ITEM = 52 // hauteur d'un élément (px) : hauteur de la surbrillance

interface ModelRailProps {
    models: PredictModel[]
    value: string
    onChange: (id: string) => void
    /** Préfixe des identifiants pour relier chaque onglet à sa feuille (aria-controls). */
    idPrefix: string
}

/**
 * Rangée horizontale de modèles (liste d'onglets) : un onglet par modèle, une feuille par onglet.
 * Une seule surbrillance glisse vers l'onglet choisi. Elle défile horizontalement si elle est trop large.
 * Clavier : flèches gauche/droite (ou haut/bas), Début et Fin ; seul l'onglet actif est dans l'ordre de tabulation.
 */
export default function ModelRail({ models, value, onChange, idPrefix }: ModelRailProps) {
    const root = useRef<HTMLDivElement>(null)
    const indicator = useRef<HTMLSpanElement>(null)
    const tabs = useRef<(HTMLButtonElement | null)[]>([])
    const reduce = useReducedMotion()
    const index = Math.max(0, models.findIndex(m => m.id === value))

    // Surbrillance unique qui glisse (transform uniquement)
    useAnimeScope(root, () => {
        const el = indicator.current
        const tab = tabs.current[index]
        if (!el || !tab) return
        // Les onglets n'ont pas tous la même largeur : la surbrillance prend la position et la largeur de l'onglet actif
        animate(el, {
            translateX: tab.offsetLeft - 8,
            width: tab.offsetWidth,
            opacity: 1,
            ...(reduce ? { duration: duration.fast } : { ease: springs.glide() }),
        })
    }, [index, reduce])

    const select = (i: number) => {
        const next = (i + models.length) % models.length
        onChange(models[next].id)
        tabs.current[next]?.focus()
    }

    const onKeyDown = (e: KeyboardEvent) => {
        switch (e.key) {
            case "ArrowDown": case "ArrowRight": e.preventDefault(); select(index + 1); break
            case "ArrowUp": case "ArrowLeft": e.preventDefault(); select(index - 1); break
            case "Home": e.preventDefault(); select(0); break
            case "End": e.preventDefault(); select(models.length - 1); break
        }
    }

    return (
        <div
            ref={root}
            role="tablist"
            aria-orientation="horizontal"
            aria-label="Modèles à essayer"
            onKeyDown={onKeyDown}
            className="glass-card relative flex w-fit max-w-full gap-1 overflow-x-auto !rounded-full p-2"
        >
            <span
                ref={indicator}
                aria-hidden="true"
                className="absolute left-2 top-2 rounded-full bg-white/15 shadow-[inset_0_1px_0_var(--glass-highlight)]"
                style={{ height: ITEM, opacity: 0 }}
            />
            {models.map((m, i) => {
                const selected = m.id === value
                return (
                    <button
                        key={m.id}
                        ref={el => { tabs.current[i] = el }}
                        type="button"
                        role="tab"
                        id={`${idPrefix}-tab-${m.id}`}
                        aria-selected={selected}
                        aria-controls={`${idPrefix}-panel-${m.id}`}
                        tabIndex={selected ? 0 : -1}
                        onClick={() => onChange(m.id)}
                        style={{ minHeight: ITEM }}
                        className={`relative flex shrink-0 flex-col items-start justify-center rounded-full px-4 text-left transition-colors focus-visible:outline-2 focus-visible:outline-[var(--accent-soft)] items-center ${selected ? "text-white" : "text-[var(--text-2)] hover:text-white"}`}
                    >
                        <span className="whitespace-nowrap text-sm font-medium">{m.name}</span>
                        {/* Une seule ligne secondaire : « Meilleur » (orange) ou « Bientôt » ; l'état « bientôt » est aussi dit aux lecteurs d'écran */}
                        {m.best
                            ? <span className="text-[11px] leading-tight" style={{ color: "var(--series-predicted)" }}>Meilleur</span>
                            : !m.served && <span className="text-[11px] leading-tight text-[var(--text-2)]">Bientôt</span>}
                        {!m.served && <span className="sr-only">, bientôt disponible</span>}
                    </button>
                )
            })}
        </div>
    )
}
