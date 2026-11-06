import { useRef } from "react"
import { createTimeline, stagger } from "animejs"
import { CHART } from "../../design/chartColors"
import { easeOut } from "../../design/motion"
import { useInViewLoop } from "../../hooks/useInViewLoop"

/*
 * Cinq illustrations animées, une par modèle. Règles communes :
 *  - le SVG est écrit dans son état FINAL (complet, lisible) : c'est ce que voit l'utilisateur en mouvement réduit ;
 *  - l'animation part d'un état de départ et revient à cet état, puis la boucle repart (pause entre deux passages) ;
 *  - aucun cercle décoratif : des unités carrées arrondies, des barres et des tracés ;
 *  - bleu pour la structure ; l'orange est réservé à LightGBM, le meilleur modèle.
 */

const BLUE = CHART.model
const SOFT = "#5cc0ff"
const DIM = CHART.axis
const GRID = CHART.grid
const LIGHT = "#cfe6ff"
const ORANGE = CHART.best

interface ArtProps {
    reduce: boolean
}

const svgClass = "h-auto w-full"
const pulse = { transformBox: "fill-box", transformOrigin: "50% 100%" } as const
const grow = { transformBox: "fill-box", transformOrigin: "0% 50%" } as const

/** Tracé « dessiné » (avec l attribut pathLength={1} sur le path) : longueur normalisée à 1, donc strokeDashoffset va de 1 (invisible) à 0 (complet). */
const drawn = { strokeDasharray: 1, strokeDashoffset: 0 } as const

/** Courbe y = f(t) échantillonnée en tracé SVG. */
function curve(f: (t: number) => number, x0: number, x1: number, n = 80): string {
    return Array.from({ length: n + 1 }, (_, i) => {
        const t = i / n
        return `${i === 0 ? "M" : "L"} ${(x0 + t * (x1 - x0)).toFixed(1)} ${f(t).toFixed(1)}`
    }).join(" ")
}

// --- MLP : des couches d'unités reliées entre elles --------------------------

const MLP_IN = [44, 92, 140, 188]
const MLP_HID = [24, 70, 116, 162, 208]
const MLP_OUT = 116
const MLP_XI = 96
const MLP_XH = 196
const MLP_XO = 296
const MLP_LABELS = ["Météo", "Heure", "Jour", "Fériés"]

export function MlpArt({ reduce }: ArtProps) {
    const root = useRef<SVGSVGElement>(null)

    useInViewLoop(root, q =>
        createTimeline({ loop: true, loopDelay: 900, defaults: { ease: easeOut } })
            .add(q(".mlp-in"), { fillOpacity: [0.7, 1, 0.7], duration: 500, delay: stagger(90) }, 0)
            .add(q(".mlp-l1"), { strokeOpacity: [0.2, 0.85, 0.2], duration: 600, delay: stagger(25) }, 450)
            .add(q(".mlp-hid"), { fillOpacity: [0.7, 1, 0.7], duration: 500, delay: stagger(80) }, 1000)
            .add(q(".mlp-l2"), { strokeOpacity: [0.2, 0.85, 0.2], duration: 600, delay: stagger(60) }, 1500)
            .add(q(".mlp-out"), { fillOpacity: [0.7, 1, 0.7], duration: 700 }, 2000), reduce)

    return (
        <svg ref={root} viewBox="0 0 360 224" className={svgClass} role="img"
            aria-label="Réseau de neurones : la météo, l'heure et le calendrier traversent des couches d'unités jusqu'à la consommation">
            {MLP_IN.flatMap(yi => MLP_HID.map(yh => (
                <line key={`a${yi}-${yh}`} className="mlp-l1" x1={MLP_XI + 11} y1={yi} x2={MLP_XH - 11} y2={yh} stroke={SOFT} strokeOpacity={0.2} />
            )))}
            {MLP_HID.map(yh => (
                <line key={`b${yh}`} className="mlp-l2" x1={MLP_XH + 11} y1={yh} x2={MLP_XO - 11} y2={MLP_OUT} stroke={SOFT} strokeOpacity={0.2} />
            ))}
            {MLP_IN.map((y, i) => (
                <g key={`i${y}`}>
                    <text x={MLP_XI - 18} y={y + 4} textAnchor="end" fontSize={12} fill={DIM}>{MLP_LABELS[i]}</text>
                    <rect className="mlp-in" x={MLP_XI - 10} y={y - 10} width={20} height={20} rx={6} fill={BLUE} fillOpacity={0.7} />
                </g>
            ))}
            {MLP_HID.map(y => (
                <rect key={`h${y}`} className="mlp-hid" x={MLP_XH - 10} y={y - 10} width={20} height={20} rx={6} fill={BLUE} fillOpacity={0.7} />
            ))}
            <rect className="mlp-out" x={MLP_XO - 12} y={MLP_OUT - 12} width={24} height={24} rx={7} fill={SOFT} fillOpacity={0.7} />
            <text x={MLP_XO + 22} y={MLP_OUT + 4} fontSize={12} fill={DIM}>GW</text>
        </svg>
    )
}

