# Stops the CampusMind backend (:8000) and app (:3000) started by start.ps1. Leaves Ollama running.
$ErrorActionPreference = "SilentlyContinue"

function Stop-Port($port, $match, $name) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen
    if (-not $conns) { Write-Host "  $name is not running"; return }
    foreach ($c in $conns) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"
        if ($proc.CommandLine -match $match) {
            # Stop the listener, its worker children (uvicorn --reload spawns one that keeps the port)
            # and its launcher parent (venv python / cmd wrapper).
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)"
            Get-CimInstance Win32_Process -Filter "ParentProcessId=$($proc.ProcessId)" |
                ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
            Stop-Process -Id $proc.ProcessId -Force
            if ($parent -and $parent.CommandLine -match $match) { Stop-Process -Id $parent.ProcessId -Force }
            Write-Host "  Stopped $name (PID $($proc.ProcessId))"
        } else {
            Write-Host "  Port $port is used by another program; left it alone: $($proc.Name)"
        }
    }
}

Write-Host ""
Stop-Port 8000 "uvicorn app\.main:app" "Backend"
Stop-Port 3000 "next" "App"
Write-Host ""
