import { useState } from "react"
import ModelRail from "../components/predict/ModelRail"
import PredictSheet from "../components/predict/PredictSheet"
import { PREDICT_MODELS } from "../lib/predictModels"

/**
 * Onglet « Prédire » : une rangée horizontale de modèles, au-dessus de la feuille, une feuille par modèle. Chaque feuille offre les mêmes
 * fonctions (prédire maintenant, performance sur 7 jours) avec le modèle choisi.
 * Les feuilles déjà visitées restent montées (masquées) : leurs résultats et une analyse en cours sont conservés.
 */
export default function PredictionPage() {
    const [active, setActive] = useState(PREDICT_MODELS[0].id)
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
                <ModelRail models={PREDICT_MODELS} value={active} onChange={choose} idPrefix="predict" />

                <div>
                    {PREDICT_MODELS.filter(m => visited.includes(m.id)).map(m => (
                        <div
                            key={m.id}
                            role="tabpanel"
                            id={`predict-panel-${m.id}`}
                            aria-labelledby={`predict-tab-${m.id}`}
                            hidden={m.id !== active}
                        >
                            <PredictSheet model={m} />
                        </div>
                    ))}
                </div>
            </div>
        </main>
    )
}
