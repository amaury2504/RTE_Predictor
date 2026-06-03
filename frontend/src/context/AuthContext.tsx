import { createContext, useContext, useState } from "react"
import type { ReactNode } from "react"

interface AuthContextType {
    token: string | null
    setToken: (token: string | null) => void
    logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setTokenState] = useState<string | null>(
        () => localStorage.getItem("token")
    )

    const setToken = (newToken: string | null) => {
        if (newToken) {
            localStorage.setItem("token", newToken)
        } else {
            localStorage.removeItem("token")
        }
        setTokenState(newToken)
    }

    const logout = () => setToken(null)

    return (
        <AuthContext.Provider value={{ token, setToken, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error("useAuth must be used inside AuthProvider")
    return ctx
}
