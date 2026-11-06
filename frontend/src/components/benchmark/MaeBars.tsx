import { useRef } from "react"
import { animate, stagger } from "animejs"
import type { BarKind } from "../../design/chartColors"
import { KIND_FILL } from "../../design/chartColors"
import { duration, easeOut } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { num } from "../../lib/format"
import GlassCard from "../glass/GlassCard"

export interface BarRow {
    id: string
    name: string
    value: number
    kind: BarKind
}

/**
 * Classement par erreur moyenne : barres horizontales qui poussent depuis la base en cascade.
 * Orange = meilleur modèle, bleu = autres modèles, gris = repères. Aucune puce, aucun axe : le nom, la barre, le chiffre.
 */
export default function MaeBars({ rows }: { rows: BarRow[] }) {
    const root = useRef<HTMLUListElement>(null)
    const reduce = useReducedMotion()
    const max = Math.max(...rows.map(r => r.value))

    useAnimeScope(root, () => {
        animate(".mae-bar", {
            scaleX: [0, 1],
            duration: reduce ? duration.fast : duration.hero,
            ease: easeOut,
            delay: reduce ? 0 : stagger(70),
        })
    }, [reduce, rows.map(r => r.id).join()])

    return (
        <GlassCard className="px-6 py-5">
            <ul ref={root} className="space-y-3">
                {rows.map(r => (
                    <li key={r.id} className="grid grid-cols-[8.5rem_1fr_5.5rem] items-center gap-4">
                        <span className={`whitespace-nowrap text-sm ${r.kind === "best" ? "font-semibold text-[var(--text-1)]" : "text-[var(--text-2)]"}`}>
                            {r.name}
                        </span>
                        <span className="h-3 rounded-full bg-white/5">
                            <span
                                className="mae-bar block h-3 origin-left rounded-full"
                                style={{ width: `${(r.value / max) * 100}%`, background: KIND_FILL[r.kind], transform: "scaleX(0)" }}
                            />
                        </span>
                        <span className="tabular whitespace-nowrap text-right text-sm text-[var(--text-1)]">{num(r.value)} GW</span>
                    </li>
                ))}
            </ul>
        </GlassCard>
    )
}
