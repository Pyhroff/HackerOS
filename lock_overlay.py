"""
lock_overlay.py — Terminal-style security lock overlay.

Four live panels:
  ▸ TERMINAL SESSION  — shell commands executing in real time
  ▸ PACKET CAPTURE    — network traffic being dropped packet by packet
  ▸ MEMORY MAP        — memory pages being wiped row by row
  ▸ PYTHON REPL       — encryption code typing itself out

Run with --preview to skip the actual workstation lock.
"""
import tkinter as tk
import random
import subprocess
import sys
from datetime import datetime

PREVIEW = "--preview" in sys.argv

# ── palette ───────────────────────────────────────────────────────────────────
BG     = "#000000"
GREEN  = "#00FF41"
DKGRN  = "#00CC33"
MGRN   = "#009922"
DIMGRN = "#005511"
BORDER = "#007722"
DIM    = "#003308"
RED    = "#FF0000"
DKRED  = "#AA0000"
YELLOW = "#CCCC00"
MONO   = "Courier New"

HOST = "WORKSTATION"

def _ts():
    n = datetime.now()
    return n.strftime("%H:%M:%S.") + f"{n.microsecond // 1000:03d}"

def _hex(n):
    return "".join(f"{random.randint(0, 15):X}" for _ in range(n))

def _pid():
    return random.randint(1000, 9999)

# ── static values generated once so they stay consistent across frames ────────
_SESSION_KEY = _hex(16)
_SESSION_ID  = _hex(8).upper()
_IP          = f"192.168.{random.randint(1,5)}.{random.randint(10,200)}"
_HASH32      = _hex(32).lower()

# ── terminal script: (tick_to_show, text, color_tag) ─────────────────────────
TERM_SCRIPT = [
    (0,   f"┌─[root@{HOST}]─[~]\n",                      "prompt"),
    (1,   f"└──╼ ",                                        "prompt"),
    (2,   "systemctl stop NetworkManager\n",               "cmd"),
    (6,   "         Stopping Network Manager...\n",        "dim"),
    (9,   "[  OK  ] NetworkManager.service stopped.\n",    "ok"),
    (13,  f"┌─[root@{HOST}]─[~]\n",                       "prompt"),
    (14,  f"└──╼ ",                                        "prompt"),
    (15,  "iptables -F && iptables -X\n",                  "cmd"),
    (18,  "iptables -P INPUT DROP\n",                      "cmd"),
    (21,  "iptables -P OUTPUT DROP\n",                     "cmd"),
    (24,  "[  OK  ] All traffic: BLOCKED\n",               "ok"),
    (28,  f"┌─[root@{HOST}]─[~]\n",                       "prompt"),
    (29,  f"└──╼ ",                                        "prompt"),
    (30,  f"pkill -9 -u {HOST}\n",                         "cmd"),
    (33,  f"   killed {_pid()}  chrome.exe\n",             "kill"),
    (35,  f"   killed {_pid()}  msedge.exe\n",             "kill"),
    (37,  f"   killed {_pid()}  OneDrive.exe\n",           "kill"),
    (39,  f"   killed {_pid()}  SearchHost.exe\n",         "kill"),
    (41,  f"   killed {_pid()}  sihost.exe\n",             "kill"),
    (43,  f"   23 processes terminated.\n",                "ok"),
    (47,  f"┌─[root@{HOST}]─[~]\n",                       "prompt"),
    (48,  f"└──╼ ",                                        "prompt"),
    (49,  "python3 /opt/lockd/seal_session.py\n",          "cmd"),
    (53,  f"  [lockd] gen key  AES-256-GCM\n",             "muted"),
    (56,  f"  [lockd] key      {_SESSION_KEY[:8]}...{_SESSION_KEY[-4:]}  (TPM-sealed)\n", "muted"),
    (59,  f"  [lockd] sealing  4096 memory pages\n",       "muted"),
    (62,  f"  [lockd] zeroing  swap + credential store\n", "muted"),
    (65,  f"  [lockd] hash     SHA-256:{_HASH32[:16]}...\n","muted"),
    (68,  f"  [lockd] done     session sealed ✓\n",        "ok"),
    (72,  f"┌─[root@{HOST}]─[~]\n",                       "prompt"),
    (73,  f"└──╼ ",                                        "prompt"),
    (74,  "loginctl lock-sessions && exit\n",              "cmd"),
    (79,  "\n  *** SESSION TERMINATED ***\n\n",            "warn"),
]