// --- LightGBM : des arbres qui corrigent l'erreur des précédents -------------

const GB = { x0: 24, x1: 336, top: 30, bottom: 196 }
const gbTarget = (t: number) => 0.5 + 0.28 * Math.sin(t * Math.PI * 2 * 1.15) + 0.13 * Math.sin(t * Math.PI * 2 * 3.1 + 1)
const gbX = (t: number) => GB.x0 + t * (GB.x1 - GB.x0)
const gbY = (v: number) => GB.bottom - v * (GB.bottom - GB.top)

/** Approximation en escalier de la courbe cible avec k marches : chaque marche est la moyenne de la cible sur son intervalle. */
function staircase(k: number): string {
    let d = ""
    for (let i = 0; i < k; i++) {
        const samples = Array.from({ length: 16 }, (_, s) => gbTarget((i + s / 15) / k))
        const level = gbY(samples.reduce((a, b) => a + b, 0) / samples.length)
        d += `${i === 0 ? "M" : " V"} ${i === 0 ? `${gbX(0).toFixed(1)} ` : ""}${level.toFixed(1)} H ${gbX((i + 1) / k).toFixed(1)}`
    }
    return d
}

const GB_STAGES = [
    { k: 3, label: "Arbre 1" },
    { k: 6, label: "Arbres 1 à 3" },
    { k: 14, label: "Arbres 1 à 14" },
]

export function LightGbmArt({ reduce }: ArtProps) {
    const root = useRef<SVGSVGElement>(null)

    useInViewLoop(root, q => {
        const tl = createTimeline({ loop: true, loopDelay: 700, defaults: { ease: easeOut } })
        GB_STAGES.forEach((_, i) => {
            const at = i * 1250
            const last = i === GB_STAGES.length - 1
            tl.add(q(`.gb-s${i}`), { strokeDashoffset: [1, 0], opacity: [0, 1], duration: 700 }, at)
                .add(q(`.gb-t${i}`), { opacity: [0, 1], duration: 250 }, at)
            if (!last) {
                tl.add(q(`.gb-s${i}`), { opacity: [1, 0], duration: 300 }, at + 1050)
                    .add(q(`.gb-t${i}`), { opacity: [1, 0], duration: 250 }, at + 1050)
            }
        })
        const end = (GB_STAGES.length - 1) * 1250 + 1500
        return tl
            .add(q(`.gb-s${GB_STAGES.length - 1}`), { opacity: [1, 0], duration: 450 }, end)
            .add(q(`.gb-t${GB_STAGES.length - 1}`), { opacity: [1, 0], duration: 450 }, end)
    }, reduce)

    return (
        <svg ref={root} viewBox="0 0 360 224" className={svgClass} role="img"
            aria-label="LightGBM : des arbres successifs approchent de mieux en mieux la courbe de consommation, chacun corrigeant l'erreur des précédents">
            <line x1={GB.x0} x2={GB.x1} y1={GB.bottom + 8} y2={GB.bottom + 8} stroke={GRID} />
            <path d={curve(t => gbY(gbTarget(t)), GB.x0, GB.x1, 120)} fill="none" stroke={SOFT} strokeOpacity={0.55} strokeWidth={2} />
            {GB_STAGES.map((s, i) => {
                const last = i === GB_STAGES.length - 1
                return (
                    <g key={s.k}>
                        <path className={`gb-s${i}`} pathLength={1} d={staircase(s.k)} fill="none" stroke={ORANGE} strokeWidth={2.5} strokeLinejoin="round"
                            style={{ ...drawn, opacity: last ? 1 : 0 }} />
                        <text className={`gb-t${i}`} x={GB.x1} y={16} textAnchor="end" fontSize={13} fontWeight={600} fill={ORANGE}
                            style={{ opacity: last ? 1 : 0 }}>{s.label}</text>
                    </g>
                )
            })}
            <text x={GB.x0} y={16} fontSize={12} fill={DIM}>Consommation</text>
        </svg>
    )
}

// --- Timestral : un modèle de fondation qui lit le passé et complète le futur

const TS_BASE = 170
const TS_PAST = [34, 52, 66, 58, 40, 30, 46, 64, 60]
const TS_FUTURE = [38, 54, 68, 56, 40, 34]
const TS_BLOCK = { x: 156, y: 68, w: 76, h: 96 }

