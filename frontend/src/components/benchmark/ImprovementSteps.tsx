import { useRef, useState } from "react"
import { animate, stagger } from "animejs"
import type { BenchmarkResults } from "../../types/api"
import { rowOf } from "../../benchmark/selectors"
import { CHART } from "../../design/chartColors"
import { duration, easeOut } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { num } from "../../lib/format"
import { FAMILIES } from "../../lib/modelNames"
import GlassCard from "../glass/GlassCard"
import PillTabs from "../nav/PillTabs"

interface Step {
    label: string
    from: number
    to: number
    /** « total » : barre depuis zéro ; « gain » : baisse d'erreur due à une décision */
    kind: "total" | "gain" | "final"
}

/**
 * L'impact de chaque décision, en escalier : de l'erreur brute au résultat final, une marche par décision.
 * Chaque barre flottante montre de combien la décision a fait baisser l'erreur.
 */
export default function ImprovementSteps({ results }: { results: BenchmarkResults }) {
    const [family, setFamily] = useState<string>("lightgbm")
    const root = useRef<HTMLDivElement>(null)
    const reduce = useReducedMotion()

    const mae = (id: string) => rowOf(results, id)?.mae ?? null
    const raw = mae(family)
    const corrected = mae(`${family}_corr`)
    const full = mae(`${family}_niveau_corr`)
    const steps: Step[] =
        raw != null && corrected != null && full != null
            ? [
                { label: "Brut", from: 0, to: raw, kind: "total" },
                { label: "Correction du biais", from: corrected, to: raw, kind: "gain" },
                { label: "Consommation récente", from: full, to: corrected, kind: "gain" },
                { label: "Résultat", from: 0, to: full, kind: "final" },
            ]
            : []

    // Échelle commune à toutes les familles : changer de famille ne change pas l'unité
    const scaleMax = Math.max(...FAMILIES.map(f => mae(f.id) ?? 0))

    useAnimeScope(root, () => {
        animate(".step-bar", {
            scaleX: [0, 1],
            duration: reduce ? duration.fast : duration.hero,
            ease: easeOut,
            delay: reduce ? 0 : stagger(220),
        })
        animate(".step-value", { opacity: [0, 1], duration: duration.base, delay: reduce ? 0 : stagger(220, { start: 450 }) })
    }, [family, reduce])

    const fill = (k: Step["kind"]) => (k === "final" ? CHART.best : k === "gain" ? "#7fb4f0" : CHART.model)

    return (
        <div className="space-y-4">
            <PillTabs
                tabs={FAMILIES.map(f => ({ id: f.id, label: f.label }))}
                value={family}
                onChange={setFamily}
                idPrefix="improve"
                ariaLabel="Famille de modèle"
            />
            <GlassCard className="px-6 py-6">
                <div ref={root} className="space-y-4">
                    {steps.map(s => (
                        <div key={s.label} className="grid grid-cols-[10.5rem_1fr] items-center gap-4">
                            <span className={`whitespace-nowrap text-sm ${s.kind === "final" ? "font-semibold text-[var(--text-1)]" : "text-[var(--text-2)]"}`}>
                                {s.label}
                            </span>
                            <div className="relative h-9">
                                <span
                                    className="step-bar absolute top-1 h-7 origin-left rounded-md"
                                    style={{
                                        left: `${(s.from / scaleMax) * 78}%`,
                                        width: `${((s.to - s.from) / scaleMax) * 78}%`,
                                        background: fill(s.kind),
                                        transform: "scaleX(0)",
                                    }}
                                />
                                <span
                                    className="step-value tabular absolute top-1.5 whitespace-nowrap text-sm text-[var(--text-1)]"
                                    style={{ left: `calc(${(s.to / scaleMax) * 78}% + 10px)`, opacity: 0 }}
                                >
                                    {s.kind === "gain" ? `−${num(((s.to - s.from) / s.to) * 100, 0)} %` : `${num(s.to)} GW`}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </GlassCard>
        </div>
    )
}
