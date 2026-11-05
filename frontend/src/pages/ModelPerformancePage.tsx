import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
    ResponsiveContainer, LineChart, Line, XAxis, YAxis,
    CartesianGrid, Tooltip, Legend, BarChart, Bar, ScatterChart, Scatter, ReferenceLine,
} from "recharts"
import { fetchWeekWeather, batchPredict, fetchRTEWeek, fetchKpis } from "../services/api"
import { useAuth } from "../context/AuthContext"
import Navbar from "../components/Navbar"
import { REGIONS } from "../types/api"
import type { RegionWeather, KpiReport, KpiPoint, SegmentKpi } from "../types/api"

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

const AXIS_TICK = { fontSize: 12, fill: "#8a9bb8" }
const TOOLTIP_STYLE = {
    background: "#0a1322",
    borderRadius: "10px",
    border: "1px solid #1ea0ff55",
    fontSize: "13px",
    color: "#e8eef8",
}

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
            label: `${dt.toLocaleDateString("fr-FR", { weekday: "short" })} ${String(h).padStart(2, "0")}h`,
        }
    })
}

// --- Formatage ---------------------------------------------------------------

const nf = (digits: number) => new Intl.NumberFormat("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits })

const num = (v: number | null, digits = 2, unit = "") => (v == null ? "—" : `${nf(digits).format(v)}${unit}`)
const pct = (v: number | null, digits = 1) => num(v, digits, " %")
const signed = (v: number | null, digits = 2, unit = "") =>
    v == null ? "—" : `${v > 0 ? "+" : ""}${nf(digits).format(v)}${unit}`

// --- Composants d'affichage --------------------------------------------------

type Tone = "default" | "good" | "warn"

interface KpiItem {
    label: string
    value: string
    hint: string
    tone?: Tone
}

const TONE_CLASS: Record<Tone, string> = {
    default: "text-ink",
    good: "text-emerald-400",
    warn: "text-amber-400",
}

function KpiCard({ label, value, hint, tone = "default" }: KpiItem) {
    return (
        <div className="rounded-xl border border-line bg-surface p-5 shadow-card">
            <p className="text-xs font-medium uppercase tracking-widest text-muted">{label}</p>
            <p className={`mt-1.5 text-2xl font-semibold tabular-nums ${TONE_CLASS[tone]}`}>{value}</p>
            <p className="mt-1.5 text-xs leading-snug text-faint">{hint}</p>
        </div>
    )
}

function KpiGroup({ title, items }: { title: string; items: KpiItem[] }) {
    return (
        <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-neon-soft">{title}</h2>
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
        {
            title: "Biais et dispersion",
            items: [
                {
                    label: "Biais moyen", value: signed(k.bias, 2, " GW"),
                    hint: k.bias > 0 ? "Le modèle surestime en moyenne" : k.bias < 0 ? "Le modèle sous-estime en moyenne" : "Aucun biais moyen",
                },
                { label: "Erreur médiane", value: num(k.median_ae, 2, " GW"), hint: "La moitié des heures a une erreur inférieure" },
                { label: "Erreur P95", value: num(k.p95_ae, 2, " GW"), hint: "95 % des heures ont une erreur inférieure" },
                { label: "Pire erreur", value: num(k.max_ae, 2, " GW"), hint: "Plus grand écart observé sur la période" },
            ],
        },
        {
            title: "Fiabilité",
            items: [
                { label: "Heures à ±5 %", value: pct(k.within_5_pct, 0), hint: "Part des heures avec une erreur relative d'au plus 5 %" },
                { label: "Heures à ±10 %", value: pct(k.within_10_pct, 0), hint: "Part des heures avec une erreur relative d'au plus 10 %" },
                { label: "R²", value: num(k.r2, 3), hint: "Part de la variation réelle expliquée (1 = parfait)" },
                {
                    label: "MASE", value: num(k.mase, 2),
                    hint: k.mase == null
                        ? "Indisponible : il faut au moins 24 h d'historique"
                        : k.mase < 1 ? "Meilleur qu'une prévision naïve (même heure la veille)" : "Moins bon qu'une prévision naïve (même heure la veille)",
                    tone: k.mase == null ? "default" : k.mase < 1 ? "good" : "warn",
                },
            ],
        },
        {
            title: "Pointe journalière",
            items: [
                { label: "Erreur sur le pic", value: num(k.peak_mae, 2, " GW"), hint: "Écart absolu moyen sur la valeur maximale du jour" },
                { label: "Biais sur le pic", value: signed(k.peak_bias, 2, " GW"), hint: "Positif : le pic est surestimé en moyenne" },
                { label: "Décalage de l'heure du pic", value: num(k.peak_hour_mae, 1, " h"), hint: "Écart moyen entre l'heure du pic prédit et réel" },
                { label: "Jours analysés", value: String(k.peak_days), hint: "Journées complètes utilisées pour la pointe" },
            ],
        },
    ]
}

function SegmentTable({ title, rows }: { title: string; rows: SegmentKpi[] }) {
    return (
        <div className="rounded-xl border border-line bg-surface p-6 shadow-card">
            <h2 className="mb-4 text-lg font-semibold text-ink">{title}</h2>
            <div className="overflow-x-auto">
                <table className="w-full text-sm tabular-nums">
                    <thead>
                        <tr className="border-b border-line text-left text-xs uppercase tracking-widest text-muted">
                            <th className="py-2 pr-4 font-medium">Période</th>
                            <th className="py-2 pr-4 text-right font-medium">Heures</th>
                            <th className="py-2 pr-4 text-right font-medium">MAE</th>
                            <th className="py-2 pr-4 text-right font-medium">MAPE</th>
                            <th className="py-2 text-right font-medium">Biais</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map(r => (
                            <tr key={r.key} className="border-b border-line/60 last:border-0">
                                <td className="py-2 pr-4 text-ink">{r.key}</td>
                                <td className="py-2 pr-4 text-right text-muted">{r.n}</td>
                                <td className="py-2 pr-4 text-right text-ink">{num(r.mae, 2, " GW")}</td>
                                <td className="py-2 pr-4 text-right text-ink">{pct(r.mape)}</td>
                                <td className="py-2 text-right text-ink">{signed(r.bias, 2, " GW")}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// --- Page --------------------------------------------------------------------

export default function ModelPerformancePage() {
    const [step, setStep] = useState("")
    const [status, setStatus] = useState<"loading" | "done" | "error">("loading")
    const [chartData, setChartData] = useState<ChartPoint[]>([])
    const [kpis, setKpis] = useState<KpiReport | null>(null)
    const [avgPredicted, setAvgPredicted] = useState<number | null>(null)
    const [rteAvailable, setRteAvailable] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const { token, logout } = useAuth()
    const navigate = useNavigate()

    const runTest = async () => {
        if (!token) return
        setStatus("loading")
        setError(null)
        setRteAvailable(true)
        setKpis(null)

        try {
            const hours = generateHours()

            setStep("Météo historique (13 régions × 7 jours)...")
            const weatherMaps = await fetchWeekWeather()

            const batchItems = hours.map(h => ({
                date: h.apiDate,
                hour: h.hour,
                temperatures: Object.fromEntries(REGIONS.map(r => [r, (weatherMaps[r]?.[h.isoKey] ?? DEFAULT_W).temperature])),
                wind_speeds: Object.fromEntries(REGIONS.map(r => [r, (weatherMaps[r]?.[h.isoKey] ?? DEFAULT_W).wind_speed])),
                humidities: Object.fromEntries(REGIONS.map(r => [r, (weatherMaps[r]?.[h.isoKey] ?? DEFAULT_W).humidity])),
            }))

            setStep("168 prédictions ML en cours...")
            const predictions = await batchPredict(batchItems, token)
            const predMap: Record<string, number> = {}
            hours.forEach((h, i) => { predMap[h.isoKey] = predictions[i]?.power ?? 0 })

            setStep("Données RTE (7 jours)...")
            let rteMap: Record<string, number> = {}
            let rteOk = true
            try {
                rteMap = await fetchRTEWeek(token)
            } catch {
                rteOk = false
                setRteAvailable(false)
            }

            // Les prédictions ne sont PAS arrondies : un arrondi au GW fausserait les KPI d'erreur.
            const data: ChartPoint[] = hours.map(h => ({
                label: h.label,
                predicted: predMap[h.isoKey] ?? 0,
                real: rteMap[h.isoKey] != null ? rteMap[h.isoKey] / 1000 : null,
            }))
            setChartData(data)
            setAvgPredicted(data.reduce((a, d) => a + d.predicted, 0) / data.length)

            const points: KpiPoint[] = hours.flatMap((h, i) =>
                data[i].real != null
                    ? [{ datetime: h.isoKey, predicted: data[i].predicted, actual: data[i].real as number }]
                    : []
            )

            if (rteOk && points.length > 0) {
                setStep("Calcul des KPI...")
                setKpis(await fetchKpis(points, token))
            }
            setStatus("done")
        } catch (err: unknown) {
            if (err instanceof Error && err.message.includes("401")) {
                logout(); navigate("/login")
            } else {
                setError(err instanceof Error ? err.message : "Erreur inconnue")
                setStatus("error")
            }
        }
    }

    // Lance l'analyse une seule fois, à l'ouverture de la page
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { runTest() }, [])

    const tickIndices = chartData.reduce((acc, _, i) => {
        if (i % 24 === 0) acc.push(chartData[i]?.label)
        return acc
    }, [] as string[])

    const scatterData = chartData
        .filter(d => d.real != null)
        .map(d => ({ real: d.real as number, predicted: d.predicted }))
    const scatterValues = scatterData.flatMap(d => [d.real, d.predicted])
    const scatterMin = scatterValues.length ? Math.floor(Math.min(...scatterValues)) : 0
    const scatterMax = scatterValues.length ? Math.ceil(Math.max(...scatterValues)) : 1

    const hourData = (kpis?.by_hour ?? []).map(s => ({ hour: `${s.key}h`, mae: s.mae, bias: s.bias }))

    const cardClass = "rounded-xl border border-line bg-surface shadow-card"

    return (
        <div className="min-h-screen">
            <Navbar
                maxWidth="5xl"
                onBack={() => navigate("/predict")}
                right={<span className="font-medium">Robustesse du modèle</span>}
            />

            <main className="mx-auto max-w-5xl space-y-8 px-6 py-8">

                {status === "loading" && (
                    <div className={`${cardClass} p-12 text-center`}>
                        <div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-2 border-line border-t-neon" />
                        <p className="text-sm text-ink">{step}</p>
                        <p className="mt-2 text-xs text-faint">Analyse sur 7 jours — quelques secondes...</p>
                    </div>
                )}

                {status === "error" && (
                    <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-8 text-center text-red-300">
                        <p className="font-medium">Erreur lors de l'analyse</p>
                        <p className="mt-1 text-sm">{error}</p>
                        <button
                            onClick={runTest}
                            className="mt-4 rounded-lg border border-red-400/50 px-4 py-2 text-sm text-red-200 transition-colors hover:bg-red-500/20"
                        >
                            Réessayer
                        </button>
                    </div>
                )}

                {status === "done" && (
                    <>
                        {!rteAvailable && (
                            <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
                                Données RTE indisponibles — seule la courbe ML est affichée, les KPI ne peuvent pas être calculés.
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
                        <div className={`${cardClass} p-6`}>
                            <h2 className="mb-1 text-lg font-semibold text-ink">
                                Prédiction vs Consommation réelle — 7 derniers jours
                            </h2>
                            <p className="mb-6 text-sm text-faint">Puissance en GW, pas horaire</p>
                            <ResponsiveContainer width="100%" height={380}>
                                <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#172640" />
                                    <XAxis dataKey="label" ticks={tickIndices} tick={AXIS_TICK} axisLine={false} tickLine={false} />
                                    <YAxis tickFormatter={v => v.toFixed(1)} tick={AXIS_TICK} axisLine={false} tickLine={false} unit=" GW" />
                                    <Tooltip
                                        formatter={(value, name) => [
                                            typeof value === "number" ? `${value.toFixed(2)} GW` : "—",
                                            name === "predicted" ? "Prédiction ML" : "Réel RTE",
                                        ]}
                                        contentStyle={TOOLTIP_STYLE}
                                        labelStyle={{ color: "#8a9bb8" }}
                                    />
                                    <Legend
                                        formatter={name => name === "predicted" ? "Prédiction ML" : "Réel RTE"}
                                        wrapperStyle={{ fontSize: "13px", color: "#8a9bb8" }}
                                    />
                                    <Line type="monotone" dataKey="predicted" stroke="#1ea0ff" strokeWidth={2} dot={false} name="predicted" />
                                    {rteAvailable && (
                                        <Line
                                            type="monotone" dataKey="real" stroke="#ffb454" strokeWidth={2}
                                            strokeDasharray="5 4" dot={false} connectNulls={false} name="real"
                                        />
                                    )}
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {kpis && (
                            <>
                                {/* Erreur par heure du jour */}
                                <div className={`${cardClass} p-6`}>
                                    <h2 className="mb-1 text-lg font-semibold text-ink">Erreur selon l'heure de la journée</h2>
                                    <p className="mb-6 text-sm text-faint">
                                        MAE et biais moyen par heure : repère les moments où le modèle se trompe le plus
                                    </p>
                                    <ResponsiveContainer width="100%" height={300}>
                                        <BarChart data={hourData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#172640" vertical={false} />
                                            <XAxis dataKey="hour" tick={AXIS_TICK} axisLine={false} tickLine={false} interval={1} />
                                            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} unit=" GW" />
                                            <ReferenceLine y={0} stroke="#5b6c8a" />
                                            <Tooltip
                                                formatter={(value, name) => [
                                                    typeof value === "number" ? `${value.toFixed(2)} GW` : "—",
                                                    name === "mae" ? "MAE" : "Biais",
                                                ]}
                                                contentStyle={TOOLTIP_STYLE}
                                                labelStyle={{ color: "#8a9bb8" }}
                                                cursor={{ fill: "#1ea0ff10" }}
                                            />
                                            <Legend
                                                formatter={name => name === "mae" ? "MAE" : "Biais"}
                                                wrapperStyle={{ fontSize: "13px", color: "#8a9bb8" }}
                                            />
                                            <Bar dataKey="mae" name="mae" fill="#1ea0ff" radius={[3, 3, 0, 0]} />
                                            <Bar dataKey="bias" name="bias" fill="#ffb454" radius={[3, 3, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Prédit contre réel */}
                                <div className={`${cardClass} p-6`}>
                                    <h2 className="mb-1 text-lg font-semibold text-ink">Prédit contre réel</h2>
                                    <p className="mb-6 text-sm text-faint">
                                        Un point par heure. Plus il est proche de la diagonale, meilleure est la prédiction.
                                    </p>
                                    <ResponsiveContainer width="100%" height={340}>
                                        <ScatterChart margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#172640" />
                                            <XAxis
                                                type="number" dataKey="real" name="Réel" unit=" GW"
                                                domain={[scatterMin, scatterMax]} tick={AXIS_TICK} axisLine={false} tickLine={false}
                                            />
                                            <YAxis
                                                type="number" dataKey="predicted" name="Prédit" unit=" GW"
                                                domain={[scatterMin, scatterMax]} tick={AXIS_TICK} axisLine={false} tickLine={false}
                                            />
                                            <ReferenceLine
                                                segment={[{ x: scatterMin, y: scatterMin }, { x: scatterMax, y: scatterMax }]}
                                                stroke="#5b6c8a" strokeDasharray="5 4"
                                            />
                                            <Tooltip
                                                formatter={value => typeof value === "number" ? `${value.toFixed(2)} GW` : "—"}
                                                contentStyle={TOOLTIP_STYLE}
                                                cursor={{ strokeDasharray: "3 3", stroke: "#1ea0ff55" }}
                                            />
                                            <Scatter data={scatterData} fill="#1ea0ff" fillOpacity={0.55} />
                                        </ScatterChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Détail par période */}
                                <SegmentTable
                                    title="Semaine et week-end"
                                    rows={[kpis.weekday, kpis.weekend].filter((s): s is SegmentKpi => s != null)}
                                />
                                <SegmentTable title="Détail par jour" rows={kpis.by_day} />
                            </>
                        )}
                    </>
                )}
            </main>
        </div>
    )
}
