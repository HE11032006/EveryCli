# EveryCli - installeur Windows.
#
# Usage :
#   Par defaut -- tente le mecanisme le plus avantageux (service Windows
#   natif : redemarrage auto en cas de crash, demarre avant connexion
#   utilisateur), via auto-elevation UAC (comme Docker Desktop) :
#     .\install.ps1 -LocalSource "dist\windows"
#   Sans jamais demander l'elevation (dossier Demarrage directement,
#   aucune permission speciale, mais pas de redemarrage auto en cas de
#   crash et ne demarre qu'a l'ouverture de session) :
#     .\install.ps1 -LocalSource "dist\windows" -NoService
#
# Ce que ca fait :
#   1. Place les binaires/modele/runtime/corpus dans %LOCALAPPDATA%\EveryCli
#   2. Ajoute le dossier bin au PATH utilisateur (pas besoin d'admin)
#   3. Arrete toute instance du daemon deja active (service OU processus
#      autonome) ET retire les artefacts de l'AUTRE mecanisme -- jamais
#      deux daemons actifs en meme temps qui se disputent le port
#   4. Installe/demarre le daemon selon le mode choisi, attend qu'il
#      reponde vraiment avant de conclure (pas un delai fixe arbitraire)
#
# Debogage du mode service : toute la sortie du processus elevee est
# capturee via Start-Transcript dans %LOCALAPPDATA%\EveryCli\logs\install-service.log

param(
    [string]$LocalSource = "",
    [string]$InstallDir = "$env:LOCALAPPDATA\EveryCli",
    [string]$Version = "latest",
    [switch]$NoService
)

$ErrorActionPreference = "Stop"

function Test-Elevated {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Stop-ExistingDaemon {
    sc.exe query EveryCliDaemon 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Arret du service EveryCliDaemon existant..."
        sc.exe stop EveryCliDaemon 2>$null | Out-Null
        Start-Sleep -Seconds 1
    }
    $proc = Get-Process everycli-daemon -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Arret du processus everycli-daemon existant (PID $($proc.Id))..."
        $proc | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
}

function Remove-StartupLauncher {
    $StartupDir = [Environment]::GetFolderPath("Startup")
    $path = Join-Path $StartupDir "EveryCliDaemon.vbs"
    if (Test-Path $path) {
        Write-Host "Retrait de l'ancien lanceur du dossier Demarrage..."
        Remove-Item $path -Force -ErrorAction SilentlyContinue
    }
}

function Remove-WindowsServiceIfPresent {
    sc.exe query EveryCliDaemon 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Suppression de l'ancien service EveryCliDaemon..."
        sc.exe stop EveryCliDaemon 2>$null | Out-Null
        Start-Sleep -Seconds 1
        sc.exe delete EveryCliDaemon 2>$null | Out-Null
    }
}

