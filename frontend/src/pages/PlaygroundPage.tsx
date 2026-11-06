import { useEffect, useRef, useState } from "react"
import { animate, stagger } from "animejs"
import { ShieldCheck, Zap } from "lucide-react"
import AuroraBackground from "../components/background/AuroraBackground"
import AnimatedNumber from "../components/data/AnimatedNumber"
import GlassButton from "../components/glass/GlassButton"
import GlassCard from "../components/glass/GlassCard"
import LogoMark from "../components/LogoMark"
import VariantPreview from "../components/playground/VariantPreview"
import { useAuth } from "../context/AuthContext"
import { bestModel, bestReference, rowOf } from "../benchmark/selectors"
import { loadBenchmark } from "../benchmark/loader"
import { describeModel } from "../lib/benchmarkModels"
import { duration, easeOut, springs, STAGGER_MS } from "../design/motion"
import { useAnimeScope } from "../hooks/useAnimeScope"
import { useReducedMotion } from "../hooks/useReducedMotion"
import { loginAsGuest } from "../services/api"
import type { BenchmarkResults } from "../types/api"

/**
 * Page interne (développement seulement) pour régler chaque brique visuelle isolément, avec les vraies
 * données du benchmark : aucun chiffre n'est écrit ici, tout vient de l'API.
 */
export default function PlaygroundPage() {
    const { token } = useAuth()
    const [results, setResults] = useState<BenchmarkResults | null>(null)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        // Hors connexion, un jeton invité éphémère suffit (lecture seule), sans toucher à la session
        const fetchResults = async () => loadBenchmark(token ?? (await loginAsGuest()))
        fetchResults()
            .then(r => { if (!cancelled) setResults(r) })
            .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Erreur inconnue") })
        return () => { cancelled = true }
    }, [token])

    return (
        <div className="min-h-screen px-6 py-10 text-[var(--text-1)]">
            <AuroraBackground />
            <main className="mx-auto max-w-5xl space-y-12">
                <header className="flex items-center gap-3">
                    <LogoMark />
                    <div>
                        <p className="text-xs font-medium uppercase tracking-widest text-[var(--accent-soft)]">RTE Predictor · playground</p>
                        <h1 className="bg-gradient-to-b from-white to-white/60 bg-clip-text text-3xl font-semibold text-transparent">
                            Fondations du design
                        </h1>
                    </div>
                </header>

                {error && (
                    <p role="alert" className="rounded-xl border border-[var(--state-danger)]/40 bg-[var(--state-danger)]/10 p-4 text-sm">
                        Résultats du benchmark indisponibles : {error}
                    </p>
                )}

                {results && <Content results={results} />}
            </main>
        </div>
    )
}

function Content({ results }: { results: BenchmarkResults }) {
    const best = bestModel(results)
    const reference = bestReference(results)
    const raw = rowOf(results, "lightgbm")
    const kpis = [
        best && { label: "Meilleur modèle", sub: describeModel(best.model).label, value: best.mae },
        reference && { label: "Meilleure référence (RTE)", sub: describeModel(reference.model).label, value: reference.mae },
        raw && { label: "Modèle brut, piste A", sub: describeModel(raw.model).label, value: raw.mae },
    ].flatMap(k => (k && k.value != null ? [{ ...k, value: k.value }] : []))

    return (
        <>
            <section aria-labelledby="pg-cards" className="space-y-4">
                <h2 id="pg-cards" className="text-sm font-semibold uppercase tracking-widest text-[var(--text-3)]">
                    Indicateurs (erreur moyenne en GW, lue dans les résultats)
                </h2>
                <KpiRow kpis={kpis} />
                {best && (
                    <GlassCard className="p-8">
                        <div className="flex items-center gap-4">
                            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-[var(--glass-border)] bg-[var(--glass-bg)]">
                                <ShieldCheck className="text-[var(--state-ok)]" aria-hidden="true" />
                            </span>
                            <div>
                                <p className="text-lg font-semibold">{describeModel(best.model).label}</p>
                                <p className="text-sm text-[var(--text-2)]">
                                    Carte héros, réservée aux moments forts (verdict, accès vérifié).
                                </p>
                            </div>
                        </div>
                    </GlassCard>
                )}
            </section>

            <section aria-labelledby="pg-ab" className="space-y-4">
                <h2 id="pg-ab" className="text-sm font-semibold uppercase tracking-widest text-[var(--text-3)]">
                    Test A/B : couleur de marque
                </h2>
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                    <VariantPreview
                        variant="A"
                        title="Variante A : tout en bleu"
                        description="Le réel est en bleu, le prédit en bleu clair pointillé. Lueur de la sidebar bleue."
                    />
                    <VariantPreview
                        variant="B"
                        title="Variante B : bleu et orange"
                        description="Le réel est en bleu, le prédit en orange pointillé. Lueur de la sidebar orange (CDC)."
                    />
                </div>
            </section>

            <ButtonsSection />
            <SpringSection />
        </>
    )
}

