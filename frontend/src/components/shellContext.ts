import { createContext, useContext } from "react"

/** Vrai quand la page est affichée dans la coquille (la barre du haut des anciennes pages est alors masquée). */
export const ShellContext = createContext(false)

export const useInShell = () => useContext(ShellContext)
