"""Erzeugt das Videovollautomat-Logo als SVG (Schrift in Pfade umgewandelt).

Aufruf:  python3 logo/build_logo.py
Benötigt: fonttools + brotli (pip install fonttools brotli)
Schriften: explainer-protein/styleframes/fonts (Anton, Space Mono, SIL OFL)
"""
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "explainer-protein" / "styleframes" / "fonts"

# Farben aus motion-spec, Stil A (Neo-Brutalismus)
INK = "#000000"
PAPER = "#F4F4F0"
PINK = "#FF90E8"
YELLOW = "#FFC900"
PERI = "#90A8ED"
TEAL = "#23A094"
CORAL = "#FF7051"
WHITE = "#FFFFFF"


class Font:
    def __init__(self, name):
        self.f = TTFont(FONTS / name)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        self.hmtx = self.f["hmtx"]
        self.cap = self.f["OS/2"].sCapHeight or 0.7 * self.upm

    def text(self, s, x, y, cap_px, tracking=0.0):
        """Pfad für Text; y = Grundlinie, cap_px = Versalhöhe in px.
        Gibt (d, breite) zurück."""
        scale = cap_px / self.cap
        pen = SVGPathPen(self.gs)
        cx = 0.0
        names = [self.cmap[ord(c)] for c in s]
        for i, gname in enumerate(names):
            tp = TransformPen(pen, (scale, 0, 0, -scale, x + cx, y))
            self.gs[gname].draw(tp)
            cx += self.hmtx[gname][0] * scale
            if i < len(names) - 1:
                cx += tracking * cap_px
        return pen.getCommands(), cx

    def width(self, s, cap_px, tracking=0.0):
        return self.text(s, 0, 0, cap_px, tracking)[1]

    def ink_bounds(self, s, cap_px, tracking=0.0):
        """Tatsächliche Tintenbreite (ohne Seitenabstände der Glyphen)."""
        scale = cap_px / self.cap
        bp = BoundsPen(self.gs)
        cx = 0.0
        names = [self.cmap[ord(c)] for c in s]
        for i, gname in enumerate(names):
            tp = TransformPen(bp, (scale, 0, 0, scale, cx, 0))
            self.gs[gname].draw(tp)
            cx += self.hmtx[gname][0] * scale
            if i < len(names) - 1:
                cx += tracking * cap_px
        xmin, _, xmax, _ = bp.bounds
        return xmin, xmax


ANTON = Font("Anton-400.woff2")
MONO = Font("SpaceMono-700.woff2")


def signet(ox=0, oy=0, s=1.0, ink=INK, body=YELLOW, screen=PINK, shadow=True):
    """Signet im 512er-Raster: ein Automat mit Bildschirm (Play),
    Zahnrad-Knopf und Ausgabeschacht, aus dem ein Filmstreifen läuft."""
    sw = 14  # Konturstärke
    g = [f'<g transform="translate({ox} {oy}) scale({s})" '
         f'stroke-linejoin="round" stroke-linecap="round">']
    # harter Versatzschatten (Neo-Brutalismus)
    if shadow:
        g.append(f'<rect x="96" y="60" width="336" height="420" rx="30" fill="{ink}"/>')
    # Gehäuse
    g.append(f'<rect x="72" y="36" width="336" height="420" rx="30" '
             f'fill="{body}" stroke="{ink}" stroke-width="{sw}"/>')
    # Bildschirm
    g.append(f'<rect x="112" y="76" width="256" height="184" rx="14" '
             f'fill="{screen}" stroke="{ink}" stroke-width="{sw}"/>')
    # Play-Dreieck mit weichen Ecken
    g.append(f'<path d="M210 122 L298 168 L210 214 Z" fill="{WHITE}" '
             f'stroke="{ink}" stroke-width="{sw}"/>')
    # Statuslämpchen
    g.append(f'<circle cx="138" cy="102" r="7" fill="{ink}" stroke="none"/>')
    # Bedienleiste: Zahnrad-Knopf + zwei Tasten
    g.append(gear(150, 318, 30, 8, ink, PERI, sw))
    g.append(f'<rect x="214" y="298" width="64" height="40" rx="10" '
             f'fill="{TEAL}" stroke="{ink}" stroke-width="{sw}"/>')
    g.append(f'<rect x="296" y="298" width="72" height="40" rx="10" '
             f'fill="{CORAL}" stroke="{ink}" stroke-width="{sw}"/>')
    # Ausgabeschacht
    g.append(f'<rect x="132" y="376" width="216" height="34" rx="10" '
             f'fill="{ink}" stroke="{ink}" stroke-width="{sw}"/>')
    # Filmstreifen, der aus dem Schacht kommt
    g.append(filmstrip(ink, sw))
    g.append("</g>")
    return "\n".join(g)


