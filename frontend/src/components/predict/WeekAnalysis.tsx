import { useEffect, useLayoutEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { animate } from "animejs"
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts"
import { fetchWeekWeather, batchPredict, fetchRTEWeek, fetchKpis } from "../../services/api"
import { useAuth } from "../../context/AuthContext"
import { duration } from "../../design/motion"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { num, pct } from "../../lib/format"
import { REGIONS } from "../../types/api"
import type { RegionWeather, KpiReport, KpiPoint } from "../../types/api"
import KpiCard from "../KpiCard"
import type { KpiItem } from "../KpiCard"
import LazyMount from "../LazyMount"
import GlassCard from "../glass/GlassCard"

interface HourEntry {
    apiDate: string
    hour: number
    isoKey: string
    label: string
}

interface ChartPoint {
    label: string
    predicted: number
    real: number | null
}

const DEFAULT_W: RegionWeather = { temperature: 10, wind_speed: 20, humidity: 70 }

// Couleurs des séries (jetons de design) : prédit en orange, réel en bleu. 
const PREDICTED = "var(--series-predicted)"
const REAL = "var(--series-real)"

const AXIS_TICK = { fontSize: 12, fill: "#8a9bb8" }
const TOOLTIP_STYLE = {
    background: "#0a1322",
    borderRadius: "10px",
    border: "1px solid #1ea0ff55",
    fontSize: "13px",
    color: "#e8eef8",
}

// Formatteur créé une seule fois : toLocaleDateString("fr-FR", ...) recrée un Intl.DateTimeFormat
// à chaque appel (168 fois ici), ce qui coûtait plusieurs centaines de ms sur mobile.
const WEEKDAY_FORMAT = new Intl.DateTimeFormat("fr-FR", { weekday: "short" })

function generateHours(): HourEntry[] {
    const now = new Date()
    const start = new Date(now)
    start.setDate(start.getDate() - 7)
    start.setHours(0, 0, 0, 0)

    return Array.from({ length: 168 }, (_, i) => {
        const dt = new Date(start.getTime() + i * 3600000)
        const d = String(dt.getDate()).padStart(2, "0")
        const m = String(dt.getMonth() + 1).padStart(2, "0")
        const y = dt.getFullYear()
        const h = dt.getHours()
        return {
            apiDate: `${d}/${m}/${y}`,
            hour: h,
            isoKey: `${y}-${m}-${d}T${String(h).padStart(2, "0")}:00`,
            label: `${WEEKDAY_FORMAT.format(dt)} ${String(h).padStart(2, "0")}h`,
        }
    })
}

// --- Composants d'affichage --------------------------------------------------

function KpiGroup({ title, items }: { title: string; items: KpiItem[] }) {
    return (
        <section>
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-widest text-[var(--accent-soft)]">{title}</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {items.map(item => <KpiCard key={item.label} {...item} />)}
            </div>
        </section>
    )
}

function buildGroups(k: KpiReport): { title: string; items: KpiItem[] }[] {
    return [
        {
            title: "Niveau",
            items: [
                { label: "Moy. prédiction ML", value: num(k.mean_predicted, 2, " GW"), hint: "Consommation moyenne prédite" },
                { label: "Moy. consommation RTE", value: num(k.mean_actual, 2, " GW"), hint: "Consommation moyenne réelle" },
                { label: "Heures analysées", value: String(k.n), hint: "Points comparés (prédit contre réel)" },
            ],
        },
        {
            title: "Précision",
            items: [
                { label: "MAE", value: num(k.mae, 2, " GW"), hint: "Erreur absolue moyenne : écart typique en GW" },
                { label: "RMSE", value: num(k.rmse, 2, " GW"), hint: "Pénalise davantage les gros écarts que la MAE" },
                { label: "MAPE", value: pct(k.mape), hint: "Erreur relative moyenne, heure par heure" },
                { label: "WAPE", value: pct(k.wape), hint: "Erreurs cumulées rapportées à la consommation cumulée" },
            ],
        },
    ]
}

// --- Analyse -----------------------------------------------------------------

const REVEAL_MS = 1500   // apparition des résultats
const SCROLL_MS = 1400   // descente vers les résultats

interface WeekAnalysisProps {
    /** Modèle qui prédit (identifiant de l'onglet « Prédire »). */
    modelId: string
    /**
     * Vrai quand l'animation de la carte est terminée. Tant qu'il est faux, les résultats (même prêts) restent masqués :
     * on ne les montre qu'une fois la scène refermée, puis on y descend tranquillement.
     */
    reveal: boolean
    /** Prévient la page parente quand l'analyse tourne, pour bloquer les boutons (limite de requêtes météo). */
    onBusyChange?: (busy: boolean) => void
}

/**
 * Comparaison sur 7 jours (168 heures) : météo historique, prédictions du modèle servi, consommation réelle RTE,
 * puis indicateurs d'erreur. L'analyse démarre au montage ; pour la relancer, la page parente remonte le composant.
 */
export default function WeekAnalysis({ modelId, reveal, onBusyChange }: WeekAnalysisProps) {
    const [step, setStep] = useState("")
    const [status, setStatus] = useState<"loading" | "done" | "error">("loading")
    const [chartData, setChartData] = useState<ChartPoint[]>([])
    const [kpis, setKpis] = useState<KpiReport | null>(null)
    const [avgPredicted, setAvgPredicted] = useState<number | null>(null)
    const [rteAvailable, setRteAvailable] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const { token, logout } = useAuth()
    const navigate = useNavigate()
    const reduce = useReducedMotion()
    const root = useRef<HTMLDivElement>(null)

    useEffect(() => {
        let cancelled = false
        // Après un annulation (démontage), aucun état n'est plus modifié
        const guard = <T,>(fn: () => T) => { if (!cancelled) fn() }

        async function run() {
            if (!token) return
            onBusyChange?.(true)
            try {
                const hours = generateHours()

                guard(() => setStep("Météo historique (13 régions × 7 jours)..."))
                const weatherMaps = await fetchWeekWeather()
                // Une région sans aucune donnée (limite de requêtes, réseau) est remplacée par une météo par défaut (DEFAULT_W)

                const batchItems = hours.map(h => ({
                    date: h.apiDate,
                    hour: h.hour,
                    temperatures: Object.fromEntries(REGIONS.map(r => [r, (weatherMaps[r]?.[h.isoKey] ?? DEFAULT_W).temperature])),
                    wind_speeds: Object.fromEntries(REGIONS.map(r => [r, (weatherMaps[r]?.[h.isoKey] ?? DEFAULT_W).wind_speed])),
                    humidities: Object.fromEntries(REGIONS.map(r => [r, (weatherMaps[r]?.[h.isoKey] ?? DEFAULT_W).humidity])),
                }))

                guard(() => setStep("168 prédictions en cours..."))
                const predictions = await batchPredict(batchItems, token, modelId)
                const predMap: Record<string, number> = {}
                hours.forEach((h, i) => { predMap[h.isoKey] = predictions[i]?.power ?? 0 })

                guard(() => setStep("Données RTE (7 jours)..."))
                let rteMap: Record<string, number> = {}
                let rteOk = true
                try {
                    rteMap = await fetchRTEWeek(token)
                } catch {
                    rteOk = false
                    guard(() => setRteAvailable(false))
                }

                // Les prédictions ne sont PAS arrondies : un arrondi au GW fausserait les KPI d'erreur.
                const data: ChartPoint[] = hours.map(h => ({
                    label: h.label,
                    predicted: predMap[h.isoKey] ?? 0,
                    real: rteMap[h.isoKey] != null ? rteMap[h.isoKey] / 1000 : null,
                }))
                guard(() => {
                    setChartData(data)
                    setAvgPredicted(data.reduce((a, d) => a + d.predicted, 0) / data.length)
                })

                const points: KpiPoint[] = hours.flatMap((h, i) =>
                    data[i].real != null
                        ? [{ datetime: h.isoKey, predicted: data[i].predicted, actual: data[i].real as number }]
                        : []
                )

                if (rteOk && points.length > 0) {
                    guard(() => setStep("Calcul des indicateurs..."))
                    const report = await fetchKpis(points, token)
                    guard(() => setKpis(report))
                }
                guard(() => setStatus("done"))
            } catch (err: unknown) {
                if (cancelled) return
                if (err instanceof Error && err.message.includes("401")) {
                    logout(); navigate("/login")
                } else {
                    setError(err instanceof Error ? err.message : "Erreur inconnue")
                    setStatus("error")
                }
            } finally {
                onBusyChange?.(false)
            }
        }

        // La page remonte ce composant (clé) pour relancer : un seul départ par montage
        run()
        return () => { cancelled = true }
        // Un seul lancement par montage : token, logout et navigate ne doivent pas relancer l'analyse
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // Les résultats sont prêts ET l'animation est refermée : ils apparaissent lentement (fondu et glissement) pendant que
    // la page descend vers eux, à vitesse douce. Un geste de l'utilisateur (molette, toucher, clavier) interrompt la descente.
    const showResults = status === "done" && reveal
    useLayoutEffect(() => {
        const el = root.current
        if (!showResults || !el) return
        const target = Math.max(0, el.getBoundingClientRect().top + window.scrollY - 24)   // mesuré avant tout décalage
        el.style.opacity = "0"
        const fade = animate(el, {
            opacity: [0, 1],
            translateY: reduce ? 0 : [28, 0],
            duration: reduce ? duration.fast : REVEAL_MS,
            ease: "inOutQuad",
        })
        const position = { y: window.scrollY }
        const scroll = animate(position, {
            y: target,
            duration: reduce ? 0 : SCROLL_MS,
            ease: "inOutQuad",
            onUpdate: () => window.scrollTo(0, position.y),
        })
        const stop = () => scroll.pause()
        const events = ["wheel", "touchstart", "keydown"] as const
        events.forEach(e => window.addEventListener(e, stop, { passive: true, once: true }))
        return () => {
            fade.pause()
            scroll.pause()
            events.forEach(e => window.removeEventListener(e, stop))
        }
    }, [showResults, reduce])

    const tickIndices = chartData.filter((_, i) => i % 24 === 0).map(d => d.label)

    // Tant que la scène n'est pas refermée, rien ne s'affiche (sauf une erreur, qui ne doit pas attendre)
    if (!reveal && status !== "error") return null

    return (
        <div ref={root} className="space-y-6">
            <h2 className="text-xl font-semibold text-[var(--text-1)]">Résultats sur 7 jours</h2>

            {status === "loading" && (
                <GlassCard className="p-10 text-center">
                    <div role="status">
                        <div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-2 border-[var(--glass-border)] border-t-[var(--accent-soft)] motion-reduce:animate-none" aria-hidden="true" />
                        <p className="text-sm text-[var(--text-1)]">{step || "Chargement..."}</p>
                        <p className="mt-2 text-xs text-[var(--text-2)]">168 heures, quelques secondes</p>
                    </div>
                </GlassCard>
            )}

            {status === "error" && (
                <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-8 text-center text-red-300">
                    <p className="font-medium">Erreur lors de l'analyse</p>
                    <p className="mt-1 text-sm">{error}</p>
                </div>
            )}

            {status === "done" && (
                <>
                    {!rteAvailable && (
                        <div role="status" className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
                            Données RTE indisponibles : seule la courbe prédite est affichée, les indicateurs ne peuvent pas être calculés.
                        </div>
                    )}

                    {!kpis && avgPredicted != null && (
                        <KpiGroup
                            title="Niveau"
                            items={[{ label: "Moy. prédiction ML", value: num(avgPredicted, 2, " GW"), hint: "Consommation moyenne prédite" }]}
                        />
                    )}

                    {kpis && buildGroups(kpis).map(g => <KpiGroup key={g.title} title={g.title} items={g.items} />)}

                    {/* Courbe prédiction vs réel */}
                    <GlassCard className="p-6">
                        <h3 className="mb-1 text-lg font-semibold text-[var(--text-1)]">Comparaison des prédictions sur une semaine</h3>
                        <p className="mb-6 text-sm text-[var(--text-2)]">Puissance en GW, pas horaire</p>
                        <LazyMount height={380}>
                            <ResponsiveContainer width="100%" height={380}>
                                <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#172640" />
                                    <XAxis dataKey="label" ticks={tickIndices} tick={AXIS_TICK} axisLine={false} tickLine={false} />
                                    <YAxis tickFormatter={v => v.toFixed(1)} tick={AXIS_TICK} axisLine={false} tickLine={false} unit=" GW" />
                                    <Tooltip
                                        formatter={(value, name) => [
                                            typeof value === "number" ? `${value.toFixed(2)} GW` : "—",
                                            name === "predicted" ? "Prédiction modèle ML" : "Données réelles (base RTE)",
                                        ]}
                                        contentStyle={TOOLTIP_STYLE}
                                        labelStyle={{ color: "#8a9bb8" }}
                                    />
                                    <Legend
                                        formatter={name => name === "predicted" ? "Prédiction modèle ML" : "Données réelles (base RTE)"}
                                        wrapperStyle={{ fontSize: "13px", color: "#8a9bb8" }}
                                    />
                                    {/* Animation interne de Recharts coupée : elle re-rend le graphique image par image (coût CPU élevé sur mobile) */}
                                    <Line type="monotone" dataKey="predicted" stroke={PREDICTED} strokeWidth={2} dot={false} name="predicted" isAnimationActive={false} />
                                    {rteAvailable && (
                                        <Line
                                            type="monotone" dataKey="real" stroke={REAL} strokeWidth={2}
                                            dot={false} connectNulls={false} name="real" isAnimationActive={false}
                                        />
                                    )}
                                </LineChart>
                            </ResponsiveContainer>
                        </LazyMount>
                    </GlassCard>

                </>
            )}
        </div>
    )
}
