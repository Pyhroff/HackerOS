# lid_watcher.ps1 — Monitor for system sleep and trigger the lock animation.
# Runs as a background script; register it via install.ps1 to auto-start at login.
#
# Usage:
#   .\lid_watcher.ps1           ← normal mode (stays running, watches for sleep)
#   .\lid_watcher.ps1 -Test     ← fire the overlay immediately (preview)

param(
    [string]$ScriptDir = $PSScriptRoot,
    [switch]$Test
)

$overlayScript = Join-Path $ScriptDir "lock_overlay.py"

function Start-Overlay([string]$extraArgs = "") {
    # Prefer pythonw (no console window) but fall back to python
    $pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue)?.Source
    if (-not $pythonw) {
        $pythonw = (Get-Command python.exe -ErrorAction SilentlyContinue)?.Source
    }
    if (-not $pythonw) {
        Write-Warning "[HackerOS] Python not found — cannot launch overlay."
        return
    }
    $args = if ($extraArgs) { "`"$overlayScript`" $extraArgs" } else { "`"$overlayScript`"" }
    Start-Process $pythonw -ArgumentList $args -WindowStyle Hidden
}

# ── test mode ────────────────────────────────────────────────────────────────
if ($Test) {
    Write-Host "[HackerOS] TEST: Launching lock overlay with --preview flag..." -ForegroundColor Green
    Start-Overlay "--preview"
    exit 0
}

# ── live mode ────────────────────────────────────────────────────────────────
Write-Host "[HackerOS] Lid watcher active. Close lid (or sleep) to trigger animation." -ForegroundColor Green
Write-Host "[HackerOS] Press Ctrl+C to stop." -ForegroundColor DarkGray

# Win32_PowerManagementEvent EventType 7 = Entering Standby/Hibernate.
# This fires when the system is about to sleep, which includes lid close
# if the lid-close action is configured to sleep (default on most laptops).
$scriptDirCopy = $ScriptDir   # capture for use inside the -Action scriptblock

$eventAction = {
    $eventType = $Event.SourceEventArgs.NewEvent.EventType
    if ($eventType -eq 7) {
        $dir       = $using:scriptDirCopy
        $overlay   = Join-Path $dir "lock_overlay.py"
        $pythonw   = (Get-Command pythonw.exe -ErrorAction SilentlyContinue)?.Source
        if (-not $pythonw) {
            $pythonw = (Get-Command python.exe -ErrorAction SilentlyContinue)?.Source
        }
        if ($pythonw) {
            Start-Process $pythonw -ArgumentList "`"$overlay`"" -WindowStyle Hidden
        }
    }
}

$null = Register-WmiEvent -Class Win32_PowerManagementEvent `
    -SourceIdentifier "HackerOS_Sleep" `
    -Action $eventAction

try {
    while ($true) { Start-Sleep -Seconds 2 }
}
finally {
    Unregister-Event -SourceIdentifier "HackerOS_Sleep" -ErrorAction SilentlyContinue
    Write-Host "`n[HackerOS] Lid watcher stopped." -ForegroundColor Yellow
}