export function TimestralArt({ reduce }: ArtProps) {
    const root = useRef<SVGSVGElement>(null)

    useInViewLoop(root, q =>
        createTimeline({ loop: true, loopDelay: 800, defaults: { ease: easeOut } })
            .add(q(".ts-past"), { scaleY: [0, 1], duration: 500, delay: stagger(55) }, 0)
            .add(q(".ts-att"), { strokeOpacity: [0.15, 0.85, 0.15], duration: 650, delay: stagger(45) }, 600)
            .add(q(".ts-block"), { strokeOpacity: [0.7, 1, 0.7], duration: 700 }, 750)
            .add(q(".ts-future"), { scaleY: [0, 1], duration: 500, delay: stagger(70) }, 1450)
            .add(q(".ts-fade"), { opacity: [1, 0], duration: 450 }, 3100), reduce)

    return (
        <svg ref={root} viewBox="0 0 360 224" className={svgClass} role="img"
            aria-label="Timestral : le modèle lit les dernières valeurs et la météo, relie les moments qui se ressemblent, puis complète les heures à venir">
            <line x1={14} x2={346} y1={TS_BASE} y2={TS_BASE} stroke={GRID} />
            {TS_PAST.map((h, i) => (
                <line key={`l${i}`} className="ts-att" x1={20 + i * 16 + 5} y1={TS_BASE - h * 1.4} x2={TS_BLOCK.x} y2={TS_BLOCK.y + 14 + i * 8}
                    stroke={SOFT} strokeOpacity={0.15} />
            ))}
            <g className="ts-fade">
                {TS_PAST.map((h, i) => (
                    <rect key={`p${i}`} className="ts-past" x={20 + i * 16} y={TS_BASE - h * 1.4} width={10} height={h * 1.4} rx={3}
                        fill={BLUE} style={pulse} />
                ))}
            </g>
            <rect className="ts-block" x={TS_BLOCK.x} y={TS_BLOCK.y} width={TS_BLOCK.w} height={TS_BLOCK.h} rx={16}
                fill={BLUE} fillOpacity={0.18} stroke={SOFT} strokeOpacity={0.7} strokeWidth={1.5} />
            <text x={TS_BLOCK.x + TS_BLOCK.w / 2} y={TS_BLOCK.y + TS_BLOCK.h / 2 + 5} textAnchor="middle" fontSize={15} fontWeight={600} fill="#e8eef8">28M</text>
            <g className="ts-fade">
                {TS_FUTURE.map((h, i) => (
                    <rect key={`f${i}`} className="ts-future" x={252 + i * 16} y={TS_BASE - h * 1.4} width={10} height={h * 1.4} rx={3}
                        fill={LIGHT} style={pulse} />
                ))}
            </g>
            <text x={92} y={192} textAnchor="middle" fontSize={12} fill={DIM}>Passé</text>
            <text x={292} y={192} textAnchor="middle" fontSize={12} fill={DIM}>Futur</text>
            {[0, 1, 2].map(i => (
                <rect key={`w${i}`} x={178 + i * 14} y={190 - [10, 16, 12][i]} width={8} height={[10, 16, 12][i]} rx={2} fill={SOFT} fillOpacity={0.7} />
            ))}
            <text x={TS_BLOCK.x + TS_BLOCK.w / 2} y={214} textAnchor="middle" fontSize={12} fill={DIM}>Météo</text>
        </svg>
    )
}

// --- Ridge : une somme pondérée dont la pénalité freine les poids ------------

const RIDGE_ROWS = [
    { label: "Température", w: 120, y: 34 },
    { label: "Heure", w: 92, y: 76 },
    { label: "Jour", w: 64, y: 118 },
    { label: "Fériés", w: 40, y: 160 },
]
const RIDGE_X = 112

