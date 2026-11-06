import { useEffect, useRef } from "react"
import type { KeyboardEvent } from "react"
import { animate, utils } from "animejs"
import { duration, springs } from "../../design/motion"
import { useReducedMotion } from "../../hooks/useReducedMotion"

export interface TabDef {
    id: string
    label: string
}

interface PillTabsProps {
    tabs: TabDef[]
    value: string
    onChange: (id: string) => void
    /** Préfixe des identifiants ARIA (relie chaque onglet à son panneau) */
    idPrefix: string
    ariaLabel: string
}

/**
 * Onglets en pilules (pattern ARIA tabs). Un seul indicateur plein glisse sous l'onglet choisi, avec un ressort
 * rigide ; la position et la largeur sont lues sur l'onglet cible. Flèches gauche/droite pour naviguer.
 */
export default function PillTabs({ tabs, value, onChange, idPrefix, ariaLabel }: PillTabsProps) {
    const list = useRef<HTMLDivElement>(null)
    const indicator = useRef<HTMLSpanElement>(null)
    const placed = useRef(false)
    const reduce = useReducedMotion()

    useEffect(() => {
        const place = () => {
            const target = list.current?.querySelector<HTMLElement>(`[data-tab="${value}"]`)
            const el = indicator.current
            if (!target || !el) return
            // Une seule ligne défilante (mobile) : l'onglet actif reste visible
            // (défilement limité à la barre : scrollIntoView ferait aussi défiler la page)
            const bar = list.current!
            if (target.offsetLeft < bar.scrollLeft) bar.scrollLeft = target.offsetLeft - 8
            else if (target.offsetLeft + target.offsetWidth > bar.scrollLeft + bar.clientWidth) {
                bar.scrollLeft = target.offsetLeft + target.offsetWidth - bar.clientWidth + 8
            }
            const props = { translateX: target.offsetLeft, width: target.offsetWidth }
            if (!placed.current || reduce) {
                // Premier affichage (ou mouvement réduit) : placement direct, sans glissement
                utils.set(el, { ...props, opacity: 1 })
                placed.current = true
            } else {
                animate(el, { ...props, ease: springs.glide() })
            }
        }
        place()
        // Remesure quand la police est chargée ou que la barre change de taille (les largeurs d'onglets changent)
        void document.fonts?.ready.then(place)
        const observer = new ResizeObserver(place)
        if (list.current) observer.observe(list.current)
        return () => observer.disconnect()
    }, [value, reduce])

    const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
        const index = tabs.findIndex(t => t.id === value)
        const next = e.key === "ArrowRight" ? index + 1 : e.key === "ArrowLeft" ? index - 1 : null
        if (next === null) return
        e.preventDefault()
        const tab = tabs[(next + tabs.length) % tabs.length]
        onChange(tab.id)
        list.current?.querySelector<HTMLElement>(`[data-tab="${tab.id}"]`)?.focus()
    }

    return (
        <div
            ref={list}
            role="tablist"
            aria-label={ariaLabel}
            onKeyDown={onKeyDown}
            className="relative flex max-w-full flex-nowrap gap-1 overflow-x-auto rounded-full border border-[var(--glass-border)] bg-[var(--glass-bg)] p-1"
        >
            <span
                ref={indicator}
                aria-hidden="true"
                className="absolute bottom-1 left-0 top-1 rounded-full bg-[var(--accent-deep)] shadow-[0_0_20px_-4px_var(--accent-glow)]"
                style={{ opacity: 0 }}
            />
            {tabs.map(tab => {
                const active = tab.id === value
                return (
                    <button
                        key={tab.id}
                        data-tab={tab.id}
                        role="tab"
                        id={`${idPrefix}-tab-${tab.id}`}
                        aria-selected={active}
                        aria-controls={`${idPrefix}-panel`}
                        tabIndex={active ? 0 : -1}
                        onClick={() => onChange(tab.id)}
                        style={{ transitionDuration: `${duration.fast}ms` }}
                        className={`relative z-10 shrink-0 whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--accent-soft)] ${active ? "text-white" : "text-[var(--text-2)] hover:text-white"}`}
                    >
                        {tab.label}
                    </button>
                )
            })}
        </div>
    )
}
