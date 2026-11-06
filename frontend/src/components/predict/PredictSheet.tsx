import { lazy, Suspense, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { animate } from "animejs"
import { predict, fetchCurrentWeather, fetchRTENow } from "../../services/api"
import { useAuth } from "../../context/AuthContext"
import AnimatedNumber from "../data/AnimatedNumber"
import GlassButton from "../glass/GlassButton"
import FranceScan from "../data/FranceScan"
import FranceStack from "../data/FranceStack"
import GlassCard from "../glass/GlassCard"
import { duration, easeOut, SCAN_SWEEP_MS } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { signed } from "../../lib/format"
import type { PredictModel } from "../../lib/predictModels"
import { REGIONS } from "../../types/api"
import type { PredictionResponse } from "../../types/api"

// L'analyse sur 7 jours embarque Recharts : chargée seulement quand on clique sur le bouton
const WeekAnalysis = lazy(() => import("./WeekAnalysis"))

function toApiDate(isoDate: string): string {
    const [y, m, d] = isoDate.split("-")
    return `${d}/${m}/${y}`
}

/** Un chiffre de résultat : étiquette, valeur animée, couleur de la série (prédit en orange, réel en bleu). */
function Figure({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div>
            <p className="flex items-center gap-2 text-sm text-[var(--text-2)]">
                <span className="h-0.5 w-6 rounded" style={{ background: color }} aria-hidden="true" />
                {label}
            </p>
            <p className="mt-1 whitespace-nowrap text-5xl font-semibold tracking-tight text-[var(--text-1)]">
                <AnimatedNumber value={value} unit=" GW" />
            </p>
        </div>
    )
}

/**
 * Une feuille de l'onglet « Prédire », pour un modèle : carte, « Prédire maintenant », analyse sur 7 jours et
 * statistiques. Chaque feuille a son propre état (résultats, analyse en cours) : changer de modèle ne perd rien.
 *
 * Prédiction en temps réel : un seul geste. La météo actuelle est récupérée, le modèle prédit la consommation
 * de l'heure en cours, et on la compare à la consommation réelle publiée par RTE.
 */
export default function PredictSheet({ model }: { model: PredictModel }) {
    const [result, setResult] = useState<PredictionResponse | null>(null)
    const [rteConsumptionMW, setRteConsumptionMW] = useState<number | null>(null)
    const [loading, setLoading] = useState(false)
    const [scanning, setScanning] = useState(false)
    const [loadingStep, setLoadingStep] = useState("")
    const [error, setError] = useState<string | null>(null)
    const resultRef = useRef<HTMLDivElement>(null)
    // Analyse sur 7 jours : le compteur remonte le composant (relance), « busy » bloque les boutons pendant l'exécution
    const [weekRun, setWeekRun] = useState(0)
    const [weekBusy, setWeekBusy] = useState(false)
    // Animation « plusieurs cartes » : montée dès le clic, démontée une fois la scène revenue à plat
    const [stackOn, setStackOn] = useState(false)
    const [weekDone, setWeekDone] = useState(false)
    const reduce = useReducedMotion()

    const { token, logout } = useAuth()
    const navigate = useNavigate()

    // Un modèle pas encore servi par le backend : la feuille est visible, mais les actions sont inactives
    const unavailable = !model.served

    // Le résultat apparaît en fondu, avec un léger glissement
    useAnimeScope(resultRef, () => {
        animate(resultRef.current!, {
            opacity: [0, 1],
            translateY: reduce ? 0 : [12, 0],
            duration: reduce ? duration.fast : duration.slow,
            ease: easeOut,
        })
    }, [result, reduce])

    const handleWeek = () => {
        setError(null)
        setWeekBusy(true)
        setWeekRun(n => n + 1)
        // Mouvement réduit : pas de scène en 3D, la carte simple indique seulement que l'analyse est en cours
        if (!reduce) setStackOn(true)
    }

    const handleNow = async () => {
        if (!token) return
        setError(null)
        setResult(null)
        setRteConsumptionMW(null)
        setLoading(true)
        setScanning(true)
        const startedAt = performance.now()

        try {
            const now = new Date()
            const todayStr = now.toISOString().split("T")[0]
            const roundedHour = now.getMinutes() <= 30 ? now.getHours() : (now.getHours() + 1) % 24

            setLoadingStep("Météo en direct...")
            const liveWeather = await fetchCurrentWeather()

            setLoadingStep("Prédiction...")
            const res = await predict({
                date: toApiDate(todayStr),
                hour: roundedHour,
                temperatures: Object.fromEntries(REGIONS.map(r => [r, liveWeather[r].temperature])),
                wind_speeds: Object.fromEntries(REGIONS.map(r => [r, liveWeather[r].wind_speed])),
                humidities: Object.fromEntries(REGIONS.map(r => [r, liveWeather[r].humidity])),
            }, token, model.id)

            setLoadingStep("Consommation réelle RTE...")
            let rte: number | null = null
            try {
                rte = await fetchRTENow(toApiDate(todayStr), roundedHour, token)
            } catch {
                // La consommation réelle est optionnelle : elle ne bloque pas le résultat
            }

            // Le scanner termine toujours son balayage en cours : le résultat s'affiche à la fin d'un passage complet
            const elapsed = performance.now() - startedAt
            const toNextSweepEnd = elapsed < SCAN_SWEEP_MS ? SCAN_SWEEP_MS - elapsed : SCAN_SWEEP_MS - (elapsed % SCAN_SWEEP_MS)
            await new Promise(resolve => setTimeout(resolve, toNextSweepEnd))
            setResult(res)
            setRteConsumptionMW(rte)
        } catch (err: unknown) {
            if (err instanceof Error && err.message.includes("401")) {
                logout(); navigate("/login")
            } else {
                setError(err instanceof Error ? err.message : "Erreur inconnue")
            }
        } finally {
            setScanning(false)
            setLoading(false)
            setLoadingStep("")
        }
    }

    const predictedGW = result?.power ?? null
    const actualGW = rteConsumptionMW != null ? rteConsumptionMW / 1000 : null
    // Écart relatif au réel, en % (signé : positif = le modèle surestime)
    const gapPct = predictedGW != null && actualGW != null && actualGW !== 0 ? ((predictedGW - actualGW) / actualGW) * 100 : null
    const busy = loading || weekBusy || stackOn || unavailable

    return (
        <div className="space-y-6">
            <GlassCard className="overflow-hidden px-4 py-4">
                {stackOn ? (
                    <FranceStack
                        active={weekBusy}
                        startLit={result != null || weekDone}
                        onExited={() => { setStackOn(false); setWeekDone(true) }}
                    />
                ) : (
                    <FranceScan state={scanning || (reduce && weekBusy) ? "scanning" : result || weekDone ? "done" : "idle"} />
                )}
            </GlassCard>

            {unavailable && (
                <div role="status" className="rounded-xl border border-[var(--glass-border)] bg-white/5 px-4 py-3 text-sm text-[var(--text-1)]">
                    Bientôt disponible : {model.name} n'est pas encore servi par l'API.
                </div>
            )}

            {/* Deux cases de même hauteur : côte à côte, elles occupent ensemble la largeur de la carte */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <GlassCard className="flex h-full flex-col justify-between gap-5 px-6 py-5">
                    <div>
                        <p className="text-lg font-semibold text-[var(--text-1)]">Prédiction sur l'heure en cours</p>
                        <p className="text-sm text-[var(--text-2)]">Modèle : {model.name} ({model.kind.toLowerCase()})</p>
                    </div>
                    <div>
                        <GlassButton primary onClick={handleNow} disabled={busy} className="whitespace-nowrap disabled:opacity-50">
                            {loading ? loadingStep || "Chargement..." : "Prédire maintenant"}
                        </GlassButton>
                    </div>
                </GlassCard>

                <GlassCard className="flex h-full flex-col justify-between gap-5 px-6 py-5">
                    <div>
                        <p className="text-lg font-semibold text-[var(--text-1)]">Performance de la prédiction sur 7 jours</p>
                        <p className="text-sm text-[var(--text-2)]">Modèle : {model.name} ({model.kind.toLowerCase()})</p>
                    </div>
                    <div>
                        <GlassButton primary onClick={handleWeek} disabled={busy} className="whitespace-nowrap disabled:opacity-50">
                            {weekBusy ? "Analyse en cours..." : "Analyser"}
                        </GlassButton>
                    </div>
                </GlassCard>
            </div>

            {error && (
                <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    {error}
                </div>
            )}

            {/* Résultat de « Prédire maintenant » : sous les deux cases, sur toute la largeur */}
            {result && predictedGW != null && (
                <div ref={resultRef} style={{ opacity: 0 }}>
                    <GlassCard className="px-8 py-7">
                        <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-6">
                            <Figure label="Prédit par notre modèle" value={predictedGW} color="var(--series-predicted)" />
                            {actualGW != null && <Figure label="Données réelles (base RTE)" value={actualGW} color="var(--series-real)" />}
                        </div>
                        <div className="mt-5 flex flex-wrap items-center gap-3 text-sm">
                            {gapPct != null && (
                                <span className="whitespace-nowrap rounded-full border border-[var(--glass-border)] bg-white/5 px-3 py-1 text-[var(--text-1)]">
                                    écart {signed(gapPct, 1)} %
                                </span>
                            )}
                            <span className="text-[var(--text-2)]">{result.date} · {String(result.hour).padStart(2, "0")}h00</span>
                        </div>
                    </GlassCard>
                </div>
            )}

            {/* Résultats de l'analyse sur 7 jours : également sous les deux cases, sur toute la largeur */}
            {weekRun > 0 && (
                <Suspense fallback={<GlassCard className="p-10 text-center text-sm text-[var(--text-2)]">Chargement...</GlassCard>}>
                    <WeekAnalysis key={weekRun} modelId={model.id} onBusyChange={setWeekBusy} />
                </Suspense>
            )}
        </div>
    )
}
