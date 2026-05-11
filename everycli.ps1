# everycli.ps1 — Wrapper haute performance pour Windows
# Ce script permet une recherche instantanée sur Windows en parlant au daemon via TCP.

$DAEMON_PORT = if ($env:EVERYCLI_PORT) { $env:EVERYCLI_PORT } else { 51821 }
$EVERYCLI_BIN = Join-Path $PSScriptRoot "everycli-daemon.exe"
$PID_FILE = Join-Path $HOME ".everycli\daemon.pid"

function Test-DaemonRunning {
    if (Test-Path $PID_FILE) {
        $pidVal = Get-Content $PID_FILE -ErrorAction SilentlyContinue
        if ($pidVal) {
            try {
                return Get-Process -Id $pidVal -ErrorAction SilentlyContinue
            } catch {
                return $false
            }
        }
    }
    return $false
}

function Invoke-FastSearch {
    param($query)
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", $DAEMON_PORT)
        $stream = $client.GetStream()
        
        $payload = @{ action = "search"; query = $query; top_k = 3 } | ConvertTo-Json -Compress
        $data = [System.Text.Encoding]::UTF8.GetBytes($payload + "`n")
        $stream.Write($data, 0, $data.Length)
        
        $reader = New-Object System.IO.StreamReader($stream)
        $responseRaw = $reader.ReadLine()
        if (-not $responseRaw) { return $false }
        
        $response = $responseRaw | ConvertFrom-Json
        
        if ($response.ok) {
            Write-Host ""
            foreach ($r in $response.results) {
                Write-Host "✦ $($r.description)" -ForegroundColor Cyan
                Write-Host "  $($r.command)" -ForegroundColor Green
                if ($r.explanation) { Write-Host "  $($r.explanation)" -ForegroundColor Gray }
                Write-Host ""
            }
            return $true
        }
    } catch {
        return $false
    } finally {
        if ($client) { $client.Close() }
    }
    return $false
}

# --- Logique principale ---
if ($args.Count -eq 0) {
    Start-Process -FilePath $EVERYCLI_BIN -ArgumentList "--help" -NoNewWindow -Wait
    exit 0
}

$firstArg = $args[0]
$queryArgs = $args
if ($firstArg -eq "search") {
    $queryArgs = $args[1..($args.Count-1)]
}
$fullQuery = $queryArgs -join " "

# Si c'est une recherche et que le daemon tourne -> FAST PATH
if ($firstArg -ne "daemon" -and $firstArg -ne "add" -and (Test-DaemonRunning)) {
    if (Invoke-FastSearch $fullQuery) { exit 0 }
}

# Fallback sur le binaire complet (PyInstaller)
# Note: On utilise Start-Process pour une meilleure gestion des signaux sur Windows
& $EVERYCLI_BIN $args
