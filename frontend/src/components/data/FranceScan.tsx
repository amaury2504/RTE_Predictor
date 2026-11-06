import { useEffect, useId, useRef } from "react"
import { animate } from "animejs"
import { duration, easeOut, SCAN_SWEEP_MS } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { FRANCE_HEIGHT, FRANCE_REGIONS, FRANCE_WIDTH } from "../../lib/franceRegions"

export type ScanState = "idle" | "scanning" | "done"

const PAD = 14
const STATUS_HIDE_MS = 3000 // délai avant que la ligne d'état disparaisse, une fois l'analyse terminée
const TRAIL = 70 // hauteur de la traînée lumineuse au-dessus du faisceau (unités du dessin)

// Palette de la carte : aplat bleu comme les cartes vectorielles de référence, frontières blanches fines
const DIM_FILL = "rgba(57, 135, 229, 0.16)"
const LIT_FILL = "#3987e5"
const BORDER_DIM = "rgba(255, 255, 255, 0.16)"
const BORDER_LIT = "rgba(255, 255, 255, 0.85)"

/**
 * Carte vectorielle de la France : un aplat bleu aux frontières régionales fines (contours IGN). Pendant le calcul,
 * un faisceau orange balaie la carte de haut en bas ; derrière lui le territoire s'allume. La ligne d'état
 * indique la région en cours de lecture. Une fois fini, toute la carte reste allumée.
 * Mouvement réduit : carte fixe, allumée si le calcul est terminé.
 */
