#!/usr/bin/env python3
"""Deterministically generate entry.png: 25 November 2026 world news.

Pure Python 3 standard library only. No network, no randomness, no clock.
Text is drawn with a small 5x7 bitmap font defined below (ASCII only).
39 stories: 6 fuller top stories + 33 compact one-line items in 7 regional
sections. All items are from Reuters dated 25 Nov 2026 (see BUILD-REPORT.md).
Run:  python3 main.py   -> writes entry.png to $MAKEFUN_OUTPUT_DIR when set,
else to /output when that directory exists, else to the working folder.
The image bytes are identical wherever they are written.
"""
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (247, 243, 232)
INK = (22, 22, 22)
GREY = (90, 90, 90)
WHITE = (255, 255, 255)
RED = (176, 32, 40)
DARK = (45, 45, 45)

# ---------------------------------------------------------------- font (5x7)
# Each glyph: 7 strings of 5 chars, '#' = on. (Same font as v1, our own code.)
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "2": (".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": (".##..", ".##..", ".#...", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "$": (".####", "#.#..", "#.#..", ".###.", "..#.#", "..#.#", "####."),
    "%": ("##..#", "##.#.", "....#", "...#.", "..#..", ".#...", "#..##"),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
}

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def fill_rect(x, y, w, h, color):
    r, g, b = color
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b


def text_width(text, scale):
    return len(text) * 6 * scale - scale if text else 0


def draw_text(x, y, text, scale, color):
    for ch in text:
        glyph = FONT[ch]
        for row in range(7):
            line = glyph[row]
            for col in range(5):
                if line[col] == "#":
                    fill_rect(x + col * scale, y + row * scale, scale, scale, color)
        x += 6 * scale
    return x


def draw_text_bold1(x, y, text, color):
    """Scale-1 text with a 1px horizontal double-strike for legibility."""
    for ch in text:
        glyph = FONT[ch]
        for row in range(7):
            line = glyph[row]
            for col in range(5):
                if line[col] == "#":
                    fill_rect(x + col, y + row, 2, 1, color)
        x += 6
    return x


def draw_centered(cx, y, text, scale, color):
    draw_text(cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap(text, max_chars):
    lines = []
    cur = ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- content
# Top stories: the six verified Reuters items of 25 Nov 2026 (see BUILD-REPORT.md).
TOP = [
    (
        "ASIA - MARKETS", (176, 32, 40),
        "ASIAN STOCKS TUMBLE ON FRESH US TARIFF THREATS",
        "MSCI ASIA EX-JAPAN FELL 2.3 PCT, KOREA DOWN 5.3 PCT, TAIWAN 5.1 PCT, "
        "NIKKEI 2.9 PCT.",
    ),
    (
        "TECH - MARKETS", (23, 64, 140),
        "SOFTBANK SLUMPS 13.8 PCT AS CHIP STOCKS CRATER",
        "ADVANTEST FELL 12.7 PCT AND TOKYO ELECTRON 11.8 PCT, SAMSUNG AND SK "
        "HYNIX DOWN OVER 7 PCT.",
    ),
    (
        "ENERGY - MARKETS", (0, 105, 105),
        "OIL FALLS AS GLUT FEARS OUTWEIGH HORMUZ RISKS",
        "BRENT FELL 0.5 PCT TO $90.97 AND WTI 0.6 PCT TO $81.58, DESPITE THREE "
        "SHIPS HIT NEAR HORMUZ.",
    ),
    (
        "US - MARKETS", (96, 48, 140),
        "DOW TOPS 50,000 FOR THE FIRST TIME",
        "THE BLUE-CHIP INDEX CLOSED ABOVE 50,000 ON TUESDAY, A FIRST, AS US "
        "STOCKS HELD UP.",
    ),
    (
        "US - EARNINGS", (150, 100, 20),
        "DELL POSTS RECORD QUARTER, LIFTS FY2027 OUTLOOK",
        "DELL RAISED ITS FY2027 REVENUE OUTLOOK TO $202 BLN, SHARES ROSE 4.1 "
        "PCT AFTER HOURS.",
    ),
    (
        "ASIA - CRYPTO", (30, 115, 60),
        "SOUTH KOREA DRAFTS STABLECOIN RULES FOR BANKS",
        "SEOUL UNVEILED DRAFT RULES LETTING BANKS ISSUE WON-BACKED "
        "STABLECOINS, A FIRST IN ASIA.",
    ),
]

# Compact one-line items by region. All Reuters, 25 Nov 2026 (see BUILD-REPORT.md).
SECTIONS = [
    ("ASIA-PACIFIC", (0, 105, 105), [
        "MALAYSIA AVIATION GROUP BUYS 10 BOEING 787S",
        "AUSTRALIA, SOLOMON ISLANDS SIGN SECURITY PACT",
        "MYANMAR LANDMINE TOLL HIGHEST FOR 3RD YEAR",
        "AUSTRALIA CPI HOTTER THAN EXPECTED",
        "JAPAN 40-YEAR BOND AUCTION DRAWS WEAK DEMAND",
        "CHINA, INDIA SET FOR RECORD RUSSIAN OIL IMPORTS",
        "JAPAN TRADE MINISTER HEADS TO WASHINGTON",
    ]),
    ("UNITED STATES", (23, 64, 140), [
        "US PCE INFLATION DUE TODAY, CORE SEEN UP 0.3 PCT",
        "US Q3 GDP SECOND ESTIMATE DUE TODAY",
        "US JOBLESS CLAIMS DUE TODAY",
        "FED'S BEIGE BOOK DUE TODAY",
        "DEERE EARNINGS DUE BEFORE THE BELL",
        "TRUMP AWARDS GIULIANI MEDAL OF FREEDOM",
        "TRUMP PARDONS TURKEYS FREEDOM AND FEATHERS",
        "TRUMP HEADS TO MAR-A-LAGO FOR THANKSGIVING",
        "ABREGO GARCIA TO LEAVE US VOLUNTARILY",
        "HOUSE DEMOCRATS ALARM AT FAA AI TOOL",
    ]),
    ("EUROPE", (96, 48, 140), [
        "GERMAN Q3 GDP DUE TODAY",
        "FRENCH CONSUMER CONFIDENCE DUE TODAY",
        "EUROPEAN SHARES SET TO OPEN LOWER",
        "DRONE STRIKES REPORTED AT TWO RUSSIAN REFINERIES",
    ]),
    ("MARKETS AND ENERGY", (70, 70, 70), [
        "NVIDIA SLIDES 5.9 PCT AS AI FEARS SPREAD",
        "ANTHROPIC SHARES 6.5 PCT BELOW IPO PRICE",
        "BITCOIN SLIPS TO $59,258, ETHER TO $1,661",
        "OPEC+ MEETS NOV 29 TO SET 2027 OUTPUT POLICY",
        "IRAQ PRESSES OPEC+ TO LIFT CAPACITY ESTIMATE",
        "US FUTURES SLIP AS TARIFF FEARS WEIGH",
    ]),
    ("MIDDLE EAST AND AFRICA", (150, 100, 20), [
        "LIBYA'S SHARARA OIL PIPELINE REOPENS",
        "THREE VESSELS STRUCK NEAR STRAIT OF HORMUZ",
    ]),
    ("LATIN AMERICA", (176, 32, 40), [
        "SENATE PROBES VANCE ROLE IN VITOL VENEZUELA DEAL",
    ]),
    ("GLOBAL - SPORT", (30, 115, 60), [
        "GUKESH HOLDS SINDAROV IN GAME 1 DRAW AT WORLD CHESS",
        "CZECHIA REACH DAVIS CUP SEMIS, 2-0 VS CANADA",
        "DAVIS CUP: ITALY FACE SOUTH KOREA IN QUARTERS",
    ]),
]

LEFT = 24
RIGHT = W - 24
COLW = (RIGHT - LEFT - 16) // 2  # compact column width


def check_content():
    texts = ["THE WORLD IN ONE IMAGE", "25 NOVEMBER 2026",
             "WEDNESDAY - 39 STORIES FROM AROUND THE GLOBE", "TOP STORIES",
             "ALL ITEMS FROM REUTERS, 25 NOV 2026"]
    for tag, _c, head, body in TOP:
        texts += [tag, head, body]
        if len(wrap(head, 38)) > 2:
            raise ValueError("top headline too long: " + head)
        if len(wrap(body, 76)) > 3:
            raise ValueError("top body too long: " + head)
    for name, _c, items in SECTIONS:
        texts.append(name)
        for it in items:
            texts.append(it)
            if text_width(it, 1) > COLW - 14:
                raise ValueError("compact item too wide: " + it)
    for t in texts:
        for ch in t:
            if ch not in FONT:
                raise ValueError("missing glyph: %r" % ch)


def main():
    check_content()
    fill_rect(0, 0, W, H, PAPER)

    # outer frame
    fill_rect(10, 10, W - 20, 4, INK)
    fill_rect(10, H - 14, W - 20, 4, INK)
    fill_rect(10, 10, 4, H - 20, INK)
    fill_rect(W - 14, 10, 4, H - 20, INK)

    # masthead
    draw_centered(W // 2, 24, "THE WORLD IN ONE IMAGE", 4, INK)
    fill_rect(40, 60, W - 80, 3, INK)
    draw_centered(W // 2, 72, "25 NOVEMBER 2026", 7, RED)
    draw_centered(W // 2, 132, "WEDNESDAY - 39 STORIES FROM AROUND THE GLOBE", 2, GREY)
    fill_rect(40, 154, W - 80, 5, INK)

    # ---- top stories ----
    y = 166
    fill_rect(LEFT, y, RIGHT - LEFT, 20, INK)
    draw_text(LEFT + 10, y + 3, "TOP STORIES", 2, WHITE)
    y += 28
    gap = 10
    cell_w = (RIGHT - LEFT - gap) // 2
    cell_h = 80
    for idx, (tag, color, head, body) in enumerate(TOP):
        cx = LEFT + (idx % 2) * (cell_w + gap)
        cy = y + (idx // 2) * (cell_h + 8)
        fill_rect(cx, cy, cell_w, cell_h, WHITE)
        fill_rect(cx, cy, cell_w, 2, INK)
        fill_rect(cx, cy + cell_h - 2, cell_w, 2, INK)
        fill_rect(cx, cy, 2, cell_h, INK)
        fill_rect(cx + cell_w - 2, cy, 2, cell_h, INK)
        fill_rect(cx + 2, cy + 2, cell_w - 4, 15, color)
        draw_text(cx + 10, cy + 6, tag, 1, WHITE)
        yy = cy + 22
        for line in wrap(head, 38):
            draw_text(cx + 10, yy, line, 2, INK)
            yy += 16
        yy += 2
        for line in wrap(body, 76):
            draw_text(cx + 10, yy, line, 1, DARK)
            yy += 9
    y += 3 * cell_h + 2 * 8 + 10

    # ---- compact regional sections ----
    for name, color, items in SECTIONS:
        fill_rect(LEFT, y, RIGHT - LEFT, 20, color)
        draw_text(LEFT + 10, y + 3, name, 2, WHITE)
        y += 26
        rows = (len(items) + 1) // 2
        for r in range(rows):
            for c in range(2):
                i = r * 2 + c
                if i >= len(items):
                    break
                ix = LEFT + c * (COLW + 16)
                fill_rect(ix + 1, y + 2, 4, 4, color)
                draw_text_bold1(ix + 12, y, items[i], INK)
            y += 13
        y += 8

    # footer
    fill_rect(40, y + 2, W - 80, 3, INK)
    draw_centered(W // 2, y + 12, "ALL ITEMS FROM REUTERS, 25 NOV 2026", 2, GREY)
    if y + 30 > H - 20:
        raise ValueError("layout overflow: footer at %d" % y)

    # ---- encode PNG (filter 0 per scanline, zlib) ----
    raw = bytearray()
    row_bytes = W * 3
    for yy in range(H):
        raw.append(0)
        raw += buf[yy * row_bytes:(yy + 1) * row_bytes]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = bytearray()
    png += b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or (
        "/output" if os.path.isdir("/output") else "."
    )
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
