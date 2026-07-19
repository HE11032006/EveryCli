# EveryCli PowerShell integration. Source this file once from your PowerShell profile.
# Example: . D:\EveryCli\everycli.ps1

$script:EveryCliRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Invoke-EveryCliShellSelection {
    param([Parameter(Mandatory = $true)][string]$Query)

    $arguments = @("search", $Query, "-s")
    if ($env:EVERYCLI_BIN -and (Test-Path -LiteralPath $env:EVERYCLI_BIN)) {
        & $env:EVERYCLI_BIN @arguments
        return
    }

    $binary = Join-Path $script:EveryCliRoot "everycli.exe"
    if (Test-Path -LiteralPath $binary) {
        & $binary @arguments
        return
    }

    $python = Join-Path $script:EveryCliRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $python) {
        & $python -m everycli.everycli @arguments
        return
    }

    Write-Error "EveryCli not found. Set EVERYCLI_BIN or create the local .venv."
}

function evc {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$Query
    )

    if (-not $Query -or $Query.Count -eq 0) {
        Write-Host 'Usage: evc "describe what you want to do"'
        return
    }

    # The child writes the visual result to stderr and only its confirmed
    # command to stdout. PowerShell captures stdout here without executing it.
    $selected = Invoke-EveryCliShellSelection -Query ($Query -join " ")
    $command = ($selected -join "`n").TrimEnd("`r", "`n")
    if ([string]::IsNullOrWhiteSpace($command)) {
        return
    }

    try {
        Import-Module PSReadLine -ErrorAction Stop
        [Microsoft.PowerShell.PSConsoleReadLine]::Insert($command)
    }
    catch {
        # Never execute automatically: if PSReadLine is absent, make the
        # command visible so it can be copied and edited manually.
        Write-Host $command
        Write-Warning "PSReadLine is unavailable; copy the command manually."
    }
}
