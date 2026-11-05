# Entraîne et évalue TOUS les modèles du benchmark, d'une traite (prévu pour la nuit).
#
# Ordre : références, lissage exponentiel et Timestral (rapides, pour détecter une erreur tout de suite),
# puis le MLP (long : 4 graines), puis Ridge, LightGBM et la piste B (5 graines).
# Chaque exécution terminée est sauvegardée dans benchmark_cache/ : si le calcul est interrompu (coupure, plantage),
# relancer ce même script reprend là où il s'est arrêté, sans rien refaire.
#
# Usage, depuis n'importe où :   powershell -ExecutionPolicy Bypass -File backend\scripts\run_night.ps1
# La sortie s'affiche en direct dans la fenêtre (barre de progression comprise) et est aussi écrite dans
# backend\benchmark_night.log. Résultats finaux : backend\benchmark\.

Set-Location (Join-Path $PSScriptRoot "..")

# Empêche la mise en veille tant que ce script tourne (aucun réglage de Windows n'est modifié durablement)
Add-Type -Namespace Win -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);'
[Win.Power]::SetThreadExecutionState(0x80000001) | Out-Null   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

try {
    Write-Host "Début : $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
    # Pas de tube ni de redirection : la sortie de Python va directement à la console (barre de progression en direct),
    # et Python écrit lui-même le journal (--log).
    & .\.venv\Scripts\python.exe scripts/run_benchmark.py --seeds 5 --heavy-seeds 4 --log benchmark_night.log
    Write-Host "Fin : $(Get-Date -Format 'dd/MM/yyyy HH:mm') (code de sortie Python : $LASTEXITCODE)"
}
finally {
    [Win.Power]::SetThreadExecutionState(0x80000000) | Out-Null   # ES_CONTINUOUS : la veille redevient possible
}
