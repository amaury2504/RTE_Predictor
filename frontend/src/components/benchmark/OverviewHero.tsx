import type { BenchmarkResults } from "../../types/api"
import { bestModel, rowOf } from "../../benchmark/selectors"
import { shortName } from "../../lib/modelNames"
import { num } from "../../lib/format"
import AnimatedNumber from "../data/AnimatedNumber"
import GlassCard from "../glass/GlassCard"

function Chip({ children }: { children: string }) {
    return (
        <span className="whitespace-nowrap rounded-full border border-[var(--glass-border)] bg-white/5 px-3 py-1 text-sm text-[var(--text-1)]">
            {children}
        </span>
    )
}

/** Le verdict en un coup d'œil : un nom, un chiffre, deux mots-clés. */
export default function OverviewHero({ results }: { results: BenchmarkResults }) {
    const best = bestModel(results)
    if (!best || best.mae == null) return null

    const naive = rowOf(results, "ref_naive_j1")
    const rte = rowOf(results, "ref_rte_j1")
    const gain = naive?.mae != null ? naive.mae / best.mae : null
    const gapRte = rte?.mae != null && rte.mae !== 0 ? ((best.mae - rte.mae) / rte.mae) * 100 : null

    return (
        <GlassCard className="px-8 py-7">
            <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
                <div>
                    <p className="text-sm uppercase tracking-widest text-[var(--text-3)]">Meilleur modèle</p>
                    <p className="mt-1 text-5xl font-semibold tracking-tight" style={{ color: "var(--series-predicted)" }}>
                        {shortName(best.model)}
                    </p>
                </div>
                <div className="text-right">
                    <p className="whitespace-nowrap text-6xl font-semibold tracking-tight text-[var(--text-1)]">
                        <AnimatedNumber value={best.mae} unit=" GW" />
                    </p>
                    <p className="text-sm text-[var(--text-3)]">erreur moyenne</p>
                </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
                {gain != null && <Chip>{`${num(gain, 1)}× plus précis que la naïve`}</Chip>}
                {gapRte != null && <Chip>{Math.abs(gapRte) < 2 ? "au niveau de RTE (veille)" : `${gapRte > 0 ? "+" : "−"}${num(Math.abs(gapRte), 0)} % vs RTE (veille)`}</Chip>}
            </div>
        </GlassCard>
    )
}
