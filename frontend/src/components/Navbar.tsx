import type { ReactNode } from "react"
import LogoMark from "./LogoMark"
import { useInShell } from "./shellContext"

interface NavbarProps {
    /** Si défini, affiche un bouton « Retour » à gauche du logo */
    onBack?: () => void
    /** Contenu aligné à droite */
    right?: ReactNode
    /** Largeur max du contenu (doit correspondre à celle de la page) */
    maxWidth?: "4xl" | "5xl"
}

export default function Navbar({ onBack, right, maxWidth = "4xl" }: NavbarProps) {
    // Dans la coquille, la navigation est portée par la sidebar : pas de barre du haut en double
    if (useInShell()) return null
    return (
        <nav className="sticky top-0 z-40 border-b border-line bg-canvas/80 backdrop-blur">
            <div className={`mx-auto flex items-center justify-between px-6 py-3.5 ${maxWidth === "5xl" ? "max-w-5xl" : "max-w-4xl"}`}>
                <div className="flex items-center gap-4">
                    {onBack && (
                        <button
                            onClick={onBack}
                            className="flex items-center gap-1 text-sm text-muted transition-colors hover:text-ink"
                        >
                            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                                <path d="M9 2L4 7l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                            Retour
                        </button>
                    )}
                    <div className="flex items-center gap-2.5">
                        <LogoMark />
                        <span className="font-semibold tracking-tight text-ink">ML Predictor</span>
                    </div>
                </div>
                <div className="text-sm text-muted">{right}</div>
            </div>
        </nav>
    )
}
