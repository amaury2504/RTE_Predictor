import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider } from "./context/AuthContext"
import ProtectedRoute from "./components/ProtectedRoute"
import LoginPage from "./pages/LoginPage"
import PredictionPage from "./pages/PredictionPage"
import ModelPerformancePage from "./pages/ModelPerformancePage"

export default function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route
                        path="/predict"
                        element={
                            <ProtectedRoute>
                                <PredictionPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/performance"
                        element={
                            <ProtectedRoute>
                                <ModelPerformancePage />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="*" element={<Navigate to="/login" replace />} />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    )
}
