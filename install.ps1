# install.ps1 - HackerOS Aesthetic Pack installer
# Compatible with Windows PowerShell 5.1

$ScriptDir = $PSScriptRoot

function Ask($prompt) {
    Write-Host ""
    Write-Host "  $prompt [y/N]: " -ForegroundColor Cyan -NoNewline
    return (Read-Host).Trim().ToLower()
}

function OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function WARN($msg) { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function ERR($msg)  { Write-Host "  [X]  $msg" -ForegroundColor Red }
function STEP($msg) { Write-Host "  -->  $msg" -ForegroundColor Cyan }

Clear-Host
Write-Host ""
Write-Host "  +================================================+" -ForegroundColor Green
Write-Host "  |     HackerOS Aesthetic Pack  -  Installer     |" -ForegroundColor Green
Write-Host "  +================================================+" -ForegroundColor Green
Write-Host ""

# ── 1. Check Python ───────────────────────────────────────────────────────────
STEP "Checking Python..."
$pyCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCheck) {
    ERR "Python not found. Install Python 3.x from https://python.org"
    exit 1
}
$pyVer = python --version 2>&1
OK "Found: $pyVer"

# ── 2. Install pip packages ───────────────────────────────────────────────────
STEP "Installing Python packages..."
python -m pip install pyfiglet colorama --quiet --disable-pip-version-check
OK "pyfiglet + colorama ready"

# ── 3. Hex stream screensaver ─────────────────────────────────────────────────
$ans = Ask "Set hex_stream.py as screensaver (activates after 5 min idle)"
if ($ans -eq "y") {
    $hexScript = Join-Path $ScriptDir "hex_stream.py"

    $pyExe = $pyCheck.Source
    $pyW   = $pyExe -replace "\\python\.exe$", "\pythonw.exe"
    if (-not (Test-Path $pyW)) { $pyW = $pyExe }

    $launchDir = "$env:APPDATA\HackerOS"
    New-Item -ItemType Directory -Path $launchDir -Force | Out-Null

    $vbs = Join-Path $launchDir "hex_stream.vbs"
    $vbsContent = "Set sh = CreateObject(""WScript.Shell"")" + [Environment]::NewLine
    $vbsContent += "sh.Run Chr(34) & """ + $pyW + """ & Chr(34) & "" "" & Chr(34) & """ + $hexScript + """ & Chr(34), 0, False"
    Set-Content -Path $vbs -Value $vbsContent -Encoding UTF8

    $scrCmd = "$env:SystemRoot\System32\wscript.exe `"$vbs`""
    Set-ItemProperty "HKCU:\Control Panel\Desktop" "SCRNSAVE.EXE"     $scrCmd
    Set-ItemProperty "HKCU:\Control Panel\Desktop" "ScreenSaveActive" "1"
    Set-ItemProperty "HKCU:\Control Panel\Desktop" "ScreenSaveTimeOut" "300"

    OK "Screensaver set (5 min idle). Run 'python hex_stream.py' to test."
}

# ── 4. Dramatic lock shortcut (better than lid trigger) ───────────────────────
$ans = Ask "Create a DRAMATIC LOCK desktop shortcut (click it to play animation then lock)"
if ($ans -eq "y") {
    $lockScript  = Join-Path $ScriptDir "lock_overlay.py"
    $pyExe       = $pyCheck.Source
    $pyW         = $pyExe -replace "\\python\.exe$", "\pythonw.exe"
    if (-not (Test-Path $pyW)) { $pyW = $pyExe }

    $shortcutPath = "$env:USERPROFILE\Desktop\LOCK.lnk"
    $wsh  = New-Object -ComObject WScript.Shell
    $link = $wsh.CreateShortcut($shortcutPath)
    $link.TargetPath      = $pyW
    $link.Arguments       = "`"$lockScript`""
    $link.WorkingDirectory = $ScriptDir
    $link.Description     = "HackerOS dramatic lock"
    $link.Save()

    OK "Shortcut created on Desktop: LOCK.lnk"
    WARN "Double-click it instead of Win+L for the dramatic effect."
    WARN "Or assign it a keyboard shortcut via right-click > Properties."
}

# ── 5. Terminal startup greeting ──────────────────────────────────────────────
$ans = Ask "Add hacker greeting to PowerShell profile (runs on every terminal open)"
if ($ans -eq "y") {
    $startupScript = Join-Path $ScriptDir "terminal_startup.py"
    $pyExe         = $pyCheck.Source

    if (-not (Test-Path $PROFILE)) {
        New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    }

    $existing = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($existing -notmatch "HackerOS") {
        $line = "`n# HackerOS startup`npython `"$startupScript`""
        Add-Content -Path $PROFILE -Value $line
        OK "Added to profile: $PROFILE"
        WARN "Open a new PowerShell window to see it."
    } else {
        WARN "Already in profile, skipped."
    }
}

# ── 6. Windows Terminal theme ─────────────────────────────────────────────────
$ans = Ask "Open Windows Terminal settings to apply HackerOS colour theme"
if ($ans -eq "y") {
    $wtPath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
    $themeSrc = Join-Path $ScriptDir "wt_theme.json"

    if (Test-Path $wtPath) {
        Write-Host ""
        Write-Host "  Instructions:" -ForegroundColor White
        Write-Host "    1. In settings.json find the 'schemes' array" -ForegroundColor Gray
        Write-Host "    2. Paste the contents of wt_theme.json as a new entry" -ForegroundColor Gray
        Write-Host "    3. On your default profile set: 'colorScheme': 'HackerOS'" -ForegroundColor Gray
        Write-Host "    4. Also set font face to Courier New, size 12" -ForegroundColor Gray
        Write-Host ""
        Start-Process notepad $wtPath
        Start-Process notepad $themeSrc
        OK "Opened both files in Notepad."
    } else {
        WARN "Windows Terminal not found. Install from Microsoft Store."
    }
}

# ── done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  +================================================+" -ForegroundColor Green
Write-Host "  |              All done!                        |" -ForegroundColor Green
Write-Host "  +================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  Quick test commands:" -ForegroundColor Cyan
Write-Host "    python hex_stream.py                  -> screensaver" -ForegroundColor Gray
Write-Host "    python lock_overlay.py --preview      -> lock animation" -ForegroundColor Gray
Write-Host "    python terminal_startup.py            -> greeting" -ForegroundColor Gray
Write-Host "    Double-click LOCK.lnk on Desktop      -> dramatic lock" -ForegroundColor Gray
Write-Host ""