def gear(cx, cy, r, teeth, ink, fill, sw):
    import math
    pts = []
    ro, ri = r, r * 0.72
    n = teeth * 2
    for i in range(n * 2):
        a = math.pi * 2 * i / (n * 2) - math.pi / 2
        rad = ro if (i // 2) % 2 == 0 else ri
        pts.append(f"{cx + rad * math.cos(a):.1f} {cy + rad * math.sin(a):.1f}")
    d = "M" + " L".join(pts) + " Z"
    return (f'<path d="{d}" fill="{fill}" stroke="{ink}" stroke-width="{sw * 0.8}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.28:.1f}" fill="{ink}"/>')


def filmstrip(ink, sw):
    x, y, w, h = 176, 392, 128, 104
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" '
           f'fill="{ink}" stroke="{ink}" stroke-width="{sw * 0.6}"/>']
    # Perforation links/rechts
    for i in range(4):
        py = y + 14 + i * 22
        out.append(f'<rect x="{x + 8}" y="{py}" width="12" height="10" rx="2" fill="{PAPER}"/>')
        out.append(f'<rect x="{x + w - 20}" y="{py}" width="12" height="10" rx="2" fill="{PAPER}"/>')
    # Einzelbild
    out.append(f'<rect x="{x + 30}" y="{y + 26}" width="{w - 60}" height="60" rx="4" fill="{PINK}"/>')
    return "\n".join(out)


def svg(w, h, body, bg=None, title="Videovollautomat"):
    bgrect = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" role="img" aria-label="{title}">\n'
            f'<title>{title}</title>\n{bgrect}\n{body}\n</svg>\n')


def wordmark(x, baseline, cap, ink, accent, track=0.02, tag=True, video_ink=INK, shadow_ink=None):
    """'VIDEO' auf pinkem Balken + 'VOLLAUTOMAT' in Anton, darunter Claim."""
    parts = []
    pad_x, pad_y = cap * 0.16, cap * 0.16
    vx0, vx1 = ANTON.ink_bounds("VIDEO", cap, track)
    d_video, w_video = ANTON.text("VIDEO", x + pad_x - vx0, baseline, cap, track)
    # Balken hinter VIDEO, mit hartem Schatten
    bx, by = x, baseline - cap - pad_y
    bw, bh = (vx1 - vx0) + 2 * pad_x, cap + 2 * pad_y
    off = cap * 0.07
    parts.append(f'<rect x="{bx + off:.1f}" y="{by + off:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{cap*0.06:.1f}" fill="{shadow_ink or ink}"/>')
    parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{cap*0.06:.1f}" '
                 f'fill="{accent}" stroke="{video_ink}" stroke-width="{cap*0.045:.1f}"/>')
    parts.append(f'<path d="{d_video}" fill="{video_ink}"/>')
    rx0, rx1 = ANTON.ink_bounds("VOLLAUTOMAT", cap, track)
    x2 = bx + bw + off + cap * 0.14
    d_rest, _ = ANTON.text("VOLLAUTOMAT", x2 - rx0, baseline, cap, track)
    parts.append(f'<path d="{d_rest}" fill="{ink}"/>')
    right = x2 + (rx1 - rx0)
    if tag:
        claim = "SCHNITT · MOTION · EXPORT — AUTOMATISCH"
        tcap = cap * 0.17
        tx0, tx1 = MONO.ink_bounds(claim, tcap, 0.12)
        # Claim auf volle Wortmarkenbreite strecken (über Laufweite)
        full = right - x
        n = len(claim) - 1
        extra = (full - (tx1 - tx0)) / n / tcap
        d_tag, _ = MONO.text(claim, x - tx0, baseline + pad_y + off + tcap * 2.1, tcap, 0.12 + extra)
        parts.append(f'<path d="{d_tag}" fill="{ink}"/>')
    return "\n".join(parts), right


