import { useEffect, useId, useRef } from "react"
import { animate } from "animejs"
import { duration, easeOut as motionEase, SCAN_SWEEP_MS } from "../../design/motion"
import { FRANCE_HEIGHT, FRANCE_REGIONS, FRANCE_WIDTH } from "../../lib/franceRegions"

/*
 * Animation de l'analyse sur 7 jours, en vraie 3D (perspective CSS, `transform-style: preserve-3d`) :
 *  1. la carte, vue comme un écran vertical, pivote jusqu'à ce que sa normale (la perpendiculaire à sa face)
 *     pointe vers l'Est : rotation autour de l'axe vertical uniquement (TILT_X permet d'ajouter une part de Nord) ;
 *  2. des copies naissent derrière elle, le long de cette normale (translateZ), l'une après l'autre : une vague
 *     de cartes espacées dans la profondeur, de plus en plus sombres ;
 *  3. le scan se lance sur chaque carte avec un court décalage : une vague de scan traverse la pile ;
 *  4. à la fin de l'analyse, tout se rejoue à l'envers : les copies reviennent se fondre dans la carte d'origine,
 *     qui se remet de face et retourne à sa place, allumée.
 *
 * Une seule fonction (`renderPose`) dessine la scène à partir de l'avancement `p` (ms) de l'intro : l'aller et
 * le retour sont la même animation parcourue dans un sens ou dans l'autre.
 */

// --- Réglages de la mise en scène (à ajuster ici) ---------------------------
const COPIES = 5 // cartes derrière la carte principale (4 à 5 recommandé)
const TURN_Y = 38 // rotation vers l'Est : la normale de la face penche vers la droite (degrés)
const TILT_X = 0 // rotation vers le Nord (degrés) : 0 = la normale pointe vers l'Est uniquement
const SCENE_SCALE = 0.78 // la scène rétrécit en pivotant pour rester dans la case
const SHIFT_X = 10 // recentrage de la scène pendant la rotation (px) : plus petit = pile plus à gauche
const SHIFT_Y = 0
const SPACING = 80 // espace entre deux cartes, dans la profondeur (px)
const LIFT_Z = 46 // la carte s'avance vers le spectateur en se détachant (px)
const PERSPECTIVE = 1400 // distance de fuite (px) : plus petit = perspective plus marquée
const DARKEN = 0.11 // assombrissement par rang de carte (0 à 1)

// Chronologie de l'aller (ms)
const LIFT_END = 600
const TURN_START = 250
const TURN_END = 1250
const COPY_START = 1050
const COPY_GAP = 170
const COPY_DUR = 520
const INTRO = COPY_START + (COPIES - 1) * COPY_GAP + COPY_DUR
// Vague de scan : chaque carte démarre un court instant après la précédente
const SCAN_DELAY = 130
const BACK_MS = 1500

// Temps moyen d'une analyse (ms). Les trois phrases arrivent aux quartiles de cette durée (25 %, 50 %, 75 %),
// quelle que soit la vitesse réelle du calcul : une analyse rapide ne les prive donc plus de lecture.
const AVG_MS = 8000
const PHRASE_AT = [0.25, 0.5, 0.75].map(q => q * AVG_MS)
// Temps laissé pour lire la dernière phrase avant que les cartes ne se recomposent
const READ_MS = 2500

// Phrases affichées en orange ; chacune reste affichée jusqu'à la fin. La dernière n'apparaît qu'au 3e quartile
// ET si l'analyse est réellement terminée : si le calcul est plus lent que la moyenne, elle attend (on n'annonce
// pas « terminée » avant l'heure).
const PHRASES = [
    "Extraction des données effectuée",
    "Analyse en cours",
    "Prédiction terminée",
]

const LAYERS = COPIES + 1
const PAD = 14
const TRAIL = 70

// Palette : celle de FranceScan, pour que le passage de l'une à l'autre soit invisible
const DIM_FILL = "rgba(57, 135, 229, 0.16)"
const LIT_FILL = "#3987e5"
const BORDER_DIM = "rgba(255, 255, 255, 0.16)"
const BORDER_LIT = "rgba(255, 255, 255, 0.85)"

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const seg = (p: number, a: number, b: number) => clamp01((p - a) / (b - a))
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
const easeInOutQuad = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)

