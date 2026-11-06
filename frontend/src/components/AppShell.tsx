import { Outlet } from "react-router-dom"
import AuroraBackground from "./background/AuroraBackground"
import FloatingSidebar from "./nav/FloatingSidebar"
import { ShellContext } from "./shellContext"

/**
 * Coquille de l'application connectée : fond animé, sidebar flottante (dock en bas sur mobile) et contenu.
 * Les pages n'affichent plus leur propre barre du haut : la navigation est ici.
 */
export default function AppShell() {
    return (
        <ShellContext.Provider value={true}>
            <AuroraBackground />
            <FloatingSidebar />
            <div className="pb-28 md:pb-0 md:pl-24">
                <Outlet />
            </div>
        </ShellContext.Provider>
    )
}
