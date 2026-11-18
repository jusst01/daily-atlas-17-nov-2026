#!/usr/bin/env python3
"""Build-time renderer for the make.fun news-image-20261117 entry.

Draws THE DAILY ATLAS front page: 42 stories from Tuesday 17 November 2026
on a 1024x1024 canvas, and writes entry.png next to this file.

Run with:  .venv/bin/python draw.py
"""

from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------------
# palette
# ----------------------------------------------------------------------------
PAPER = (246, 241, 231)
CARD = (252, 250, 244)
INK = (22, 21, 19)
GREY = (110, 104, 94)
RED = (168, 28, 38)
NAVY = (27, 42, 68)
BORDER = (198, 191, 172)

CONTINENT = {
    "am": (172, 62, 42),
    "eu": (58, 84, 128),
    "me": (190, 124, 40),
    "af": (122, 106, 52),
    "as": (116, 80, 148),
    "oc": (44, 124, 134),
}
CONTINENT_LABEL = {
    "am": "Americas",
    "eu": "Europe",
    "me": "Mideast",
    "af": "Africa",
    "as": "Asia",
    "oc": "Oceania",
}

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"

W = H = 1024
MAX_BYTES = 1_048_576

# ----------------------------------------------------------------------------
# self-check scaffolding
# ----------------------------------------------------------------------------
DRAWN_STORIES: set[int] = set()
OVERFLOW: list[str] = []


def note_story(n: int) -> None:
    DRAWN_STORIES.add(n)


def overflow(kind: str, name: str, detail: str) -> None:
    OVERFLOW.append(f"{kind}: {name} -- {detail}")


# ----------------------------------------------------------------------------
# fonts
# ----------------------------------------------------------------------------
_font_cache: dict[tuple[str, float], ImageFont.FreeTypeFont] = {}


def font(name: str, size: float) -> ImageFont.FreeTypeFont:
    key = (name, round(float(size), 2))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONT_DIR + name, float(size))
    return _font_cache[key]


SERIF_B = "DejaVuSerif-Bold.ttf"
SERIF = "DejaVuSerif.ttf"
SANS_B = "DejaVuSans-Bold.ttf"
SANS = "DejaVuSans.ttf"

_scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def tw(text: str, f: ImageFont.FreeTypeFont) -> float:
    return _scratch.textlength(text, font=f)


def ink_box(text: str, f: ImageFont.FreeTypeFont) -> tuple[float, float, float, float]:
    return f.getbbox(text)


# ----------------------------------------------------------------------------
# text helpers
# ----------------------------------------------------------------------------
def put(d, x, y, text, f, fill, align="l", valign="top"):
    """Draw text with its *ink* top (or centre) at y. Returns the ink bbox."""
    bb = f.getbbox(text)
    w = tw(text, f)
    if align == "r":
        x = x - w
    elif align == "c":
        x = x - w / 2.0
    if valign == "top":
        dy = -bb[1]
    elif valign == "centre":
        dy = -((bb[1] + bb[3]) / 2.0)
    elif valign == "baseline":
        dy = 0.0
    else:
        raise ValueError(valign)
    d.text((x, y + dy), text, font=f, fill=fill)
    return (x + bb[0], y + dy + bb[1], x + bb[2], y + dy + bb[3])


