import { useEffect, useRef, useState, type ReactNode } from "react"

interface LazyMountProps {
    /** Hauteur réservée en px avant l'affichage, pour éviter tout décalage de mise en page. */
    height: number
    children: ReactNode
}

/**
 * Ne monte ses enfants que lorsqu'ils approchent de l'écran.
 * Sert aux graphiques Recharts situés bas dans la page : leur rendu (mesure des textes,
 * calcul des échelles) est coûteux et bloquerait le thread principal au chargement,
 * alors que l'utilisateur ne les voit pas encore.
 * Une fois monté, le contenu reste monté (pas de démontage au défilement).
 */
export default function LazyMount({ height, children }: LazyMountProps) {
    const ref = useRef<HTMLDivElement>(null)
    // Sans IntersectionObserver (très vieux navigateurs), on affiche directement
    const [visible, setVisible] = useState(() => typeof IntersectionObserver === "undefined")

    useEffect(() => {
        const el = ref.current
        if (!el || typeof IntersectionObserver === "undefined") return
        const observer = new IntersectionObserver(
            entries => {
                if (entries.some(e => e.isIntersecting)) {
                    setVisible(true)
                    observer.disconnect()
                }
            },
            { rootMargin: "400px 0px" }, // démarre un peu avant que le bloc soit visible
        )
        observer.observe(el)
        return () => observer.disconnect()
    }, [])

    return (
        <div ref={ref} style={visible ? undefined : { height }}>
            {visible ? children : null}
        </div>
    )
}
