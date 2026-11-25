"""Front-page generator for the make.fun bounty
"Sum up 25 November's world news in one image" (news-image-20261125).

Draws a 1024x1024 newspaper front page holding 39 Reuters stories first
reported on 25 November 2026: one lead story, five shorter top-story
briefs, and 33 one-line items grouped into seven regional sections.

Pure Python 3 standard library. The PNG is encoded by hand (zlib + CRC
chunks) and text is rendered with a small 5x7 bitmap font defined below,
so the output is byte-for-byte reproducible: no clocks, no randomness,
no locale or environment input reaches the image.
"""

import binascii
import os
import struct
import zlib

# --------------------------------------------------------------------------
# Canvas geometry and palette
# --------------------------------------------------------------------------

PAGE_W = 1024
PAGE_H = 1024
MARGIN = 34                        # left/right page margin
CONTENT_W = PAGE_W - 2 * MARGIN    # 956
COLUMN_W = 468
GUTTER = CONTENT_W - 2 * COLUMN_W  # 20

PAPER = (247, 244, 236)
INK = (28, 28, 30)
ACCENT = (150, 32, 32)
FAINT = (112, 109, 100)

# --------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is seven rows of five characters; '#'
# marks a set pixel. The advance width is six cells (one blank column of
# letterspacing) times the draw scale. Uppercase letters, digits and
# punctuation are defined here; lowercase letters follow in an update.
# --------------------------------------------------------------------------

GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
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
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", ".#.##", "#..##"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "&": (".#...", "#.#..", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
}

GLYPHS.update({
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#...", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".....", ".####", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
})

# Typographic characters folded onto glyphs the font actually has.
_REPLACEMENTS = {
    "\u2014": "-", "\u2013": "-", "\u2212": "-",
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u00d7": "x", "\u2022": "-", "\u2026": "...",
}


def sanitize(text):
    """Map text onto characters the bitmap font can draw."""
    out = []
    for ch in text:
        if ch in _REPLACEMENTS:
            out.append(_REPLACEMENTS[ch])
        elif ch in GLYPHS:
            out.append(ch)
        else:
            out.append(" ")
    return "".join(out)


def text_width(text, scale):
    """Pixel width of a string at the given scale (no trailing space)."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def wrap_text(text, scale, max_width, max_lines=None):
    """Greedy word wrap; overlong words are hard-split. When max_lines
    is given, extra lines are dropped and the last kept line is trimmed
    to end with an ellipsis."""
    per_line = max(1, (max_width + scale) // (6 * scale))
    lines = []
    current = ""
    for word in sanitize(text).split():
        while len(word) > per_line:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:per_line])
            word = word[per_line:]
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and text_width(last + "...", scale) > max_width:
            last = last[:-1].rstrip()
        lines[-1] = last + "..."
    return lines


class Canvas:
    """An RGB pixel buffer with rectangle fills and bitmap text."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(background * (width * height))

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            start = (yy * self.width + x0) * 3
            self.pixels[start:start + len(row)] = row

    def draw_text(self, x, y, text, scale, color):
        cursor = x
        for ch in text:
            glyph = GLYPHS.get(ch, GLYPHS[" "])
            for row_i, row in enumerate(glyph):
                for col_i, cell in enumerate(row):
                    if cell == "#":
                        self.fill_rect(cursor + col_i * scale,
                                       y + row_i * scale,
                                       scale, scale, color)
            cursor += 6 * scale
        return cursor - x


