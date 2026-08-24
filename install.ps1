# EveryCli - installeur Windows.
#
# Usage :
#   Depuis une archive release extraite, l'installeur detecte automatiquement
#   bin/model/runtime/data a cote de lui :
#     .\install.ps1
#   Pour telecharger explicitement une release GitHub (aucun Rust requis) :
#     .\install.ps1 -Version v0.1.0
#   Pour tester un staging local :
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
    [string]$Language = "",
    [switch]$NoService
)

$ErrorActionPreference = "Stop"
$tempRoot = $null
$scriptPathAvailable = -not [string]::IsNullOrWhiteSpace($PSCommandPath)
$scriptRoot = if ($scriptPathAvailable) { $PSScriptRoot } else { $null }

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

# Avec `irm ... | iex`, PowerShell n’exécute pas un fichier :
# $PSCommandPath et $PSScriptRoot sont vides. L’auto-élévation et la
# détection d’un bundle voisin sont alors impossibles ; on utilise directement
# l’installation utilisateur et le téléchargement de la release.
if ($useService -and -not $scriptPathAvailable) {
    Write-Host "Script lance via irm|iex : installation utilisateur sans elevation admin." -ForegroundColor Yellow
    $useService = $false
}

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

Write-Host "=== Installation d'EveryCli / EveryCli Setup ===" -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($Language)) {
    Write-Host ""
    Write-Host "Select language / Choisissez votre langue :" -ForegroundColor Cyan
    Write-Host "  [1] English (default / defaut)"
    Write-Host "  [2] Francais"
    $choice = Read-Host "Choice / Choix [1-2]"
    if ($choice -eq "2" -or $choice -eq "fr" -or $choice -eq "Français") {
        $Language = "fr"
    } else {
        $Language = "en"
    }
}

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

    $forwardedArgs = @("-LocalSource", $LocalSource, "-InstallDir", $InstallDir, "-Language", $Language)
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
} elseif ($scriptRoot -and (Test-Path (Join-Path $scriptRoot "bin"))) {
    $Source = $scriptRoot
    Write-Host "Bundle local detecte a cote de l'installeur : $Source"
} else {
    # L'archive release est autonome : binaires, modele, tokenizer, runtime et corpus.
    $repo = "HE11032006/EveryCli"
    $archive = "everycli-windows-x86_64.zip"
    $releaseBase = if ($Version -eq "latest") {
        "https://github.com/$repo/releases/latest/download"
    } else {
        $tag = $Version.TrimStart('v')
        "https://github.com/$repo/releases/download/v$tag"
    }
    $releaseUrl = "$releaseBase/$archive"
    $checksumsUrl = "$releaseBase/SHA256SUMS"

    $tempRoot = Join-Path $env:TEMP "everycli-$([guid]::NewGuid())"
    $tempZip = Join-Path $tempRoot $archive
    $tempChecksums = Join-Path $tempRoot "SHA256SUMS"
    $tempExtract = Join-Path $tempRoot "extracted"
    New-Item -ItemType Directory -Force -Path $tempExtract | Out-Null

    Write-Host "Telechargement depuis $releaseUrl..."
    try {
        Invoke-WebRequest -Uri $releaseUrl -OutFile $tempZip -UseBasicParsing
        Invoke-WebRequest -Uri $checksumsUrl -OutFile $tempChecksums -UseBasicParsing
    } catch {
        Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        Write-Error "Echec du telechargement de la release -- verifie que $Version existe, ou utilise -LocalSource pour installer depuis un dossier local prepare par stage-release.ps1."
        exit 1
    }

    $checksumLine = Get-Content -LiteralPath $tempChecksums |
        Where-Object { $_ -match "\s$([regex]::Escape($archive))$" } |
        Select-Object -First 1
    if (-not $checksumLine) {
        Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        Write-Error "SHA-256 introuvable pour $archive dans SHA256SUMS."
        exit 1
    }
    $expectedHash = ($checksumLine -split '\s+')[0].ToLowerInvariant()
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $tempZip).Hash.ToLowerInvariant()
    if ($expectedHash -notmatch '^[0-9a-f]{64}$' -or $actualHash -ne $expectedHash) {
        Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        Write-Error "Echec de verification SHA-256 pour $archive."
        exit 1
    }
    Write-Host "Archive verifiee (SHA-256)."

    Write-Host "Extraction..."
    Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

    # Le zip peut contenir directement bin/model/runtime/data a la racine,
    # ou un seul dossier englobant : on detecte les deux cas.
    if (Test-Path (Join-Path $tempExtract "bin")) {
        $Source = $tempExtract
    } else {
        $inner = Get-ChildItem $tempExtract -Directory | Select-Object -First 1
        if ($inner -and (Test-Path (Join-Path $inner.FullName "bin"))) {
            $Source = $inner.FullName
        } else {
            Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
            Write-Error "Structure inattendue dans l'archive telechargee (pas de dossier 'bin' trouve)."
            exit 1
        }
    }
    Write-Host "Telecharge et extrait dans $Source"
}