def build():
    out = HERE
    # 1) Signet einzeln
    (out / "videovollautomat_signet.svg").write_text(
        svg(512, 512, signet(4, 0), title="Videovollautomat Signet"))

    # 2) Horizontales Logo
    cap = 120
    H = 300
    sig_s = 0.52
    body, right = wordmark(330, 168, cap, INK, PINK)
    W = int(right + 60)
    content = signet(40, 14, sig_s) + "\n" + body
    (out / "videovollautomat_logo.svg").write_text(svg(W, H, content))
    (out / "videovollautomat_logo_hell.svg").write_text(svg(W, H, content, bg=PAPER))

    # 3) Negativ-Version auf Dunkel
    body_d, _ = wordmark(330, 168, cap, PAPER, PINK, video_ink=INK, shadow_ink=PAPER)
    # Signet auf Dunkel: Kontur bleibt schwarz, aber heller Schatten
    sig_d = signet(40, 14, sig_s).replace(
        f'<rect x="96" y="60" width="336" height="420" rx="30" fill="{INK}"/>',
        f'<rect x="96" y="60" width="336" height="420" rx="30" fill="{PAPER}"/>')
    (out / "videovollautomat_logo_dunkel.svg").write_text(
        svg(W, H, sig_d + "\n" + body_d, bg="#121212"))

    # 4) Gestapelte Version (Endcard 9:16, 1080×1920)
    cap2 = 150
    stack = []
    stack.append(signet(540 - 0.9 * 252, 560, 0.9))
    vx0, vx1 = ANTON.ink_bounds("VIDEO", cap2 * 1.0, 0.02)
    rx0, rx1 = ANTON.ink_bounds("VOLLAUTOMAT", cap2, 0.02)
    # VIDEO-Balken zentriert
    pad = cap2 * 0.16
    bw = (vx1 - vx0) + 2 * pad
    bh = cap2 + 2 * pad
    bx = 540 - bw / 2
    by = 1110
    off = cap2 * 0.07
    stack.append(f'<rect x="{bx+off:.1f}" y="{by+off:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="9" fill="{INK}"/>')
    stack.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="9" fill="{PINK}" stroke="{INK}" stroke-width="7"/>')
    d, _ = ANTON.text("VIDEO", bx + pad - vx0, by + pad + cap2, cap2, 0.02)
    stack.append(f'<path d="{d}" fill="{INK}"/>')
    d, _ = ANTON.text("VOLLAUTOMAT", 540 - (rx1 - rx0) / 2 - rx0, by + bh + off + 40 + cap2, cap2, 0.02)
    stack.append(f'<path d="{d}" fill="{INK}"/>')
    claim = "SCHNITT · MOTION · EXPORT"
    tcap = 30
    tx0, tx1 = MONO.ink_bounds(claim, tcap, 0.25)
    d, _ = MONO.text(claim, 540 - (tx1 - tx0) / 2 - tx0, by + bh + off + 40 + cap2 + 90, tcap, 0.25)
    stack.append(f'<path d="{d}" fill="{INK}"/>')
    (out / "videovollautomat_endcard_9x16.svg").write_text(
        svg(1080, 1920, "\n".join(stack), bg=PAPER, title="Videovollautomat Endcard"))


if __name__ == "__main__":
    build()
