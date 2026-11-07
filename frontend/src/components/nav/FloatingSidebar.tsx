import { Fragment, useRef } from "react"
import { NavLink, useLocation, useNavigate } from "react-router-dom"
import { animate } from "animejs"
import { LogOut, User } from "lucide-react"
import { useAuth } from "../../context/AuthContext"
import { duration, springs } from "../../design/motion"
import { useAnimeScope } from "../../hooks/useAnimeScope"
import { useReducedMotion } from "../../hooks/useReducedMotion"
import { isGuestToken } from "../../lib/session"
import LogoMark from "../LogoMark"
import { ALL_ITEMS, NAV_GROUPS } from "./navItems"

const ITEM = 44 // hauteur d'un item (px) : sert à positionner l'indicateur
const SEPARATOR = 17 // filet entre deux groupes (8 + 1 + 8 px)

/** Pastille de statut : vert connecté, ambre invité. */
function Avatar({ guest }: { guest: boolean }) {
    return (
        <span className="relative grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[var(--glass-border)] bg-white/10">
            <User size={18} aria-hidden="true" />
            <span
                className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[var(--bg-1)]"
                style={{ background: guest ? "var(--state-warn)" : "var(--state-ok)" }}
                aria-hidden="true"
            />
        </span>
    )
}

/** Infobulle à droite d'une icône : au survol et au focus clavier. */
function Tooltip({ children }: { children: string }) {
    return (
        <span
            role="tooltip"
            className="pointer-events-none absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 whitespace-nowrap rounded-lg border border-[var(--glass-border)] bg-[var(--bg-1)] px-2.5 py-1 text-xs opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
        >
            {children}
        </span>
    )
}

/**
 * Sidebar flottante compacte (écran >= 768 px) : une pilule de verre d'icônes, qui ne s'élargit jamais et ne
 * recouvre donc jamais le contenu. Les noms apparaissent en infobulle. Une surbrillance unique glisse vers
 * l'élément actif.
 */
export default function FloatingSidebar() {
    const root = useRef<HTMLElement>(null)
    const indicator = useRef<HTMLSpanElement>(null)
    const { pathname } = useLocation()
    const navigate = useNavigate()
    const { token, logout } = useAuth()
    const reduce = useReducedMotion()
    const guest = isGuestToken(token)

    const activeIndex = ALL_ITEMS.findIndex(i => pathname === i.to || pathname.startsWith(`${i.to}/`))

    // Indicateur actif : un seul élément qui glisse (transform uniquement)
    useAnimeScope(root, () => {
        const el = indicator.current
        if (!el || activeIndex < 0) return
        animate(el, {
            translateY: indicatorOffset(activeIndex),
            opacity: 1,
            ...(reduce ? { duration: duration.fast } : { ease: springs.glide() }),
        })
    }, [activeIndex, reduce])

    return (
        <>
            <nav
                ref={root}
                aria-label="Navigation principale"
                className="glass-card fixed left-4 top-1/2 z-40 hidden w-16 -translate-y-1/2 flex-col items-center overflow-hidden !rounded-[32px] py-4 md:flex"
            >
                <LogoMark size={36} />

                <div className="relative mt-5 w-full px-2">
                    <span
                        ref={indicator}
                        aria-hidden="true"
                        className="absolute left-2 right-2 top-0 rounded-full bg-white/15 shadow-[inset_0_1px_0_var(--glass-highlight)]"
                        style={{ height: ITEM, opacity: 0 }}
                    />
                    {NAV_GROUPS.map((group, gi) => (
                        <Fragment key={group.id}>
                            {gi > 0 && <div className="mx-3 my-2 h-px bg-[var(--glass-border)]" aria-hidden="true" />}
                            <ul>
                                {group.items.map(item => (
                                    <li key={item.to} className="group relative">
                                        <NavLink
                                            to={item.to}
                                            aria-label={item.label}
                                            style={{ height: ITEM }}
                                            className={({ isActive }) =>
                                                `relative flex items-center justify-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-[var(--accent-soft)] ${isActive ? "text-white" : "text-[var(--text-2)] hover:text-white"}`}
                                        >
                                            <item.icon size={20} aria-hidden="true" />
                                        </NavLink>
                                        <Tooltip>{item.label}</Tooltip>
                                    </li>
                                ))}
                            </ul>
                        </Fragment>
                    ))}
                </div>

                <div className="mt-4 flex w-full flex-col items-center gap-1 px-2">
                    <div className="mb-2 h-px w-8 bg-[var(--glass-border)]" aria-hidden="true" />
                    <div className="group relative">
                        <Avatar guest={guest} />
                        <Tooltip>{guest ? "Invité" : "Connecté"}</Tooltip>
                    </div>
                    <div className="group relative w-full">
                        <button
                            onClick={() => { logout(); navigate("/login") }}
                            aria-label="Se déconnecter"
                            style={{ height: ITEM }}
                            className="flex w-full items-center justify-center rounded-full text-[var(--text-2)] transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-[var(--accent-soft)]"
                        >
                            <LogOut size={20} aria-hidden="true" />
                        </button>
                        <Tooltip>Déconnexion</Tooltip>
                    </div>
                </div>

                {/* Lueur de marque en bas de la pilule */}
                <span
                    aria-hidden="true"
                    className="pointer-events-none absolute inset-x-0 bottom-0 h-28"
                    style={{ background: "radial-gradient(ellipse 100% 100% at 50% 100%, var(--brand-glow), transparent 75%)" }}
                />
            </nav>

            <MobileDock guest={guest} />
        </>
    )
}

/** Position verticale de l'indicateur : les groupes sont séparés par un filet. */
function indicatorOffset(index: number): number {
    let count = 0
    let offset = 0
    for (const group of NAV_GROUPS) {
        const size = group.items.length
        if (index < count + size) return offset + (index - count) * ITEM
        count += size
        offset += size * ITEM + SEPARATOR
    }
    return 0
}

/** Écran < 768 px : la navigation devient un dock horizontal flottant en bas. */
function MobileDock({ guest }: { guest: boolean }) {
    return (
        <nav
            aria-label="Navigation principale (mobile)"
            className="glass-card fixed inset-x-4 bottom-4 z-40 flex items-center justify-around !rounded-full px-2 py-2 md:hidden"
        >
            {ALL_ITEMS.map(item => (
                <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                        `flex flex-col items-center gap-0.5 rounded-full px-4 py-1.5 text-[11px] focus-visible:outline-2 focus-visible:outline-[var(--accent-soft)] ${isActive ? "bg-white/15 text-white" : "text-[var(--text-2)]"}`}
                >
                    <item.icon size={20} aria-hidden="true" />
                    {item.shortLabel ?? item.label}
                </NavLink>
            ))}
            <span className="px-3" role="img" aria-label={guest ? "Mode invité" : "Connecté"}>
                <Avatar guest={guest} />
            </span>
        </nav>
    )
}
