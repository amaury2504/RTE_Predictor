import { useRef } from "react"
import { animate, stagger, svg } from "animejs"
import type { BarKind } from "../../design/chartColors"
import { CHART, KIND_FILL } from "../../design/chartColors"
import { duration, easeOut } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { num } from "../../lib/format"
import GlassCard from "../glass/GlassCard"

export interface StabilitySeries {
    id: string
    name: string
    kind: BarKind
    /** Erreur moyenne (GW) pour chaque année de test, dans l'ordre de `years` */
    values: (number | null)[]
}

const W = 200
const H = 96
const PAD_X = 22
const TOP = 22
const BOTTOM = 76

/**
 * Un petit graphique par modèle, sur la même échelle : un bon modèle est bas et plat.
 * La courbe se dessine à l'apparition. Orange = meilleur modèle, bleu = autres, gris = repère.
 */
export default function StabilityCards({ years, series }: { years: number[]; series: StabilitySeries[] }) {
    const root = useRef<HTMLUListElement>(null)
    const reduce = useReducedMotion()
    const yMax = Math.max(...series.flatMap(s => s.values.filter((v): v is number => v != null))) * 1.05
    const xAt = (i: number) => PAD_X + (years.length === 1 ? (W - 2 * PAD_X) / 2 : (i * (W - 2 * PAD_X)) / (years.length - 1))
    const yAt = (v: number) => BOTTOM - (v / yMax) * (BOTTOM - TOP)

    useAnimeScope(root, () => {
        const lines = svg.createDrawable(".stab-line")
        animate(lines, {
            draw: ["0 0", "0 1"],
            duration: reduce ? duration.fast : duration.hero,
            ease: easeOut,
            delay: reduce ? 0 : stagger(90),
        })
        animate(".stab-dot", {
            opacity: [0, 1],
            duration: duration.base,
            delay: reduce ? 0 : stagger(30, { start: 300 }),
        })
    }, [reduce, series.map(s => s.id).join()])

    return (
        <ul ref={root} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {series.map(s => {
                const points = s.values.flatMap((v, i) => (v == null ? [] : [{ x: xAt(i), y: yAt(v), v }]))
                const color = KIND_FILL[s.kind]
                return (
                    <li key={s.id}>
                        <GlassCard className="px-5 py-4">
                            <p className={`whitespace-nowrap text-sm ${s.kind === "best" ? "font-semibold text-[var(--text-1)]" : "text-[var(--text-2)]"}`}>
                                {s.name}
                            </p>
                            <svg viewBox={`0 0 ${W} ${H}`} className="mt-1 w-full" role="img"
                                aria-label={`${s.name} : ${points.map((p, i) => `${years[i]} ${num(p.v)} GW`).join(", ")}`}>
                                <line x1={PAD_X} x2={W - PAD_X} y1={BOTTOM} y2={BOTTOM} stroke={CHART.grid} />
                                <path
                                    className="stab-line"
                                    d={points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ")}
                                    fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"
                                />
                                {points.map((p, i) => (
                                    <g key={i} className="stab-dot" style={{ opacity: 0 }}>
                                        <circle cx={p.x} cy={p.y} r={3.5} fill={color} />
                                        <text x={p.x} y={p.y - 9} textAnchor="middle" fontSize={10} fill={CHART.text}>{num(p.v)}</text>
                                    </g>
                                ))}
                                {years.map((y, i) => (
                                    <text key={y} x={xAt(i)} y={H - 4} textAnchor="middle" fontSize={9.5} fill={CHART.axis}>{y}</text>
                                ))}
                            </svg>
                        </GlassCard>
                    </li>
                )
            })}
        </ul>
    )
}
