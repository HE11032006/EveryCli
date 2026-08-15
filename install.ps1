# EveryCli - installeur Windows.
#
# Usage :
#   Mode par defaut (aucune permission speciale) :
#     .\install.ps1 -LocalSource "dist\windows"
#   Mode service Windows natif (redemarre meme avant connexion utilisateur,
#   relance auto en cas de crash -- necessite les droits admin, invite UAC
#   automatique) :
#     .\install.ps1 -LocalSource "dist\windows" -Service
#
# Ce que ca fait :
#   1. Place les binaires/modele/runtime/corpus dans %LOCALAPPDATA%\EveryCli
#   2. Ajoute le dossier bin au PATH utilisateur (pas besoin d'admin)
#   3a. Par defaut : depose un lanceur dans le dossier Demarrage de Windows
#       (shell:startup) -- aucune permission speciale, mais ne demarre qu'a
#       l'ouverture de session utilisateur.
#   3b. Avec -Service : installe un vrai service Windows (SCM), demarrage
#       automatique meme avant connexion, relance auto en cas de crash geree
#       par Windows -- necessite les droits admin. Si l'invite UAC est
#       refusee ou echoue, repli automatique sur le mode 3a.
#   4. Demarre le daemon et attend qu'il reponde vraiment avant de conclure
#
# Debogage du mode -Service : toute la sortie du processus elevee est
# capturee via Start-Transcript dans %LOCALAPPDATA%\EveryCli\logs\install-service.log
# -- consulte ce fichier si quelque chose semble avoir echoue silencieusement.

param(
    [string]$LocalSource = "",
    [string]$InstallDir = "$env:LOCALAPPDATA\EveryCli",
    [string]$Version = "latest",
    [switch]$Service
)

$ErrorActionPreference = "Stop"

function Test-Elevated {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$transcriptStarted = $false
if ($Service -and (Test-Elevated)) {
    # On est le processus elevee (relance depuis le bloc ci-dessous, ou
    # lance directement par quelqu'un deja admin) -- demarre la capture de
    # log EN TOUT PREMIER, avant toute autre operation, pour ne rien perdre
    # meme si quelque chose plante plus loin dans le script.
    $logDir = Join-Path $InstallDir "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $elevatedLogPath = Join-Path $logDir "install-service.log"
    try {
        Start-Transcript -Path $elevatedLogPath -Force | Out-Null
        $transcriptStarted = $true
    } catch {
        Write-Host "Avertissement : Start-Transcript a echoue, pas de log de secours pour cette execution." -ForegroundColor Yellow
    }
    # Si quoi que ce soit plus loin leve une erreur terminale, on veut quand
    # meme fermer proprement le transcript avant de quitter -- sinon le
    # fichier peut rester incomplet ou verrouille.
    trap {
        Write-Host "ERREUR : $_" -ForegroundColor Red
        if ($transcriptStarted) { Stop-Transcript | Out-Null }
        exit 1
    }
}

Write-Host "=== Installation d'EveryCli ===" -ForegroundColor Cyan

# --- 0. Mode -Service demande mais pas encore elevee : auto-elevation (UAC),
# comme le font les installeurs de Docker Desktop/PostgreSQL -- un seul clic
# "Oui" sur l'invite, pas besoin d'ouvrir un terminal admin a la main. Si
# l'utilisateur refuse, on continue en mode standard (pas d'echec bloquant).
if ($Service -and -not (Test-Elevated)) {
    Write-Host "Le mode -Service necessite les droits administrateur -- une invite va apparaitre..." -ForegroundColor Yellow

    # Le processus elevee (-Verb RunAs) ne demarre PAS forcement dans le
    # meme dossier de travail que ce script -- un chemin relatif comme
    # "dist\windows" y serait resolu depuis un autre dossier et ne
    # correspondrait a rien. On resout en absolu avant l'elevation.
    if ($LocalSource -ne "") {
        $LocalSource = (Resolve-Path $LocalSource).Path
    }

    $forwardedArgs = @("-LocalSource", $LocalSource, "-InstallDir", $InstallDir, "-Service")

    try {
        # -File (pas -Command) : passage d'arguments robuste via tableau,
        # pas de string a construire/echapper a la main. La capture de log
        # se fait maintenant DANS le script lui-meme (Start-Transcript
        # ci-dessus), pas via une redirection externe fragile.
        Start-Process -FilePath "powershell.exe" `
            -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $PSCommandPath) + $forwardedArgs) `
            -Verb RunAs -Wait
    } catch {
        Write-Host "Elevation refusee ou echouee." -ForegroundColor Yellow
    }

    $elevatedLogPath = Join-Path $InstallDir "logs\install-service.log"
    Write-Host ""
    Write-Host "=== Log du processus elevee ===" -ForegroundColor Cyan
    if (Test-Path $elevatedLogPath) {
        Get-Content $elevatedLogPath | Write-Host
    } else {
        Write-Host "Aucun log trouve a $elevatedLogPath -- l'invite UAC a probablement ete refusee." -ForegroundColor Yellow
    }
    exit 0
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

# Variables d'environnement persistantes utilisateur -- utiles pour lancer
# everycli-daemon.exe manuellement depuis un terminal pour deboguer.
[Environment]::SetEnvironmentVariable("EVERYCLI_MODEL_DIR", "$InstallDir\model", "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_ONNXRUNTIME_DYLIB", "$InstallDir\runtime\onnxruntime.dll", "User")
[Environment]::SetEnvironmentVariable("EVERYCLI_DATA_DIR", "$InstallDir\data\commands", "User")

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

if ($Service) {
    # --- 4a. Vrai service Windows (SCM) ---
    Write-Host "Installation en tant que service Windows..."
    $binPath = "`"$InstallDir\bin\everycli-daemon.exe`" --service"

    sc.exe query EveryCliDaemon | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Service existant detecte, reinstallation..."
        sc.exe stop EveryCliDaemon | Out-Null
        Start-Sleep -Seconds 1
        sc.exe delete EveryCliDaemon | Out-Null
        Start-Sleep -Seconds 1
    }

    sc.exe create EveryCliDaemon binPath= $binPath start= auto DisplayName= "EveryCli Daemon" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Echec de la creation du service -- repli sur le dossier Demarrage." -ForegroundColor Yellow
        $Service = $false
    }
}

if ($Service) {
    # Les services Windows lisent leurs variables d'environnement depuis le
    # Registre (mecanisme standard, documente par Microsoft), pas depuis
    # les variables utilisateur/systeme habituelles.
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
    # --- 4b. Dossier Demarrage (par defaut, aucune permission speciale) ---
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
