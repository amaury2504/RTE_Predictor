import { useEffect, useRef, useState } from "react"
import { animate } from "animejs"
import AnimatedNumber from "../data/AnimatedNumber"
import { duration } from "../../design/motion"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { signed } from "../../lib/format"

/** Test A/B de l'affichage du résultat : A = case sous la carte (transition lente), B = chiffres autour de la carte. */
export type ResultVariant = "a" | "b"

/** Ce que les deux colonnes affichent autour de la carte pour une prédiction « maintenant ». */
export interface NowResult {
    predictedGW: number
    actualGW: number | null
    gapPct: number | null
    date: string
    hour: number
}

const FADE_IN_MS = 1400   // apparition lente : on a le temps de voir ce qui arrive
const FADE_OUT_MS = 350

/**
 * Une colonne de résultat à gauche ou à droite de la carte (variante B). Toujours présente dans la mise en page
 * (la carte ne bouge pas), mais invisible tant qu'il n'y a rien à montrer. Elle apparaît lentement, la colonne de
 * droite un instant après celle de gauche, et s'efface quand le résultat disparaît (nouveau calcul, autre onglet).
 * Les valeurs restent affichées pendant l'effacement.
 */
export default function SideResult({ side, data, className = "" }: { side: "left" | "right"; data: NowResult | null; className?: string }) {
    const ref = useRef<HTMLDivElement>(null)
    const reduce = useReducedMotion()
    // Dernier résultat connu : il reste à l'écran le temps du fondu de sortie
    const [held, setHeld] = useState<NowResult | null>(data)
    if (data && data !== held) setHeld(data)

    const visible = data != null
    useEffect(() => {
        const el = ref.current
        if (!el) return
        const animation = animate(el, {
            opacity: visible ? 1 : 0,
            duration: reduce ? duration.fast : visible ? FADE_IN_MS : FADE_OUT_MS,
            delay: visible && !reduce && side === "right" ? 350 : 0,
            ease: "inOutQuad",   // départ doux : le fondu se voit, au lieu de s'achever dans la première demi-seconde
        })
        // pause (et non revert) : un fondu interrompu s'arrête là où il en est, sans clignoter
        return () => { animation.pause() }
    }, [visible, reduce, side])

    return (
        <div ref={ref} style={{ opacity: 0 }} aria-hidden={!visible} className={`min-w-0 ${className}`}>
            {held && (side === "left" ? <Predicted data={held} /> : <Actual data={held} />)}
        </div>
    )
}

function Label({ children, color }: { children: string; color: string }) {
    return (
        <p className="flex items-center gap-2 text-sm text-[var(--text-2)]">
            <span className="h-0.5 w-6 shrink-0 rounded" style={{ background: color }} aria-hidden="true" />
            {children}
        </p>
    )
}

function Predicted({ data }: { data: NowResult }) {
    return (
        <div className="lg:text-right">
            <Label color="var(--series-predicted)">Prédit par notre modèle</Label>
            <p className="mt-1 whitespace-nowrap text-4xl font-semibold tracking-tight text-[var(--text-1)]">
                <AnimatedNumber value={data.predictedGW} unit=" GW" />
            </p>
            <p className="mt-2 text-sm text-[var(--text-2)]">{data.date} · {String(data.hour).padStart(2, "0")}h00</p>
        </div>
    )
}

function Actual({ data }: { data: NowResult }) {
    return (
        <div>
            <Label color="var(--series-real)">Données réelles (base RTE)</Label>
            {data.actualGW != null ? (
                <p className="mt-1 whitespace-nowrap text-4xl font-semibold tracking-tight text-[var(--text-1)]">
                    <AnimatedNumber value={data.actualGW} unit=" GW" />
                </p>
            ) : (
                <p className="mt-1 text-sm text-[var(--text-2)]">Indisponible pour cette heure</p>
            )}
            {data.gapPct != null && (
                <p className="mt-2">
                    <span className="whitespace-nowrap rounded-full border border-[var(--glass-border)] bg-white/5 px-3 py-1 text-sm text-[var(--text-1)]">
                        écart {signed(data.gapPct, 1)} %
                    </span>
                </p>
            )}
        </div>
    )
}
