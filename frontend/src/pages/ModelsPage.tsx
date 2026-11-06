import { useRef } from "react"
import type { ComponentType } from "react"
import { HoltWintersArt, LightGbmArt, MlpArt, RidgeArt, TimestralArt } from "../components/models/ModelArt"
import GlassCard from "../components/glass/GlassCard"
import { useReducedMotion } from "../hooks/useReducedMotion"
import { useReveal } from "../hooks/useInViewLoop"

interface ModelInfo {
    id: string
    name: string
    kind: string
    Art: ComponentType<{ reduce: boolean }>
    /** Exactement trois lignes : ce que fait le modèle, comment il apprend, ce qu'il faut en retenir. */
    lines: [string, string, string]
}

const MODELS: ModelInfo[] = [
    {
        id: "mlp",
        name: "MLP",
        kind: "Réseau de neurones",
        Art: MlpArt,
        lines: [
            "Extraction des caractéristiques en combinant météo, heure et calendrier.",
            "Les poids s'ajustent à chaque itération pour réduire l'erreur",
            "C'est ce qu'on entend traditionnellement par réseaux de neurones",
        ],
    },
    {
        id: "lightgbm",
        name: "LightGBM",
        kind: "Arbres de décision en série",
        Art: LightGbmArt,
        lines: [
            "Il empile des centaines de petits arbres de décision.",
            "Chaque arbre corrige l'erreur laissée par les précédents.",
            "Rapide et précis sur des données de tableau comme celles-ci.",
        ],
    },
    {
        id: "timestral",
        name: "Timestral",
        kind: "Modèle de fondation",
        Art: TimestralArt,
        lines: [
            "Pré-entraîné sur de très nombreuses séries, sans entraînement ici.",
            "Basé sur un Transformer : son attention relie les moments passés qui ressemblent au présent.",
            "Il complète directement les heures à venir, avec la météo en appui.",
        ],
    },
    {
        id: "ridge",
        name: "Ridge",
        kind: "Régression linéaire",
        Art: RidgeArt,
        lines: [
            "Une somme pondérée : chaque facteur reçoit un poids.",
            "Une pénalité empêche les poids de grossir et de sur-apprendre.",
            "Simple et stable : il sert de repère aux modèles entraînés.",
        ],
    },
    {
        id: "holt-winters",
        name: "Holt-Winters",
        kind: "Lissage exponentiel",
        Art: HoltWintersArt,
        lines: [
            "On sépare les caractéristiques : niveau de base, rythme de la journée et de la semaine.",
            "Chaque composante se met à jour avec les données les plus récentes.",
            "Sans météo : il prolonge le rythme des jours et des semaines.",
        ],
    },
]

function ModelSection({ model, index, reduce }: { model: ModelInfo; index: number; reduce: boolean }) {
    const root = useRef<HTMLElement>(null)
    useReveal(root, reduce)
    const { Art } = model

    return (
        <section ref={root} aria-labelledby={`modele-${model.id}`}>
            <GlassCard className="grid items-center gap-6 p-6 md:grid-cols-2 md:gap-10 md:p-8">
                <div className={`rounded-2xl border border-[var(--glass-border)] bg-black/25 p-4 ${index % 2 === 1 ? "md:order-last" : ""}`}>
                    <Art reduce={reduce} />
                </div>
                <div>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <h2 id={`modele-${model.id}`} className="text-2xl font-semibold text-[var(--text-1)]">{model.name}</h2>
                    </div>
                    <p className="mt-1 text-sm text-[var(--text-2)]">{model.kind}</p>
                    <div className="mt-5 space-y-3">
                        {model.lines.map(line => (
                            <p key={line} className="border-l-2 border-[var(--glass-border)] pl-3 text-[var(--text-1)]">{line}</p>
                        ))}
                    </div>
                </div>
            </GlassCard>
        </section>
    )
}

/** Les cinq modèles comparés, un visuel animé chacun et trois lignes pour comprendre. */
export default function ModelsPage() {
    const reduce = useReducedMotion()

    return (
        <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
            <header>
                <h1 className="text-2xl font-semibold text-ink">Modèles</h1>
                <p className="mt-1 text-sm text-[var(--text-2)]">Comment chaque modèle prédit, en trois lignes.</p>
            </header>
            {MODELS.map((m, i) => <ModelSection key={m.id} model={m} index={i} reduce={reduce} />)}
        </main>
    )
}
