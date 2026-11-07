import { useId } from "react"

/**
 * Logo de ML Predictor : un éclair (l'énergie) en blanc sur une tuile dégradée bleue, avec une petite touche
 * orange, la couleur de la prédiction dans l'application. Les identifiants des dégradés sont uniques par
 * instance : plusieurs logos peuvent coexister sur la page.
 */
export default function LogoMark({ size = 28 }: { size?: number }) {
    const uid = useId().replace(/:/g, "")
    const tile = `logo-tile-${uid}`
    const glow = `logo-glow-${uid}`
    return (
        <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <defs>
                <linearGradient id={tile} x1="3" y1="2" x2="29" y2="31" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#4cc9ff" />
                    <stop offset="0.55" stopColor="#1e8cff" />
                    <stop offset="1" stopColor="#3b54e6" />
                </linearGradient>
                <linearGradient id={glow} x1="16" y1="2" x2="16" y2="18" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#ffffff" stopOpacity="0.35" />
                    <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
                </linearGradient>
            </defs>
            <rect width="32" height="32" rx="9" fill={`url(#${tile})`} />
            <rect width="32" height="18" rx="9" fill={`url(#${glow})`} />
            <rect x="0.5" y="0.5" width="31" height="31" rx="8.5" stroke="#ffffff" strokeOpacity="0.28" />
            <path d="M18.6 5.2 L9.2 17.4 H15 L13.2 26.8 L22.8 14.1 H16.9 Z" fill="#ffffff" />
            <rect x="22.4" y="6" width="4.2" height="4.2" rx="1.4" fill="#ff9a3d" />
        </svg>
    )
}
