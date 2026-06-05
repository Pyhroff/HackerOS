"""
hex_stream.py — Live memory hex dump visualizer.

Replaces matrix rain entirely. Looks like a real memory/packet analyzer
(Wireshark hex pane, gdb x/16xb, xxd) scrolling live data.

Each row: ADDRESS │ 16 hex bytes (color-coded by value) │ ASCII
Special byte patterns (opcodes, magic numbers, strings) glow white.

ESC / mouse move  → exit
Any key           → burst (data floods in 4× faster)
"""
import tkinter as tk
import random
from datetime import datetime

# ── palette ───────────────────────────────────────────────────────────────────
BG       = "#000000"
C_ADDR   = "#005500"    # memory address
C_SEP    = "#002800"    # │ separators
C_ZERO   = "#001800"    # 00 byte — barely visible
C_DIM    = "#004400"    # 01-3F
C_MID    = "#009900"    # 40-9F
C_HI     = "#00dd00"    # A0-EF
C_BRIGHT = "#00FF41"    # F0-FF
C_HOT    = "#e8ffe8"    # special bytes — opcodes, magic numbers
C_PRNT   = "#007700"    # printable ASCII chars
C_DOT    = "#002200"    # · (non-printable)
C_HEAD   = "#00cc33"    # header / footer labels
C_RULE   = "#003300"    # horizontal rules
MONO     = "Courier New"

# bytes that get the bright "hot" highlight — common opcodes, magic numbers
_HOT = {
    0x4D, 0x5A,               # MZ  (PE header)
    0x7F,                     # ELF magic
    0x90,                     # NOP
    0xCC,                     # INT3  ← breakpoint — very suspicious
    0xEB, 0xE9,               # JMP short / near
    0xC3, 0xC2,               # RET
    0xFF,                     # 0xFF — often a prefix or fill byte
    0x48, 0x89, 0x8B,         # REX.W prefix, MOV variants (x86-64)
    0x0F,                     # two-byte opcode escape
}

def _tag(b: int) -> str:
    if b in _HOT:   return "hot"
    if b == 0x00:   return "zero"
    if b < 0x40:    return "dim"
    if b < 0xA0:    return "mid"
    if b < 0xF0:    return "hi"
    return "bright"

def _ch(b: int) -> str:
    return chr(b) if 0x20 <= b <= 0x7E else "·"

# ── interesting byte patterns injected occasionally ───────────────────────────
_PATTERNS = [
    (bytes([0x4D,0x5A,0x90,0x00,0x03,0x00,0x00,0x00,
            0x04,0x00,0x00,0x00,0xFF,0xFF,0x00,0x00]),
     "MZ header — PE executable"),

    (bytes([0x7F,0x45,0x4C,0x46,0x02,0x01,0x01,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]),
     "ELF magic — Linux binary"),

    (bytes([0x55,0x48,0x89,0xE5,0x48,0x83,0xEC,0x20,
            0x89,0x7D,0xFC,0x48,0x89,0x75,0xF0,0xC3]),
     "x86-64 function prologue"),

    (bytes([0x90]*16),
     "NOP sled — shellcode preamble"),

    (bytes([0xCC]*16),
     "INT3 × 16 — software breakpoints"),

    (bytes([0x00]*16),
     "null region — zeroed / freed"),

    (b"AES256\x00\x00KEY:\x00\x00\x00\x00",
     "embedded key material"),

    (b"password\x00\x00\x00\x00\x00\x00\x00\x00",
     "plaintext credential  ⚠"),

    (bytes([0x48,0x31,0xC0,0x48,0x31,0xFF,0x48,0x31,
            0xF6,0x48,0x31,0xD2,0x0F,0x05,0x90,0x90]),
     "syscall stub"),
]

_PATTERN_CHANCE = 0.07   # 7 % of rows get an interesting pattern

def _gen_row() -> tuple[bytes, str]:
    """Return (16 bytes, annotation_or_empty)."""
    if random.random() < _PATTERN_CHANCE:
        data, note = random.choice(_PATTERNS)
        return data[:16], note
    if random.random() < 0.08:
        # sparse zeros (freed / unmapped region)
        n = random.randint(10, 16)
        return bytes([0x00]*n + [random.randint(0, 4)]*(16-n))[:16], ""
    return bytes([random.randint(0, 255) for _ in range(16)]), ""


