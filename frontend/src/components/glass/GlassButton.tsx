import type { ButtonHTMLAttributes, ReactNode } from "react"

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children: ReactNode
    /** Bouton principal : plein, bleu */
    primary?: boolean
}

/** Bouton en verre. L'appui (réduction à 0,97) est en CSS pur, désactivé en mouvement réduit. */
export default function GlassButton({ children, primary = false, className = "", type = "button", ...props }: GlassButtonProps) {
    return (
        <button type={type} className={`glass-button ${primary ? "glass-button-primary" : ""} ${className}`} {...props}>
            {children}
        </button>
    )
}
