import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { predict, fetchCurrentWeather, fetchRTENow } from "../services/api"
import { useAuth } from "../context/AuthContext"
import ResultBanner from "../components/ResultBanner"
import { REGIONS } from "../types/api"
import type { RegionWeather, PredictionResponse } from "../types/api"

function buildDefaultWeather(): Record<string, RegionWeather> {
    return Object.fromEntries(REGIONS.map(r => [r, { temperature: 10, wind_speed: 20, humidity: 70 }]))
}

function SliderField({
    label, unit, min, max, value, onChange,
}: {
    label: string; unit: string; min: number; max: number; value: number; onChange: (v: number) => void
}) {
    return (
        <div className="flex items-center gap-4">
            <span className="w-32 text-sm text-gray-600 shrink-0">{label}</span>
            <input
                type="range" min={min} max={max} value={value}
                onChange={e => onChange(Number(e.target.value))}
                className="flex-1 accent-blue-600"
            />
            <span className="w-20 text-sm font-medium text-gray-800 text-right shrink-0">
                {value} {unit}
            </span>
        </div>
    )
}

function toApiDate(isoDate: string): string {
    const [y, m, d] = isoDate.split("-")
    return `${d}/${m}/${y}`
}

export default function PredictionPage() {
    const today = new Date().toISOString().split("T")[0]
    const [date, setDate] = useState(today)
    const [hour, setHour] = useState(12)
    const [weather, setWeather] = useState<Record<string, RegionWeather>>(buildDefaultWeather)
    const [openRegion, setOpenRegion] = useState<string | null>(null)
    const [result, setResult] = useState<PredictionResponse | null>(null)
    const [rteConsumptionMW, setRteConsumptionMW] = useState<number | null>(null)
    const [loading, setLoading] = useState(false)
    const [loadingNow, setLoadingNow] = useState(false)
    const [loadingStep, setLoadingStep] = useState("")
    const [error, setError] = useState<string | null>(null)

    const { token, logout } = useAuth()
    const navigate = useNavigate()

    const updateWeather = (region: string, field: keyof RegionWeather, value: number) => {
        setWeather(prev => ({ ...prev, [region]: { ...prev[region], [field]: value } }))
    }

    const handlePredict = async () => {
        if (!token) return
        setError(null)
        setLoading(true)
        try {
            const payload = {
                date: toApiDate(date),
                hour,
                temperatures: Object.fromEntries(REGIONS.map(r => [r, weather[r].temperature])),
                wind_speeds: Object.fromEntries(REGIONS.map(r => [r, weather[r].wind_speed])),
                humidities: Object.fromEntries(REGIONS.map(r => [r, weather[r].humidity])),
            }
            const res = await predict(payload, token)
            setResult(res)
        } catch (err: unknown) {
            if (err instanceof Error && err.message.includes("401")) {
                logout(); navigate("/login")
            } else {
                setError(err instanceof Error ? err.message : "Erreur inconnue")
            }
        } finally {
            setLoading(false)
        }
    }

    const handleNow = async () => {
        if (!token) return
        setError(null)
        setResult(null)
        setRteConsumptionMW(null)
        setLoadingNow(true)

        try {
            const now = new Date()
            const todayStr = now.toISOString().split("T")[0]
            const roundedHour = now.getMinutes() <= 30
                ? now.getHours()
                : (now.getHours() + 1) % 24

            setDate(todayStr)
            setHour(roundedHour)

            setLoadingStep("Récupération de la météo...")
            const liveWeather = await fetchCurrentWeather()
            setWeather(liveWeather)

            setLoadingStep("Calcul de la prédiction ML...")
            const payload = {
                date: toApiDate(todayStr),
                hour: roundedHour,
                temperatures: Object.fromEntries(REGIONS.map(r => [r, liveWeather[r].temperature])),
                wind_speeds: Object.fromEntries(REGIONS.map(r => [r, liveWeather[r].wind_speed])),
                humidities: Object.fromEntries(REGIONS.map(r => [r, liveWeather[r].humidity])),
            }
            const res = await predict(payload, token)
            setResult(res)

            setLoadingStep("Consommation réelle RTE...")
            try {
                const rte = await fetchRTENow(toApiDate(todayStr), roundedHour, token)
                setRteConsumptionMW(rte)
            } catch {
                // RTE optionnel — ne bloque pas le résultat
            }

        } catch (err: unknown) {
            if (err instanceof Error && err.message.includes("401")) {
                logout(); navigate("/login")
            } else {
                setError(err instanceof Error ? err.message : "Erreur inconnue")
            }
        } finally {
            setLoadingNow(false)
            setLoadingStep("")
        }
    }

    const handleLogout = () => { logout(); navigate("/login") }
    const isAnyLoading = loading || loadingNow

    return (
        <div className={`min-h-screen bg-gray-50 ${result ? "pb-28" : ""}`}>
            <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-40">
                <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-xl">⚡</span>
                        <span className="font-bold text-gray-900">RTE Predictor</span>
                    </div>
                    <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-800 transition-colors">
                        Déconnexion
                    </button>
                </div>
            </nav>

            <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">

                {/* Bouton "Maintenant" */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl p-6">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        <div>
                            <h2 className="text-base font-semibold text-gray-900">Prédiction en temps réel</h2>
                            <p className="text-sm text-gray-500 mt-0.5">
                                Météo actuelle auto-remplie · Comparaison avec la consommation RTE
                            </p>
                        </div>
                        <button
                            onClick={handleNow}
                            disabled={isAnyLoading}
                            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors text-sm shadow-sm whitespace-nowrap"
                        >
                            {loadingNow ? loadingStep || "Chargement..." : "⚡ Prédire maintenant"}
                        </button>
                    </div>
                </div>

                {/* Date et heure */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Date et heure</h2>
                    <div className="flex flex-col sm:flex-row gap-4">
                        <div className="flex-1">
                            <label className="block text-sm text-gray-600 mb-1">Date</label>
                            <input
                                type="date" value={date}
                                onChange={e => setDate(e.target.value)}
                                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            />
                        </div>
                        <div className="flex-1">
                            <label className="block text-sm text-gray-600 mb-1">
                                Heure — {String(hour).padStart(2, "0")}h00
                            </label>
                            <input
                                type="range" min={0} max={23} value={hour}
                                onChange={e => setHour(Number(e.target.value))}
                                className="w-full mt-2 accent-blue-600"
                            />
                        </div>
                    </div>
                </div>

                {/* Accordéon régions */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Météo par région</h2>
                        <p className="text-sm text-gray-400 mt-0.5">Cliquez sur une région pour ajuster ses paramètres</p>
                    </div>
                    <div className="divide-y divide-gray-50">
                        {REGIONS.map(region => {
                            const isOpen = openRegion === region
                            const w = weather[region]
                            return (
                                <div key={region}>
                                    <button
                                        onClick={() => setOpenRegion(isOpen ? null : region)}
                                        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors text-left"
                                    >
                                        <span className="text-gray-800 font-medium text-sm">{region}</span>
                                        <div className="flex items-center gap-4 text-xs text-gray-400">
                                            <span>{w.temperature}°C</span>
                                            <span>{w.wind_speed} km/h</span>
                                            <span>{w.humidity}%</span>
                                            <span className={`transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}>▼</span>
                                        </div>
                                    </button>
                                    {isOpen && (
                                        <div className="px-6 pb-5 pt-1 space-y-4 bg-gray-50 border-t border-gray-100">
                                            <SliderField label="Température" unit="°C" min={-20} max={45}
                                                value={w.temperature} onChange={v => updateWeather(region, "temperature", v)} />
                                            <SliderField label="Vent" unit="km/h" min={0} max={150}
                                                value={w.wind_speed} onChange={v => updateWeather(region, "wind_speed", v)} />
                                            <SliderField label="Humidité" unit="%" min={0} max={100}
                                                value={w.humidity} onChange={v => updateWeather(region, "humidity", v)} />
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                </div>

                {error && (
                    <div className="bg-red-50 border border-red-100 text-red-600 text-sm rounded-lg px-4 py-3">
                        {error}
                    </div>
                )}

                <button
                    onClick={() => navigate("/performance")}
                    disabled={isAnyLoading}
                    className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 border border-gray-200 text-gray-700 font-semibold py-3 rounded-xl transition-colors text-sm shadow-sm"
                >
                    📊 Robustesse du modèle — 7 jours
                </button>

                <button
                    onClick={handlePredict}
                    disabled={isAnyLoading}
                    className="w-full bg-gray-800 hover:bg-gray-900 disabled:bg-gray-300 text-white font-semibold py-3 rounded-xl transition-colors text-sm shadow-sm"
                >
                    {loading ? "Calcul en cours..." : "Lancer la prédiction manuellement"}
                </button>
            </main>

            {result && (
                <ResultBanner power={result.power} date={result.date} hour={result.hour} rteConsumptionMW={rteConsumptionMW} />
            )}
        </div>
    )
}
