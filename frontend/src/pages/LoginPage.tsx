import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { login, register } from "../services/api"
import { useAuth } from "../context/AuthContext"

export default function LoginPage() {
    const [mode, setMode] = useState<"login" | "register">("login")
    const [mail, setMail] = useState("")
    const [password, setPassword] = useState("")
    const [error, setError] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)

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

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <span className="text-4xl">⚡</span>
                    <h1 className="text-2xl font-bold text-gray-900 mt-2">RTE Predictor</h1>
                    <p className="text-gray-500 text-sm mt-1">Prédiction de consommation électrique</p>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
                    <div className="flex rounded-lg bg-gray-100 p-1 mb-6">
                        <button
                            onClick={() => { setMode("login"); setError(null) }}
                            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                                mode === "login"
                                    ? "bg-white text-gray-900 shadow-sm"
                                    : "text-gray-500 hover:text-gray-700"
                            }`}
                        >
                            Connexion
                        </button>
                        <button
                            onClick={() => { setMode("register"); setError(null) }}
                            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                                mode === "register"
                                    ? "bg-white text-gray-900 shadow-sm"
                                    : "text-gray-500 hover:text-gray-700"
                            }`}
                        >
                            Inscription
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Adresse email
                            </label>
                            <input
                                type="email"
                                required
                                value={mail}
                                onChange={e => setMail(e.target.value)}
                                placeholder="vous@exemple.fr"
                                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Mot de passe
                            </label>
                            <input
                                type="password"
                                required
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                            />
                        </div>

                        {error && (
                            <div className="bg-red-50 border border-red-100 text-red-600 text-sm rounded-lg px-4 py-3">
                                {error}
                            </div>
                        )}

                        {mode === "register" && !error && (
                            <div className="bg-green-50 border border-green-100 text-green-700 text-sm rounded-lg px-4 py-3">
                                Après inscription, connectez-vous avec vos identifiants.
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
                        >
                            {loading
                                ? "Chargement..."
                                : mode === "login"
                                ? "Se connecter"
                                : "Créer un compte"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}