interface FranceStackProps {
    /** Vrai tant que l'analyse tourne ; passe à faux pour lancer le retour de la scène. */
    active: boolean
    /** La carte principale part déjà allumée (une prédiction a déjà été faite). */
    startLit: boolean
    /** Appelé quand la scène est revenue à plat : la page peut afficher la carte simple. */
    onExited: () => void
}

export default function FranceStack({ active, startLit, onExited }: FranceStackProps) {
    const root = useRef<HTMLDivElement>(null)
    const markDone = useRef<(() => void) | null>(null)
    const exited = useRef(onExited)
    exited.current = onExited
    const uid = useId().replace(/:/g, "")
    const shapeId = `fs-shape-${uid}`
    const terrId = `fs-terr-${uid}`
    const trailId = `fs-trail-${uid}`

    useEffect(() => {
        const el = root.current
        if (!el) return
        const scene = el.querySelector<HTMLElement>(".fs-scene")
        // Les cartes sont écrites dans le DOM de la dernière à la première : on les remet dans l'ordre des rangs
        const layers = Array.from(el.querySelectorAll<HTMLElement>("[data-layer]")).sort((x, y) => Number(x.dataset.layer) - Number(y.dataset.layer))
        const panels = layers.map(l => l.querySelector<HTMLElement>(".fs-panel"))
        const shades = layers.map(l => l.querySelector<HTMLElement>(".fs-shade"))
        const rects = layers.map(l => l.querySelector<SVGRectElement>(".fs-rect"))
        const beams = layers.map(l => l.querySelector<SVGGElement>(".fs-beam"))
        const imprint = el.querySelector<HTMLElement>(".fs-imprint")
        const lines = Array.from(el.querySelectorAll<HTMLElement>(".fs-phrase-line"))
        const phrasesBox = el.querySelector<HTMLElement>(".fs-phrases")
        if (!scene) return
        let phrasesShown = 0 // nombre de phrases déjà affichées
        let analysisDone = false // l'analyse est réellement terminée (signalé par la page)
        let lastPhraseAt: number | null = null // instant où la dernière phrase est apparue
        const phraseAnims: ReturnType<typeof animate>[] = []

        /** Fait apparaître la phrase `index` (fondu, glissement depuis la droite). Une fois affichée, elle reste. */
        const showPhrase = (index: number) => {
            const line = lines[index]
            if (!line || line.dataset.shown) return
            line.dataset.shown = "1"
            phraseAnims.push(animate(line, { opacity: [0, 1], translateX: [14, 0], duration: duration.slow, ease: motionEase }))
        }

        const state = { p: 0 }
        const swept = layers.map((_, i) => (i === 0 && startLit ? FRANCE_HEIGHT + PAD : 0))
        const mountedAt = performance.now()
        let introDoneAt: number | null = null
        let forceFull = false
        let back: ReturnType<typeof animate> | null = null

        /** Pose de la scène à l'avancement `p` : détachement, rotation de la face, naissance des copies. */
        const renderPose = () => {
            const p = state.p
            const lift = easeOut(seg(p, 0, LIFT_END))
            const turn = easeInOut(seg(p, TURN_START, TURN_END))
            const scale = 1 - (1 - SCENE_SCALE) * turn
            // Normale de la face : d'abord vers l'Est (rotateY), puis vers le Nord (rotateX), donc vers le Nord-Est
            scene.style.transform =
                `translate3d(${(SHIFT_X * turn).toFixed(1)}px, ${(SHIFT_Y * turn).toFixed(1)}px, 0) scale(${scale.toFixed(4)}) rotateX(${(TILT_X * turn).toFixed(2)}deg) rotateY(${(TURN_Y * turn).toFixed(2)}deg)`
            if (imprint) imprint.style.opacity = String(0.5 * lift)
            layers.forEach((layer, i) => {
                const c = i === 0 ? 1 : easeOut(seg(p, COPY_START + (i - 1) * COPY_GAP, COPY_START + (i - 1) * COPY_GAP + COPY_DUR))
                layer.style.visibility = c === 0 ? "hidden" : "visible"
                if (c === 0) return
                // Les copies s'écartent le long de la normale (z négatif = derrière la carte principale)
                const z = LIFT_Z * lift - i * SPACING * c - i * 0.5
                layer.style.transform = `translateZ(${z.toFixed(1)}px)`
                layer.style.opacity = String(c)
                // L'écran apparaît en même temps que la rotation ; plus une carte est loin, plus elle est dans l'ombre
                if (panels[i]) panels[i]!.style.opacity = String(turn)
                if (shades[i]) shades[i]!.style.opacity = String(DARKEN * i * c * 5)
            })
        }

        /** Faisceau et zone allumée de chaque carte : le balayage démarre carte après carte (vague de scan). */
        const renderScan = () => {
            const now = performance.now()
            if (introDoneAt == null && state.p >= INTRO) introDoneAt = now
            if (!forceFull) {
                const elapsed = now - mountedAt
                // Phrases aux quartiles du temps moyen
                while (phrasesShown < PHRASES.length - 1 && elapsed >= PHRASE_AT[phrasesShown]) showPhrase(phrasesShown++)
                // Dernière phrase : au 3e quartile, mais seulement une fois l'analyse réellement terminée
                if (phrasesShown === PHRASES.length - 1 && elapsed >= PHRASE_AT[phrasesShown] && analysisDone) {
                    showPhrase(phrasesShown++)
                    lastPhraseAt = now
                }
                // Retour des cartes quand la dernière phrase a eu le temps d'être lue
                if (lastPhraseAt != null && now - lastPhraseAt >= READ_MS) startBack()
            }
            layers.forEach((_, i) => {
                const startAt = introDoneAt == null ? null : introDoneAt + i * SCAN_DELAY
                const running = !forceFull && startAt != null && now >= startAt
                let y = 0
                if (running) {
                    y = easeInOutQuad((((now - (startAt as number)) % SCAN_SWEEP_MS) / SCAN_SWEEP_MS)) * FRANCE_HEIGHT
                    swept[i] = Math.max(swept[i], Math.min(y, FRANCE_HEIGHT + PAD))
                }
                if (forceFull) swept[i] = FRANCE_HEIGHT + PAD
                rects[i]?.setAttribute("height", String(swept[i] + PAD))
                beams[i]?.setAttribute("transform", `translate(0 ${y})`)
                beams[i]?.setAttribute("opacity", running ? "1" : "0")
            })
        }

        const renderAll = () => { renderPose(); renderScan() }
        renderAll()

        const intro = animate(state, { p: INTRO, duration: INTRO, ease: "linear", onUpdate: renderAll })
        // Métronome : redessine le balayage à chaque image, même quand l'intro est terminée
        const tick = animate({ t: 0 }, { t: 1, duration: 1000, ease: "linear", loop: true, onUpdate: renderScan })

        function startBack() {
            if (back) return
            intro.pause()
            // Les phrases orange s'effacent en fondu (léger glissement vers la droite) pendant que les cartes se recomposent
            if (phrasesBox) phraseAnims.push(animate(phrasesBox, { opacity: [1, 0], translateX: [0, 14], duration: duration.slow * 1.5, ease: "linear" }))
            forceFull = true // pendant le retour, toutes les cartes sont allumées
            const ms = Math.max(600, Math.min(BACK_MS, (state.p / INTRO) * BACK_MS))
            back = animate(state, { p: 0, duration: ms, ease: "inOutQuad", onUpdate: renderAll, onComplete: () => exited.current() })
        }
        // La page signale la fin réelle de l'analyse ; la scène, elle, se referme à son propre rythme (phrases à lire)
        markDone.current = () => { analysisDone = true }

        return () => {
            markDone.current = null
            phraseAnims.forEach(a => a.revert())
            intro.revert()
            tick.revert()
            back?.revert()
        }
        // La scène se construit une seule fois par montage
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    useEffect(() => {
        if (!active) markDone.current?.()
    }, [active])

    const viewBox = `${-PAD} ${-PAD} ${FRANCE_WIDTH + 2 * PAD} ${FRANCE_HEIGHT + 2 * PAD}`
    const paths = FRANCE_REGIONS.map(r => <path key={r.name} d={r.d} />)
    // La carte principale (rang 0) est écrite en dernier : à profondeur égale elle est peinte au-dessus des copies
    const order = Array.from({ length: LAYERS }, (_, k) => LAYERS - 1 - k)

    return (
        <div ref={root} className="relative mx-auto w-full max-w-[460px]">
            {/* Définitions partagées : le contour est écrit une seule fois, chaque carte le réutilise */}
            <svg width={0} height={0} className="absolute" aria-hidden="true" focusable="false">
                <defs>
                    <g id={shapeId}>{paths}</g>
                    <clipPath id={terrId}>{paths}</clipPath>
                    <linearGradient id={trailId} x1="0" y1="1" x2="0" y2="0">
                        <stop offset="0" stopColor="var(--series-predicted)" stopOpacity="0.5" />
                        <stop offset="1" stopColor="var(--series-predicted)" stopOpacity="0" />
                    </linearGradient>
                </defs>
            </svg>

            <div className="relative" role="img" aria-label="Carte de France : plusieurs mesures sont analysées en parallèle"
                style={{ aspectRatio: `${FRANCE_WIDTH + 2 * PAD} / ${FRANCE_HEIGHT + 2 * PAD}`, perspective: `${PERSPECTIVE}px` }}>
                {/* Empreinte : le contour de la carte reste dans la case une fois l'originale détachée */}
                <div className="fs-imprint absolute inset-0" style={{ opacity: 0 }} aria-hidden="true">
                    <svg viewBox={viewBox} className="h-full w-full">
                        <use href={`#${shapeId}`} fill="none" stroke={BORDER_DIM} strokeWidth={0.9} strokeLinejoin="round" />
                    </svg>
                </div>

                {/* Scène 3D : c'est elle qui pivote ; chaque carte y est reculée le long de la normale */}
                <div className="fs-scene absolute inset-0 will-change-transform" style={{ transformStyle: "preserve-3d" }}>
                    {order.map(i => (
                        <div key={i} data-layer={i} aria-hidden="true" className="absolute inset-0"
                            style={{ visibility: i === 0 ? "visible" : "hidden" }}>
                            {/* Écran : panneau de verre sombre derrière la carte, invisible tant que la carte est à plat */}
                            <div className="fs-panel absolute rounded-[26px]" style={{
                                inset: -10,
                                opacity: 0,
                                border: "1px solid rgba(255, 255, 255, 0.16)",
                                background: "linear-gradient(160deg, rgba(40, 90, 170, 0.24), rgba(6, 14, 28, 0.62))",
                                boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 30px 60px -20px rgba(0, 0, 0, 0.75)",
                            }} />
                            <svg viewBox={viewBox} className="relative h-full w-full">
                                <defs>
                                    <clipPath id={`${uid}-rv${i}`}>
                                        <rect className="fs-rect" x={-PAD} y={-PAD} width={FRANCE_WIDTH + 2 * PAD} height={0} />
                                    </clipPath>
                                </defs>
                                <use href={`#${shapeId}`} fill={DIM_FILL} stroke={BORDER_DIM} strokeWidth={0.7} strokeLinejoin="round" />
                                <g clipPath={`url(#${uid}-rv${i})`}>
                                    <use href={`#${shapeId}`} fill={LIT_FILL} stroke={BORDER_LIT} strokeWidth={0.8} strokeLinejoin="round" />
                                </g>
                                <g className="fs-beam" opacity={0}>
                                    <g clipPath={`url(#${terrId})`}>
                                        <rect x={-PAD} y={-TRAIL} width={FRANCE_WIDTH + 2 * PAD} height={TRAIL} fill={`url(#${trailId})`} />
                                    </g>
                                    <line x1={-PAD} x2={FRANCE_WIDTH + PAD} y1={0} y2={0} stroke="var(--series-predicted)" strokeWidth={1.8} strokeLinecap="round"
                                        style={{ filter: "drop-shadow(0 0 5px var(--series-predicted))" }} />
                                </g>
                            </svg>
                            {/* Ombre : voile sombre d'autant plus épais que la carte est loin derrière */}
                            <div className="fs-shade pointer-events-none absolute rounded-[26px]" style={{ inset: -10, opacity: 0, background: "rgba(3, 8, 16, 0.2)" }} />
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-3 flex items-baseline justify-between text-sm">
                <span className="text-[var(--text-2)]">Analyse de 168 mesures</span>
            </div>

            {/* Phrases en orange, à droite de la scène : chacune apparaît à son tour et reste jusqu'à la fin de la simulation.
                Sous 1100 px il n'y a pas la place à droite : elles s'empilent sous la carte (hauteur réservée). */}
            <div role="status" className="fs-phrases mt-3 min-h-[5.25rem] space-y-1 text-sm font-medium text-[var(--series-predicted)] min-[1100px]:absolute min-[1100px]:left-[calc(100%-28px)] min-[1100px]:top-1/2 min-[1100px]:mt-0 min-[1100px]:min-h-0 min-[1100px]:w-[250px] min-[1100px]:-translate-y-1/2">
                {PHRASES.map(text => (
                    <p key={text} className="fs-phrase-line" style={{ opacity: 0 }}>{text}</p>
                ))}
            </div>
        </div>
    )
}
