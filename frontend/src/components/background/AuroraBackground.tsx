import { useEffect, useState } from "react"

/**
 * Fond de rubans lumineux bleus, abstraits, qui dérivent très lentement derrière les surfaces en verre.
 * Léger : trois formes floutées animées en `transform` (cycles de 26 à 40 s), aucune bibliothèque.
 * Mis en pause quand l'onglet est masqué ; figé si les animations sont réduites (règles CSS).
 * Purement décoratif : masqué aux lecteurs d'écran.
 */
export default function AuroraBackground() {
    const [paused, setPaused] = useState(() => typeof document !== "undefined" && document.hidden)

    useEffect(() => {
        const onChange = () => setPaused(document.hidden)
        document.addEventListener("visibilitychange", onChange)
        return () => document.removeEventListener("visibilitychange", onChange)
    }, [])

    return (
        <div
            aria-hidden="true"
            className={`pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-[var(--bg-0)] ${paused ? "aurora-paused" : ""}`}
        >
            <div
                className="aurora-ribbon"
                style={{
                    width: "70vw", height: "26vw", left: "-10vw", top: "8vh",
                    background: "linear-gradient(90deg, rgba(30,160,255,0), rgba(30,160,255,0.55), rgba(92,192,255,0.15))",
                    animation: "aurora-drift-a 34s ease-in-out infinite",
                }}
            />
            <div
                className="aurora-ribbon"
                style={{
                    width: "60vw", height: "20vw", right: "-14vw", top: "46vh",
                    background: "linear-gradient(90deg, rgba(43,120,224,0.5), rgba(30,160,255,0.2), rgba(30,160,255,0))",
                    animation: "aurora-drift-b 40s ease-in-out infinite",
                }}
            />
            <div
                className="aurora-ribbon"
                style={{
                    width: "46vw", height: "46vw", left: "30vw", top: "-22vw",
                    background: "radial-gradient(closest-side, rgba(30,160,255,0.28), rgba(30,160,255,0))",
                    animation: "aurora-drift-c 26s ease-in-out infinite",
                }}
            />
            {/* Dégradé vers le fond en bas de page, pour garder le texte lisible */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[var(--bg-0)]" />
        </div>
    )
}