# Refuser d'écraser une installation existante si l'archive est incomplète.
$requiredPaths = @(
    "bin\everycli.exe",
    "bin\everycli-daemon.exe",
    "model\model.onnx",
    "model\tokenizer.json",
    "runtime\onnxruntime.dll",
    "data\commands"
)
foreach ($relativePath in $requiredPaths) {
    if (-not (Test-Path (Join-Path $Source $relativePath))) {
        if ($tempRoot) { Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }
        Write-Error "Bundle incomplet : fichier ou dossier absent : $relativePath"
        exit 1
    }
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
$UserCommandsDir = Join-Path -Path $env:USERPROFILE -ChildPath ".everycli"
$UserCommandsDir = Join-Path -Path $UserCommandsDir -ChildPath "commands"
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
        "EVERYCLI_DATA_DIR=$InstallDir\data\commands",
        "EVERYCLI_USER_DATA_DIR=$UserCommandsDir"
    )
    Set-ItemProperty -Path $envRegPath -Name "Environment" -Value $envVars -Type MultiString

    Write-Host "Demarrage du service..."
    sc.exe start EveryCliDaemon | Out-Null

    Write-Host "Attente que le daemon soit pret (calcul des embeddings du corpus, jusqu'a ~3 min au premier demarrage)..."
    if (Wait-ForDaemon -TimeoutSeconds 180) {
        Write-Host "Service EveryCliDaemon installe, demarre, cache d'embeddings ecrit sur disque." -ForegroundColor Green
    } else {
        Write-Host "Le daemon ne repond pas encore apres 3 min -- verifie : sc.exe query EveryCliDaemon" -ForegroundColor Yellow
        Write-Host "et les logs : $InstallDir\logs\daemon.log"
    }
} else {
    $LauncherPath = "$InstallDir\bin\run-daemon.cmd"
    @"
@echo off
set EVERYCLI_MODEL_DIR=$InstallDir\model
set EVERYCLI_ONNXRUNTIME_DYLIB=$InstallDir\runtime\onnxruntime.dll
set EVERYCLI_DATA_DIR=$InstallDir\data\commands
set EVERYCLI_USER_DATA_DIR=$UserCommandsDir
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

    Write-Host "Attente que le daemon soit pret (calcul des embeddings du corpus, jusqu'a ~3 min au premier demarrage)..."
    if (Wait-ForDaemon -TimeoutSeconds 180) {
        Write-Host "Daemon pret, cache d'embeddings calcule et ecrit sur disque." -ForegroundColor Green
    } else {
        Write-Host "Le daemon ne repond pas encore apres 3 min -- verifie les logs : $InstallDir\logs\daemon.log" -ForegroundColor Yellow
        Write-Host "everycli fonctionnera quand meme en mode recherche locale en attendant."
    }
}

# --- Enregistrer la preference de langue dans config.toml ---
$userConfigDir = Join-Path $env:USERPROFILE ".everycli"
New-Item -ItemType Directory -Force -Path $userConfigDir | Out-Null
$userConfigFile = Join-Path $userConfigDir "config.toml"
if (Test-Path $userConfigFile) {
    $configContent = Get-Content $userConfigFile -Raw
    if ($configContent -notmatch 'language\s*=') {
        Add-Content -Path $userConfigFile -Value "`nlanguage = `"$Language`""
    } else {
        $configContent = $configContent -replace 'language\s*=\s*"[^"]*"', "language = `"$Language`""
        Set-Content -Path $userConfigFile -Value $configContent
    }
} else {
    Set-Content -Path $userConfigFile -Value "language = `"$Language`""
}

Write-Host ""
Write-Host "=== Installation terminee / Setup complete ===" -ForegroundColor Green
Write-Host "Language / Langue : $(if ($Language -eq 'fr') { 'Francais' } else { 'English' })"
Write-Host "Ouvre un NOUVEAU terminal et tape / Open a NEW terminal and type: everycli search <query>"
Write-Host "Logs du daemon : $InstallDir\logs\daemon.log"

if ($tempRoot) {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

if ($transcriptStarted) {
    Stop-Transcript | Out-Null
}