export function RidgeArt({ reduce }: ArtProps) {
    const root = useRef<SVGSVGElement>(null)

    // Sans pénalité les poids grossissent (départ) ; avec la pénalité ils se calment (état final du SVG)
    useInViewLoop(root, q =>
        createTimeline({ loop: true, alternate: true, loopDelay: 600, defaults: { ease: easeOut } })
            .add(q(".rg-w"), { scaleX: [1.55, 1], duration: 900, delay: stagger(120) }, 0)
            .add(q(".rg-sum"), { scaleX: [1.3, 1], duration: 900 }, 500), reduce)

    return (
        <svg ref={root} viewBox="0 0 360 224" className={svgClass} role="img"
            aria-label="Ridge : chaque facteur reçoit un poids, la pénalité empêche les poids de grossir, et la somme donne la consommation">
            {RIDGE_ROWS.map(r => (
                <g key={r.label}>
                    <text x={RIDGE_X - 12} y={r.y + 12} textAnchor="end" fontSize={12} fill={DIM}>{r.label}</text>
                    <rect x={RIDGE_X} y={r.y} width={190} height={16} rx={8} fill={GRID} />
                    <rect className="rg-w" x={RIDGE_X} y={r.y} width={r.w} height={16} rx={8} fill={BLUE} style={grow} />
                </g>
            ))}
            <line x1={RIDGE_X} x2={RIDGE_X + 190} y1={192} y2={192} stroke={GRID} />
            <text x={RIDGE_X - 12} y={214} textAnchor="end" fontSize={12} fill={DIM}>Somme</text>
            <rect x={RIDGE_X} y={202} width={190} height={16} rx={8} fill={GRID} />
            <rect className="rg-sum" x={RIDGE_X} y={202} width={150} height={16} rx={8} fill={SOFT} style={grow} />
        </svg>
    )
}

// --- Holt-Winters : niveau, tendance et saison, puis prolongement ------------

const HW = { x0: 20, x1: 340, top: 18, bottom: 112, cut: 0.68 }
const hwSeason = (t: number) => Math.sin(t * Math.PI * 2 * 5)
const hwSignal = (t: number) => 0.4 + 0.34 * t + 0.14 * hwSeason(t)
const hwX = (t: number) => HW.x0 + t * (HW.x1 - HW.x0)
const hwY = (v: number) => HW.bottom - ((v - 0.2) / 0.8) * (HW.bottom - HW.top)

const HW_STRIPS = [
    { label: "Niveau", y: 142, f: () => 0 },
    { label: "Tendance", y: 174, f: (t: number) => t - 0.5 },
    { label: "Saison", y: 206, f: (t: number) => hwSeason(t) * 0.5 },
]
const HW_STRIP_X0 = 112

export function HoltWintersArt({ reduce }: ArtProps) {
    const root = useRef<SVGSVGElement>(null)

    useInViewLoop(root, q =>
        createTimeline({ loop: true, loopDelay: 700, defaults: { ease: easeOut } })
            .add(q(".hw-strip"), { strokeDashoffset: [1, 0], duration: 700, delay: stagger(220) }, 0)
            .add(q(".hw-past"), { strokeDashoffset: [1, 0], duration: 1000 }, 900)
            .add(q(".hw-future"), { strokeDashoffset: [1, 0], duration: 700 }, 1900)
            .add(q(".hw-band"), { opacity: [0, 1], duration: 400 }, 1900)
            .add(q(".hw-fade"), { opacity: [1, 0], duration: 450 }, 3300), reduce)

    return (
        <svg ref={root} viewBox="0 0 360 224" className={svgClass} role="img"
            aria-label="Holt-Winters : la consommation est décomposée en niveau, tendance et saison, puis son rythme est prolongé vers l'avenir">
            <g className="hw-fade">
                <rect className="hw-band" x={hwX(HW.cut)} y={HW.top - 6} width={HW.x1 - hwX(HW.cut)} height={HW.bottom - HW.top + 12} rx={8} fill="#ffffff" fillOpacity={0.05} />
                <path className="hw-past" pathLength={1} d={curve(t => hwY(hwSignal(t * HW.cut)), HW.x0, hwX(HW.cut), 70)}
                    fill="none" stroke={BLUE} strokeWidth={2.5} strokeLinejoin="round" style={drawn} />
                <path className="hw-future" pathLength={1} d={curve(t => hwY(hwSignal(HW.cut + t * (1 - HW.cut))), hwX(HW.cut), HW.x1, 50)}
                    fill="none" stroke={LIGHT} strokeWidth={2.5} strokeLinejoin="round" style={drawn} />
                <text x={(hwX(HW.cut) + HW.x1) / 2} y={HW.top + 2} textAnchor="middle" fontSize={12} fill={DIM}>Prolongement</text>
                {HW_STRIPS.map(s => (
                    <g key={s.label}>
                        <text x={HW_STRIP_X0 - 12} y={s.y + 4} textAnchor="end" fontSize={12} fill={DIM}>{s.label}</text>
                        <path className="hw-strip" pathLength={1} d={curve(t => s.y - s.f(t) * 22, HW_STRIP_X0, HW.x1, 60)}
                            fill="none" stroke={SOFT} strokeOpacity={0.85} strokeWidth={2} strokeLinejoin="round" style={drawn} />
                    </g>
                ))}
            </g>
        </svg>
    )
}
