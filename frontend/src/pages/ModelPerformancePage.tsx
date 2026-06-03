import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
    ResponsiveContainer, LineChart, Line, XAxis, YAxis,
    CartesianGrid, Tooltip, Legend,
} from "recharts"
import { fetchWeekWeather, batchPredict, fetchRTEWeek } from "../services/api"
import { useAuth } from "../context/AuthContext"
import { REGIONS } from "../types/api"
import type { RegionWeather } from "../types/api"

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

interface Metrics {
    avgPredicted: number
    avgReal: number | null
    mape: number | null
}

const DEFAULT_W: RegionWeather = { temperature: 10, wind_speed: 20, humidity: 70 }

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

const fmt = (v: number) => new Intl.NumberFormat("fr-FR").format(Math.round(v))

export default function ModelPerformancePage() {
    const [step, setStep] = useState("")
    const [status, setStatus] = useState<"loading" | "done" | "error">("loading")
    const [chartData, setChartData] = useState<ChartPoint[]>([])
    const [metrics, setMetrics] = useState<Metrics | null>(null)
    const [rteAvailable, setRteAvailable] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const { token, logout } = useAuth()
    const navigate = useNavigate()

    useEffect(() => { runTest() }, [])

    const runTest = async () => {
        if (!token) return
        setStatus("loading")
        setError(null)

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
            try {
                rteMap = await fetchRTEWeek(token)
            } catch {
                setRteAvailable(false)
            }

            const data: ChartPoint[] = hours.map(h => ({
                label: h.label,
                predicted: Math.round(predMap[h.isoKey] ?? 0),
                real: rteMap[h.isoKey] != null ? rteMap[h.isoKey] / 1000 : null,
            }))

            setChartData(data)

            const predicted = data.map(d => d.predicted)
            const avgPredicted = predicted.reduce((a, b) => a + b, 0) / predicted.length

            const realValues = data.map(d => d.real).filter(v => v !== null) as number[]
            const avgReal = realValues.length > 0
                ? realValues.reduce((a, b) => a + b, 0) / realValues.length
                : null

            const mape = realValues.length > 0
                ? data
                    .filter(d => d.real !== null)
                    .reduce((sum, d) => sum + Math.abs((d.predicted - d.real!) / d.real!) * 100, 0)
                    / realValues.length
                : null

            setMetrics({ avgPredicted, avgReal, mape })
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

    const tickIndices = chartData.reduce((acc, _, i) => {
        if (i % 24 === 0) acc.push(chartData[i]?.label)
        return acc
    }, [] as string[])

    return (
        <div className="min-h-screen bg-gray-50">
            <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-40">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => navigate("/predict")}
                            className="text-gray-400 hover:text-gray-700 transition-colors text-sm"
                        >
                            ← Retour
                        </button>
                        <div className="flex items-center gap-2">
                            <span className="text-xl">⚡</span>
                            <span className="font-bold text-gray-900">RTE Predictor</span>
                        </div>
                    </div>
                    <span className="text-sm text-gray-500 font-medium">Robustesse du modèle</span>
                </div>
            </nav>

            <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">

                {status === "loading" && (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
                        <div className="animate-spin text-4xl mb-4">⚡</div>
                        <p className="text-gray-500 text-sm">{step}</p>
                        <p className="text-gray-400 text-xs mt-2">Analyse sur 7 jours — quelques secondes...</p>
                    </div>
                )}

                {status === "error" && (
                    <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-8 text-center">
                        <p className="font-medium">Erreur lors de l'analyse</p>
                        <p className="text-sm mt-1">{error}</p>
                        <button
                            onClick={runTest}
                            className="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700 transition-colors"
                        >
                            Réessayer
                        </button>
                    </div>
                )}

                {status === "done" && metrics && (
                    <>
                        {/* Métriques */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Moy. prédiction ML</p>
                                <p className="text-2xl font-bold text-blue-600">{fmt(metrics.avgPredicted)} GW</p>
                            </div>
                            <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center ${!rteAvailable ? "opacity-40" : ""}`}>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Moy. consommation RTE</p>
                                <p className="text-2xl font-bold text-red-500">
                                    {metrics.avgReal ? fmt(metrics.avgReal) + " GW" : "Indisponible"}
                                </p>
                            </div>
                            <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center ${!rteAvailable ? "opacity-40" : ""}`}>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Écart moyen (MAPE)</p>
                                <p className={`text-2xl font-bold ${metrics.mape != null && metrics.mape < 10 ? "text-green-600" : "text-yellow-600"}`}>
                                    {metrics.mape != null ? metrics.mape.toFixed(1) + " %" : "Indisponible"}
                                </p>
                            </div>
                        </div>

                        {!rteAvailable && (
                            <div className="bg-yellow-50 border border-yellow-100 text-yellow-700 text-sm rounded-xl px-4 py-3">
                                ⚠ Données RTE indisponibles — seule la courbe ML est affichée.
                            </div>
                        )}

                        {/* Graphique */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-1">
                                Prédiction vs Consommation réelle — 7 derniers jours
                            </h2>
                            <p className="text-sm text-gray-400 mb-6">Puissance en GW, pas horaire</p>
                            <ResponsiveContainer width="100%" height={380}>
                                <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis
                                        dataKey="label"
                                        ticks={tickIndices}
                                        tick={{ fontSize: 12, fill: "#9ca3af" }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        tickFormatter={v => v.toFixed(1)}
                                        tick={{ fontSize: 12, fill: "#9ca3af" }}
                                        axisLine={false}
                                        tickLine={false}
                                        unit=" GW"
                                    />
                                    <Tooltip
                                        formatter={(value, name) => [
                                            typeof value === "number" ? `${value.toFixed(2)} GW` : "—",
                                            name === "predicted" ? "Prédiction ML" : "Réel RTE",
                                        ]}
                                        contentStyle={{ borderRadius: "12px", border: "1px solid #e5e7eb", fontSize: "13px" }}
                                    />
                                    <Legend
                                        formatter={name => name === "predicted" ? "Prédiction ML" : "Réel RTE"}
                                        wrapperStyle={{ fontSize: "13px" }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="predicted"
                                        stroke="#2563eb"
                                        strokeWidth={2}
                                        dot={false}
                                        name="predicted"
                                    />
                                    {rteAvailable && (
                                        <Line
                                            type="monotone"
                                            dataKey="real"
                                            stroke="#dc2626"
                                            strokeWidth={2}
                                            strokeDasharray="5 4"
                                            dot={false}
                                            connectNulls={false}
                                            name="real"
                                        />
                                    )}
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </>
                )}
            </main>
        </div>
    )
}