export default function FranceScan({ state }: { state: ScanState }) {
    const root = useRef<HTMLDivElement>(null)
    const status = useRef<HTMLDivElement>(null)
    const reduce = useReducedMotion()
    const uid = useId().replace(/:/g, "")
    const territory = `fr-territory-${uid}`
    const revealed = `fr-revealed-${uid}`

    // Balayage vertical
    useAnimeScope(root, () => {
        const el = root.current!
        const beam = el.querySelector<SVGGElement>(".fr-beam")
        const rect = el.querySelector<SVGRectElement>(".fr-reveal-rect")
        const label = el.querySelector<HTMLElement>(".fr-label")
        const percent = el.querySelector<HTMLElement>(".fr-percent")
        const flashes = Array.from(el.querySelectorAll<SVGPathElement>(".fr-flash"))
        const flashed = new Set<SVGPathElement>()
        let swept = 0

        const draw = (y: number, running: boolean) => {
            swept = Math.max(swept, Math.min(y, FRANCE_HEIGHT + PAD))
            // le rectangle de révélation démarre à -PAD : sa hauteur doit couvrir aussi la marge
            rect?.setAttribute("height", String(swept + PAD))
            beam?.setAttribute("transform", `translate(0 ${y})`)
            beam?.setAttribute("opacity", running ? "1" : "0")
            if (running) {
                // Un éclair discret sur chaque région au moment où le faisceau atteint son centre
                for (const f of flashes) {
                    if (!flashed.has(f) && swept >= Number(f.dataset.cy)) {
                        flashed.add(f)
                        animate(f, { opacity: [0.4, 0], duration: 900, ease: easeOut })
                    }
                }
            }
            if (label) {
                // En mouvement réduit, le calcul est « en cours » sans faisceau : on ne doit pas afficher « terminée »
                label.textContent = state === "idle"
                    ? "Prêt"
                    : running
                        ? nearestRegion(y)
                        : state === "scanning" ? "Analyse en cours" : "Analyse terminée"
            }
            if (percent) {
                percent.textContent = state === "idle" || (state === "scanning" && !running)
                    ? ""
                    : running ? `${Math.round((swept / FRANCE_HEIGHT) * 100)} %` : "100 %"
            }
        }

        if (state !== "scanning" || reduce) {
            if (state === "done") swept = FRANCE_HEIGHT + PAD
            draw(state === "done" ? FRANCE_HEIGHT + PAD : 0, false)
            return
        }
        const t = { y: 0 }
        animate(t, {
            y: FRANCE_HEIGHT,
            duration: SCAN_SWEEP_MS,
            ease: "inOutQuad",
            loop: true,
            onUpdate: () => draw(t.y, true),
        })
    }, [state, reduce])

    // La ligne d'état (« Analyse terminée 100 % ») s'efface en fondu 3 s après la fin ; elle revient au prochain calcul.
    // Seule l'opacité change : la carte ne bouge pas.
    useEffect(() => {
        const el = status.current
        if (!el) return
        el.style.opacity = "1"
        if (state !== "done") return
        const timer = window.setTimeout(() => {
            animate(el, { opacity: 0, duration: reduce ? duration.fast : duration.slow * 1.5, ease: "linear" })
        }, STATUS_HIDE_MS)
        return () => window.clearTimeout(timer)
    }, [state, reduce])

    return (
        <div ref={root} className="mx-auto w-full max-w-[460px]">
            <svg
                viewBox={`${-PAD} ${-PAD} ${FRANCE_WIDTH + 2 * PAD} ${FRANCE_HEIGHT + 2 * PAD}`}
                className="h-auto w-full"
                role="img"
                aria-label={state === "scanning" ? "Carte de France scannée pendant le calcul" : "Carte de France"}
            >
                <defs>
                    <clipPath id={territory}>
                        {FRANCE_REGIONS.map(r => <path key={r.name} d={r.d} />)}
                    </clipPath>
                    <clipPath id={revealed}>
                        <rect className="fr-reveal-rect" x={-PAD} y={-PAD} width={FRANCE_WIDTH + 2 * PAD} height={0} />
                    </clipPath>
                    <linearGradient id={`${uid}-trail`} x1="0" y1="1" x2="0" y2="0">
                        <stop offset="0" stopColor="var(--series-predicted)" stopOpacity="0.5" />
                        <stop offset="1" stopColor="var(--series-predicted)" stopOpacity="0" />
                    </linearGradient>
                </defs>

                {/* Carte éteinte */}
                <g stroke={BORDER_DIM} strokeWidth={0.7} strokeLinejoin="round" fill={DIM_FILL}>
                    {FRANCE_REGIONS.map(r => <path key={r.name} d={r.d} />)}
                </g>

                {/* Carte allumée : révélée derrière le faisceau */}
                <g clipPath={`url(#${revealed})`}>
                    <g stroke={BORDER_LIT} strokeWidth={0.8} strokeLinejoin="round" fill={LIT_FILL}>
                        {FRANCE_REGIONS.map(r => <path key={r.name} d={r.d} />)}
                    </g>
                    <g fill="#ffffff" stroke="none">
                        {FRANCE_REGIONS.map(r => (
                            <path key={r.name} className="fr-flash" data-cy={r.cy} d={r.d} opacity={0} />
                        ))}
                    </g>
                </g>

                {/* Faisceau : traînée douce limitée au territoire, puis trait net */}
                <g className="fr-beam" opacity={0}>
                    <g clipPath={`url(#${territory})`}>
                        <rect x={-PAD} y={-TRAIL} width={FRANCE_WIDTH + 2 * PAD} height={TRAIL} fill={`url(#${uid}-trail)`} />
                    </g>
                    <line
                        x1={-PAD} x2={FRANCE_WIDTH + PAD} y1={0} y2={0}
                        stroke="var(--series-predicted)" strokeWidth={1.8} strokeLinecap="round"
                        style={{ filter: "drop-shadow(0 0 5px var(--series-predicted))" }}
                    />
                </g>
            </svg>

            <div ref={status} className="mt-3 flex items-baseline justify-between text-sm">
                <span className="fr-label text-[var(--text-2)]">Prêt</span>
                <span className="fr-percent tabular text-[var(--series-predicted)]" />
            </div>
        </div>
    )
}

/** Nom de la région dont le centre est le plus proche de la hauteur du faisceau. */
function nearestRegion(y: number): string {
    let best = FRANCE_REGIONS[0]
    for (const r of FRANCE_REGIONS) if (Math.abs(r.cy - y) < Math.abs(best.cy - y)) best = r
    return best.name
}
