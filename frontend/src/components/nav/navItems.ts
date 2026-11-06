import { BarChart3, BrainCircuit, Zap } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
    to: string
    label: string
    /** Libellé court pour le dock mobile (peu de place). */
    shortLabel?: string
    icon: LucideIcon
}

export interface NavGroup {
    id: string
    label: string
    items: NavItem[]
}

/** Trois onglets : la prédiction d'abord (fonction principale), puis la comparaison, puis l'explication des modèles. */
export const NAV_GROUPS: NavGroup[] = [
    {
        id: "main",
        label: "Navigation",
        items: [
            { to: "/predict", label: "Prédire", icon: Zap },
            { to: "/benchmark", label: "Comparaison de modèles", shortLabel: "Comparer", icon: BarChart3 },
            { to: "/modeles", label: "Modèles", icon: BrainCircuit },
        ],
    },
]

export const ALL_ITEMS = NAV_GROUPS.flatMap(g => g.items)
