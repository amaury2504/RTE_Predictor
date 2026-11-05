import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { predict, fetchCurrentWeather, fetchRTENow } from "../services/api"
import { useAuth } from "../context/AuthContext"
import ResultBanner from "../components/ResultBanner"
import Navbar from "../components/Navbar"
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
            <span className="w-32 shrink-0 text-sm text-muted">{label}</span>
            <input
                type="range" min={min} max={max} value={value}
                onChange={e => onChange(Number(e.target.value))}
                className="flex-1"
            />
            <span className="w-20 shrink-0 text-right text-sm font-medium text-ink tabular-nums">
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

    const cardClass = "rounded-xl border border-line bg-surface shadow-card"

    return (
        <div className={`min-h-screen ${result ? "pb-28" : ""}`}>
            <Navbar
                right={
                    <button onClick={handleLogout} className="transition-colors hover:text-ink">
                        Déconnexion
                    </button>
                }
            />

            <main className="mx-auto max-w-4xl space-y-6 px-6 py-8">

                {/* Bouton "Maintenant" */}
                <div className="rounded-xl border border-neon/30 bg-gradient-to-r from-neon/10 to-transparent p-6 shadow-card">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                        <div>
                            <h2 className="text-base font-semibold text-ink">Prédiction en temps réel</h2>
                            <p className="mt-0.5 text-sm text-muted">
                                Météo actuelle auto-remplie · Comparaison avec la consommation RTE
                            </p>
                        </div>
                        <button
                            onClick={handleNow}
                            disabled={isAnyLoading}
                            className="whitespace-nowrap rounded-lg bg-neon px-6 py-2.5 text-sm font-semibold text-canvas shadow-glow transition-colors hover:bg-neon-soft disabled:opacity-40 disabled:shadow-none"
                        >
                            {loadingNow ? loadingStep || "Chargement..." : "Prédire maintenant"}
                        </button>
                    </div>
                </div>

                {/* Date et heure */}
                <div className={`${cardClass} p-6`}>
                    <h2 className="mb-4 text-lg font-semibold text-ink">Date et heure</h2>
                    <div className="flex flex-col gap-4 sm:flex-row">
                        <div className="flex-1">
                            <label className="mb-1.5 block text-sm text-muted">Date</label>
                            <input
                                type="date" value={date}
                                onChange={e => setDate(e.target.value)}
                                className="w-full rounded-lg border border-line bg-raised px-4 py-2.5 text-sm text-ink transition-colors focus:border-neon focus:outline-none focus:ring-1 focus:ring-neon"
                            />
                        </div>
                        <div className="flex-1">
                            <label className="mb-1.5 block text-sm text-muted">
                                Heure — <span className="text-ink tabular-nums">{String(hour).padStart(2, "0")}h00</span>
                            </label>
                            <input
                                type="range" min={0} max={23} value={hour}
                                onChange={e => setHour(Number(e.target.value))}
                                className="mt-2 w-full"
                            />
                        </div>
                    </div>
                </div>

                {/* Accordéon régions */}
                <div className={`${cardClass} overflow-hidden`}>
                    <div className="border-b border-line px-6 py-4">
                        <h2 className="text-lg font-semibold text-ink">Météo par région</h2>
                        <p className="mt-0.5 text-sm text-faint">Cliquez sur une région pour ajuster ses paramètres</p>
                    </div>
                    <div className="divide-y divide-line">
                        {REGIONS.map(region => {
                            const isOpen = openRegion === region
                            const w = weather[region]
                            return (
                                <div key={region}>
                                    <button
                                        onClick={() => setOpenRegion(isOpen ? null : region)}
                                        className="flex w-full items-center justify-between px-6 py-4 text-left transition-colors hover:bg-raised"
                                    >
                                        <span className="text-sm font-medium text-ink">{region}</span>
                                        <div className="flex items-center gap-4 text-xs text-muted tabular-nums">
                                            <span>{w.temperature}°C</span>
                                            <span>{w.wind_speed} km/h</span>
                                            <span>{w.humidity}%</span>
                                            <svg
                                                width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"
                                                className={`text-faint transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                                            >
                                                <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        </div>
                                    </button>
                                    {isOpen && (
                                        <div className="space-y-4 border-t border-line bg-canvas/50 px-6 pb-5 pt-4">
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
                    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                        {error}
                    </div>
                )}

                <button
                    onClick={() => navigate("/performance")}
                    disabled={isAnyLoading}
                    className="w-full rounded-lg border border-line bg-surface py-3 text-sm font-semibold text-ink transition-colors hover:border-neon/50 hover:text-neon-soft disabled:opacity-50"
                >
                    Robustesse du modèle sur 7 jours
                </button>

                <button
                    onClick={() => navigate("/benchmark")}
                    disabled={isAnyLoading}
                    className="w-full rounded-lg border border-line bg-surface py-3 text-sm font-semibold text-ink transition-colors hover:border-neon/50 hover:text-neon-soft disabled:opacity-50"
                >
                    Comparaison des modèles
                </button>

                <button
                    onClick={handlePredict}
                    disabled={isAnyLoading}
                    className="w-full rounded-lg border border-neon/50 bg-transparent py-3 text-sm font-semibold text-neon-soft transition-colors hover:bg-neon/10 disabled:opacity-40"
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
