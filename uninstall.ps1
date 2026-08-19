# EveryCli - desinstalleur Windows.
#
# Usage :
#   .\uninstall.ps1
#   .\uninstall.ps1 -RemoveUserCommands   # supprime aussi ~/.everycli (tes commandes perso)
#
# Ce que ca fait : arrete et retire le service Windows (si present, demande
# l'elevation UAC automatiquement seulement dans ce cas), retire le lanceur
# du dossier Demarrage (si present), nettoie le PATH et les variables
# d'environnement persistantes, supprime le dossier d'installation.
# Les commandes personnalisees (~/.everycli) sont conservees par defaut --
# ce sont des donnees utilisateur, pas des fichiers d'installation.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\EveryCli",
    [switch]$RemoveUserCommands
)

$ErrorActionPreference = "Stop"

function Test-Elevated {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Host "=== Desinstallation d'EveryCli ===" -ForegroundColor Cyan

$serviceExists = $false
sc.exe query EveryCliDaemon 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $serviceExists = $true
}

# --- 0. Le service (s'il existe) necessite les droits admin pour etre
# retire -- auto-elevation seulement dans ce cas, comme install.ps1.
if ($serviceExists -and -not (Test-Elevated)) {
    Write-Host "Un service EveryCliDaemon existe -- droits administrateur necessaires pour le retirer, une invite va apparaitre..." -ForegroundColor Yellow

    $forwardedArgs = @("-InstallDir", $InstallDir)
    if ($RemoveUserCommands) { $forwardedArgs += "-RemoveUserCommands" }

    try {
        Start-Process -FilePath "powershell.exe" `
            -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $PSCommandPath) + $forwardedArgs) `
            -Verb RunAs -Wait -WorkingDirectory $PSScriptRoot
    } catch {
        Write-Host "Elevation refusee ou echouee -- desinstallation annulee, le service reste actif." -ForegroundColor Yellow
    }
    exit 0
}

# --- 1. Arreter et retirer le service (si present) ---
if ($serviceExists) {
    Write-Host "Arret et suppression du service EveryCliDaemon..."
    sc.exe stop EveryCliDaemon 2>$null | Out-Null
    Start-Sleep -Seconds 1
    sc.exe delete EveryCliDaemon 2>$null | Out-Null
}

# --- 2. Tuer tout processus autonome (dossier Demarrage ou lance a la main) ---
$proc = Get-Process everycli-daemon -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "Arret du processus everycli-daemon (PID $($proc.Id))..."
    $proc | Stop-Process -Force -ErrorAction SilentlyContinue
}

# --- 3. Retirer le lanceur du dossier Demarrage ---
$StartupDir = [Environment]::GetFolderPath("Startup")
$startupLauncher = Join-Path $StartupDir "EveryCliDaemon.vbs"
if (Test-Path $startupLauncher) {
    Write-Host "Retrait du lanceur du dossier Demarrage..."
    Remove-Item $startupLauncher -Force -ErrorAction SilentlyContinue
}

# --- 4. Retirer du PATH utilisateur ---
$BinDir = "$InstallDir\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -and $currentPath -like "*$BinDir*") {
    Write-Host "Retrait de $BinDir du PATH utilisateur..."
    $newPath = ($currentPath -split ';' | Where-Object { $_ -and $_ -ne $BinDir }) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

# --- 5. Retirer les variables d'environnement persistantes ---
[Environment]::SetEnvironmentVariable("EVERYCLI_MODEL_DIR", $null, "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_ONNXRUNTIME_DYLIB", $null, "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_DATA_DIR", $null, "User")

# --- 6. Supprimer le dossier d'installation ---
if (Test-Path $InstallDir) {
    Write-Host "Suppression de $InstallDir..."
    Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
}

# --- 7. Commandes personnalisees -- conservees par defaut (donnees
# utilisateur, pas des fichiers d'installation) ---
$userCommandsDir = Join-Path $env:USERPROFILE ".everycli"
if (Test-Path $userCommandsDir) {
    if ($RemoveUserCommands) {
        Write-Host "Suppression des commandes personnalisees ($userCommandsDir)..."
        Remove-Item -Recurse -Force $userCommandsDir -ErrorAction SilentlyContinue
    } else {
        Write-Host "Tes commandes personnalisees sont conservees dans $userCommandsDir"
        Write-Host "(relance avec -RemoveUserCommands si tu veux aussi les supprimer)"
    }
}

Write-Host ""
Write-Host "=== EveryCli desinstalle ===" -ForegroundColor Green
Write-Host "Ouvre un nouveau terminal pour que le retrait du PATH prenne effet."
