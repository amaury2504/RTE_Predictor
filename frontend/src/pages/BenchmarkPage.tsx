import { useEffect, useMemo, useRef, useState } from "react"
import { Navigate, useNavigate, useParams } from "react-router-dom"
import { loadBenchmark } from "../benchmark/loader"
import { bestModel, primaryRows } from "../benchmark/selectors"
import { useAuth } from "../context/AuthContext"
import AdvancedStats from "../components/benchmark/AdvancedStats"
import BiasMotion from "../components/benchmark/BiasMotion"
import { CARD } from "../components/benchmark/chartStyle"
import ImprovementSteps from "../components/benchmark/ImprovementSteps"
import MaeBars from "../components/benchmark/MaeBars"
import OverviewHero from "../components/benchmark/OverviewHero"
import StabilityCards from "../components/benchmark/StabilityCards"
import PillTabs from "../components/nav/PillTabs"
import type { TabDef } from "../components/nav/PillTabs"
import { useTabTransition } from "../hooks/useTabTransition"
import { rankModels } from "../lib/benchmarkModels"
import { PRIMARY_MODELS, REFERENCE_MODELS, shortName } from "../lib/modelNames"
import type { BarKind } from "../design/chartColors"
import type { BenchmarkResults } from "../types/api"

const TABS: TabDef[] = [
    { id: "overview", label: "Vue d'ensemble" },
    { id: "bias", label: "Biais" },
    { id: "improve", label: "Améliorations" },
    { id: "stability", label: "Stabilité" },
    { id: "details", label: "Détails" },
]
const TAB_IDS = TABS.map(t => t.id)

/** Contenu d'un onglet. Les blocs marqués `data-stagger` apparaissent en cascade (voir useTabTransition). */
function TabContent({ tab, results }: { tab: string; results: BenchmarkResults }) {
    const ranking = useMemo(() => rankModels(results.summary), [results])
    const best = bestModel(results)?.model
    const rows = useMemo(() => primaryRows(results, PRIMARY_MODELS, REFERENCE_MODELS), [results])
    const kindOf = (model: string): BarKind =>
        REFERENCE_MODELS.includes(model) ? "reference" : model === best ? "best" : "model"

    switch (tab) {
        case "overview":
            return (
                <div className="space-y-6">
                    <div data-stagger><OverviewHero results={results} /></div>
                    <div data-stagger>
                        <MaeBars
                            rows={rows.flatMap(r => (r.mae == null ? [] : [{ id: r.model, name: shortName(r.model), value: r.mae, kind: kindOf(r.model) }]))}
                        />
                    </div>
                    <p data-stagger className="px-1 text-xs text-[var(--text-3)]">
                        LightGBM, MLP et Ridge : avec correction du biais et consommation récente. Erreur moyenne sur{" "}
                        {results.protocol.test_years.join(", ")}.
                    </p>
                </div>
            )
        case "bias":
            return <div data-stagger><BiasMotion results={results} /></div>
        case "improve":
            return <div data-stagger><ImprovementSteps results={results} /></div>
        case "stability":
            return (
                <div data-stagger>
                    <StabilityCards
                        years={results.protocol.test_years}
                        series={rows.map(r => ({
                            id: r.model,
                            name: shortName(r.model),
                            kind: kindOf(r.model),
                            values: results.protocol.test_years.map(y => results.by_fold.find(f => f.model === r.model && f.test_year === y)?.mae ?? null),
                        }))}
                    />
                </div>
            )
        case "details":
            return (
                <div className="space-y-6">
                    <ul data-stagger className={`${CARD} space-y-1.5 px-6 py-5 text-sm text-muted`}>
                        <li>Météo observée utilisée comme prévision parfaite : avantage face à RTE.</li>
                        <li>Les prévisions RTE disposent d'informations que ce projet n'a pas : plafond de comparaison.</li>
                        <li>Cause du changement de niveau après 2022 : non établie.</li>
                    </ul>
                    <div data-stagger><AdvancedStats results={results} ranking={ranking} /></div>
                </div>
            )
        default:
            return null
    }
}

export default function BenchmarkPage() {
    const navigate = useNavigate()
    const { tab = "overview" } = useParams()
    const { token, logout } = useAuth()
    const [results, setResults] = useState<BenchmarkResults | null>(null)
    const [error, setError] = useState<string | null>(null)
    const panel = useRef<HTMLDivElement>(null)
    const validTab = TAB_IDS.includes(tab) ? tab : "overview"
    const shown = useTabTransition(validTab, TAB_IDS, panel)

    useEffect(() => {
        if (!token) return
        loadBenchmark(token)
            .then(setResults)
            .catch((err: unknown) => {
                if (err instanceof Error && err.message.includes("401")) {
                    logout(); navigate("/login")
                } else {
                    setError(err instanceof Error ? err.message : "Erreur inconnue")
                }
            })
        // logout change à chaque affichage : le chargement ne doit dépendre que du jeton
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token])

    if (!TAB_IDS.includes(tab)) return <Navigate to="/benchmark/overview" replace />

    return (
        <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
            <header className="space-y-4">
                <h1 className="text-2xl font-semibold text-ink">Comparaison de modèles</h1>
                <PillTabs
                    tabs={TABS}
                    value={validTab}
                    onChange={id => navigate(`/benchmark/${id}`)}
                    idPrefix="benchmark"
                    ariaLabel="Sections du benchmark"
                />
            </header>

            {error && (
                <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-8 text-center text-red-300">
                    <p className="font-medium">Résultats indisponibles</p>
                    <p className="mt-1 text-sm">{error}</p>
                </div>
            )}

            {!results && !error && (
                <div className={`${CARD} p-12 text-center`}>
                    <div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-2 border-line border-t-neon" />
                    <p className="text-sm text-ink">Chargement...</p>
                </div>
            )}

            {results && (
                <div
                    ref={panel}
                    role="tabpanel"
                    id="benchmark-panel"
                    aria-labelledby={`benchmark-tab-${shown}`}
                    tabIndex={0}
                    className="focus-visible:outline-2 focus-visible:outline-[var(--accent-soft)]"
                >
                    <TabContent tab={shown} results={results} />
                </div>
            )}
        </main>
    )
}