/** Cascade d'apparition (40 ms d'écart) puis compteurs : le motif réutilisé sur toutes les pages. */
function KpiRow({ kpis }: { kpis: { label: string; sub: string; value: number }[] }) {
    const root = useRef<HTMLUListElement>(null)
    const reduce = useReducedMotion()

    useAnimeScope(root, () => {
        animate(".kpi", {
            opacity: [0, 1],
            translateY: reduce ? [0, 0] : [14, 0],
            duration: reduce ? duration.fast : duration.slow,
            ease: easeOut,
            delay: stagger(STAGGER_MS),
        })
    }, [reduce, kpis.length])

    return (
        <ul ref={root} className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            {kpis.map(k => (
                <li key={k.label} className="kpi" style={{ opacity: 0 }}>
                    <GlassCard interactive className="p-6">
                        <p className="text-sm text-[var(--text-2)]">{k.label}</p>
                        <p className="mt-1 text-3xl font-semibold"><AnimatedNumber value={k.value} unit=" GW" /></p>
                        <p className="mt-2 text-sm text-[var(--text-3)]">{k.sub}</p>
                    </GlassCard>
                </li>
            ))}
        </ul>
    )
}

function ButtonsSection() {
    const [count, setCount] = useState(0)
    return (
        <section aria-labelledby="pg-buttons" className="space-y-4">
            <h2 id="pg-buttons" className="text-sm font-semibold uppercase tracking-widest text-[var(--text-3)]">Boutons</h2>
            <div className="flex flex-wrap items-center gap-3">
                <GlassButton primary onClick={() => setCount(c => c + 1)}>
                    <span className="inline-flex items-center gap-2"><Zap size={16} aria-hidden="true" /> Action principale</span>
                </GlassButton>
                <GlassButton onClick={() => setCount(c => c + 1)}>Action secondaire</GlassButton>
                <span className="tabular text-sm text-[var(--text-2)]" aria-live="polite">
                    {count} clic{count > 1 ? "s" : ""}
                </span>
            </div>
        </section>
    )
}

/** Indicateur qui glisse avec le ressort « glide » (même réglage que les onglets et la sidebar). */
function SpringSection() {
    const track = useRef<HTMLDivElement>(null)
    const thumb = useRef<HTMLDivElement>(null)
    const right = useRef(false)
    const reduce = useReducedMotion()

    const toggle = () => {
        if (!track.current || !thumb.current) return
        right.current = !right.current
        const distance = track.current.clientWidth - thumb.current.offsetWidth - 8
        animate(thumb.current, {
            translateX: right.current ? distance : 0,
            // Mouvement réduit : simple déplacement court ; sinon le ressort fixe sa propre durée
            ...(reduce ? { duration: duration.fast, ease: "linear" } : { ease: springs.glide() }),
        })
    }

    return (
        <section aria-labelledby="pg-springs" className="space-y-4">
            <h2 id="pg-springs" className="text-sm font-semibold uppercase tracking-widest text-[var(--text-3)]">Ressort</h2>
            <GlassCard className="p-6">
                <div ref={track} className="h-12 rounded-full border border-[var(--glass-border)] bg-white/5 p-1" aria-hidden="true">
                    <div ref={thumb} className="h-10 w-1/3 rounded-full bg-[var(--accent-deep)] shadow-[0_0_24px_-4px_var(--accent-glow)]" />
                </div>
                <GlassButton className="mt-4" onClick={toggle}>Faire glisser (ressort « glide »)</GlassButton>
            </GlassCard>
        </section>
    )
}
