import { BarChart3, LayoutDashboard, Settings, Target, Zap } from "lucide-react"
import GlassButton from "../glass/GlassButton"
import GlassCard from "../glass/GlassCard"

interface VariantPreviewProps {
    /** « A » : tout en bleu. « B » : bleu et orange. Les couleurs viennent de design/tokens.css. */
    variant: "A" | "B"
    title: string
    description: string
}

// Courbe d'illustration (décorative : aucun chiffre, aucun axe). Le « prédit » suit le « réel » avec un léger décalage.
const REAL = "M0,70 C40,60 60,20 100,28 S160,78 200,52 S260,14 300,30"
const PREDICTED = "M0,64 C40,58 62,26 100,32 S160,70 200,56 S262,20 300,34"

const ICONS = [LayoutDashboard, BarChart3, Target, Settings]

/** Un aperçu miniature du produit (sidebar, courbe réel/prédit, tuile, bouton) pour comparer deux partis pris de couleur. */
export default function VariantPreview({ variant, title, description }: VariantPreviewProps) {
    return (
        <figure data-variant={variant} className="space-y-3">
            <figcaption>
                <p className="text-base font-semibold text-[var(--text-1)]">{title}</p>
                <p className="text-sm text-[var(--text-2)]">{description}</p>
            </figcaption>

            <div className="flex gap-4 rounded-[var(--radius-card)] border border-[var(--glass-border)] bg-[var(--bg-1)] p-4">
                {/* Sidebar en pilule, lueur de marque en bas */}
                <nav
                    aria-label={`Aperçu de la navigation, variante ${variant}`}
                    className="relative flex w-14 shrink-0 flex-col items-center gap-4 overflow-hidden rounded-full border border-[var(--glass-border)] bg-[var(--glass-bg)] py-5"
                >
                    {ICONS.map((Icon, i) => (
                        <span
                            key={i}
                            className={`grid h-9 w-9 place-items-center rounded-full ${i === 0 ? "bg-white/15 text-white" : "text-[var(--text-2)]"}`}
                        >
                            <Icon size={18} aria-hidden="true" />
                        </span>
                    ))}
                    <span
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-x-0 bottom-0 h-24"
                        style={{ background: "radial-gradient(ellipse 100% 100% at 50% 100%, var(--brand-glow), transparent 75%)" }}
                    />
                </nav>

                <div className="min-w-0 flex-1 space-y-4">
                    <GlassCard className="p-4">
                        <p className="text-sm text-[var(--text-2)]">Réel et prédit (illustration)</p>
                        <svg viewBox="0 0 300 90" role="img" aria-label="Courbe réelle en trait plein, courbe prédite en pointillé" className="mt-2 w-full">
                            <path d={REAL} fill="none" stroke="var(--series-real)" strokeWidth="2.5" strokeLinecap="round" />
                            <path d={PREDICTED} fill="none" stroke="var(--series-predicted)" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="6 5" />
                        </svg>
                        {/* Légende : le sens ne repose pas sur la couleur seule (trait plein / pointillé) */}
                        <p className="mt-2 flex gap-5 text-xs text-[var(--text-2)]">
                            <span className="inline-flex items-center gap-2">
                                <svg width="22" height="4" aria-hidden="true"><line x1="0" y1="2" x2="22" y2="2" stroke="var(--series-real)" strokeWidth="2.5" /></svg>
                                Réel
                            </span>
                            <span className="inline-flex items-center gap-2">
                                <svg width="22" height="4" aria-hidden="true">
                                    <line x1="0" y1="2" x2="22" y2="2" stroke="var(--series-predicted)" strokeWidth="2.5" strokeDasharray="5 3" />
                                </svg>
                                Prédit
                            </span>
                        </p>
                    </GlassCard>

                    <div className="flex flex-wrap items-center gap-3">
                        <GlassButton primary>
                            <span className="inline-flex items-center gap-2"><Zap size={16} aria-hidden="true" /> Prédire</span>
                        </GlassButton>
                        <span className="inline-flex items-center gap-2 text-xs text-[var(--text-2)]">
                            <span className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--series-predicted)" }} aria-hidden="true" />
                            Modèle servi (prédiction)
                        </span>
                    </div>
                </div>
            </div>
        </figure>
    )
}
