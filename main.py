#!/usr/bin/env python3
"""SOLMARA — a 1930s-style travel poster for a place that isn't there.

A harbour town inside a drowned volcano crater, drawn entirely with the
Python standard library: no PIL, no font files, no network. The place
name is drawn as stroke geometry, the scene is painted into an RGB
buffer, and the buffer is encoded as a PNG by hand (zlib + struct).

Writes entry.png (1024x1024, <= 1 MiB) to $MAKEFUN_OUTPUT_DIR
(default /output). Deterministic: fixed seed, no wall-clock input.
"""

import math
import os
import random
import struct
import zlib

W = H = 1024

# ---------------------------------------------------------------- palette
INK      = (18, 58, 56)    # dark green-teal ink: name, frame, silhouettes
CREAM    = (246, 231, 198) # sky top, house walls
APRICOT  = (240, 176, 120) # sky middle
CORAL    = (224, 122, 96)  # sky near horizon
SUN      = (217, 90, 36)   # burnt-orange sun disc
GOLD     = (232, 168, 60)  # halo / glitter path
SEA_HI   = (84, 158, 148)  # sea at the horizon
SEA_LO   = (13, 66, 65)    # sea in the foreground
OLIVE    = (122, 122, 78)  # terraced hill
OLIVE_DK = (94, 104, 60)   # hill shadow facets
HOUSE    = (243, 230, 200) # house walls
ROOF     = (180, 85, 45)   # terracotta roofs
SAND     = (234, 217, 168) # pale sand crescent
UMBER    = (92, 58, 40)    # rocky headland
UMBER_DK = (70, 44, 30)    # headland shadow
RIDGE    = (168, 128, 108) # hazy low ridge behind the sun
LANTERN  = (245, 185, 66)  # amber lantern light
DARK     = (28, 48, 46)    # lighthouse cap / gallery

HORIZON = 540  # sea line, just below the middle of the square

# ------------------------------------------------------------------ buffer
buf = bytearray(W * H * 3)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def fill_span(y, x0, x1, rgb):
    """Fill one horizontal run of pixels on row y (inclusive)."""
    if y < 0 or y >= H:
        return
    x0 = max(0, int(x0))
    x1 = min(W - 1, int(x1))
    if x1 < x0:
        return
    n = x1 - x0 + 1
    i = (y * W + x0) * 3
    buf[i:i + 3 * n] = bytes(rgb) * n


def fill_rect(x0, y0, x1, y1, rgb):
    for y in range(max(0, y0), min(H, y1 + 1)):
        fill_span(y, x0, x1, rgb)


def vgrad(y0, y1, c_top, c_bot):
    """Vertical gradient band, full width, rows y0..y1."""
    span = max(1, y1 - y0)
    for y in range(max(0, y0), min(H, y1 + 1)):
        t = (y - y0) / span
        fill_span(y, 0, W - 1, lerp(c_top, c_bot, t))


def fill_circle(cx, cy, r, rgb):
    cx, cy = int(cx), int(cy)
    r = int(r)
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        fill_span(cy + dy, cx - dx, cx + dx, rgb)


def fill_poly(pts, rgb):
    """Scanline fill of a simple polygon given as [(x, y), ...]."""
    if len(pts) < 3:
        return
    ys = [p[1] for p in pts]
    y0, y1 = int(max(0, min(ys))), int(min(H - 1, max(ys)))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, yy0 = pts[i]
            x1, yy1 = pts[(i + 1) % n]
            if yy0 == yy1:
                continue
            if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                t = (y - yy0) / (yy1 - yy0)
                xs.append(x0 + t * (x1 - x0))
        if len(xs) < 2:
            continue
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            fill_span(y, int(math.ceil(xs[k])), int(math.floor(xs[k + 1])), rgb)


def _thick_segment(x0, y0, x1, y1, w, rgb):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        fill_circle(x0, y0, w / 2, rgb)
        return
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    fill_poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
               (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], rgb)
    fill_circle(x0, y0, w / 2, rgb)
    fill_circle(x1, y1, w / 2, rgb)


