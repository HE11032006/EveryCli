# everycli.ps1 — Intelligent High-Performance Wrapper for Windows
# Version: 1.1.0

$DAEMON_PORT = if ($env:EVERYCLI_PORT) { $env:EVERYCLI_PORT } else { 51821 }
$EVERYCLI_BIN = Join-Path $PSScriptRoot "everycli-daemon.exe"

function Test-PortOpen {
    param($port)
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    try {
        $asyncResult = $tcpClient.BeginConnect("127.0.0.1", $port, $null, $null)
        $wait = $asyncResult.AsyncWaitHandle.WaitOne(200, $false)
        if ($wait -and $tcpClient.Connected) {
            return $true
        }
    } catch {
        return $false
    } finally {
        $tcpClient.Close()
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
        
        $payload = @{ action = "search"; query = $query; top_k = 5 } | ConvertTo-Json -Compress
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
                # if ($r.explanation) { Write-Host "  $($r.explanation)" -ForegroundColor Gray }
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

# --- Main Logic ---
if ($args.Count -eq 0) {
    if (Test-Path $EVERYCLI_BIN) {
        & $EVERYCLI_BIN --help
    } else {
        Write-Host "EveryCli - Command Line Interface"
        Write-Host "Usage: everycli <query>"
    }
    exit 0
}

$firstArg = $args[0]
$queryArgs = $args
if ($firstArg -eq "search") {
    $queryArgs = $args[1..($args.Count-1)]
}
$fullQuery = $queryArgs -join " "

# --- Step 1: Check if it's a search command ---
if ($firstArg -eq "daemon" -or $firstArg -eq "add" -or $firstArg -eq "list" -or $firstArg -eq "export" -or $firstArg -eq "import" -or $firstArg -eq "update" -or $firstArg -eq "--help") {
    if (Test-Path $EVERYCLI_BIN) {
        & $EVERYCLI_BIN $args
        exit 0
    }
}

# --- Step 2: Try Fast Search ---
if (-not (Test-PortOpen $DAEMON_PORT)) {
    if (Test-Path $EVERYCLI_BIN) {
        Write-Host "[everycli] Starting daemon..." -ForegroundColor Gray
        Start-Process -FilePath $EVERYCLI_BIN -ArgumentList "--start" -WindowStyle Hidden
        
        # Wait for daemon (max 10 seconds)
        for ($i=0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 500
            if (Test-PortOpen $DAEMON_PORT) { break }
        }
    }
}

if (Invoke-FastSearch $fullQuery) {
    exit 0
} else {
    Write-Error "Could not connect to EveryCli daemon."
    exit 1
}