# ── main app ──────────────────────────────────────────────────────────────────
class HexStream:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost",    True)
        self.root.config(cursor="none")

        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Key>",    self._on_key)
        self.root.bind("<Motion>", self._on_mouse)
        self._mpos    = None
        self._boost   = 1
        self._boost_t = 0

        self.root.update()
        W, H = self.root.winfo_width(), self.root.winfo_height()

        # pick a font size that makes a full 16-byte row fit comfortably
        # row format: "  XXXXXXXX  │  XX XX × 8  ·  XX XX × 8  │  ................  [annotation]"
        # ≈ 100 chars wide — scale font to fit W
        fs = max(9, min(16, W // 105))
        font     = (MONO, fs)
        font_hdr = (MONO, fs, "bold")

        # start address somewhere in kernel/user-space boundary
        self._addr    = (random.randint(0x00007FF6, 0x00007FFF) << 16) & ~0xF
        self._total_b = 0
        self._total_r = 0

        # ── header ────────────────────────────────────────────────────────────
        self._hdr = tk.Label(self.root, text="", font=font_hdr,
                             fg=C_HEAD, bg=BG, anchor="w")
        self._hdr.pack(fill=tk.X, padx=10, pady=(8, 2))

        tk.Frame(self.root, bg=C_RULE, height=1).pack(fill=tk.X, padx=10)

        # column header
        col_hdr = (
            f"  {'ADDRESS':<10}  │  "
            f"{'── 00 01 02 03 04 05 06 07':28}  "
            f"{'08 09 0A 0B 0C 0D 0E 0F ──':28}  │  "
            f"{'0123456789ABCDEF':<16}"
        )
        tk.Label(self.root, text=col_hdr, font=(MONO, fs-1),
                 fg=C_RULE, bg=BG, anchor="w").pack(fill=tk.X, padx=10)

        tk.Frame(self.root, bg=C_RULE, height=1).pack(fill=tk.X, padx=10)

        # ── main text area ────────────────────────────────────────────────────
        self._txt = tk.Text(self.root, font=font, bg=BG, fg=C_MID,
                            bd=0, highlightthickness=0,
                            state="disabled", wrap=tk.NONE,
                            cursor="none", insertwidth=0)
        self._txt.pack(fill=tk.BOTH, expand=True, padx=10)

        for tag, color in [
            ("zero",   C_ZERO),  ("dim",    C_DIM),
            ("mid",    C_MID),   ("hi",     C_HI),
            ("bright", C_BRIGHT),("hot",    C_HOT),
            ("addr",   C_ADDR),  ("sep",    C_SEP),
            ("prnt",   C_PRNT),  ("dot",    C_DOT),
            ("note",   C_RULE),
        ]:
            kw = {"foreground": color}
            if tag == "hot":
                kw["font"] = (MONO, fs, "bold")
            self._txt.tag_configure(tag, **kw)

        tk.Frame(self.root, bg=C_RULE, height=1).pack(fill=tk.X, padx=10)

        # ── footer ────────────────────────────────────────────────────────────
        self._ftr = tk.Label(self.root, text="", font=(MONO, fs-1),
                             fg=C_RULE, bg=BG, anchor="w")
        self._ftr.pack(fill=tk.X, padx=10, pady=(2, 8))

        # how many lines fit before we trim
        self._max_lines = max(8, (H - 120) // (fs + 4))

        self._tick()
        self.root.mainloop()

    # ── input ─────────────────────────────────────────────────────────────────

    def _on_key(self, event):
        if event.keysym == "Escape":
            self.root.destroy()
            return
        self._boost   = 4
        self._boost_t = 22

    def _on_mouse(self, event):
        p = (event.x, event.y)
        if self._mpos and abs(p[0]-self._mpos[0]) + abs(p[1]-self._mpos[1]) > 7:
            self.root.destroy()
        self._mpos = p

    # ── row renderer ──────────────────────────────────────────────────────────

    def _add_row(self):
        data, note = _gen_row()
        addr = self._addr
        self._addr    += 16
        self._total_b += 16
        self._total_r += 1

        t = self._txt
        t.config(state="normal")

        # address
        t.insert("end", f"  {addr:016X}  ", "addr")
        t.insert("end", "│  ", "sep")

        # hex bytes: two groups of 8
        for i, b in enumerate(data):
            if i == 8:
                t.insert("end", "  ", "sep")
            t.insert("end", f"{b:02X} ", _tag(b))

        t.insert("end", " │  ", "sep")

        # ASCII representation
        for b in data:
            c = _ch(b)
            t.insert("end", c, "prnt" if c != "·" else "dot")

        # optional annotation for interesting patterns
        if note:
            t.insert("end", f"  ← {note}", "note")

        t.insert("end", "\n")

        # trim oldest lines
        lines = int(t.index("end-1c").split(".")[0])
        if lines > self._max_lines + 2:
            t.delete("1.0", f"{lines - self._max_lines}.0")

        t.config(state="disabled")

    # ── animation ─────────────────────────────────────────────────────────────

    def _tick(self):
        rows = self._boost
        for _ in range(rows):
            self._add_row()

        now = datetime.now()
        ts  = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
        self._hdr.config(
            text=(f"  HEX STREAM  ·  "
                  f"0x{self._addr - rows*16:016X} – 0x{self._addr:016X}  ·  "
                  f"LIVE  ·  {ts}")
        )
        self._ftr.config(
            text=(f"  {self._total_b:,} bytes scanned  ·  "
                  f"{self._total_r:,} rows  ·  "
                  f"{'BURST MODE' if self._boost > 1 else 'stream'}  ·  "
                  f"ESC to exit  ·  any key = burst")
        )

        if self._boost_t > 0:
            self._boost_t -= 1
            if self._boost_t == 0:
                self._boost = 1

        self.root.after(55, self._tick)


if __name__ == "__main__":
    HexStream()
