# EveryCli - installeur Windows.
#
# Usage :
#   Test local (avant qu'une vraie release existe) :
#     .\install.ps1 -LocalSource "dist\windows"
#
# Ce que ca fait :
#   1. Place les binaires/modele/runtime/corpus dans %LOCALAPPDATA%\EveryCli
#   2. Ajoute le dossier bin au PATH utilisateur (pas besoin d'admin)
#   3. Depose un lanceur dans le dossier Demarrage de Windows (shell:startup)
#      pour lancer le daemon a l'ouverture de session, sans fenetre visible
#      -- alternative au Planificateur de taches, qui ne demande AUCUNE
#      permission speciale (contrairement a schtasks, qui peut etre bloque
#      par des restrictions locales/de groupe sur certaines machines)
#   4. Demarre le daemon immediatement

param(
    [string]$LocalSource = "",
    [string]$InstallDir = "$env:LOCALAPPDATA\EveryCli",
    [string]$Version = "latest"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Installation d'EveryCli ===" -ForegroundColor Cyan

# --- 1. Obtenir les fichiers (local ou telechargement) ---
if ($LocalSource -ne "") {
    if (-not (Test-Path $LocalSource)) {
        Write-Error "Dossier source introuvable : $LocalSource"
        exit 1
    }
    Write-Host "Source locale : $LocalSource"
    $Source = $LocalSource
} else {
    # NOTE : pas encore de release GitHub publique avec les binaires Rust.
    # Utilise -LocalSource avec un dossier prepare par
    # scripts\windows\stage-release.ps1 en attendant.
    Write-Error "Le telechargement depuis une release GitHub n'est pas encore disponible. Utilise -LocalSource."
    exit 1
}

# --- 2. Copier vers le dossier d'installation ---
Write-Host "Installation dans $InstallDir..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\logs" | Out-Null

Copy-Item "$Source\bin" "$InstallDir\" -Recurse -Force
Copy-Item "$Source\model" "$InstallDir\" -Recurse -Force
Copy-Item "$Source\runtime" "$InstallDir\" -Recurse -Force
Copy-Item "$Source\data" "$InstallDir\" -Recurse -Force

# --- 3. Ajouter au PATH utilisateur (idempotent) ---
$BinDir = "$InstallDir\bin"
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$BinDir*") {
    Write-Host "Ajout de $BinDir au PATH utilisateur..."
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;$BinDir", "User")
} else {
    Write-Host "$BinDir est deja dans le PATH."
}

# Variables d'environnement persistantes -- utiles si l'utilisateur lance
# everycli-daemon.exe manuellement depuis un terminal pour deboguer. Le
# lanceur (run-daemon.cmd, plus bas) ne depend PAS de ces variables : il
# est autonome via des chemins absolus generes a l'installation.
[Environment]::SetEnvironmentVariable("EVERYCLI_MODEL_DIR", "$InstallDir\model", "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_ONNXRUNTIME_DYLIB", "$InstallDir\runtime\onnxruntime.dll", "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_DATA_DIR", "$InstallDir\data\commands", "User")

# --- 4. Lanceur autonome (variables d'environnement + logs) ---
$LauncherPath = "$InstallDir\bin\run-daemon.cmd"
@"
@echo off
set EVERYCLI_MODEL_DIR=$InstallDir\model
set EVERYCLI_ONNXRUNTIME_DYLIB=$InstallDir\runtime\onnxruntime.dll
set EVERYCLI_DATA_DIR=$InstallDir\data\commands
"$InstallDir\bin\everycli-daemon.exe" >> "$InstallDir\logs\daemon.log" 2>&1
"@ | Set-Content -Path $LauncherPath -Encoding ASCII

# --- 5. Lanceur invisible (VBScript, pas de fenetre console au demarrage) ---
$HiddenLauncherPath = "$InstallDir\bin\run-daemon-hidden.vbs"
@"
Set objShell = CreateObject("WScript.Shell")
objShell.Run """$LauncherPath""", 0, False
"@ | Set-Content -Path $HiddenLauncherPath -Encoding ASCII

# --- 6. Deposer dans le dossier Demarrage de Windows (aucune permission requise) ---
Write-Host "Enregistrement dans le dossier Demarrage..."
$StartupDir = [Environment]::GetFolderPath("Startup")
Copy-Item $HiddenLauncherPath "$StartupDir\EveryCliDaemon.vbs" -Force

# --- 7. Demarrer maintenant (pas besoin d'attendre le prochain login) ---
Write-Host "Demarrage du daemon..."
Start-Process -FilePath $LauncherPath -WindowStyle Hidden
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "=== Installation terminee ===" -ForegroundColor Green
Write-Host "Ouvre un NOUVEAU terminal et tape : everycli search ""ta requete"""
Write-Host "Logs du daemon : $InstallDir\logs\daemon.log"
