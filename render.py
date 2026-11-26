#!/usr/bin/env python3
"""Render entry.png -- THE WORLD TODAY, Thursday 26 November 2026.

Pillow only. Every illustration is built from flat vector-style shapes
(polygons, ellipses, lines); no photographs or external images are used.
The page is drawn at 2x and downsampled for smooth anti-aliasing.
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

SS = 2                      # supersampling factor
W = H = 1024                # final size
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")

PAPER = (251, 248, 241)
INK = (17, 20, 24)
BODY = (34, 38, 44)
RED = (200, 16, 46)
GREY = (74, 79, 87)
WHITE = (255, 255, 255)

# ----------------------------------------------------------------- fonts
FONT_ROOTS = ["/usr/share/fonts", "/usr/local/share/fonts",
              os.path.expanduser("~/.fonts")]
_index = None


def find_font(*names):
    global _index
    if _index is None:
        _index = {}
        for root in FONT_ROOTS:
            if os.path.isdir(root):
                for dp, _, files in os.walk(root):
                    for f in files:
                        _index.setdefault(f, os.path.join(dp, f))
    for n in names:
        if n in _index:
            return _index[n]
    raise SystemExit("missing font: " + ", ".join(names))


SERIF_B = find_font("DejaVuSerif-Bold.ttf")
SANS_B = find_font("DejaVuSans-Bold.ttf")
SANS = find_font("DejaVuSans.ttf")
COND_B = find_font("DejaVuSansCondensed-Bold.ttf", "DejaVuSans-Bold.ttf")
COND = find_font("DejaVuSansCondensed.ttf", "DejaVuSans.ttf")
OBL = find_font("DejaVuSans-Oblique.ttf", "DejaVuSansCondensed-Oblique.ttf",
                "DejaVuSans.ttf")

_fc = {}


def font(path, size):
    """size is in final-image pixels."""
    key = (path, max(6, int(round(size * SS))))
    if key not in _fc:
        _fc[key] = ImageFont.truetype(path, key[1])
    return _fc[key]


def tw(text, path, size):
    return font(path, size).getlength(text) / SS


def wrap(text, path, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = word if not cur else cur + " " + word
        if not cur or tw(t, path, size) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(text, path, start, minimum, max_w, max_lines):
    size = start
    while True:
        lines = wrap(text, path, size, max_w)
        ok = len(lines) <= max_lines and max(tw(l, path, size) for l in lines) <= max_w
        if ok or size <= minimum:
            return size, lines
        size -= 0.5


def put(d, x, y, text, path, size, fill, anchor="la"):
    d.text((x * SS, y * SS), text, font=font(path, size), fill=fill, anchor=anchor)


def rect(d, x0, y0, x1, y1, fill):
    d.rectangle([x0 * SS, y0 * SS, x1 * SS - 1, y1 * SS - 1], fill=fill)


def text_block(d, x, y_top, y_bot, max_w, parts):
    """Lay out stacked text parts, shrinking until they fit the box height,
    then centre the block vertically."""
    avail = y_bot - y_top
    for shrink in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65):
        laid, total = [], 0.0
        for p in parts:
            s, lines = fit(p["text"], p["path"], p["size"] * shrink,
                           p["min"] * shrink, max_w, p["lines"])
            lh = s * p["lh"]
            laid.append((p, s, lines, lh))
            total += lh * len(lines) + p["gap"]
        total -= parts[-1]["gap"]
        if total <= avail:
            break
    y = y_top + max(0.0, (avail - total) / 2.0)
    for p, s, lines, lh in laid:
        for ln in lines:
            put(d, x, y, ln, p["path"], s, p["color"])
            y += lh
        y += p["gap"]


# ------------------------------------------------------------ art layers
class Art:
    """A clipped drawing layer. Shapes use a 100x100 unit square centred in
    the box; units outside 0..100 reach into the wider side of the box."""

    def __init__(self, w, h, bg):
        self.img = Image.new("RGB", (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.img)
        side = min(w, h)
        self.k = side * SS / 100.0
        self.ox = (w - side) * SS / 2.0
        self.oy = (h - side) * SS / 2.0

    def P(self, x, y):
        return (self.ox + x * self.k, self.oy + y * self.k)

    def _box(self, x0, y0, x1, y1):
        (a, b), (c, e) = self.P(x0, y0), self.P(x1, y1)
        return [min(a, c), min(b, e), max(a, c), max(b, e)]

    def W(self, w):
        return max(1, int(round(w * self.k)))

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0, r=0):
        box = self._box(x0, y0, x1, y1)
        wd = self.W(width) if outline else 0
        if r:
            self.d.rounded_rectangle(box, radius=r * self.k, fill=fill,
                                     outline=outline, width=wd)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=wd)

    def ell(self, x0, y0, x1, y1, fill=None, outline=None, width=0):
        wd = self.W(width) if outline else 0
        self.d.ellipse(self._box(x0, y0, x1, y1), fill=fill, outline=outline, width=wd)

    def circ(self, cx, cy, r, fill=None, outline=None, width=0):
        self.ell(cx - r, cy - r, cx + r, cy + r, fill, outline, width)

    def poly(self, pts, fill):
        self.d.polygon([self.P(*p) for p in pts], fill=fill)

    def line(self, pts, fill, width):
        self.d.line([self.P(*p) for p in pts], fill=fill, width=self.W(width),
                    joint="curve")

    def arc(self, x0, y0, x1, y1, start, end, fill, width):
        self.d.arc(self._box(x0, y0, x1, y1), start, end, fill=fill, width=self.W(width))

    def text(self, cx, cy, s, path, size, fill):
        f = ImageFont.truetype(path, max(6, int(round(size * self.k))))
        self.d.text(self.P(cx, cy), s, font=f, fill=fill, anchor="mm")

    def paste(self, img, x, y):
        img.paste(self.img, (int(x * SS), int(y * SS)))


# ---------------------------------------------------------- illustrations
def art_globe(a):
    a.circ(50, 50, 47, (30, 90, 160))
    g = (70, 170, 95)
    a.poly([(25, 30), (45, 20), (56, 34), (46, 50), (30, 46)], g)
    a.poly([(56, 56), (76, 50), (81, 70), (62, 83)], g)
    a.poly([(14, 60), (29, 61), (25, 79)], g)
    a.ell(30, 3, 70, 97, outline=(200, 225, 250), width=1.2)
    a.line([(3, 50), (97, 50)], (200, 225, 250), 1.2)
    a.circ(50, 50, 47, outline=INK, width=2.5)


def art_neuralink(a):
    tr = (196, 216, 238)
    for y in (10, 28, 46, 64, 82):
        a.line([(-20, y), (0, y), (6, y + 6), (14, y + 6)], tr, 1.2)
        a.circ(14, y + 6, 1.6, tr)
    for y in (70, 82, 94):
        a.line([(120, y), (102, y), (96, y - 6), (88, y - 6)], tr, 1.2)
        a.circ(88, y - 6, 1.6, tr)
    head = (27, 58, 92)
    a.ell(24, 14, 72, 66, head)
    a.poly([(30, 58), (36, 30), (52, 16), (64, 18), (72, 28), (74, 38), (80, 49),
            (75, 52), (76, 57), (73, 61), (74, 66), (68, 71), (60, 71), (58, 82),
            (62, 100), (26, 100), (33, 80)], head)
    a.ell(31, 21, 65, 47, (61, 110, 158))
    fold = (125, 165, 205)
    a.arc(34, 26, 48, 40, 200, 340, fold, 1.2)
    a.arc(46, 24, 60, 38, 200, 340, fold, 1.2)
    a.arc(37, 34, 51, 46, 180, 320, fold, 1.2)
    a.arc(50, 33, 63, 45, 200, 340, fold, 1.2)
    cyan = (25, 195, 230)
    for (x0, x1, y1) in ((44, 40, 30), (48, 47, 36), (52, 57, 31)):
        a.line([(x0, 17), (x1, y1)], cyan, 1.0)
        a.circ(x1, y1, 1.4, cyan)
    a.rect(41, 11, 55, 18, (242, 183, 5), r=1.5)
    a.rect(44.5, 13, 51.5, 16, (60, 50, 20))
    for r in (5, 8.5, 12):
        a.arc(48 - r, 13 - r, 48 + r, 13 + r, 215, 325, cyan, 1.3)
    # FDA approval badge
    a.circ(99, 24, 13, (30, 142, 62))
    a.circ(99, 24, 11, outline=WHITE, width=0.7)
    a.text(99, 21, "FDA", SANS_B, 7.5, WHITE)
    a.line([(93.5, 28), (97, 31.5), (104, 25.5)], WHITE, 1.8)
    a.rect(84, 42, 114, 52, INK, r=5)
    a.text(99, 47, "LINK TRIAL", COND_B, 4.6, WHITE)


def art_north_korea(a):
    a.rect(-20, 86, 120, 100, (230, 208, 208))
    a.rect(6, 42, 56, 86, (138, 148, 166))
    a.poly([(2, 42), (31, 26), (60, 42)], (74, 85, 104))
    win = (220, 230, 240)
    for (x, y) in ((11, 48), (43, 48), (11, 66), (43, 66)):
        a.rect(x, y, x + 8, y + 8, win)
    a.rect(25, 62, 37, 86, (60, 66, 80))
    a.line([(31, 26), (31, 4)], (60, 60, 60), 1.2)
    a.rect(31, 4, 43, 16, (213, 43, 30))
    a.rect(35.6, 6.5, 38.4, 13.5, WHITE)
    a.rect(33.5, 8.6, 40.5, 11.4, WHITE)
    a.line([(8, 44), (54, 84)], RED, 3)
    a.line([(54, 44), (8, 84)], RED, 3)
    # departing envoy with suitcase
    fig = (40, 44, 52)
    a.line([(71, 70), (67, 86)], fig, 3)
    a.line([(77, 70), (82, 86)], fig, 3)
    a.poly([(70, 54), (78, 54), (80, 71), (68, 71)], fig)
    a.circ(74, 48, 4.2, fig)
    a.line([(78, 57), (85, 66)], fig, 2)
    a.rect(82, 66, 95, 79, (150, 90, 40), r=1)
    a.line([(64, 34), (96, 34)], RED, 2.5)
    a.poly([(95, 29), (104, 34), (95, 39)], RED)
    a.rect(64, 8, 104, 23, RED, r=7)
    a.text(84, 15.5, "48 HRS", COND_B, 7.5, WHITE)


def art_iran_funding(a):
    a.rect(6, 24, 54, 86, WHITE, outline=(110, 110, 110), width=0.8, r=2)
    a.rect(6, 24, 54, 38, RED)
    a.text(30, 31, "JAN", SANS_B, 9, WHITE)
    a.text(30, 62, "31", SERIF_B, 24, INK)
    a.rect(15, 19, 19, 29, (60, 60, 60), r=1)
    a.rect(41, 19, 45, 29, (60, 60, 60), r=1)
    jet = (70, 78, 90)
    a.poly([(58, 21), (63, 21), (68, 29), (60, 30)], jet)
    a.poly([(75, 29), (84, 13), (89, 13), (85, 29)], jet)
    a.poly([(75, 30), (83, 44), (88, 44), (85, 31)], jet)
    a.poly([(57, 30), (90, 26), (105, 29.5), (90, 33)], jet)
    green, dark = (46, 139, 87), (25, 95, 55)
    for (x, y) in ((60, 76), (63, 67), (58, 58)):
        a.rect(x, y, x + 40, y + 10, green, outline=dark, width=0.7, r=1)
        a.circ(x + 20, y + 5, 3.2, outline=(200, 235, 210), width=0.6)
    a.text(78, 63, "$", SANS_B, 6.5, WHITE)


def _tanker(a, x, y, w):
    h = w * 0.18
    fx = x + w * 0.42
    smoke = (105, 105, 110)
    a.circ(fx - w * 0.05, y - h - w * 0.52, w * 0.13, smoke)
    a.circ(fx + w * 0.12, y - h - w * 0.62, w * 0.16, (130, 130, 135))
    a.circ(fx + w * 0.30, y - h - w * 0.72, w * 0.12, (150, 150, 155))
    a.poly([(x, y - h), (x + w, y - h), (x + w * 0.93, y), (x + w * 0.06, y)],
           (125, 35, 35))
    a.rect(x + w * 0.10, y - h - w * 0.05, x + w * 0.66, y - h, (85, 85, 90))
    a.rect(x + w * 0.74, y - h - w * 0.18, x + w * 0.90, y - h, (236, 236, 236))
    a.poly([(fx - w * 0.20, y - h), (fx - w * 0.12, y - h - w * 0.28),
            (fx - w * 0.03, y - h - w * 0.17), (fx + w * 0.05, y - h - w * 0.42),
            (fx + w * 0.13, y - h - w * 0.19), (fx + w * 0.21, y - h)], (240, 110, 30))
    a.poly([(fx - w * 0.10, y - h), (fx - w * 0.02, y - h - w * 0.14),
            (fx + w * 0.05, y - h - w * 0.26), (fx + w * 0.11, y - h)], (255, 210, 60))


def art_hormuz(a):
    a.rect(-20, 0, 120, 60, (255, 226, 200))
    a.rect(-20, 60, 120, 100, (31, 78, 121))
    # waves first so the burning ships sit on top of them
    for (x, y) in ((20, 94), (66, 66), (100, 96)):
        a.arc(x - 5, y - 2, x + 5, y + 2, 200, 340, (120, 170, 215), 0.8)
    _tanker(a, -2, 63, 26)        # far, left
    _tanker(a, 86, 63.5, 22)      # far, right (clear of the near smoke)
    _tanker(a, -6, 84, 50)        # near, left
    _tanker(a, 52, 92, 54)        # near, right
    a.circ(46, 94, 3.2, (25, 25, 28))
    for (dx, dy) in ((0, -5), (4, -3.5), (-4, -3.5)):
        a.line([(46, 94), (46 + dx, 94 + dy)], (25, 25, 28), 1)


def art_tariff(a):
    a.text(57, 15, "UP TO", COND_B, 5.5, INK)
    a.text(25, 43, "25%", SANS_B, 9, INK)
    a.text(57, 24, "40%", SANS_B, 9, INK)
    a.rect(14, 49, 36, 80, (255, 153, 51))
    a.rect(46, 30, 68, 80, (222, 41, 16))
    a.line([(6, 80), (80, 80)], INK, 1.5)
    a.text(25, 88, "INDIA", COND_B, 6.5, INK)
    a.text(57, 88, "CHINA", COND_B, 6.5, INK)
    for (y0, col) in ((60, (40, 120, 160)), (40, (230, 160, 40))):
        a.rect(80, y0, 106, y0 + 20, col)
        for i in range(1, 6):
            a.line([(80 + i * 4.3, y0 + 2), (80 + i * 4.3, y0 + 18)], (255, 255, 255), 0.6)


def art_nvidia(a):
    pin = (60, 70, 60)
    for i in range(5):
        p = 46 + i * 8
        a.line([(p, 20), (p, 26)], pin, 1.5)
        a.line([(p, 70), (p, 76)], pin, 1.5)
        q = 32 + i * 8
        a.line([(34, q), (40, q)], pin, 1.5)
        a.line([(84, q), (90, q)], pin, 1.5)
    a.rect(40, 26, 84, 70, (29, 43, 31), r=2)
    a.rect(48, 34, 76, 62, (118, 185, 0))
    a.text(62, 48, "GPU", SANS_B, 8, (29, 43, 31))
    a.circ(84, 14, 11.5, (205, 230, 250), outline=(40, 40, 40), width=2.5)
    a.line([(92.5, 22.5), (105, 35)], (40, 40, 40), 3.5)
    a.poly([(4, 34), (20, 28), (36, 34), (35, 56), (20, 70), (5, 56)], (43, 91, 168))
    a.line([(12, 48), (18, 55), (28, 41)], WHITE, 2.5)


def art_canary(a):
    a.circ(88, 14, 8, (255, 200, 60))
    a.rect(-20, 58, 120, 100, (44, 125, 184))
    a.poly([(56, 60), (68, 40), (76, 46), (88, 30), (100, 44), (112, 60)], (150, 110, 70))
    a.poly([(84, 36), (88, 30), (92, 36)], (90, 150, 80))
    a.poly([(52, 62), (114, 62), (112, 58), (56, 58)], (240, 215, 150))
    cols = [(230, 80, 70), (250, 200, 60), (60, 160, 90), (240, 240, 240),
            (90, 120, 200), (200, 90, 160), (250, 140, 40), (60, 60, 60)]
    for i in range(8):
        x = 7 + i * 5.6
        a.rect(x, 66, x + 4.4, 71, cols[i])
        a.circ(x + 2.2, 63.5, 2.4, cols[(i + 3) % 8])
    a.poly([(2, 70), (52, 70), (46, 82), (8, 82)], (224, 122, 47))
    for (x, y) in ((62, 74), (80, 84), (30, 90), (96, 70)):
        a.arc(x - 6, y - 2, x + 6, y + 2, 200, 340, (200, 230, 250), 0.8)
    a.rect(-6, 86, 52, 97, WHITE, r=5)
    a.text(23, 91.5, "NEARLY 2,000", COND_B, 6, INK)


# ---------------------------------------------------------------- content
LEAD = dict(
    kicker="LEAD STORY · SCIENCE & HEALTH",
    head="NEURALINK WINS FDA NOD FOR BRAIN-CHIP TRIAL",
    sub="Elon Musk's Neuralink gets US approval to begin the LINK pivotal "
        "trial of its brain implant.",
    src="Moneycontrol, 26 Nov 2026",
)

CARDS = [
    dict(kicker="STRAIT OF HORMUZ", head="FOUR TANKERS ABLAZE IN HORMUZ",
         sub="Mine strikes set four tankers on fire; Iran warns ships off "
             "unauthorised routes.",
         src="Saudi Gazette · Gulf News", bg=(255, 226, 200), art=art_hormuz),
    dict(kicker="US · IRAN", head="TRUMP: IRAN CAMPAIGN FUNDED TO JANUARY",
         sub="President says operations are funded to January's end; Tehran "
             "rules out talks on Hormuz.",
         src="Sunday Guardian", bg=(236, 241, 228), art=art_iran_funding),
    dict(kicker="KOREAN PENINSULA", head="NORTH KOREA EXPELS SWISS ENVOY",
         sub="Pyongyang orders Switzerland's new office shut and its envoy "
             "out within 48 hours.",
         src="Indian Express · Manila Times", bg=(253, 234, 234),
         art=art_north_korea),
    dict(kicker="TRADE", head="US TARIFF PLAN: INDIA 25%, CHINA UP TO 40%",
         sub="Washington's proposal hits 14 economies, with China facing "
             "rates as high as 40%.",
         src="Sunday Guardian", bg=(241, 236, 255), art=art_tariff),
    dict(kicker="TECH & POLITICS", head="VANCE DEFENDS NVIDIA'S HUANG",
         sub="Vice-president backs the Nvidia chief as Washington's scrutiny "
             "of the chipmaker grows.",
         src="Manila Times · AP", bg=(230, 244, 231), art=art_nvidia),
    dict(kicker="MIGRATION", head="RECORD DAY FOR CANARY ARRIVALS",
         sub="Nearly 2,000 migrants land in Spain's Canary Islands in a "
             "single day, a record.",
         src="Manila Times", bg=(223, 243, 255), art=art_canary),
]

TICKER = [
    "Anthropic CEO: humans must never give up free will to AI",
    "Egypt: 30 killed in blaze after vehicle overturns",
    "China and Cambodia hold joint military drills",
    "Kuala Lumpur sues Google for $146M over content",
]


# ------------------------------------------------------------- sections
def masthead(img, d):
    title = "THE WORLD TODAY"
    s, _ = fit(title, SERIF_B, 66, 40, 740, 1)
    put(d, W / 2, 80, title, SERIF_B, s, INK, anchor="ms")
    for gx in (44, W - 44 - 62):
        g = Art(62, 62, PAPER)
        art_globe(g)
        g.paste(img, gx, 22)
    rect(d, 14, 92, W - 14, 95, INK)
    rect(d, 14, 97, W - 14, 98, INK)
    put(d, W / 2, 121, "THURSDAY, 26 NOVEMBER 2026", SANS_B, 20, INK, anchor="ms")
    put(d, 14, 120, "WORLD EDITION", COND_B, 14, RED, anchor="ls")
    put(d, W - 14, 120, "7 STORIES · 4 BRIEFS", COND_B, 14, GREY, anchor="rs")
    rect(d, 14, 128, W - 14, 130, INK)


def lead(img, d):
    top, bot = 140, 458
    a = Art(420, bot - top, (227, 238, 250))
    art_neuralink(a)
    a.paste(img, 14, top)
    rect(d, 441, top + 24, 445, bot - 24, RED)   # lead accent bar in the gutter
    text_block(d, 454, top, bot, 556, [
        dict(text=LEAD["kicker"], path=SANS_B, size=15, min=12, lines=1,
             color=RED, lh=1.25, gap=10),
        dict(text=LEAD["head"], path=SERIF_B, size=42, min=30, lines=3,
             color=INK, lh=1.1, gap=12),
        dict(text=LEAD["sub"], path=SANS, size=19.5, min=16, lines=3,
             color=BODY, lh=1.32, gap=12),
        dict(text="Source: " + LEAD["src"], path=OBL, size=13, min=11, lines=1,
             color=GREY, lh=1.2, gap=0),
    ])
    rect(d, 14, 467, W - 14, 469, INK)


def grid(img, d):
    tops, ch = (478, 636, 794), 150
    for i, st in enumerate(CARDS):
        r, c = divmod(i, 2)
        y0 = tops[r]
        x0 = 14 if c == 0 else 520
        x1 = x0 + 490
        a = Art(170, 140, st["bg"])
        st["art"](a)
        a.paste(img, x0, y0 + 5)
        tx = x0 + 184
        text_block(d, tx, y0 + 4, y0 + ch - 4, x1 - tx, [
            dict(text=st["kicker"], path=COND_B, size=12.5, min=11, lines=1,
                 color=RED, lh=1.25, gap=3),
            dict(text=st["head"], path=COND_B, size=23, min=16, lines=2,
                 color=INK, lh=1.1, gap=6),
            dict(text=st["sub"], path=COND, size=15, min=12.5, lines=2,
                 color=BODY, lh=1.28, gap=5),
            dict(text="Source: " + st["src"], path=OBL, size=11.5, min=10,
                 lines=1, color=GREY, lh=1.2, gap=0),
        ])
    for y in (tops[1] - 5, tops[2] - 5):
        rect(d, 14, y, W - 14, y + 1, (160, 160, 160))
    rect(d, 511, tops[0], 513, tops[2] + ch, (160, 160, 160))


def ticker(img, d):
    y0 = 954
    rect(d, 0, y0, W, H, (18, 20, 24))
    rect(d, 0, y0, W, y0 + 3, RED)
    rect(d, 0, y0 + 3, 120, H, RED)
    s, _ = fit("IN BRIEF", SANS_B, 17, 12, 100, 1)
    put(d, 60, (y0 + 3 + H) / 2, "IN BRIEF", SANS_B, s, WHITE, anchor="mm")
    rect(d, 136, 989, W - 14, 990, (70, 74, 80))
    rect(d, 568, y0 + 12, 569, H - 10, (70, 74, 80))
    cols, rows = (136, 582), (973, 1007)
    for i, item in enumerate(TICKER):
        r, c = divmod(i, 2)
        x, cy = cols[c], rows[r]
        rect(d, x, cy - 3, x + 6, cy + 3, RED)
        s, _ = fit(item, COND, 15, 11, 410, 1)   # 596 + 410 = 1006 < 1010
        put(d, x + 14, cy, item, COND, s, WHITE, anchor="lm")


def save(im):
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    data = buf.getvalue()
    if len(data) > 1000000:
        buf = io.BytesIO()
        im.quantize(colors=256).save(buf, "PNG", optimize=True)
        data = buf.getvalue()
    with open(OUT, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (OUT, len(data)))


def main():
    img = Image.new("RGB", (W * SS, H * SS), PAPER)
    d = ImageDraw.Draw(img)
    masthead(img, d)
    lead(img, d)
    grid(img, d)
    ticker(img, d)
    lanczos = getattr(Image, "Resampling", Image).LANCZOS
    save(img.resize((W, H), lanczos))


if __name__ == "__main__":
    main()
