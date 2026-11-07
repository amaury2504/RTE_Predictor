import { useState } from "react"
import ModelRail from "../components/predict/ModelRail"
import PredictSheet from "../components/predict/PredictSheet"
import type { ResultVariant } from "../components/predict/SideResult"
import { PREDICT_MODELS } from "../lib/predictModels"

/**
 * Onglet « Prédire » : une rangée horizontale de modèles, au-dessus de la feuille, une feuille par modèle. Chaque feuille offre les mêmes
 * fonctions (prédire maintenant, performance sur 7 jours) avec le modèle choisi.
 * Les feuilles déjà visitées restent montées (masquées) : leurs résultats et une analyse en cours sont conservés.
 */
export default function PredictionPage() {
    const [active, setActive] = useState(PREDICT_MODELS[0].id)
    // Test A/B provisoire de l'affichage du résultat « maintenant » (à retirer une fois la variante choisie)
    const [variant, setVariant] = useState<ResultVariant>("a")
    const [visited, setVisited] = useState<string[]>([PREDICT_MODELS[0].id])

    const choose = (id: string) => {
        setActive(id)
        setVisited(v => (v.includes(id) ? v : [...v, id]))
    }

    return (
        <main className="mx-auto max-w-6xl px-6 py-8">
            <header className="mb-10 mt-4 max-w-3xl">
                <h1 className="title-sheen text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
                    Benchmark de modèles ML pour la prédiction
                </h1>
                <p className="mt-4 text-lg text-[var(--text-2)]">
                    Appliqué à la prédiction de consommation électrique française en fonction de la météo
                </p>
            </header>

            <div className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <ModelRail models={PREDICT_MODELS} value={active} onChange={choose} idPrefix="predict" />
                    <AbSwitch value={variant} onChange={setVariant} />
                </div>

                <div>
                    {PREDICT_MODELS.filter(m => visited.includes(m.id)).map(m => (
                        <div
                            key={m.id}
                            role="tabpanel"
                            id={`predict-panel-${m.id}`}
                            aria-labelledby={`predict-tab-${m.id}`}
                            hidden={m.id !== active}
                        >
                            <PredictSheet model={m} variant={variant} active={m.id === active} />
                        </div>
                    ))}
                </div>
            </div>
        </main>
    )
}

/** Sélecteur provisoire du test A/B : compare les deux façons d'afficher le résultat de « Prédire maintenant ». */
function AbSwitch({ value, onChange }: { value: ResultVariant; onChange: (v: ResultVariant) => void }) {
    const options: { id: ResultVariant; label: string; hint: string }[] = [
        { id: "a", label: "A", hint: "Case sous la carte, apparition lente" },
        { id: "b", label: "B", hint: "Chiffres autour de la carte" },
    ]
    return (
        <div role="group" aria-label="Test A/B : affichage du résultat" className="flex items-center gap-2 text-xs text-[var(--text-2)]">
            <span>Test A/B</span>
            <div className="glass-card flex gap-1 !rounded-full p-1">
                {options.map(o => (
                    <button
                        key={o.id}
                        type="button"
                        title={o.hint}
                        aria-pressed={value === o.id}
                        onClick={() => onChange(o.id)}
                        className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${value === o.id ? "bg-white/15 text-white" : "hover:text-white"}`}
                    >
                        {o.label}
                    </button>
                ))}
            </div>
            <span className="hidden sm:inline">{options.find(o => o.id === value)?.hint}</span>
        </div>
    )
}
