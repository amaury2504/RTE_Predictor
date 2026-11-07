import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { login, register, loginAsGuest } from "../services/api"
import { useAuth } from "../context/AuthContext"
import LogoMark from "../components/LogoMark"

export default function LoginPage() {
    const [mode, setMode] = useState<"login" | "register">("login")
    const [mail, setMail] = useState("")
    const [password, setPassword] = useState("")
    const [error, setError] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)
    const [showPassword, setShowPassword] = useState(false)

    const { setToken } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)
        setLoading(true)
        try {
            if (mode === "register") {
                await register(mail, password)
                setMode("login")
                setError(null)
                setPassword("")
                return
            }
            const token = await login(mail, password)
            setToken(token)
            navigate("/predict")
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Erreur inconnue")
        } finally {
            setLoading(false)
        }
    }

    const inputClass =
        "w-full rounded-lg border border-line bg-raised px-4 py-2.5 text-sm text-ink placeholder-faint transition-colors focus:border-neon focus:outline-none focus:ring-1 focus:ring-neon"

    const tabClass = (active: boolean) =>
        `flex-1 rounded-md py-2 text-sm font-medium transition-all ${
            active ? "bg-surface text-neon-soft shadow-glow" : "text-muted hover:text-ink"
        }`

    const handleGuest = async () => {
        setError(null)
        setLoading(true)
        try {
            const token = await loginAsGuest()
            setToken(token)
            navigate("/predict")
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Erreur inconnue")
        } finally {
            setLoading(false)
        }
    }

    return (
        <main className="flex min-h-screen items-center justify-center px-4">
            <div className="w-full max-w-md">
                <div className="mb-8 flex flex-col items-center text-center">
                    <LogoMark size={44} />
                    <h1 className="mt-4 text-2xl font-semibold tracking-tight text-ink">ML Predictor</h1>
                    <p className="mt-1 text-sm text-muted">Prédiction de consommation électrique</p>
                </div>

                <div className="rounded-xl border border-line bg-surface p-8 shadow-card">
                    <div className="mb-6 flex rounded-lg border border-line bg-canvas p-1">
                        <button
                            onClick={() => { setMode("login"); setError(null) }}
                            className={tabClass(mode === "login")}
                        >
                            Connexion
                        </button>
                        <button
                            onClick={() => { setMode("register"); setError(null) }}
                            className={tabClass(mode === "register")}
                        >
                            Inscription
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-muted">
                                Adresse email
                            </label>
                            <input
                                type="email"
                                required
                                value={mail}
                                onChange={e => setMail(e.target.value)}
                                placeholder="vous@exemple.fr"
                                className={inputClass}
                            />
                        </div>

                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-muted">
                                Mot de passe
                            </label>
                            <input
                                type={showPassword ? "text" : "password"}
                                required
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className={inputClass}
                            />
                            <label className="mt-2 flex w-fit cursor-pointer items-center gap-2 text-xs text-muted transition-colors hover:text-ink">
                                <input
                                    type="checkbox"
                                    checked={showPassword}
                                    onChange={e => setShowPassword(e.target.checked)}
                                />
                                Afficher le mot de passe
                            </label>
                        </div>

                        {error && (
                            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                                {error}
                            </div>
                        )}

                        {mode === "register" && !error && (
                            <div className="rounded-lg border border-neon/30 bg-neon/10 px-4 py-3 text-sm text-neon-soft">
                                Après inscription, connectez-vous avec vos identifiants.
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full rounded-lg bg-neon py-2.5 text-sm font-semibold text-canvas shadow-glow transition-colors hover:bg-neon-soft disabled:opacity-40 disabled:shadow-none"
                        >
                            {loading
                                ? "Chargement..."
                                : mode === "login"
                                ? "Se connecter"
                                : "Créer un compte"}
                        </button>
                    </form>
                </div>

                {/* Mode démo : accès sans compte */}
                <button
                    type="button"
                    onClick={handleGuest}
                    disabled={loading}
                    className="mt-4 w-full rounded-lg border border-line bg-surface/60 py-2.5 text-sm text-muted transition-colors hover:border-neon/50 hover:text-neon-soft disabled:opacity-40"
                >
                    Continuer avec un profil invité
                </button>
            </div>
        </main>
    )
}
