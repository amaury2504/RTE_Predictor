import { useEffect, useRef, useState } from "react"
import { animate, stagger } from "animejs"
import type { BenchmarkResults, BenchmarkRow } from "../../types/api"
import { rowOf } from "../../benchmark/selectors"
import { CHART } from "../../design/chartColors"
import { duration, easeOut, springs } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { FAMILIES, shortName } from "../../lib/modelNames"
import GlassCard from "../glass/GlassCard"
import PillTabs from "../nav/PillTabs"

interface Pt { x: number; y: number }
interface Dot {
    id: string
    label: string
    color: string
    before: Pt
    after: Pt
}

// Repère de dessin (unités du viewBox)
const W = 720
const H = 400
const L = 56
const R = 24
const T = 24
const B = 52

const at = (row: BenchmarkRow | undefined): Pt | null =>
    row && row.bias != null && row.mae_debiased != null ? { x: row.bias, y: row.mae_debiased } : null

/**
 * La carte du biais : en abscisse le niveau (le modèle surestime-t-il ?), en ordonnée la forme (suit-il la courbe ?).
 * Au chargement, les modèles sont « avant correction » (décalés vers la droite), puis glissent vers le niveau juste.
 * Orange = LightGBM (meilleur modèle), bleu = autres modèles, gris = repères.
 */
export default function BiasMotion({ results }: { results: BenchmarkResults }) {
    const [stage, setStage] = useState<"before" | "after">("before")
    const root = useRef<SVGSVGElement>(null)
    const touched = useRef(false)
    const reduce = useReducedMotion()

    const dots: Dot[] = [
        ...FAMILIES.flatMap(f => {
            const before = at(rowOf(results, f.id))
            const after = at(rowOf(results, `${f.id}_corr`))
            return before && after
                ? [{ id: f.id, label: f.label, color: f.id === "lightgbm" ? CHART.best : CHART.model, before, after }]
                : []
        }),
        ...["ts_timestral_209m_meteo", "ts_holt_winters"].flatMap(id => {
            const p = at(rowOf(results, id))
            return p ? [{ id, label: shortName(id), color: CHART.model, before: p, after: p }] : []
        }),
        ...["ref_rte_j1", "ref_naive_j1"].flatMap(id => {
            const p = at(rowOf(results, id))
            return p ? [{ id, label: shortName(id), color: CHART.reference, before: p, after: p }] : []
        }),
    ]

    const xs = dots.flatMap(d => [d.before.x, d.after.x])
    const ys = dots.flatMap(d => [d.before.y, d.after.y])
    const xMin = Math.min(-0.5, ...xs) - 0.3
    const xMax = Math.max(...xs) + 0.5
    const yMax = Math.max(...ys) * 1.12
    const px = (x: number) => L + ((x - xMin) / (xMax - xMin)) * (W - L - R)
    const py = (y: number) => H - B - (y / yMax) * (H - B - T)

    // Entrée : les points apparaissent en cascade
    useAnimeScope(root, () => {
        animate(".bias-dot", {
            opacity: [0, 1],
            scale: reduce ? [1, 1] : [0.2, 1],
            duration: duration.slow,
            ease: easeOut,
            delay: reduce ? 0 : stagger(70),
        })
    }, [reduce])

    // Glissement vers la position choisie
    useAnimeScope(root, () => {
        for (const d of dots) {
            const p = stage === "after" ? d.after : d.before
            animate(`[data-dot="${d.id}"]`, {
                translateX: px(p.x),
                translateY: py(p.y),
                ...(reduce ? { duration: duration.fast } : { ease: springs.glide() }),
            })
        }
    }, [stage, reduce, results])

    // Lecture automatique : après un court instant, la correction est appliquée (sauf si l'utilisateur a déjà choisi)
    useEffect(() => {
        const t = setTimeout(() => { if (!touched.current) setStage("after") }, 1400)
        return () => clearTimeout(t)
    }, [])

    const choose = (id: string) => { touched.current = true; setStage(id as "before" | "after") }

    return (
        <div className="space-y-4">
            <PillTabs
                tabs={[{ id: "before", label: "Avant correction" }, { id: "after", label: "Après correction" }]}
                value={stage}
                onChange={choose}
                idPrefix="bias"
                ariaLabel="Avant ou après correction du biais"
            />
            <GlassCard className="p-4">
                <svg ref={root} viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
                    aria-label="Carte du biais : chaque modèle selon son biais moyen et l'erreur de forme">
                    {/* Niveau juste : biais nul */}
                    <line x1={px(0)} x2={px(0)} y1={T} y2={H - B} stroke={CHART.reference} strokeDasharray="5 5" />
                    <text x={px(0)} y={T - 8} textAnchor="middle" fontSize={12} fill={CHART.axis}>niveau juste</text>
                    <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={CHART.grid} />
                    <text x={L} y={H - 16} fontSize={12} fill={CHART.axis}>← sous-estime</text>
                    <text x={W - R} y={H - 16} textAnchor="end" fontSize={12} fill={CHART.axis}>surestime →</text>
                    <text x={L} y={T - 8} fontSize={12} fill={CHART.axis}>↑ forme moins bonne</text>

                    {dots.map(d => (
                        <g key={d.id} data-dot={d.id} style={{ transform: `translate(${px(d.before.x)}px, ${py(d.before.y)}px)` }}>
                            <g className="bias-dot" style={{ opacity: 0, transformBox: "fill-box", transformOrigin: "center" }}>
                                <circle r={8} fill={d.color} stroke="#050a14" strokeWidth={2.5} />
                                <text x={14} y={d.id === "mlp" ? -4 : d.id === "lightgbm" ? 12 : 4} fontSize={13} fill={CHART.text} fontWeight={d.color === CHART.best ? 700 : 400}>{d.label}</text>
                            </g>
                        </g>
                    ))}
                </svg>
            </GlassCard>
        </div>
    )
}
