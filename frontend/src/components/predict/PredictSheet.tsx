import { lazy, Suspense, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { predict, fetchCurrentWeather, fetchRTENow } from "../../services/api"
import { useAuth } from "../../context/AuthContext"
import GlassButton from "../glass/GlassButton"
import FranceScan from "../data/FranceScan"
import FranceStack from "../data/FranceStack"
import GlassCard from "../glass/GlassCard"
import SideResult from "./SideResult"
import type { NowResult } from "./SideResult"
import { SCAN_SWEEP_MS } from "../../design/motion"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import type { PredictModel } from "../../lib/predictModels"
import { REGIONS } from "../../types/api"
import type { PredictionResponse } from "../../types/api"

// L'analyse sur 7 jours embarque Recharts : chargée seulement quand on clique sur le bouton
const WeekAnalysis = lazy(() => import("./WeekAnalysis"))

function toApiDate(isoDate: string): string {
    const [y, m, d] = isoDate.split("-")
    return `${d}/${m}/${y}`
}

/**
 * Une feuille de l'onglet « Prédire », pour un modèle : carte, « Prédire maintenant », analyse sur 7 jours et
 * statistiques. Chaque feuille a son propre état (résultats, analyse en cours) : changer de modèle ne perd rien.
 *
 * Prédiction en temps réel : un seul geste. La météo actuelle est récupérée, le modèle prédit la consommation
 * de l'heure en cours, et on la compare à la consommation réelle publiée par RTE.
 */
export default function PredictSheet({ model, active }: { model: PredictModel; active: boolean }) {
    const [result, setResult] = useState<PredictionResponse | null>(null)
    const [rteConsumptionMW, setRteConsumptionMW] = useState<number | null>(null)
    const [loading, setLoading] = useState(false)
    const [scanning, setScanning] = useState(false)
    const [loadingStep, setLoadingStep] = useState("")
    const [error, setError] = useState<string | null>(null)
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

    const handleWeek = () => {
        setError(null)
        // Un nouveau flux fait disparaître les chiffres affichés autour de la carte
        setResult(null)
        setRteConsumptionMW(null)
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

    // Changer d'onglet (autre modèle) efface aussi les chiffres autour de la carte
    if (!active && result) { setResult(null); setRteConsumptionMW(null) }

    // Mémorisé : la colonne de résultat compare cet objet d'un rendu à l'autre
    const sideData = useMemo<NowResult | null>(
        () => result && predictedGW != null
            ? { predictedGW, actualGW, gapPct, date: result.date, hour: result.hour }
            : null,
        [result, predictedGW, actualGW, gapPct],
    )

    const map = stackOn ? (
        <FranceStack
            active={weekBusy}
            startLit={result != null || weekDone}
            onExited={() => { setStackOn(false); setWeekDone(true) }}
        />
    ) : (
        <FranceScan state={scanning || (reduce && weekBusy) ? "scanning" : result || weekDone ? "done" : "idle"} />
    )

    return (
        <div className="space-y-6">
            <GlassCard className="overflow-hidden px-4 py-4">
                {/* La prédiction (gauche) et la consommation réelle (droite) entourent la carte */}
                <div className="grid grid-cols-2 gap-x-6 gap-y-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,460px)_minmax(0,1fr)] lg:items-center">
                    <div className="col-span-2 lg:col-span-1 lg:col-start-2 lg:row-start-1">{map}</div>
                    <SideResult side="left" data={sideData} className="lg:col-start-1 lg:row-start-1" />
                    <SideResult side="right" data={sideData} className="lg:col-start-3 lg:row-start-1" />
                </div>
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

            {/* Résultats de l'analyse sur 7 jours : également sous les deux cases, sur toute la largeur */}
            {weekRun > 0 && (
                <Suspense fallback={<GlassCard className="p-10 text-center text-sm text-[var(--text-2)]">Chargement...</GlassCard>}>
                    <WeekAnalysis key={weekRun} modelId={model.id} reveal={!stackOn} onBusyChange={setWeekBusy} />
                </Suspense>
            )}
        </div>
    )
}