def stroke(pts, w, rgb):
    """A polyline drawn as a thick round-capped stroke."""
    for a, b in zip(pts, pts[1:]):
        _thick_segment(a[0], a[1], b[0], b[1], w, rgb)


def blend_px(x, y, rgb, alpha):
    """Alpha-blend one pixel over the buffer (alpha 0..1)."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        for c in range(3):
            buf[i + c] = int(round(buf[i + c] * (1 - alpha) + rgb[c] * alpha))


def radial_glow(cx, cy, r, rgb, peak):
    """Soft radial glow: alpha falls off quadratically to zero at r."""
    r = int(r)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d2 = dx * dx + dy * dy
            if d2 > r * r:
                continue
            t = 1 - math.sqrt(d2) / r
            blend_px(cx + dx, cy + dy, rgb, peak * t * t)


# ------------------------------------------------------------- letterforms
# Decorative spaced capitals, drawn as stroke geometry in a 0..1 box.
def _ellipse(cx, cy, rx, ry, steps=28):
    return [(cx + rx * math.cos(2 * math.pi * k / steps),
             cy + ry * math.sin(2 * math.pi * k / steps))
            for k in range(steps + 1)]


LETTERS = {
    "S": [[(0.82, 0.10), (0.62, 0.02), (0.34, 0.02), (0.16, 0.12),
           (0.14, 0.28), (0.30, 0.40), (0.62, 0.44), (0.80, 0.52),
           (0.86, 0.66), (0.78, 0.86), (0.58, 0.97), (0.32, 0.97),
           (0.14, 0.88), (0.12, 0.74)]],
    "O": [_ellipse(0.5, 0.5, 0.36, 0.47)],
    "L": [[(0.22, 0.04), (0.22, 0.96), (0.84, 0.96)]],
    "M": [[(0.14, 0.96), (0.14, 0.04), (0.50, 0.58),
           (0.86, 0.04), (0.86, 0.96)]],
    "A": [[(0.08, 0.96), (0.50, 0.04), (0.92, 0.96)],
          [(0.30, 0.64), (0.70, 0.64)]],
    "R": [[(0.20, 0.96), (0.20, 0.04), (0.62, 0.04), (0.84, 0.20),
           (0.84, 0.34), (0.62, 0.50), (0.20, 0.50)],
          [(0.58, 0.50), (0.86, 0.96)]],
}


def draw_word(word, x0, y0, lw, lh, gap, w, rgb):
    x = x0
    for ch in word:
        for poly in LETTERS[ch]:
            pts = [(x + px * lw, y0 + py * lh) for px, py in poly]
            stroke(pts, w, rgb)
        x += lw + gap


# ------------------------------------------------------------------ houses
def draw_house(x, y, s, rng):
    """A small white house with a terracotta roof; (x, y) is its base."""
    bw, bh = int(30 * s), int(20 * s)
    rh = int(12 * s)
    fill_rect(x - bw // 2, y - bh, x + bw // 2, y, HOUSE)
    fill_poly([(x - bw // 2 - 3, y - bh), (x + bw // 2 + 3, y - bh),
               (x, y - bh - rh)], ROOF)
    # two tiny ink windows and a door
    wx = int(7 * s)
    for dx in (-bw // 4, bw // 4):
        fill_rect(x + dx - 2, y - bh + 6, x + dx + 2, y - bh + 10, INK)
    fill_rect(x - 2, y - 6, x + 2, y, INK)
    _ = rng  # placement is seeded by the caller; kept for symmetry


def draw_cypress(x, y, h, wdt, rgb=INK):
    """A tall dark cypress: pointed teardrop silhouette."""
    fill_poly([(x - wdt // 2, y), (x - wdt // 2 + 3, y - h * 0.55),
               (x, y - h), (x + wdt // 2 - 3, y - h * 0.55),
               (x + wdt // 2, y)], rgb)
    fill_circle(x, int(y - h * 0.45), wdt // 2 - 1, rgb)


def draw_bird(x, y, s):
    """A small swallow: two short arcs meeting at a point."""
    stroke([(x - 11 * s, y - 4 * s), (x, y + 2 * s), (x + 11 * s, y - 4 * s)],
           3, INK)


def draw_boat(x, y, s, sail_rgb, hull_rgb):
    """A sailboat; (x, y) is the waterline under the hull."""
    # hull
    fill_poly([(x - 34 * s, y - 8 * s), (x + 34 * s, y - 8 * s),
               (x + 24 * s, y + 6 * s), (x - 24 * s, y + 6 * s)], hull_rgb)
    # mast
    stroke([(x, y - 8 * s), (x, y - 62 * s)], 3, hull_rgb)
    # mainsail
    fill_poly([(x + 2, y - 58 * s), (x + 2, y - 12 * s),
               (x + 30 * s, y - 12 * s)], sail_rgb)
    # jib
    fill_poly([(x - 2, y - 54 * s), (x - 2, y - 12 * s),
               (x - 26 * s, y - 12 * s)], sail_rgb)


# -------------------------------------------------------------------- scene
def paint():
    rng = random.Random(20261121)

    # 1. Sky: cream -> apricot -> soft coral down to the horizon.
    vgrad(0, 330, CREAM, APRICOT)
    vgrad(330, HORIZON, APRICOT, CORAL)

    # 2. Gold halo around the sun.
    radial_glow(512, 505, 260, GOLD, 0.38)

    # 3. Low hazy ridge behind the sun, spanning the crater gap.
    fill_poly([(0, 512), (180, 498), (380, 504), (620, 496), (840, 506),
               (1024, 500), (1024, HORIZON), (0, HORIZON)], RIDGE)

    # 4. The sun itself: one big burnt-orange disc, low over the bay.
    fill_circle(512, 505, 108, SUN)

    # 5. Terraced olive hill on the left, sloping down to the crater gap.
    hill = [(0, 296), (120, 318), (230, 360), (330, 410), (410, 470),
            (462, HORIZON), (0, HORIZON)]
    fill_poly(hill, OLIVE)
    # shadow facets on the hill face
    fill_poly([(0, 470), (180, 430), (330, 470), (410, 500), (300, HORIZON),
               (0, HORIZON)], OLIVE_DK)
    # terrace lines following the slope
    for t in (0.30, 0.52, 0.74):
        pts = []
        for k in range(9):
            u = k / 8
            x = int(20 + u * 400)
            y = int(330 + u * 190 + 26 * math.sin(u * 3.1))
            pts.append((x, y))
        stroke(pts, 3, OLIVE_DK)

    # houses climbing the hill, shrinking as they rise; each sits on the
    # hill's own surface, found by interpolating the slope's top edge.
    hill_top = [(0, 296), (120, 318), (230, 360), (330, 410), (410, 470),
                (462, HORIZON)]

    def surface_y(x):
        for (ax, ay), (bx, by) in zip(hill_top, hill_top[1:]):
            if ax <= x <= bx:
                t = (x - ax) / max(1, bx - ax)
                return ay + t * (by - ay)
        return HORIZON

    house_spots = []
    for _ in range(15):
        x = int(rng.uniform(35, 400))
        sy = surface_y(x)
        y = int(sy + rng.uniform(18, 95))
        if y > HORIZON - 12:
            continue
        s = 1.05 - (sy - 296) / 244 * 0.45 - rng.uniform(0, 0.12)
        house_spots.append((x, y, max(0.45, s)))
    house_spots.sort(key=lambda h: h[1])
    for x, y, s in house_spots:
        draw_house(x, y, s, rng)

    # two dark cypresses standing on the hill
    draw_cypress(196, 402, 74, 22)
    draw_cypress(318, 452, 60, 18)

    # 6. Rocky umber headland on the right, carrying the lighthouse.
    head = [(1024, 372), (918, 396), (846, 452), (806, 512),
            (800, HORIZON), (1024, HORIZON)]
    fill_poly(head, UMBER)
    fill_poly([(1024, 470), (940, 452), (860, 500), (830, HORIZON),
               (1024, HORIZON)], UMBER_DK)
    # lighthouse: banded tower, gallery, dark cap, amber lantern
    lx = 884
    tower = [(lx - 26, 470), (lx - 19, 322), (lx + 19, 322), (lx + 26, 470)]
    fill_poly(tower, HOUSE)
    for band_y0, band_y1 in ((428, 452), (372, 396)):
        fill_poly([(lx - 25, band_y0), (lx + 25, band_y0),
                   (lx + 22, band_y1), (lx - 22, band_y1)], ROOF)
    # gallery + cap + lantern
    fill_rect(lx - 24, 306, lx + 24, 322, DARK)
    fill_rect(lx - 10, 288, lx + 10, 306, LANTERN)
    radial_glow(lx, 297, 46, LANTERN, 0.55)
    fill_poly([(lx - 13, 288), (lx + 13, 288), (lx + 7, 274),
               (lx - 7, 274)], DARK)
    fill_rect(lx - 30, 470, lx + 30, 478, UMBER_DK)

    # 7. The sea: teal, bright at the horizon, dark toward the viewer.
    vgrad(HORIZON, 760, SEA_HI, (24, 96, 94))
    vgrad(760, H, (24, 96, 94), SEA_LO)

    # 8. Gold glitter path under the sun, widening as it nears.
    for k in range(46):
        t = rng.random()
        y = int(HORIZON + 8 + t * (H - HORIZON - 30))
        half = int(26 + t * 150)
        cx = 512 + int(rng.uniform(-half, half))
        wdt = int(rng.uniform(10, 46) * (0.5 + t))
        a = 0.28 + 0.5 * rng.random()
        for yy in range(y, y + 3):
            for xx in range(cx - wdt // 2, cx + wdt // 2):
                blend_px(xx, yy, GOLD, a * (1 - abs(xx - cx) / (wdt / 2 + 1)))

    # 9. Pale sand crescent at the foot of the left hill.
    fill_poly([(0, 560), (110, 566), (210, 584), (290, 612), (272, 626),
               (150, 632), (40, 612), (0, 592)], SAND)

    # 10. Two sailboats: one big pale sail left of the glitter path,
    #     one small dark silhouette lower right.
    draw_boat(330, 726, 1.0, CREAM, INK)
    draw_boat(712, 862, 0.62, (60, 90, 88), INK)

    # 11. Four swallows in the right-centre sky.
    for bx, by, bs in ((700, 178, 1.0), (762, 208, 0.85), (648, 238, 0.9),
                       (826, 168, 0.75)):
        draw_bird(bx, by, bs)

    # 12. Tall dark cypress silhouettes framing the bottom corners.
    draw_cypress(64, H, 210, 46)
    draw_cypress(962, H, 180, 40)

    # 13. The name, and only the name.
    draw_word("SOLMARA", 210, 62, 64, 92, 26, 10, INK)
    # printer's rule with a small diamond at its centre
    stroke([(310, 190), (714, 190)], 3, INK)
    fill_poly([(512, 180), (522, 190), (512, 200), (502, 190)], INK)

    # 14. Double-rule ink frame, drawn last over everything.
    for inset, w in ((26, 5), (42, 2)):
        x0, y0, x1, y1 = inset, inset, W - 1 - inset, H - 1 - inset
        fill_rect(x0, y0, x1, y0 + w - 1, INK)
        fill_rect(x0, y1 - w + 1, x1, y1, INK)
        fill_rect(x0, y0, x0 + w - 1, y1, INK)
        fill_rect(x1 - w + 1, y0, x1, y1, INK)


# ---------------------------------------------------------------------- png
def _chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * W * 3:(y + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    paint()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
