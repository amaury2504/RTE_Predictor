/** Le jeton invité porte `sub: "guest"` (voir `POST /auth/guest`). Lecture seule, sans vérification de signature : sert à l'affichage. */
export function isGuestToken(token: string | null): boolean {
    if (!token) return false
    try {
        const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")))
        return payload.sub === "guest"
    } catch {
        return false
    }
}