PACKETS = [
    (_IP,          "8.8.8.8",       "DNS",   53,   "DROP"),
    (_IP,          "93.184.216.34", "HTTPS", 443,  "RST "),
    (_IP,          "1.1.1.1",       "DNS",   53,   "DROP"),
    ("192.168.1.1", _IP,            "ARP",   0,    "DROP"),
    (_IP,          "52.96.29.17",   "HTTPS", 443,  "RST "),
    ("ff02::1",    _IP,             "ICMPv6",0,    "DROP"),
    (_IP,          "10.0.0.1",      "SSH",   22,   "RST "),
    (_IP,          "172.217.3.110", "HTTPS", 443,  "DROP"),
]

# memory base addresses
MEM_ADDRS = [f"0x7FFE{i:04X}000" for i in range(8)]

CODE_LINES = [
    (">>> ", "repl"),
    (">>> import os, hashlib, gc\n", "code"),
    (">>> from Crypto.Cipher import AES\n", "code"),
    (">>> from Crypto.Random import get_random_bytes\n", "code"),
    (">>> \n", "repl"),
    (">>> # generate ephemeral lock key\n", "comment"),
    (">>> salt   = get_random_bytes(32)\n", "code"),
    (">>> key    = hashlib.pbkdf2_hmac(\n", "code"),
    ("...            'sha256', os.urandom(32), salt, 100_000)\n", "code"),
    (">>> nonce  = get_random_bytes(16)\n", "code"),
    (">>> cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)\n", "code"),
    (">>> ct, tag = cipher.encrypt_and_digest(session_data)\n", "code"),
    (f">>> print(ct.hex()[:32])\n", "code"),
    (f"{_hex(32).lower()}\n", "out"),
    (">>> key = bytes(len(key)); del cipher, ct, tag\n", "code"),
    (">>> gc.collect()\n", "code"),
    ("0\n", "out"),
    (">>> # memory cleared.\n", "comment"),
]


class LockOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost",    True)
        self.root.overrideredirect(True)
        self.root.config(cursor="none")

        if PREVIEW:
            self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.root.update()
        W, H = self.root.winfo_width(), self.root.winfo_height()
        self.W, self.H = W, H
        self.fs = max(10, W // 165)

        # animation state — must come before _build_ui() which calls _render_mem_map()
        self.tick       = 0
        self.phase      = 0
        self._term_idx  = 0
        self._pkt_i     = 0
        self._pkt_total = 0
        self._code_i    = 0
        self._mem_wipe  = 0

        self._build_ui()
        self._mem_wipe  = 0   # how many mem rows wiped so far

        self._animate()
        self.root.mainloop()

    # ─────────────────────────────────────────────────────────────────────────
    # UI construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        W, H, fs = self.W, self.H, self.fs
        fbold = (MONO, fs, "bold")
        fmono = (MONO, fs)
        fsmol = (MONO, fs - 1)

        # ── header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill=tk.X, padx=10, pady=(8, 3))

        self._hdr_title = tk.Label(hdr, text="", font=fbold, fg=GREEN, bg=BG, anchor="w")
        self._hdr_title.pack(side=tk.LEFT)

        self._hdr_right = tk.Label(hdr, text="", font=fsmol, fg=DIMGRN, bg=BG, anchor="e")
        self._hdr_right.pack(side=tk.RIGHT)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X, padx=10)

        # ── main area ─────────────────────────────────────────────────────────
        mid = tk.Frame(self.root, bg=BG)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 0))

        # left: terminal (58% width)
        left = tk.Frame(mid, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._panel_title(left, "▸ TERMINAL SESSION")
        self._term = self._make_text(left, fmono, fill=True, expand=True)
        self._term.tag_configure("prompt",  foreground=DKGRN,  font=fbold)
        self._term.tag_configure("cmd",     foreground=GREEN,   font=fbold)
        self._term.tag_configure("ok",      foreground=DKGRN)
        self._term.tag_configure("kill",    foreground=MGRN)
        self._term.tag_configure("muted",   foreground=MGRN)
        self._term.tag_configure("dim",     foreground=DIMGRN)
        self._term.tag_configure("warn",    foreground=YELLOW,  font=fbold)
        self._term.tag_configure("cursor",  foreground=GREEN,   font=fbold)

        # right column
        right = tk.Frame(mid, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, padx=(8, 0))

        # packet capture
        self._panel_title(right, "▸ PACKET CAPTURE  [ eth0 ]")
        self._pkt = self._make_text(right, fsmol, height=10)
        self._pkt.tag_configure("src",   foreground=MGRN)
        self._pkt.tag_configure("arrow", foreground=DIMGRN)
        self._pkt.tag_configure("dst",   foreground=DIMGRN)
        self._pkt.tag_configure("drop",  foreground=DKRED)
        self._pkt.tag_configure("rst",   foreground=YELLOW)
        self._pkt.tag_configure("stat",  foreground=DIMGRN)

        tk.Frame(right, bg=DIM, height=1).pack(fill=tk.X, pady=2)

        # memory map
        self._panel_title(right, "▸ MEMORY MAP  [ zeroing pages ]")
        self._mem_text = self._make_text(right, fsmol, height=8)
        self._mem_text.tag_configure("addr",   foreground=MGRN)
        self._mem_text.tag_configure("wiped",  foreground=DIMGRN)
        self._mem_text.tag_configure("active", foreground=GREEN)
        self._mem_text.tag_configure("queued", foreground=DIM)
        self._render_mem_map()   # initial render

        # ── separator ─────────────────────────────────────────────────────────
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X, padx=10)

        # ── python repl ───────────────────────────────────────────────────────
        bot = tk.Frame(self.root, bg=BG)
        bot.pack(fill=tk.X, padx=10, pady=(3, 8))

        self._panel_title(bot, "▸ PYTHON 3.12  [seal_session.py]")
        self._code = self._make_text(bot, fsmol, height=7)
        self._code.tag_configure("repl",    foreground=MGRN)
        self._code.tag_configure("code",    foreground=GREEN)
        self._code.tag_configure("comment", foreground=DIMGRN)
        self._code.tag_configure("out",     foreground=DKGRN)

        # ── ACCESS DENIED overlay (hidden until phase 2) ──────────────────────
        self._denied_frame = tk.Frame(self.root, bg=BG)
        self._denied_lbl   = None   # created in _show_denied()

    def _panel_title(self, parent, text):
        tk.Label(parent, text=f"  {text}",
                 font=(MONO, self.fs - 1, "bold"),
                 fg=BORDER, bg=BG, anchor="w").pack(fill=tk.X)

    def _make_text(self, parent, font, height=None, fill=False, expand=False):
        kw = dict(font=font, bg=BG, fg=DIMGRN,
                  bd=0, highlightthickness=0,
                  state="disabled", wrap=tk.NONE, insertwidth=0)
        if height:
            kw["height"] = height
        t = tk.Text(parent, **kw)
        t.pack(fill=tk.BOTH if fill else tk.X, expand=expand)
        return t

    # ─────────────────────────────────────────────────────────────────────────
    # Text helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _append(self, w, text, tag=""):
        w.config(state="normal")
        if tag:
            w.insert("end", text, tag)
        else:
            w.insert("end", text)
        w.config(state="disabled")
        w.see("end")

    def _trim(self, w, maxlines=20):
        w.config(state="normal")
        lines = int(w.index("end-1c").split(".")[0])
        if lines > maxlines:
            w.delete("1.0", f"{lines - maxlines}.0")
        w.config(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    # Panel renderers
    # ─────────────────────────────────────────────────────────────────────────

    def _render_mem_map(self):
        w = self._mem_text
        w.config(state="normal")
        w.delete("1.0", "end")
        for i, addr in enumerate(MEM_ADDRS):
            size = f"{(i + 1) * 4}KB"
            w.insert("end", f"  {addr}  {size:>6}  ", "addr")
            if i < self._mem_wipe:
                w.insert("end", "░░░░░░░░░░░░░░░░  zeroed\n", "wiped")
            elif i == self._mem_wipe:
                w.insert("end", "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  wiping...\n", "active")
            else:
                w.insert("end", "████████████████  mapped\n", "queued")
        w.config(state="disabled")

    def _add_packet(self):
        p = PACKETS[self._pkt_i % len(PACKETS)]
        src, dst, proto, dport, action = p
        port_str = f":{dport}" if dport else "    "
        line_ts = _ts()
        self._append(self._pkt, f"  {line_ts}  ", "stat")
        self._append(self._pkt, f"{src}", "src")
        self._append(self._pkt, f" → {dst}{port_str}  {proto:<6}  ", "arrow")
        tag = "drop" if action == "DROP" else "rst"
        self._append(self._pkt, f"{action}\n", tag)
        self._trim(self._pkt, 13)
        self._pkt_i     += 1
        self._pkt_total += 1

        if self._pkt_total % 8 == 0:
            self._append(
                self._pkt,
                f"  ── {self._pkt_total} blocked / 0 forwarded ──\n",
                "stat"
            )
            self._trim(self._pkt, 13)

    # ─────────────────────────────────────────────────────────────────────────
    # Animation loop
    # ─────────────────────────────────────────────────────────────────────────

    def _animate(self):
        t = self.tick
        self.tick += 1

        # ── header (always) ──────────────────────────────────────────────────
        dot  = "●" if t % 8 < 5 else "○"
        stat = "RUNNING" if self.phase == 0 else ("SECURED" if self.phase == 1 else "LOCKED")
        self._hdr_title.config(
            text=f"  HACKEROS SECURITY LOCK v4.2.1   {dot} {stat}",
            fg=(GREEN if self.phase < 2 else RED)
        )
        self._hdr_right.config(
            text=f"{_ts()}  ·  {_IP}  ·  TPM 2.0  ·  Session: {_SESSION_ID}"
        )

        # ── phase 0: main animation ───────────────────────────────────────────
        if self.phase == 0:

            # — terminal: reveal lines per script timing —
            while (self._term_idx < len(TERM_SCRIPT) and
                   TERM_SCRIPT[self._term_idx][0] <= t):
                _, text, tag = TERM_SCRIPT[self._term_idx]
                self._append(self._term, text, tag)
                self._trim(self._term, 35)
                self._term_idx += 1

            # blinking cursor after last appended line (only while waiting for next cmd)
            # We skip rewriting for simplicity — the content itself sells it.

            # — packet capture: one packet every 2 ticks —
            if t % 2 == 0:
                self._add_packet()

            # — memory map: advance wipe every 9 ticks —
            if t % 9 == 0 and self._mem_wipe < len(MEM_ADDRS):
                self._mem_wipe += 1
                self._render_mem_map()

            # — python repl: one line every 4 ticks, start at tick 10 —
            if t >= 10 and t % 4 == 0 and self._code_i < len(CODE_LINES):
                text, tag = CODE_LINES[self._code_i]
                self._append(self._code, text, tag)
                self._trim(self._code, 9)
                self._code_i += 1

            # — transition to phase 1 after terminal script finishes —
            if self._term_idx >= len(TERM_SCRIPT) and t >= TERM_SCRIPT[-1][0] + 6:
                self.phase = 1
                self.tick  = 0

        # ── phase 1: brief "done" pause ──────────────────────────────────────
        elif self.phase == 1:
            if t == 0:
                self._append(self._term, "\n[  LOCK  ] Integrity hash committed.\n", "ok")
                self._append(self._term, "[  LOCK  ] System secured. ✓\n", "ok")
                self._append(self._code, ">>> # session sealed.\n", "comment")
            if t >= 12:
                self.phase = 2
                self.tick  = 0
                self._show_denied()

        # ── phase 2: ACCESS DENIED flash ────────────────────────────────────
        elif self.phase == 2:
            if self._denied_lbl:
                colors = [RED, DKRED, "#FF2222", "#CC0000", RED, "#FF5555", DKRED]
                self._denied_lbl.config(fg=colors[t % len(colors)])
            bg_cycle = ["#000000", "#0c0000", "#000000", "#060000"]
            self._denied_frame.config(bg=bg_cycle[t % len(bg_cycle)])
            if t >= 24:
                self._finish()
                return

        self.root.after(80, self._animate)

    # ─────────────────────────────────────────────────────────────────────────

    def _show_denied(self):
        for w in self.root.winfo_children():
            w.pack_forget()

        self._denied_frame.pack(fill=tk.BOTH, expand=True)
        W, H, fs = self.W, self.H, self.fs

        denied_fs = max(36, int(fs * 3.6))

        box = tk.Frame(self._denied_frame, bg="#0c0000",
                       highlightbackground=RED, highlightthickness=2)
        box.place(relx=0.5, rely=0.5, anchor="center",
                  width=int(W * 0.62), height=int(H * 0.44))

        self._denied_lbl = tk.Label(
            box, text="ACCESS  DENIED",
            font=(MONO, denied_fs, "bold"),
            fg=RED, bg="#0c0000"
        )
        self._denied_lbl.pack(pady=(30, 10))

        tk.Label(box,
                 text="AUTHENTICATION REQUIRED TO RESUME SESSION",
                 font=(MONO, fs + 1), fg="#CC0000", bg="#0c0000").pack()

        tk.Label(box,
                 text=f"User: {HOST}   ·   Session: {_SESSION_ID}   ·   Sealed by TPM 2.0",
                 font=(MONO, fs - 1), fg=DIMGRN, bg="#0c0000").pack(pady=10)

        tk.Frame(box, bg=DKRED, height=1).pack(fill=tk.X, padx=30)

        tk.Label(box,
                 text="[ Enter PIN · Fingerprint · Smart Card ]",
                 font=(MONO, fs - 1), fg=DIM, bg="#0c0000").pack(side=tk.BOTTOM, pady=14)

    def _finish(self):
        self.root.destroy()
        if not PREVIEW:
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])


if __name__ == "__main__":
    LockOverlay()