function Wait-ForDaemon {
    param([int]$TimeoutSeconds = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $client.Connect("127.0.0.1", 51821)
            $stream = $client.GetStream()
            $writer = New-Object System.IO.StreamWriter($stream)
            $writer.AutoFlush = $true
            $writer.WriteLine('{"action":"ping"}')
            $reader = New-Object System.IO.StreamReader($stream)
            $response = $reader.ReadLine()
            $client.Close()
            if ($response -like '*"pong":true*') {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

$useService = -not $NoService
$transcriptStarted = $false

if ($useService -and (Test-Elevated)) {
    # On est le processus elevee (relance depuis le bloc ci-dessous) --
    # demarre la capture de log EN TOUT PREMIER, avant toute autre
    # operation, pour ne rien perdre meme si quelque chose plante plus loin.
    $logDir = Join-Path $InstallDir "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $elevatedLogPath = Join-Path $logDir "install-service.log"
    try {
        Start-Transcript -Path $elevatedLogPath -Force | Out-Null
        $transcriptStarted = $true
    } catch {
        Write-Host "Avertissement : Start-Transcript a echoue." -ForegroundColor Yellow
    }
    trap {
        Write-Host "ERREUR : $_" -ForegroundColor Red
        if ($transcriptStarted) { Stop-Transcript | Out-Null }
        exit 1
    }
}

Write-Host "=== Installation d'EveryCli ===" -ForegroundColor Cyan

# --- 0. Par defaut, tente le mecanisme le plus avantageux (service Windows
# natif) via auto-elevation UAC. -NoService saute directement au mode sans
# droits admin. Si l'elevation est refusee/echoue, repli automatique --
# jamais d'echec bloquant sur ce choix.
if ($useService -and -not (Test-Elevated)) {
    Write-Host "Installation en service Windows (recommande : redemarrage auto en cas de crash) -- une invite va apparaitre..." -ForegroundColor Yellow
    Write-Host "(Utilise -NoService pour installer sans droits admin, dans le dossier Demarrage a la place.)"

    if ($LocalSource -ne "") {
        $LocalSource = (Resolve-Path $LocalSource).Path
    }

    $logDir = Join-Path $InstallDir "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $elevatedLogPath = Join-Path $logDir "install-service.log"
    Remove-Item $elevatedLogPath -ErrorAction SilentlyContinue

    $forwardedArgs = @("-LocalSource", $LocalSource, "-InstallDir", $InstallDir)
    $elevationRan = $false
    try {
        Start-Process -FilePath "powershell.exe" `
            -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $PSCommandPath) + $forwardedArgs) `
            -Verb RunAs -Wait -WorkingDirectory $PSScriptRoot
        $elevationRan = $true
    } catch {
        Write-Host "Elevation refusee ou echouee." -ForegroundColor Yellow
    }

    if ($elevationRan) {
        Write-Host ""
        Write-Host "=== Log du processus elevee ===" -ForegroundColor Cyan
        if (Test-Path $elevatedLogPath) {
            Get-Content $elevatedLogPath | Write-Host
        } else {
            Write-Host "Aucun log genere." -ForegroundColor Yellow
        }
        exit 0
    }

    Write-Host "Repli sur installation sans droits admin (dossier Demarrage)..." -ForegroundColor Yellow
    $useService = $false
}

# --- 1. Obtenir les fichiers (local ou telechargement) ---
if ($LocalSource -ne "") {
    if (-not (Test-Path $LocalSource)) {
        Write-Error "Dossier source introuvable : $LocalSource"
        exit 1
    }
    Write-Host "Source locale : $LocalSource"
    $Source = $LocalSource
} else {
    # Convention : un seul zip par OS, nommé "everycli-windows.zip",
    # attaché en asset de release GitHub, contenant directement les
    # dossiers bin/model/runtime/data (même structure que produit
    # scripts\windows\stage-release.ps1). PAS ENCORE TESTE de bout en
    # bout -- aucune release publique avec ces binaires n'existe à ce jour.
    $repo = "HE11032006/EveryCli"
    $releaseUrl = if ($Version -eq "latest") {
        "https://github.com/$repo/releases/latest/download/everycli-windows.zip"
    } else {
        "https://github.com/$repo/releases/download/$Version/everycli-windows.zip"
    }

    $tempZip = Join-Path $env:TEMP "everycli-$([guid]::NewGuid()).zip"
    $tempExtract = Join-Path $env:TEMP "everycli-$([guid]::NewGuid())"

    Write-Host "Telechargement depuis $releaseUrl..."
    try {
        Invoke-WebRequest -Uri $releaseUrl -OutFile $tempZip -UseBasicParsing
    } catch {
        Write-Error "Echec du telechargement depuis $releaseUrl -- verifie que la release existe, ou utilise -LocalSource pour installer depuis un dossier local prepare par stage-release.ps1."
        exit 1
    }

    Write-Host "Extraction..."
    Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
    Remove-Item $tempZip -ErrorAction SilentlyContinue

    # Le zip peut contenir directement bin/model/runtime/data a la racine,
    # ou un seul dossier englobant (GitHub ajoute parfois ca automatiquement
    # selon comment l'asset a ete construit) -- on detecte les deux cas.
    if (Test-Path (Join-Path $tempExtract "bin")) {
        $Source = $tempExtract
    } else {
        $inner = Get-ChildItem $tempExtract -Directory | Select-Object -First 1
        if ($inner -and (Test-Path (Join-Path $inner.FullName "bin"))) {
            $Source = $inner.FullName
        } else {
            Write-Error "Structure inattendue dans l'archive telechargee (pas de dossier 'bin' trouve)."
            exit 1
        }
    }
    Write-Host "Telecharge et extrait dans $Source"
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

[Environment]::SetEnvironmentVariable("EVERYCLI_MODEL_DIR", "$InstallDir\model", "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_ONNXRUNTIME_DYLIB", "$InstallDir\runtime\onnxruntime.dll", "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_DATA_DIR", "$InstallDir\data\commands", "User")

# --- 4. Nettoyage : une seule instance active possible, jamais deux
# mecanismes qui se disputent le port 51821 ---
Stop-ExistingDaemon
if ($useService) {
    Remove-StartupLauncher
} elseif (Test-Elevated) {
    Remove-WindowsServiceIfPresent
} else {
    sc.exe query EveryCliDaemon 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Un ancien service EveryCliDaemon existe encore -- il ne peut pas etre retire sans droits admin." -ForegroundColor Yellow
        Write-Host "Lance 'sc.exe delete EveryCliDaemon' depuis un terminal admin si tu veux le nettoyer."
    }
}

# --- 5. Demarrage selon le mode choisi ---
if ($useService) {
    Write-Host "Installation en tant que service Windows..."
    $binPath = "`"$InstallDir\bin\everycli-daemon.exe`" --service"

    sc.exe create EveryCliDaemon binPath= $binPath start= auto DisplayName= "EveryCli Daemon" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Echec de la creation du service -- repli sur le dossier Demarrage." -ForegroundColor Yellow
        $useService = $false
    }
}

if ($useService) {
    $envRegPath = "HKLM:\SYSTEM\CurrentControlSet\Services\EveryCliDaemon"
    $envVars = @(
        "EVERYCLI_MODEL_DIR=$InstallDir\model",
        "EVERYCLI_ONNXRUNTIME_DYLIB=$InstallDir\runtime\onnxruntime.dll",
        "EVERYCLI_DATA_DIR=$InstallDir\data\commands"
    )
    Set-ItemProperty -Path $envRegPath -Name "Environment" -Value $envVars -Type MultiString

    Write-Host "Demarrage du service..."
    sc.exe start EveryCliDaemon | Out-Null

    Write-Host "Attente que le daemon soit pret (calcul des embeddings du corpus, jusqu'a ~30s au premier demarrage)..."
    if (Wait-ForDaemon -TimeoutSeconds 30) {
        Write-Host "Service EveryCliDaemon installe, demarre, cache d'embeddings ecrit sur disque." -ForegroundColor Green
    } else {
        Write-Host "Le daemon ne repond pas encore apres 30s -- verifie : sc.exe query EveryCliDaemon" -ForegroundColor Yellow
        Write-Host "et les logs : $InstallDir\logs\daemon.log"
    }
} else {
    $LauncherPath = "$InstallDir\bin\run-daemon.cmd"
    @"
@echo off
set EVERYCLI_MODEL_DIR=$InstallDir\model
set EVERYCLI_ONNXRUNTIME_DYLIB=$InstallDir\runtime\onnxruntime.dll
set EVERYCLI_DATA_DIR=$InstallDir\data\commands
"$InstallDir\bin\everycli-daemon.exe" >> "$InstallDir\logs\daemon.log" 2>&1
"@ | Set-Content -Path $LauncherPath -Encoding ASCII

    $HiddenLauncherPath = "$InstallDir\bin\run-daemon-hidden.vbs"
    @"
Set objShell = CreateObject("WScript.Shell")
objShell.Run """$LauncherPath""", 0, False
"@ | Set-Content -Path $HiddenLauncherPath -Encoding ASCII

    Write-Host "Enregistrement dans le dossier Demarrage..."
    $StartupDir = [Environment]::GetFolderPath("Startup")
    Copy-Item $HiddenLauncherPath "$StartupDir\EveryCliDaemon.vbs" -Force

    Write-Host "Demarrage du daemon..."
    Start-Process -FilePath $LauncherPath -WindowStyle Hidden

    Write-Host "Attente que le daemon soit pret (calcul des embeddings du corpus, jusqu'a ~30s au premier demarrage)..."
    if (Wait-ForDaemon -TimeoutSeconds 30) {
        Write-Host "Daemon pret, cache d'embeddings calcule et ecrit sur disque." -ForegroundColor Green
    } else {
        Write-Host "Le daemon ne repond pas encore apres 30s -- verifie les logs : $InstallDir\logs\daemon.log" -ForegroundColor Yellow
        Write-Host "everycli fonctionnera quand meme en mode recherche locale en attendant."
    }
}

Write-Host ""
Write-Host "=== Installation terminee ===" -ForegroundColor Green
Write-Host "Ouvre un NOUVEAU terminal et tape : everycli search ""ta requete"""
Write-Host "Logs du daemon : $InstallDir\logs\daemon.log"

if ($transcriptStarted) {
    Stop-Transcript | Out-Null
}
