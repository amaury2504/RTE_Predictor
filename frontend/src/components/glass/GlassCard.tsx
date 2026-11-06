import type { ReactNode } from "react"

interface GlassCardProps {
    children: ReactNode
    className?: string
    /** Élévation et éclaircissement au survol (cartes cliquables ou KPI) */
    interactive?: boolean
}

/**
 * Surface en verre dépoli : flou, bordure fine, liseré lumineux en haut, ombre profonde.
 * Le survol (élévation) est en CSS pur : plus fluide qu'un moteur JS pour un effet aussi simple.
 */
export default function GlassCard({ children, className = "", interactive = false }: GlassCardProps) {
    return (
        <div className={`glass-card ${interactive ? "glass-card-interactive" : ""} ${className}`}>
            {children}
        </div>
    )
}
