# HackerOS Aesthetic Pack

Turns your Windows 11 laptop into something out of a hacker movie. Green terminals, dramatic lock screens, live hex dump screensaver. All visual — nothing actually dangerous.

## Features

- **Hex Stream** — fullscreen scrolling memory hex dump (screensaver)
- **Lock Overlay** — dramatic terminal animation before your screen locks
- **Terminal Startup** — hacker greeting every time you open PowerShell
- **HackerOS Theme** — green-on-black Windows Terminal colour scheme

## Setup

```
pip install pyfiglet colorama
powershell -ExecutionPolicy Bypass -File install.ps1
```

## Quick run

```
python hex_stream.py               # screensaver
python lock_overlay.py --preview   # lock animation (no actual lock)
python terminal_startup.py         # terminal greeting
```

## Requirements

- Windows 11
- Python 3.x
- Windows Terminal (optional, for theme)

## Uninstall

Delete the folder. Remove the line from your PowerShell profile. Done.
