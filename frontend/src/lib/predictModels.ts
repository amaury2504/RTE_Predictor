/**
 * Les modèles que l'on peut essayer dans l'onglet « Prédire » (une feuille par modèle).
 * `served` : le backend sait déjà répondre pour ce modèle. Les autres sont affichés mais pas encore actifs.
 */
export interface PredictModel {
    id: string
    /** Nom court affiché dans la barre. */
    name: string
    kind: string
    served: boolean
}

export const PREDICT_MODELS: PredictModel[] = [
    { id: "mlp", name: "MLP", kind: "Réseau de neurones", served: true },
    { id: "lightgbm", name: "LightGBM", kind: "Arbres de décision en série", served: true },
    { id: "timestral", name: "Timestral", kind: "Modèle de fondation", served: true },
    { id: "ridge", name: "Ridge", kind: "Régression linéaire", served: true },
    { id: "holt-winters", name: "Holt-Winters", kind: "Lissage exponentiel", served: true },
]