def _png_chunk(tag, payload):
    crc = binascii.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def write_png(canvas, path):
    """Encode the canvas as a deterministic RGB PNG (filter 0 rows,
    fixed compression level, no ancillary chunks)."""
    raw = bytearray()
    stride = canvas.width * 3
    for y in range(canvas.height):
        raw.append(0)
        raw += canvas.pixels[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _png_chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(data)

# --------------------------------------------------------------------------
# Story data: 39 Reuters items first reported on 25 November 2026.
# --------------------------------------------------------------------------

LEAD = (
    "Asian stocks tumble on fresh US tariff threats",
    "MSCI Asia ex-Japan -2.3%; Korea -5.3%, Taiwan -5.1%, Nikkei -2.9%",
)

BRIEFS = [
    ("SoftBank slumps 13.8% as chip stocks crater",
     "Advantest -12.7%, Tokyo Electron -11.8%; Samsung, SK Hynix -7%+"),
    ("Oil falls as glut fears outweigh Hormuz risks",
     "Brent $90.97 (-0.5%), WTI $81.58 (-0.6%)"),
    ("Dow tops 50,000 for the first time", ""),
    ("Dell posts record quarter, lifts FY2027 outlook to $202bn",
     "shares +4.1% after hours"),
    ("South Korea drafts stablecoin rules for banks", ""),
]

SECTIONS = [
    ("Asia-Pacific", [
        "Malaysia Aviation Group buys 10 Boeing 787 Dreamliners",
        "Australia and Solomon Islands sign security pact",
        "Myanmar landmine casualties highest for third straight year - 1,891 killed or injured in 2025",
        "Australia CPI hotter than expected",
        "Japan's 40-year bond auction draws weak demand",
        "China and India on track for record Russian oil imports",
        "Japan's trade minister heads to Washington over tariffs",
    ]),
    ("United States", [
        "US PCE inflation due today, core seen up 0.3% on month",
        "US Q3 GDP second estimate due today",
        "US jobless claims due today",
        "Fed's Beige Book due today",
        "Deere earnings due before the bell",
        "Trump awards Giuliani Medal of Freedom",
        'Trump pardons turkeys "Freedom" and "Feathers"',
        "Trump heads to Mar-a-Lago for Thanksgiving",
        "Abrego Garcia to leave US voluntarily",
        "House Democrats alarm at FAA AI tool deployment",
    ]),
    ("Europe", [
        "German Q3 GDP due today",
        "French consumer confidence due today",
        "European shares set to open lower as tech selloff spreads",
        "Drone strikes reported at two Russian oil refineries (Syzran, Kuibyshev, Samara region)",
    ]),
    ("Markets and Energy", [
        "Nvidia slides 5.9% as AI fears spread",
        "Anthropic shares 6.5% below IPO price",
        "Bitcoin slips to $59,258, ether to $1,661",
        "OPEC+ meets Nov 29 to set 2027 output policy",
        "Iraq presses OPEC+ to lift capacity estimate",
        "US futures slip as tariff fears weigh",
    ]),
    ("Middle East and Africa", [
        "Libya's Sharara oil pipeline reopens",
        "Three vessels struck near Strait of Hormuz on Monday (UKMTO)",
    ]),
    ("Latin America", [
        "Senate probes Vance role in Vitol Venezuela oil deal",
    ]),
    ("Global - Sport", [
        "Gukesh holds Sindarov in Game 1 draw at World Chess Championship - 38 moves",
        "Czechia reach Davis Cup semi-finals, 2-0 vs Canada - first since 2014",
        "Davis Cup: Italy face South Korea in quarter-finals today",
    ]),
]

# --------------------------------------------------------------------------
# Page layout
# --------------------------------------------------------------------------

LEFT_X = MARGIN
RIGHT_X = MARGIN + COLUMN_W + GUTTER
ITEM_INDENT = 10
FOOTER_RULE_Y = 966


def _centered_x(text, scale):
    return (PAGE_W - text_width(sanitize(text), scale)) // 2


def _rule(canvas, y, color=INK, height=1):
    canvas.fill_rect(MARGIN, y, CONTENT_W, height, color)


def draw_masthead(canvas):
    title = "THE WORLD LEDGER"
    canvas.draw_text(_centered_x(title, 7), 28, title, 7, INK)
    _rule(canvas, 90, ACCENT, 3)
    _rule(canvas, 97, INK, 1)
    dateline = "WEDNESDAY, 25 NOVEMBER 2026 - 39 STORIES"
    canvas.draw_text(_centered_x(dateline, 2), 106, dateline, 2, INK)
    _rule(canvas, 128, INK, 1)
    return 140


def draw_lead(canvas, y):
    canvas.draw_text(MARGIN, y, "TOP STORY", 1, ACCENT)
    y += 12
    headline, summary = LEAD
    for line in wrap_text(headline, 3, CONTENT_W, max_lines=2):
        canvas.draw_text(MARGIN, y, line, 3, INK)
        y += 26
    for line in wrap_text(summary, 2, CONTENT_W, max_lines=3):
        canvas.draw_text(MARGIN, y, line, 2, INK)
        y += 19
    return y + 8


def _draw_brief(canvas, x, y, headline, summary):
    for line in wrap_text(headline, 2, COLUMN_W, max_lines=2):
        canvas.draw_text(x, y, line, 2, INK)
        y += 18
    if summary:
        for line in wrap_text(summary, 1, COLUMN_W, max_lines=4):
            canvas.draw_text(x, y, line, 1, INK)
            y += 11
    return y + 14


def draw_briefs(canvas, y):
    canvas.draw_text(MARGIN, y, "MORE TOP STORIES", 1, ACCENT)
    y += 14
    left_y = y
    for headline, summary in BRIEFS[:3]:
        left_y = _draw_brief(canvas, LEFT_X, left_y, headline, summary)
    right_y = y
    for headline, summary in BRIEFS[3:]:
        right_y = _draw_brief(canvas, RIGHT_X, right_y, headline, summary)
    return max(left_y, right_y)


def _item_lines(item):
    return wrap_text(item, 1, COLUMN_W - ITEM_INDENT, max_lines=3)


def _section_height(items):
    height = 26
    for item in items:
        height += len(_item_lines(item)) * 12 + 4
    return height + 10


def _draw_section(canvas, x, y, name, items):
    canvas.draw_text(x, y, sanitize(name).upper(), 2, ACCENT)
    canvas.fill_rect(x, y + 17, COLUMN_W, 1, INK)
    y += 26
    for item in items:
        canvas.fill_rect(x, y + 2, 3, 3, ACCENT)
        for line in _item_lines(item):
            canvas.draw_text(x + ITEM_INDENT, y, line, 1, INK)
            y += 12
        y += 4
    return y + 10


def draw_sections(canvas, y):
    heights = [_section_height(items) for _, items in SECTIONS]
    half = sum(heights) / 2
    split = 0
    running = 0
    while split < len(SECTIONS) and (split == 0 or running + heights[split] <= half):
        running += heights[split]
        split += 1
    left_y = y
    for name, items in SECTIONS[:split]:
        left_y = _draw_section(canvas, LEFT_X, left_y, name, items)
    right_y = y
    for name, items in SECTIONS[split:]:
        right_y = _draw_section(canvas, RIGHT_X, right_y, name, items)
    return max(left_y, right_y)


def draw_footer(canvas):
    _rule(canvas, FOOTER_RULE_Y, INK, 1)
    text = "ALL ITEMS FROM REUTERS, 25 NOV 2026"
    canvas.draw_text(_centered_x(text, 1), FOOTER_RULE_Y + 8, text, 1, FAINT)


def render():
    canvas = Canvas(PAGE_W, PAGE_H, PAPER)
    y = draw_masthead(canvas)
    y = draw_lead(canvas, y)
    _rule(canvas, y, INK, 1)
    y = draw_briefs(canvas, y + 10)
    _rule(canvas, y, INK, 1)
    draw_sections(canvas, y + 10)
    draw_footer(canvas)
    return canvas


if __name__ == "__main__":
    target_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not target_dir:
        target_dir = "/output" if os.path.isdir("/output") else "."
    write_png(render(), os.path.join(target_dir, "entry.png"))
