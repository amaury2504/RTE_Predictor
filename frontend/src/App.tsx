import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider } from "./context/AuthContext"
import AppShell from "./components/AppShell"
import ProtectedRoute from "./components/ProtectedRoute"
import LoginPage from "./pages/LoginPage"
import PredictionPage from "./pages/PredictionPage"
import BenchmarkPage from "./pages/BenchmarkPage"
import ModelsPage from "./pages/ModelsPage"

// Page interne de réglage des animations : chargée à la demande et absente du bundle de production
const PlaygroundPage = import.meta.env.DEV ? lazy(() => import("./pages/PlaygroundPage")) : null

export default function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />

                    {/* Pages connectées : dans la coquille (sidebar flottante). Chaque onglet a sa route. */}
                    <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
                        <Route path="/predict" element={<PredictionPage />} />
                        <Route path="/benchmark" element={<Navigate to="/benchmark/overview" replace />} />
                        <Route path="/benchmark/:tab" element={<BenchmarkPage />} />
                        <Route path="/modeles" element={<ModelsPage />} />
                        {/* Ancienne page Robustesse : son analyse sur 7 jours est désormais un bouton de « Prédire » */}
                        <Route path="/performance" element={<Navigate to="/predict" replace />} />
                    </Route>
                    {/* Prédire est la page d'accueil de l'outil */}
                    <Route path="/" element={<Navigate to="/predict" replace />} />

                    {PlaygroundPage && (
                        <Route
                            path="/playground"
                            element={<Suspense fallback={null}><PlaygroundPage /></Suspense>}
                        />
                    )}
                    <Route path="*" element={<Navigate to="/login" replace />} />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    )
}