def wrap(text: str, f: ImageFont.FreeTypeFont, maxw: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = (cur + " " + word).strip()
        if tw(trial, f) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            if tw(word, f) > maxw:
                overflow("wrap", text[:28], f"word wider than {maxw:.0f}px: {word!r}")
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def block(d, x, y, lines, f, fill, lh, align="l"):
    """Draw wrapped lines. Returns (ink_bbox, ink_bottom_of_last_line)."""
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    last_bottom = y
    for i, line in enumerate(lines):
        bx0, by0, bx1, by1 = put(d, x, y + i * lh, line, f, fill, align=align)
        x0, y0 = min(x0, bx0), min(y0, by0)
        x1, y1 = max(x1, bx1), max(y1, by1)
        last_bottom = by1
    return (x0, y0, x1, y1), last_bottom


def check_fit(name, box, limit_box) -> None:
    x0, y0, x1, y1 = box
    lx0, ly0, lx1, ly1 = limit_box
    if x1 > lx1 + 0.5:
        overflow("width", name, f"ink right {x1:.1f} > {lx1:.1f}")
    if x0 < lx0 - 0.5:
        overflow("left", name, f"ink left {x0:.1f} < {lx0:.1f}")
    if y1 > ly1 + 0.5:
        overflow("height", name, f"ink bottom {y1:.1f} > {ly1:.1f}")
    if y0 < ly0 - 0.5:
        overflow("height", name, f"ink top {y0:.1f} < {ly0:.1f}")


def hr(d, y, x0, x1, colour=INK, width=1):
    d.rectangle([x0, y, x1 - 1, y + width - 1], fill=colour)


# ----------------------------------------------------------------------------
# artwork fitting
# ----------------------------------------------------------------------------
def _load(name: str) -> Image.Image:
    return Image.open(os.path.join(ASSETS, name)).convert("RGB")


def cover_fit(img: Image.Image, w: int, h: int, fx=0.5, fy=0.5) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    nw, nh = max(w, int(math.ceil(img.width * scale))), max(h, int(math.ceil(img.height * scale)))
    r = img.resize((nw, nh), Image.LANCZOS)
    ox = int(round((nw - w) * fx))
    oy = int(round((nh - h) * fy))
    ox = max(0, min(nw - w, ox))
    oy = max(0, min(nh - h, oy))
    return r.crop((ox, oy, ox + w, oy + h))


def contain_fit(img: Image.Image, w: int, h: int, bg=(255, 255, 255)) -> Image.Image:
    scale = min(w / img.width, h / img.height)
    nw, nh = max(1, int(round(img.width * scale))), max(1, int(round(img.height * scale)))
    r = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGB", (w, h), bg)
    out.paste(r, ((w - nw) // 2, (h - nh) // 2))
    return out


def num_chip(d, cx, cy, r, n, f, fill=RED, fg=(255, 255, 255)):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    d.text((cx, cy + 0.5), str(n), font=f, fill=fg, anchor="mm")


# ----------------------------------------------------------------------------
# story data
# ----------------------------------------------------------------------------
FEATURED = [
    dict(
        n=1,
        kicker="UKRAINE · KERCH BRIDGE",
        headline="Ukraine brings down a span of Putin's Crimea bridge",
        summary=("Kyiv's seven-stage operation dropped the road arch into the Kerch "
                 "Strait overnight; rail resumed on one track. Moscow vows to rebuild it."),
        art="ultra-kerch.png",
        fx=0.5,
        tag="ROAD ARCH DOWN",
        tagc=INK,
    ),
    dict(
        n=2,
        kicker="IRAN · STRAIT OF HORMUZ",
        headline="Tankers hit mines in Hormuz, Iran says; US carrier arrives",
        summary=("Tehran says two tankers struck mines and caught fire on a route it "
                 "calls unauthorised. Brent crude settled at $92.76."),
        art="ultra-hormuz.png",
        fx=0.4,
        tag="TWO TANKERS ABLAZE",
        tagc=NAVY,
    ),
    dict(
        n=3,
        kicker="CHINA · APEC SUMMIT",
        headline="Trump, Xi and Putin to meet in Shenzhen — a first",
        summary=("China confirms the first three-way summit, on Thursday at APEC: nuclear "
                 "arms, Ukraine and Iran on the agenda. Trump lands in Manila first, for ASEAN."),
        art="ultra-shenzhen.png",
        fx=0.5,
        tag="FIRST TRILATERAL",
        tagc=RED,
    ),
]

# number, kicker, headline, summary, banner spec
GRID = [
    (4, "SCIENCE · SPACE", "Vulcan rocket fails; 40 Amazon satellites lost",
     "Anomaly minutes after liftoff, Florida.", ("art", "ultra-vulcan.png", 0.55)),
    (5, "UKRAINE · WAR", "Russian missiles hit Kyiv's two Dnipro bridges",
     "Heat and water cut across the capital.", ("art", "ultra-dnipro.png", 0.5)),
    (6, "MARKETS · TECH", "Nvidia revenue doubles to $115.8bn",
     "First earnings since Huang's exit.", ("art", "ultra-nvidia.png", 0.5)),
    (7, "UNITED STATES · BANKING", "JPMorgan blames software bug for outage",
     "Payments and Zelle slowed; not hackers.", ("art", "ultra-jpmorgan.png", 0.5)),
    (8, "UNITED STATES · DEFENCE", "Pentagon fails its ninth straight audit",
     "Auditors cannot verify $4.8 trillion in assets.", ("pentagon",)),
    (9, "JAPAN · AIRSPACE", "Japan scrambles jets, protests to Moscow",
     "Suspected Russian jets, early Tuesday.", ("jets",)),
    (10, "UNITED STATES · HEALTH", "US measles cases highest since 1991",
     "13 babies born with congenital measles.", ("measles",)),
    (11, "GLOBAL · ARMS", "Geneva talks on killer robots open",
     "128 states debate an autonomous-arms ban.", ("geneva",)),
    (12, "GAZA · AID", "West urges Israel to open Gaza crossings",
     "Allies call Gaza's situation catastrophic.", ("gaza",)),
    (13, "YEMEN · WAR", "Houthis close in on Aden as Saudis pull back",
     "Army quits the coast to defend the city.", ("aden",)),
    (14, "UNITED KINGDOM · WEST BANK", "UK sanctions eight settlement builders",
     "Freezes target builders blocking Gaza aid.", ("uk",)),
    (15, "EUROPE · TECH", "EU charges Temu over illegal goods",
     "Platform did too little on illegal sales.", ("temu",)),
]

BRIEFS = [
    (16, "Ebola cases pass 11,000 in DR Congo"),
    (17, "Mongolia's president quits over graft claims"),
    (18, "California sues OpenAI over AI-agent attack"),
    (19, "Dhoni retires from the IPL, turns CSK mentor"),
    (20, "Nigeria inflation falls to 14.06%, a six-year low"),
    (21, "Brazil rout Singapore 7–0; Vinícius hat-trick"),
    (22, "Five nations plan a Rwanda return hub"),
    (23, "US closes AI-chip loophole; Singapore seeks access"),
    (24, "Xi–Carney: China cuts $280m of Canada tariffs"),
    (25, "Brent crude settles at $92.76 on tanker risk"),
    (26, "Le Pen pledges an earlier retirement"),
    (27, "NYC: Mamdani disbands a police unit"),
    (28, "Washington state faces a $4bn gap"),
    (29, "House Democrats unveil their agenda"),
    (30, "Colorado issues its first housing report"),
    (31, "US denies Iran's ‘dirty bomb’ claim"),
    (32, "Chargers beat Ravens 23–20 on Monday night"),
    (33, "World will miss the 1.5°C climate target"),
    (34, "Sri Lanka bowled out for 98 in Rawalpindi"),
    (35, "Seattle shuts I-5 express lanes for repairs"),
    (36, "Estonia shuts its border crossings on 1 Dec"),
    (37, "Cybercrime losses hit $10.5tn a year"),
    (38, "Driverless taxis launch in Shenzhen"),
    (39, "Pope Leo XIV returns to Chiclayo, Peru"),
    (40, "Microsoft explains the global outage"),
    (41, "US flights still delayed as air recovers"),
    (42, "Netanyahu camp accused over arrests"),
]

# story: (lon, lat, dx, dy)
PINS = {
    1: (37.0, 45.4, 0, 0),
    2: (56.5, 26.5, 8, 6),
    3: (114.06, 22.55, -5, -13),
    4: (-80.6, 28.5, 0, 6),
    5: (30.5, 50.4, 8, -2),
    6: (-122.0, 37.4, -8, -6),
    7: (-74.0, 40.7, 12, 8),
    8: (-77.0, 38.9, 14, 12),
    9: (138.0, 37.0, 0, 0),
    10: (-98.0, 39.0, 0, 0),
    11: (6.1, 46.2, -8, -8),
    12: (34.3, 31.4, -12, 4),
    13: (45.0, 12.8, 6, 6),
    14: (-0.1, 51.5, -10, -6),
    15: (4.35, 50.85, 10, -10),
    16: (23.0, -2.0, 0, 0),
    17: (106.9, 47.9, 0, -6),
    19: (78.0, 21.0, 0, 0),
    20: (8.0, 10.0, 0, 0),
    21: (103.8, 1.35, 4, 8),
    22: (30.0, -2.0, 10, 10),
    24: (-75.7, 45.4, -6, 10),
    34: (80.7, 7.9, 4, 6),
    35: (-122.3, 47.6, -8, 8),
    36: (25.0, 59.0, 0, -6),
    39: (-79.8, -6.8, 8, 0),
}

REGION = {
    1: "eu", 2: "me", 3: "as", 4: "am", 5: "eu", 6: "am", 7: "am", 8: "am",
    9: "as", 10: "am", 11: "eu", 12: "me", 13: "me", 14: "eu", 15: "eu",
    16: "af", 17: "as", 19: "as", 20: "af", 21: "as", 22: "af", 24: "am",
    34: "as", 35: "am", 36: "eu", 39: "am",
}

# crude continent mask: per latitude row, list of (lon_start, lon_end) land spans.
# 36 rows from ~76N down to ~54S (lat step 134/36).
LAND = [
    [(-120, -62), (-55, -20), (8, 32), (55, 112)],              # 76N
    [(-160, -60), (-55, -20), (2, 36), (46, 122)],              # 72N
    [(-166, -58), (-52, -20), (-5, 36), (40, 140)],             # 68N
    [(-168, -56), (-50, -18), (-10, 36), (35, 160)],            # 65N
    [(-168, -56), (-46, -18), (-10, 42), (30, 172)],            # 61N
    [(-168, -56), (-130, -60), (-10, 44), (28, 178)],           # 57N
    [(-168, -56), (-10, 46), (26, 180)],                        # 54N
    [(-166, -55), (-9, 50), (24, 180)],                         # 50N
    [(-150, -56), (-9, 58), (22, 180)],                         # 46N
    [(-126, -66), (-9, 46), (42, 180)],                         # 43N
    [(-125, -72), (-9, 40), (44, 180)],                         # 39N
    [(-121, -76), (-9, 36), (46, 180)],                         # 35N
    [(-118, -79), (-10, 34), (35, 180)],                        # 31N
    [(-115, -80), (-11, 36), (35, 122), (128, 180)],            # 28N
    [(-112, -82), (-12, 36), (36, 120), (125, 180)],            # 24N
    [(-107, -83), (-16, 38), (38, 118), (122, 180)],            # 20N
    [(-100, -83), (-17, 44), (44, 112), (120, 180)],            # 17N
    [(-94, -82), (-17, 50), (50, 110)],                         # 13N
    [(-84, -78), (-16, 52), (52, 128)],                         # 9N
    [(-80, -76), (-12, 48), (55, 132)],                         # 5N
    [(-81, -72), (8, 44), (55, 138)],                           # 2N
    [(-81, -68), (10, 43), (58, 140)],                          # 2S
    [(-80, -62), (11, 42), (60, 142)],                          # 6S
    [(-79, -54), (11, 41), (62, 145)],                          # 9S
    [(-78, -48), (12, 40), (66, 152), (166, 178)],              # 13S
    [(-76, -42), (12, 40), (68, 150), (166, 178)],              # 17S
    [(-73, -40), (12, 39), (72, 148), (166, 179)],              # 21S
    [(-72, -46), (13, 38), (110, 155), (166, 179)],             # 24S
    [(-72, -49), (14, 36), (112, 154), (167, 179)],             # 28S
    [(-73, -52), (15, 33), (113, 152)],                         # 32S
    [(-74, -56), (16, 30), (114, 150)],                         # 36S
    [(-75, -60), (17, 28), (115, 148)],                         # 40S
    [(-75, -64), (18, 27), (172, 178)],                         # 43S
    [(-75, -66), (19, 26)],                                     # 47S
    [(-74, -68)],                                               # 50S
    [],                                                         # 54S
]


def continent_of(lon: float, lat: float) -> str:
    if lon < -30:
        return "am"
    if lon >= 112 and lat < -11:
        return "oc"
    if lon >= 52:
        return "as"
    if lat >= 42:
        return "eu"
    if lon >= 20 and lat >= 12:
        return "me"
    if lat >= 35:
        return "eu"
    return "af"


def muted(c, frac=0.5):
    return tuple(int(round(v + (p - v) * frac)) for v, p in zip(c, PAPER))


# ----------------------------------------------------------------------------
# procedural banners (all 238 x 42)
# ----------------------------------------------------------------------------
def banner_pentagon(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=(226, 222, 208))
    # grey pentagon glyph on the left
    cx, cy, r = x + 26, y + h / 2, 15
    pts = []
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=(126, 120, 108))
    d.polygon([(p[0], p[1] + 1) for p in pts], fill=None, outline=(96, 90, 80))
    d.rectangle([x + 56, y + 8, x + 56 + 96, y + h - 9], outline=RED, width=2)
    put(d, x + 62, y + h / 2, "9TH FAIL", font(SANS_B, 16), RED, valign="centre")


def _jet(d, cx, cy, s, colour, contrail, trail_len):
    # delta silhouette pointing right
    body = [
        (cx + s * 1.0, cy),
        (cx - s * 0.35, cy - s * 0.42),
        (cx - s * 0.12, cy - s * 0.10),
        (cx - s * 0.62, cy - s * 0.40),
        (cx - s * 0.40, cy - s * 0.06),
        (cx - s * 0.95, cy - s * 0.16),
        (cx - s * 0.45, cy),
        (cx - s * 0.95, cy + s * 0.16),
        (cx - s * 0.40, cy + s * 0.06),
        (cx - s * 0.62, cy + s * 0.40),
        (cx - s * 0.12, cy + s * 0.10),
        (cx - s * 0.35, cy + s * 0.42),
    ]
    if trail_len:
        for off in (-2, 2):
            d.line([(cx - s * 0.95, cy + off), (cx - s * 0.95 - trail_len, cy + off)],
                   fill=contrail, width=1)
    d.polygon(body, fill=colour)


def banner_jets(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h // 2 - 1], fill=(150, 182, 214))
    d.rectangle([x, y + h // 2, x + w - 1, y + h - 1], fill=(128, 164, 200))
    _jet(d, x + 66, y + 13, 13, (58, 60, 66), (250, 250, 250), 34)
    _jet(d, x + 118, y + 31, 11, (70, 72, 78), (250, 250, 250), 28)
    _jet(d, x + 196, y + 21, 21, RED, (168, 28, 38), 46)


def banner_measles(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=(250, 246, 238))
    cx, cy = x + 24, y + h / 2
    d.rectangle([cx - 6, cy - 15, cx + 6, cy + 15], fill=RED)
    d.rectangle([cx - 15, cy - 6, cx + 15, cy + 6], fill=RED)
    put(d, x + 48, h / 2 + y, "HIGHEST SINCE 1991", font(SANS_B, 13), INK, valign="centre")


def banner_geneva(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=(32, 36, 48))
    # monitor with two red dots
    mx0, my0, mx1, my1 = x + 9, y + 7, x + 71, y + 33
    d.rectangle([mx0, my0, mx1, my1], outline=(255, 255, 255), width=2)
    d.rectangle([mx0 + 22, my1 + 2, mx0 + 40, my1 + 4], fill=(255, 255, 255))
    d.ellipse([mx0 + 12, y + 15, mx0 + 20, y + 23], fill=RED)
    d.ellipse([mx0 + 40, y + 15, mx0 + 48, y + 23], fill=RED)
    # prohibition sign over the monitor
    ccx, ccy, r = x + 40, y + 20, 21
    d.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], outline=RED, width=3)
    d.line([(ccx - r * 0.72, ccy - r * 0.72), (ccx + r * 0.72, ccy + r * 0.72)],
           fill=RED, width=3)
    put(d, x + 88, y + h / 2, "128 STATES DEBATE", font(SANS_B, 11.5), (255, 255, 255),
        valign="centre")


def banner_gaza(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=(214, 196, 160))
    d.ellipse([x + w - 46, y + 3, x + w - 18, y + 31], fill=(214, 122, 60))
    # fence
    for i in range(5):
        px = x + 10 + i * 11
        d.rectangle([px, y + 12, px + 3, y + 31], fill=(62, 58, 50))
    d.rectangle([x + 6, y + 31, x + 64, y + 34], fill=(62, 58, 50))
    # aid truck driving right
    tx, ty = x + 96, y + 16
    d.rectangle([tx, ty, tx + 84, ty + 17], fill=(252, 252, 252))
    d.rectangle([tx + 84, ty + 5, tx + 112, ty + 17], fill=(252, 252, 252))
    d.rectangle([tx + 86, ty + 7, tx + 96, ty + 13], fill=(120, 140, 160))
    d.rectangle([tx + 30, ty + 3, tx + 56, ty + 14], fill=(200, 40, 46))
    d.rectangle([tx + 41, ty + 6, tx + 45, ty + 11], fill=(255, 255, 255))
    d.rectangle([tx + 34, ty + 7, tx + 42, ty + 10], fill=(255, 255, 255))
    d.rectangle([tx + 37, ty + 4, tx + 39, ty + 13], fill=(255, 255, 255))
    for wx in (tx + 18, tx + 74, tx + 100):
        d.ellipse([wx - 7, ty + 14, wx + 7, ty + 28], fill=(46, 44, 40))
        d.ellipse([wx - 2, ty + 19, wx + 2, ty + 23], fill=(190, 186, 176))


def banner_aden(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=(240, 220, 180))
    sea_y = y + h - 12
    d.rectangle([x, sea_y, x + w - 1, y + h - 1], fill=(52, 92, 138))
    # headland from the left
    d.polygon([(x, y + 12), (x + 34, y + 14), (x + 62, y + 22), (x + 78, sea_y),
               (x, sea_y)], fill=(186, 158, 116))
    # two port cranes
    for i, cx in enumerate((x + 16, x + 44)):
        hh = 22 if i == 0 else 18
        d.rectangle([cx, y + 20 - hh + 12, cx + 2, sea_y - 1], fill=(70, 64, 56))
        d.rectangle([cx - 7, y + 20 - hh + 12, cx + 11, y + 22 - hh + 12], fill=(70, 64, 56))
        d.line([(cx + 8, y + 23 - hh + 12), (cx + 8, y + 30 - hh + 12)], fill=(70, 64, 56), width=1)
    # cargo ship at the right
    sx, sy = x + 118, sea_y - 2
    d.polygon([(sx - 4, sy), (sx + 104, sy), (sx + 96, sy + 9), (sx + 2, sy + 9)],
              fill=(48, 52, 62))
    cols = [(196, 72, 60), (58, 96, 140), (214, 168, 60), (72, 132, 96)]
    for i in range(4):
        bx = sx + 4 + i * 23
        d.rectangle([bx, sy - 14, bx + 20, sy - 3], fill=cols[i])
        d.rectangle([bx + 3, sy - 20, bx + 17, sy - 15], fill=cols[(i + 1) % 4])
    d.rectangle([sx + 86, sy - 20, sx + 96, sy - 3], fill=(224, 226, 230))
    # wake
    for i in range(3):
        yy = sy + 11 + i * 1
        d.line([(sx - 8 - i * 10, yy), (sx + 20 - i * 6, yy)], fill=(236, 244, 250), width=1)


def banner_uk(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=NAVY)
    sx, sy = x + 12, y + 5
    shield = [(sx, sy), (sx + 27, sy), (sx + 27, sy + 18), (sx + 13.5, sy + 32),
              (sx, sy + 18)]
    d.polygon(shield, outline=(255, 255, 255))
    d.line(shield + [shield[0]], fill=(255, 255, 255), width=2)
    d.line([(sx + 13.5, sy + 3), (sx + 13.5, sy + 27)], fill=(255, 255, 255), width=2)
    d.line([(sx + 4, sy + 15), (sx + 23, sy + 15)], fill=(255, 255, 255), width=2)
    put(d, x + 48, y + h / 2, "8 BUILDERS SANCTIONED", font(SANS_B, 12), (255, 255, 255),
        valign="centre")


def banner_temu(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=(240, 140, 60))
    # phone
    d.rounded_rectangle([x + 10, y + 5, x + 46, y + h - 5], radius=5,
                        outline=(255, 255, 255), width=2)
    d.rectangle([x + 18, y + 12, x + 38, y + 30], outline=(255, 255, 255), width=1)
    # parcel with tape
    px, py = x + 56, y + 9
    d.rectangle([px, py, px + 54, py + 26], fill=(146, 104, 62))
    d.polygon([(px + 8, py), (px + 20, py + 26), (px + 30, py + 26), (px + 18, py)],
              fill=(196, 160, 112))
    d.line([(px, py + 4), (px + 54, py + 22)], fill=(206, 176, 128), width=3)
    put(d, x + w - 10, y + h / 2, "EU CHARGES", font(SANS_B, 12), (255, 255, 255),
        align="r", valign="centre")


BANNERS = {
    "pentagon": banner_pentagon,
    "jets": banner_jets,
    "measles": banner_measles,
    "geneva": banner_geneva,
    "gaza": banner_gaza,
    "aden": banner_aden,
    "uk": banner_uk,
    "temu": banner_temu,
}


# ----------------------------------------------------------------------------
# page
# ----------------------------------------------------------------------------
def build() -> Image.Image:
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.fontmode = "L"

    # ---------------- header ----------------
    put(d, 24, 10, "THE WORLD'S NEWS IN ONE PICTURE", font(SANS_B, 12.5), RED)
    put(d, 1000, 10, "42 STORIES · ONE PAGE", font(SANS_B, 12.5), INK, align="r")

    DATE = "Tuesday 17 November 2026"
    size = 86.0
    while size > 20:
        f = font(SERIF_B, size)
        if tw(DATE, f) <= 972:
            break
        size -= 0.5
    fd = font(SERIF_B, size)
    date_box = put(d, 512, 24, DATE, fd, INK, align="c")
    rule_y = int(round(date_box[3])) + 5
    hr(d, rule_y, 24, 1000, INK, 3)
    thin_y = rule_y + 3 + 5
    hr(d, thin_y, 24, 1000, INK, 1)

    base = thin_y + 1 + 12  # name strip baseline, 12px below the rules
    put(d, 24, base, "THE DAILY ATLAS", font(SANS_B, 13), INK, valign="baseline")
    put(d, 512, base, "EVERY STORY REPORTED ON THE DAY", font(SANS, 10.5), GREY,
        align="c", valign="baseline")
    put(d, 1000, base, "TUESDAY EDITION · NO. 17", font(SANS_B, 11), INK,
        align="r", valign="baseline")

    # ---------------- featured row ----------------
    CARD_W, CARD_H = 317, 244
    card_top = base + 24
    panel_h = 92
    for i, st in enumerate(FEATURED):
        cx = 24 + i * 329
        d.rectangle([cx, card_top, cx + CARD_W - 1, card_top + CARD_H - 1], fill=CARD,
                    outline=BORDER)
        art = _load(st["art"])
        panel = cover_fit(art, CARD_W, panel_h, fx=st["fx"], fy=0.5)
        im.paste(panel, (cx, card_top))
        # caption bar replacing the garbled baked-in strip
        bar_top = card_top + 64
        d.rectangle([cx, bar_top, cx + CARD_W - 1, card_top + panel_h - 1], fill=st["tagc"])
        stripe = RED if st["tagc"] != RED else INK
        d.rectangle([cx, bar_top, cx + 4, card_top + panel_h - 1], fill=stripe)
        put(d, cx + 14, bar_top + 14, st["tag"], font(SANS_B, 12), (255, 255, 255),
            valign="centre")

        panel_bottom = card_top + panel_h
        num_chip(d, cx + 20, panel_bottom + 14, 10, st["n"], font(SANS_B, 11))
        note_story(st["n"])
        kbox = put(d, cx + 38, panel_bottom + 14, st["kicker"], font(SANS_B, 10.5), RED,
                   valign="centre")
        if kbox[2] > cx + CARD_W - 6:
            overflow("kicker", f"featured {st['n']}", f"{kbox[2]:.1f} > {cx + CARD_W - 6}")

        head = wrap(st["headline"], font(SERIF_B, 19), 297)
        if len(head) > 3:
            overflow("headline", f"featured {st['n']}", f"{len(head)} lines")
        hb, hbot = block(d, cx + 10, card_top + 122, head, font(SERIF_B, 19), INK, 22)
        check_fit(f"featured {st['n']} headline", hb,
                  (cx + 6, card_top + 96, cx + CARD_W - 6, card_top + 192))
        summ = wrap(st["summary"], font(SERIF, 11), 297)
        sb, _ = block(d, cx + 10, hbot + 2, summ, font(SERIF, 11), GREY, 14)
        check_fit(f"featured {st['n']} summary", sb,
                  (cx + 6, card_top + 122, cx + CARD_W - 6, card_top + CARD_H - 3))

    featured_bottom = card_top + CARD_H

    # ---------------- grid ----------------
    TILE_W, TILE_H = 238, 98
    grid_top = featured_bottom + 16
    hr(d, grid_top - 8, 24, 1000, INK, 1)
    for idx, (n, kick, head, summ, banner) in enumerate(GRID):
        col, row = idx % 4, idx // 4
        tx = 24 + col * 246
        ty = grid_top + row * 108
        d.rectangle([tx, ty, tx + TILE_W - 1, ty + TILE_H - 1], fill=CARD, outline=BORDER)
        if banner[0] == "art":
            art = _load(banner[1])
            if banner[1] == "ultra-jpmorgan.png":
                strip = contain_fit(art, TILE_W, 42)
            else:
                strip = cover_fit(art, TILE_W, 42, fx=0.5, fy=banner[2])
            im.paste(strip, (tx, ty))
        else:
            BANNERS[banner[0]](d, tx, ty, TILE_W, 42)

        num_chip(d, tx + 14, ty + 50, 6.5, n, font(SANS_B, 7.5))
        note_story(n)
        kb = put(d, tx + 26, ty + 50, kick, font(SANS_B, 8.5), RED, valign="centre")
        if kb[2] > tx + TILE_W - 5:
            overflow("kicker", f"tile {n}", f"{kb[2]:.1f} > {tx + TILE_W - 5}")
        if kb[1] < ty + 42:
            overflow("kicker", f"tile {n}", "climbs into banner")

        hl = wrap(head, font(SERIF_B, 13), 222)
        hb, hbot = block(d, tx + 8, ty + 58, hl, font(SERIF_B, 13), INK, 14)
        if len(hl) > 2:
            overflow("headline", f"tile {n}", f"{len(hl)} lines")
        sl = wrap(summ, font(SERIF, 9.6), 222)
        if len(sl) > 1:
            overflow("summary", f"tile {n}", f"{len(sl)} lines")
        sb, _ = block(d, tx + 8, hbot + 1.5, sl, font(SERIF, 9.6), GREY, 11.5)
        check_fit(f"tile {n} text", (min(hb[0], sb[0]), hb[1], max(hb[2], sb[2]), sb[3]),
                  (tx + 5, ty + 52, tx + TILE_W - 5, ty + TILE_H - 2))

    grid_bottom = grid_top + 2 * 108 + TILE_H

    # ---------------- bottom section ----------------
    hr(d, grid_bottom + 12, 24, 1000, INK, 1)
    heading_top = grid_bottom + 24
    band_top = heading_top + 22

    put(d, 24, heading_top, "WHERE IT HAPPENED", font(SANS_B, 12), RED)
    put(d, 336, heading_top, "ALSO ON TUESDAY 17 NOVEMBER", font(SANS_B, 12), INK)

    # legend, laid out right-to-left
    lx = 1000
    for key in ("oc", "as", "af", "me", "eu", "am"):
        f = font(SANS, 8.5)
        label = CONTINENT_LABEL[key]
        lw = tw(label, f)
        put(d, lx - lw, heading_top + 2, label, f, GREY)
        lx -= lw + 3
        d.ellipse([lx - 7, heading_top + 2, lx, heading_top + 9], fill=CONTINENT[key])
        lx -= 7 + 10
    if lx < 336 + tw("ALSO ON TUESDAY 17 NOVEMBER", font(SANS_B, 12)) + 12:
        overflow("legend", "continent legend", "runs into ALSO heading")

    # briefs: pick font size and column breaks
    COLS = (336, 502, 668, 834)
    TEXT_W = 144
    LH_PAD = 2.0
    best = None
    for size in (10.5, 10.25, 10.0):
        fb = font(SANS, size)
        lh = size + LH_PAD
        lines = [wrap(t, fb, TEXT_W) for _, t in BRIEFS]
        heights = [len(l) * lh for l in lines]
        n = len(BRIEFS)
        cands = []
        for a in range(5, 10):
            for b in range(a + 5, a + 10):
                for c in range(b + 5, b + 10):
                    if n - c < 5 or n - c > 9:
                        continue
                    if b >= n or c >= n:
                        continue
                    groups = [(0, a), (a, b), (b, c), (c, n)]
                    hs = [sum(heights[i] + (4 if i < e - 1 else 0) for i in range(s, e))
                          for s, e in groups]
                    cands.append((max(hs) - min(hs), max(hs), groups, hs))
        if not cands:
            continue
        cands.sort()
        spread, tallest, groups, hs = cands[0]
        if band_top + tallest <= 970:
            best = (size, fb, lh, lines, groups, hs, tallest)
            break
        if best is None:
            best = (size, fb, lh, lines, groups, hs, tallest)
    size, fb, lh, blines, groups, col_heights, band_h = best
    print(f"brief size {size}  columns {[ (g[1]-g[0]) for g in groups ]} "
          f"heights {[round(h,1) for h in col_heights]} band {band_h:.1f}")

    # map
    map_x, map_w = 24, 296
    map_y, map_h = band_top, band_h
    d.rectangle([map_x, map_y, map_x + map_w - 1, map_y + map_h - 1],
                fill=(238, 232, 216), outline=BORDER)

    NC, NR = 73, 36
    cw, ch = map_w / NC, map_h / NR
    for r in range(NR):
        spans = LAND[r] if r < len(LAND) else []
        lat = 78 - (r + 0.5) * (134 / NR)
        for c in range(NC):
            lon = -168 + (c + 0.5) * (360 / NC)
            hit = any(a <= lon <= b for a, b in spans)
            if not hit:
                continue
            col = CONTINENT[continent_of(lon, lat)]
            x0 = map_x + int(round(c * cw))
            x1 = map_x + int(round((c + 1) * cw))
            y0 = map_y + int(round(r * ch))
            y1 = map_y + int(round((r + 1) * ch))
            d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=muted(col))

    for n, (lon, lat, dx, dy) in PINS.items():
        px = map_x + (lon + 168) / 360 * map_w + dx
        py = map_y + (78 - lat) / 134 * map_h + dy
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=CONTINENT[REGION[n]],
                  outline=PAPER)
        d.text((px, py + 0.5), str(n), font=font(SANS_B, 7), fill=(255, 255, 255),
               anchor="mm")
        note_story(n)

    # brief columns
    for (s, e), col_x in zip(groups, COLS):
        y = band_top
        for i in range(s, e):
            n, text = BRIEFS[i]
            num_chip(d, col_x + 7, y + lh / 2 - 1, 6.5, n, font(SANS_B, 7.5))
            note_story(n)
            bb, ybot = block(d, col_x + 18, y, blines[i], fb, INK, lh)
            check_fit(f"brief {n}", bb, (col_x + 16, y - 1, col_x + 18 + TEXT_W + 1,
                                         y + len(blines[i]) * lh + 1))
            y = ybot
            if i < e - 1:
                # dotted separator
                sy = y + 1
                x = col_x + 7
                while x < col_x + 164:
                    d.point((x, sy), fill=BORDER)
                    x += 5
                y += 4
        if y > band_top + band_h + 0.5:
            overflow("column", f"briefs at x={col_x}", f"bottom {y:.1f} > {band_top + band_h:.1f}")

    band_bottom = band_top + band_h

    # ---------------- footer ----------------
    hr(d, band_bottom + 12, 24, 1000, INK, 1)
    it_top = band_bottom + 12 + 1 + 7
    italic_put(im, d, 512, it_top,
               "And the day's quieter line: Sri Lanka were bowled out for 98 in "
               "Rawalpindi — their lowest total at the venue.",
               font(SERIF, 10), INK)
    put(d, 512, it_top + 17,
        "Every story happened or was first reported on Tuesday 17 November 2026 · "
        "Disputed claims are attributed · Sources: Reuters · AP · AFP · BBC · "
        "Al Jazeera · CNN · NPR · UN News",
        font(SANS, 8.5), GREY, align="c")

    return im


def italic_put(im: Image.Image, d, cx, top, text, f, fill):
    """Faux-italic: render, shear right at the top, composite centred."""
    w = int(math.ceil(tw(text, f))) + 4
    bb = f.getbbox(text)
    h = bb[3] - bb[1] + 4
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((2, -bb[1] + 2), text, font=f, fill=fill + (255,))
    k = 0.22
    out_w = w + int(k * h) + 2
    sheared = layer.transform((out_w, h), Image.AFFINE, (1, -k, k * h, 0, 1, 0),
                              resample=Image.BICUBIC)
    im.paste(sheared, (int(round(cx - out_w / 2)), int(round(top))), sheared)
    if cx - out_w / 2 < 24 or cx + out_w / 2 > 1000:
        overflow("footer", "italic line", f"{out_w}px wide at x={cx}")


def main() -> int:
    im = build()

    if DRAWN_STORIES != set(range(1, 43)):
        raise AssertionError(
            f"story numbers mismatch: missing {sorted(set(range(1,43)) - DRAWN_STORIES)} "
            f"extra {sorted(DRAWN_STORIES - set(range(1,43)))}")
    if OVERFLOW:
        for line in OVERFLOW:
            print("OVERFLOW", line)
        raise AssertionError(f"{len(OVERFLOW)} text block(s) overflow")

    out = os.path.join(HERE, "entry.png")
    im.save(out, "PNG", optimize=True)
    size = os.path.getsize(out)
    if size > MAX_BYTES:
        q = im.quantize(colors=256, method=Image.MEDIANCUT)
        q.save(out, "PNG", optimize=True)
        size = os.path.getsize(out)
        print("re-saved quantized to 256 colours")
    if size > MAX_BYTES:
        raise AssertionError(f"entry.png is {size} bytes, over the 1 MiB cap")
    print(f"entry.png {W}x{H} {size} bytes ({size / 1024:.1f} KiB), 42 stories, no overflow")
    return 0


if __name__ == "__main__":
    sys.exit(main())
