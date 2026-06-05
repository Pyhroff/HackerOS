"""
terminal_startup.py — HackerOS terminal greeting.
Displays a fake system scan, ASCII-art banner, session info, and a quote.
Add to PowerShell profile to run on every terminal open.
"""
import sys
import time
import random
import os
from datetime import datetime

try:
    import pyfiglet
    HAS_FIGLET = True
except ImportError:
    HAS_FIGLET = False

try:
    import colorama
    colorama.init()
except ImportError:
    pass  # ANSI works natively in Windows Terminal / modern PowerShell

# ── ANSI colours ─────────────────────────────────────────────────────────────
G  = "\033[92m"    # bright green
DG = "\033[32m"    # dark green
B  = "\033[1m"     # bold
DM = "\033[2m"     # dim
CY = "\033[96m"    # cyan
R  = "\033[91m"    # red
RS = "\033[0m"     # reset

# ── content ──────────────────────────────────────────────────────────────────
QUOTES = [
    "The only truly secure system is one that is powered off.",
    "Security is a process, not a product.",
    "There is no patch for human stupidity.",
    "To hack is to explore the limits of what is possible.",
    "The quieter you become, the more you are able to hear.",
    "In cyberspace, the boundaries are defined by data, not geography.",
    "Privacy is not something I'm merely entitled to — it's an absolute prerequisite.",
    "Trust, but verify.",
    "Knowledge is the ultimate weapon.",
    "Hackers are breaking the systems of the future today.",
]

SCAN_ITEMS = [
    ("Initializing secure shell",        0.07),
    ("Loading kernel modules",           0.05),
    ("Mounting encrypted volumes",       0.09),
    ("Scanning network interfaces",      0.06),
    ("Verifying system integrity",       0.08),
    ("Loading firewall rules",           0.05),
    ("Establishing secure tunnel",       0.07),
    ("Checking for anomalous processes", 0.10),
    ("Randomizing hardware identifiers", 0.06),
    ("Flushing DNS cache",               0.04),
    ("Enabling stealth mode",            0.06),
    ("All systems nominal",              0.00),
]


# ── helpers ───────────────────────────────────────────────────────────────────

def slow_type(text: str, delay: float = 0.03, color: str = G):
    for ch in text:
        sys.stdout.write(color + ch + RS)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def progress_bar(label: str, width: int = 24, delay: float = 0.07):
    sys.stdout.write(f"  {DG}{label:<38}{RS} [")
    sys.stdout.flush()
    for _ in range(width):
        time.sleep(delay * random.uniform(0.4, 1.6))
        sys.stdout.write(G + "█" + RS)
        sys.stdout.flush()
    sys.stdout.write(f"] {G}OK{RS}\n")
    sys.stdout.flush()


def fake_scan():
    print(f"\n{DG}  ┌──────────────────────────────────────────────────┐{RS}")
    print(f"{DG}  │           SYSTEM DIAGNOSTIC SEQUENCE              │{RS}")
    print(f"{DG}  └──────────────────────────────────────────────────┘{RS}\n")
    for label, speed in SCAN_ITEMS:
        progress_bar(label, width=22, delay=speed)
        time.sleep(0.04)


def ascii_banner(name: str):
    if HAS_FIGLET:
        try:
            art = pyfiglet.figlet_format(name, font="cyberlarge")
        except Exception:
            art = pyfiglet.figlet_format(name)
    else:
        art = f"\n  >>  {name.upper()}  <<\n"

    for line in art.splitlines():
        print(f"{B}{G}{line}{RS}")
        time.sleep(0.035)


def get_username() -> str:
    config = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".hackeros_user")
    if os.path.exists(config):
        with open(config) as f:
            name = f.read().strip()
        if name:
            return name
    print(f"\n{CY}  First run. Enter your hacker alias:{RS} ", end="", flush=True)
    name = input().strip() or "ANON"
    with open(config, "w") as f:
        f.write(name)
    return name


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    os.system("cls" if os.name == "nt" else "clear")

    print(f"\n{DG}  ╔════════════════════════════════════════════════════╗{RS}")
    print(f"{DG}  ║              H A C K E R O S  v2.0                ║{RS}")
    print(f"{DG}  ╚════════════════════════════════════════════════════╝{RS}")

    fake_scan()
    time.sleep(0.25)
    print()

    name = get_username()
    ascii_banner(name)

    now = datetime.now()
    uptime_h = random.randint(0, 23)
    uptime_m = random.randint(0, 59)

    print(f"\n{DG}  ┌─ SESSION ───────────────────────────────────────────┐{RS}")
    print(f"{DG}  │{RS}  User    : {B}{G}{name.upper()}{RS}")
    print(f"{DG}  │{RS}  Date    : {G}{now.strftime('%Y-%m-%d')}{RS}")
    print(f"{DG}  │{RS}  Time    : {G}{now.strftime('%H:%M:%S')}{RS}")
    print(f"{DG}  │{RS}  Uptime  : {G}{uptime_h}h {uptime_m}m{RS}")
    print(f"{DG}  │{RS}  Status  : {G}SECURE  ▮{RS}")
    print(f"{DG}  └─────────────────────────────────────────────────────┘{RS}\n")

    quote = random.choice(QUOTES)
    print(f"  {DM}{DG}\"{quote}\"{RS}\n")

    slow_type("  > Shell initialized. Welcome back.\n", delay=0.022, color=G)


if __name__ == "__main__":
    main()
