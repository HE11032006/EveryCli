# Assemble un dossier "dist\windows" qui imite ce qu'une vraie release
# GitHub contiendrait — sert à tester install.ps1 localement ce soir, et
# deviendra la base du job de packaging CI plus tard.
#
# Usage (depuis la racine du repo, C:\EveryCli) :
#   .\scripts\windows\stage-release.ps1
#
# Prérequis : avoir déjà compilé en release et exporté le modèle (Axe 1) :
#   cd rust && cargo build --release -p everycli-rs -p everycli-daemon

$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Item "$PSScriptRoot\..\..").FullName
$Dist = Join-Path $RepoRoot "dist\windows"

Write-Host "Nettoyage de $Dist..."
Remove-Item -Recurse -Force $Dist -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path "$Dist\bin" | Out-Null
New-Item -ItemType Directory -Force -Path "$Dist\model" | Out-Null
New-Item -ItemType Directory -Force -Path "$Dist\runtime" | Out-Null
New-Item -ItemType Directory -Force -Path "$Dist\data\commands" | Out-Null

Write-Host "Copie des binaires..."
$ReleaseDir = Join-Path $RepoRoot "rust\target\release"
Copy-Item "$ReleaseDir\everycli-rs.exe" "$Dist\bin\everycli.exe" -ErrorAction Stop
Copy-Item "$ReleaseDir\everycli-daemon.exe" "$Dist\bin\everycli-daemon.exe" -ErrorAction Stop

Write-Host "Copie du modèle ONNX..."
$ModelSrc = Join-Path $RepoRoot "rust\onnx-bench\models\everycli-minilm-ft"
Copy-Item "$ModelSrc\model.onnx" "$Dist\model\" -ErrorAction Stop
Copy-Item "$ModelSrc\tokenizer.json" "$Dist\model\" -ErrorAction Stop

Write-Host "Copie du runtime ONNX..."
Copy-Item (Join-Path $RepoRoot "rust\onnx-bench\runtime\onnxruntime.dll") "$Dist\runtime\" -ErrorAction Stop

Write-Host "Copie du corpus de commandes..."
Copy-Item (Join-Path $RepoRoot "everycli\data\commands\*.yaml") "$Dist\data\commands\" -ErrorAction Stop

$size = (Get-ChildItem $Dist -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ""
Write-Host "Assemblé dans $Dist ($([math]::Round($size, 1)) Mo)"
Write-Host "Teste l'installeur avec :"
Write-Host "  .\install.ps1 -LocalSource `"$Dist`""
