#!/usr/bin/env python3
"""Renfert recruiting outro "KOMM INS TEAM" – 1080x1920, 60 fps, 5 s, MP4.

    python3 tools/render_outro.py                 # export/Renfert_Outro_KOMM_INS_TEAM_9x16.mp4
    python3 tools/render_outro.py --still 1.0     # single frame at t = 1.0 s
    python3 tools/render_outro.py --duration 8    # longer hold at the end

Timeline
  0.00–0.45  three diagonal bands whip across the frame, the red wins
  0.40–0.70  KOMM slams in from the left (skew + motion blur)   -> burst
  0.62–0.85  INS smashes in from 3x scale                        -> burst
  0.82–1.25  tilted white box wipes in, TEAM rises inside it     -> burst
  1.10–1.35  "///" accent pops
  1.30–2.05  logo (always inside its red box, drop shadow) pops in with a
             wobble, swooshes draw out, wordmark rises            -> burst
  bursts     little stars, confetti curls, dots and strips fly off and vanish
  2.0–end    hold: everything floats/breathes, background stripes drift
"""
import argparse
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT.parent / "captions-leon" / "fonts"
W, H, FPS = 1080, 1920, 60

RED = (200, 16, 46)          # #C8102E
RED_DARK = (150, 10, 33)
RED_LIGHT = (232, 72, 96)
PINK = (255, 190, 202)
WHITE = (255, 255, 255)


# ---------------------------------------------------------------- easing ----
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))


def expo_out(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def expo_inout(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 2 ** (20 * x - 10) / 2 if x < 0.5 else (2 - 2 ** (-20 * x + 10)) / 2


def back_out(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def elastic_out(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1


def shake(t, hits, amp=16, freq=38, decay=14):
    dx = dy = 0.0
    for i, h in enumerate(hits):
        d = t - h
        if d >= 0:
            e = amp * math.exp(-decay * d)
            dx += e * math.sin(freq * d + i * 1.7)
            dy += e * math.cos(freq * 1.13 * d + i)
    return dx, dy


# ------------------------------------------------------------- drawing ------
def place(canvas, spr, cx, cy, sx=1.0, sy=1.0, skew=0.0, rot=0.0, alpha=1.0):
    """Composite sprite centred on (cx, cy): scale, horizontal skew, rotation (deg)."""
    if alpha <= 0.003 or abs(sx) <= 0.003 or abs(sy) <= 0.003:
        return
    w, h = spr.size
    r = math.radians(rot)
    R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    A = R @ np.array([[sx, skew * sy], [0, sy]])
    corners = A @ np.array([[-w / 2, w / 2, w / 2, -w / 2], [-h / 2, -h / 2, h / 2, h / 2]])
    ow = int(math.ceil(corners[0].max() - corners[0].min())) + 4
    oh = int(math.ceil(corners[1].max() - corners[1].min())) + 4
    Ai = np.linalg.inv(A)
    a, b = Ai[0]
    d, e = Ai[1]
    c = w / 2 - a * ow / 2 - b * oh / 2
    f = h / 2 - d * ow / 2 - e * oh / 2
    im = spr.transform((ow, oh), Image.AFFINE, (a, b, c, d, e, f), resample=Image.BICUBIC)
    if alpha < 0.999:
        im.putalpha(im.getchannel("A").point([int(v * alpha) for v in range(256)]))
    canvas.alpha_composite(im, (int(round(cx - ow / 2)), int(round(cy - oh / 2))))


def text_sprite(text, font, color, pad=40):
    l, t, r, b = font.getbbox(text)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=color + (255,))
    return im


def with_shadow(spr, blur=16, offset=(0, 14), alpha=0.5, color=(40, 0, 8)):
    """Sprite + soft drop shadow baked in (canvas grows to fit)."""
    pad = blur * 3 + max(abs(offset[0]), abs(offset[1]))
    out = Image.new("RGBA", (spr.width + 2 * pad, spr.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    sh.paste(spr.getchannel("A"), (pad + offset[0], pad + offset[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).point([int(v * alpha) for v in range(256)])
    shadow = Image.new("RGBA", out.size, color + (0,))
    shadow.putalpha(sh)
    out.alpha_composite(shadow)
    return out


def band_poly(front, width, angle_deg=-18, extent=4000):
    a = math.radians(angle_deg)
    nx, ny = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
    tx, ty = math.cos(a), math.sin(a)

    def pt(u, v):
        return (W / 2 + nx * u + tx * v, H / 2 + ny * u + ty * v)
    u0, u1 = front - width, front
    return [pt(u0, -extent), pt(u1, -extent), pt(u1, extent), pt(u0, extent)]


# ----------------------------------------------------------------- logo -----
def logo_parts(box_w):
    """The Renfert logo as layers that always sit inside their red box:
    box (red rectangle) + white top swoosh / wordmark / bottom swoosh."""
    src = np.asarray(Image.open(ROOT / "assets" / "renfert_logo_source.png").convert("RGB")).astype(np.float32)
    sh, sw = src.shape[:2]
    white = np.clip((src.min(axis=2) - 60) / (235 - 60), 0, 1)
    k = 4
    m = Image.fromarray((white * 255).astype(np.uint8))
    m = m.resize((sw * k, sh * k), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.2))
    a = np.asarray(m).astype(np.float32) / 255
    a = np.clip((a - 0.5) / 0.16 + 0.5, 0, 1)
    a = a * a * (3 - 2 * a)
    full = Image.fromarray((a * 255).astype(np.uint8))
    scale = box_w / sw
    bw, bh = box_w, int(round(sh * scale))
    full = full.resize((bw, bh), Image.LANCZOS)

    def band(y0, y1):
        y0, y1 = int(y0 * scale), int(y1 * scale)
        part = Image.new("L", (bw, bh), 0)
        part.paste(full.crop((0, y0, bw, y1)), (0, y0))
        return part
    box = Image.new("RGBA", (bw, bh), RED + (255,))
    return {"box": box, "top": band(84, 133), "word": band(134, 211), "bottom": band(212, 264)}


# ------------------------------------------------------------ particles -----
def star_shape(size, points=5, inner=0.45, k=4):
    s = size * k
    im = Image.new("L", (s, s), 0)
    pts = []
    for i in range(points * 2):
        r = s / 2 * (1 if i % 2 == 0 else inner)
        ang = -math.pi / 2 + i * math.pi / points
        pts.append((s / 2 + r * math.cos(ang), s / 2 + r * math.sin(ang)))
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return im.resize((size, size), Image.LANCZOS)


def _stroke(pts, wd, k):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = wd * 2
    im = Image.new("L", (int(max(xs) - min(xs) + 2 * pad), int(max(ys) - min(ys) + 2 * pad)), 0)
    pts = [(x - min(xs) + pad, y - min(ys) + pad) for x, y in pts]
    d = ImageDraw.Draw(im)
    d.line(pts, fill=255, width=int(wd), joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse((p[0] - wd / 2, p[1] - wd / 2, p[0] + wd / 2, p[1] + wd / 2), fill=255)
    return im.resize((max(1, im.width // k), max(1, im.height // k)), Image.LANCZOS)


def curl_shape(length, width, loops=2.2, k=4):
    """Confetti curl: a looping ribbon (trochoid)."""
    L = length * k
    r = L / (loops * 2 * math.pi) * 1.6
    pts = []
    for i in range(161):
        tt = i / 160 * loops * 2 * math.pi
        pts.append((tt * L / (loops * 2 * math.pi) - r * math.sin(tt), -r * math.cos(tt)))
    return _stroke(pts, width * k, k)


def wave_shape(length, width, k=4):
    L = length * k
    pts = [(i / 40 * L, math.sin(i / 40 * 3 * math.pi) * L * 0.12) for i in range(41)]
    return _stroke(pts, width * k, k)


def dot_shape(size, ring=False, k=4):
    s = size * k
    im = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(im)
    if ring:
        d.ellipse((0, 0, s - 1, s - 1), outline=255, width=max(2, int(s * 0.22)))
    else:
        d.ellipse((0, 0, s - 1, s - 1), fill=255)
    return im.resize((size, size), Image.LANCZOS)


def colorize(mask, color):
    im = Image.new("RGBA", mask.size, color + (0,))
    im.putalpha(mask)
    return im


class Particle:
    pass


class Bursts:
    """Deterministic particle bursts: stars, curls, waves, dots, rings."""

    def __init__(self, seed=7):
        rnd = random.Random(seed)
        self.rnd = rnd
        self.shapes = []
        for col in [WHITE, WHITE, WHITE, PINK, RED_DARK]:
            self.shapes += [("star", colorize(star_shape(rnd.randint(46, 74)), col)),
                            ("star4", colorize(star_shape(rnd.randint(44, 66), points=4, inner=0.32), col)),
                            ("curl", colorize(curl_shape(rnd.randint(100, 150), 12), col)),
                            ("wave", colorize(wave_shape(rnd.randint(90, 130), 12), col)),
                            ("dot", colorize(dot_shape(rnd.randint(16, 26)), col)),
                            ("ring", colorize(dot_shape(rnd.randint(34, 48), ring=True), col))]
        self.parts = []

    def emit(self, t0, rect, n, speed=(520, 1250)):
        rnd = self.rnd
        x0, y0, x1, y1 = rect
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for _ in range(n):
            p = Particle()
            p.kind, p.spr = rnd.choice(self.shapes)
            side = rnd.random()
            if side < 0.5:
                sx_, sy_ = rnd.uniform(x0, x1), (y0 if side < 0.25 else y1)
            else:
                sx_, sy_ = (x0 if side < 0.75 else x1), rnd.uniform(y0, y1)
            ang = math.atan2(sy_ - cy, (sx_ - cx) * 0.6) + rnd.uniform(-0.5, 0.5)
            sp = rnd.uniform(*speed)
            p.x, p.y = sx_, sy_
            p.vx, p.vy = math.cos(ang) * sp, math.sin(ang) * sp - rnd.uniform(0, 250)
            p.t0 = t0 + rnd.uniform(0, 0.06)
            p.life = rnd.uniform(0.65, 1.15)
            p.rot0 = rnd.uniform(0, 360)
            p.vrot = rnd.uniform(-540, 540)
            p.size = rnd.uniform(0.75, 1.2)
            p.grav = 900 if p.kind in ("curl", "wave", "dot") else 350
            p.drag = rnd.uniform(3.2, 4.5)
            self.parts.append(p)

    def draw(self, canvas, t):
        for p in self.parts:
            d = t - p.t0
            if d < 0 or d > p.life:
                continue
            fall = (1 - math.exp(-p.drag * d)) / p.drag
            x = p.x + p.vx * fall
            y = p.y + p.vy * fall + 0.5 * p.grav * d * d
            u = d / p.life
            s = p.size * expo_out(clamp(d / 0.09)) * (1 - clamp((u - 0.6) / 0.4) ** 2)
            if p.kind in ("star", "star4"):          # little twinkle while flying
                s *= 0.85 + 0.15 * math.sin(d * 40 + p.rot0)
            place(canvas, p.spr, x, y, sx=s, sy=s, rot=p.rot0 + p.vrot * d)


# ---------------------------------------------------------------- scene -----
class Outro:
    Y_KOMM, Y_INS, Y_TEAM = 540, 770, 1010
    TEAM_TILT = -4.0
    LOGO_W, LOGO_Y = 560, 1450

    def __init__(self, duration):
        self.duration = duration
        black = ImageFont.truetype(str(FONT_DIR / "NettoPro-Black.otf"), 280)
        self.komm = text_sprite("KOMM", black, WHITE)
        self.ins = text_sprite("INS", black, WHITE)
        self.team = text_sprite("TEAM", black, RED)
        self.komm_w, self.ins_w = black.getlength("KOMM"), black.getlength("INS")
        self.team_w = black.getlength("TEAM")
        self.cap = black.getbbox("TEAM")[3] - black.getbbox("TEAM")[1]
        slash = ImageFont.truetype(str(FONT_DIR / "NettoPro-BlackItalic.otf"), 120)
        self.slash = text_sprite("/", slash, WHITE, pad=20)
        self.logo = logo_parts(self.LOGO_W)
        lw, lh = self.logo["box"].size
        # drop shadow behind the logo box (the box is part of the logo – never removed)
        self.logo_shadow = with_shadow(Image.new("RGBA", (lw, lh), (0, 0, 0, 255)),
                                       blur=22, offset=(0, 20), alpha=0.6)
        self.logo_shadow_pad = (self.logo_shadow.width - lw) // 2
        self.bursts = Bursts()
        cx, b = W / 2, self.bursts
        b.emit(0.60, (cx - self.komm_w / 2, self.Y_KOMM - 95, cx + self.komm_w / 2, self.Y_KOMM + 95), 24)
        b.emit(0.78, (cx - self.ins_w / 2, self.Y_INS - 95, cx + self.ins_w / 2, self.Y_INS + 95), 22)
        bw, bh = self.team_w + 90, self.cap + 70
        b.emit(1.00, (cx - bw / 2, self.Y_TEAM - bh / 2, cx + bw / 2, self.Y_TEAM + bh / 2), 30)
        b.emit(1.52, (cx - lw / 2, self.LOGO_Y - lh / 2, cx + lw / 2, self.LOGO_Y + lh / 2), 36,
               speed=(600, 1400))

    # -------------------------------------------------------------------
    def background(self, t):
        im = Image.new("RGBA", (W, H), WHITE + (255,))
        d = ImageDraw.Draw(im)
        diag = math.hypot(W, H)
        for i, col in enumerate([RED_DARK, RED_LIGHT, RED]):
            p = expo_inout(seg(t, -0.10 + i * 0.07, 0.40 + i * 0.05))
            d.polygon(band_poly(-diag / 2 - 200 + p * (diag + 600), 4000), fill=col + (255,))
        k = expo_out(seg(t, 0.35, 1.0))
        if k > 0:
            drift = 22 * t
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            for j, (off, wdt, col, al) in enumerate([(-520, 150, RED_DARK, 0.35),
                                                     (-330, 46, RED_LIGHT, 0.30),
                                                     (420, 210, RED_DARK, 0.28),
                                                     (650, 34, RED_LIGHT, 0.25)]):
                fr = off + drift * (1 if j % 2 else 0.6) + (1 - k) * 900
                ld.polygon(band_poly(fr, wdt), fill=col + (int(255 * al * k),))
            im.alpha_composite(layer)
        return im

    # -------------------------------------------------------------------
    def draw(self, t):
        im = self.background(t)
        fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hold = max(0.0, t - 1.9)
        ramp = min(1.0, hold * 2)
        float_y = 7 * math.sin(2 * math.pi * hold / 2.6) * ramp
        cx = W / 2

        # KOMM
        p = seg(t, 0.40, 0.68)
        if p > 0:
            place(fg, self.komm, lerp(-900, cx, back_out(p, 1.2)), self.Y_KOMM + float_y,
                  sx=lerp(1.35, 1.0, expo_out(p)), skew=lerp(0.55, 0.0, expo_out(p)),
                  rot=1.2 * math.sin(2 * math.pi * hold / 3.1) * ramp)

        # INS
        p = seg(t, 0.62, 0.84)
        if p > 0:
            s = lerp(3.2, 1.0, expo_out(p))
            place(fg, self.ins, cx, self.Y_INS + float_y * 0.8, sx=s, sy=s, alpha=clamp(p * 3),
                  rot=lerp(-14, 0, expo_out(p)) - 1.0 * math.sin(2 * math.pi * hold / 2.9) * ramp)

        # TEAM: tilted white card wipes in from the right; red text rises inside
        p = seg(t, 0.82, 1.04)
        if p > 0:
            e = expo_out(p)
            breathe = 1 + 0.015 * math.sin(2 * math.pi * hold / 2.6 + 1.2) * ramp
            bw, bh = self.team_w + 90, self.cap + 70
            card = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
            ImageDraw.Draw(card).rectangle(((1 - e) * bw, 0, bw, bh), fill=WHITE + (255,))
            q = seg(t, 0.95, 1.22)
            if q > 0:
                txt = Image.new("RGBA", card.size, (0, 0, 0, 0))
                place(txt, self.team, bw / 2, bh / 2 + (1 - expo_out(q)) * bh * 0.95)
                ta = np.minimum(np.asarray(txt.getchannel("A")), np.asarray(card.getchannel("A")))
                txt.putalpha(Image.fromarray(ta))
                card.alpha_composite(txt)
            tilt = self.TEAM_TILT * elastic_out(seg(t, 0.82, 1.5))
            place(fg, card, cx, self.Y_TEAM + float_y * 0.6, sx=breathe, sy=breathe, rot=tilt)

            for i in range(3):                               # "///"
                ps = seg(t, 1.10 + i * 0.06, 1.32 + i * 0.06)
                if ps > 0:
                    es = back_out(ps, 2.2)
                    wig = 4 * math.sin(2 * math.pi * (hold / 1.3) + i) * ramp
                    place(fg, self.slash, cx + bw / 2 - 30 + i * 50, self.Y_TEAM - bh / 2 - 80 + wig,
                          sx=es, sy=es, alpha=clamp(ps * 4))

        # soft shadow under the type
        sh = fg.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point([int(v * 0.30) for v in range(256)])
        shadow = Image.new("RGBA", (W, H), (60, 0, 10, 0))
        shadow.putalpha(sh)
        im.alpha_composite(shadow, (0, 10))
        im.alpha_composite(fg)

        # stars & confetti (below the logo, so the logo is never covered)
        self.bursts.draw(im, t)

        # logo: the red box is always there behind the white parts; drop shadow; playful pop
        p = seg(t, 1.30, 1.75)
        if p > 0:
            lg = self.logo
            lw, lh = lg["box"].size
            card = lg["box"].copy()
            for name, t0, t1 in (("top", 1.45, 1.85), ("bottom", 1.52, 1.92)):
                q = expo_out(seg(t, t0, t1))
                if q > 0:
                    half = lw / 2 * q
                    rev = Image.new("L", (lw, lh), 0)
                    ImageDraw.Draw(rev).rectangle((lw / 2 - half, 0, lw / 2 + half, lh), fill=255)
                    card.alpha_composite(colorize(Image.fromarray(np.minimum(np.asarray(lg[name]), np.asarray(rev))), WHITE))
            q = seg(t, 1.55, 1.98)
            if q > 0:
                eq = expo_out(q)
                word = colorize(lg["word"].point([int(v * clamp(q * 2.5)) for v in range(256)]), WHITE)
                wl = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
                place(wl, word, lw / 2, lh / 2 + (1 - eq) * 40, sx=lerp(0.85, 1, eq), sy=lerp(0.85, 1, eq))
                card.alpha_composite(wl)
            pad = self.logo_shadow_pad
            full = self.logo_shadow.copy()
            full.alpha_composite(card, (pad, pad))
            s = back_out(p, 2.4) * (1 + 0.01 * math.sin(2 * math.pi * hold / 2.6 + 2.4) * ramp)
            rot = lerp(-10, 0, elastic_out(seg(t, 1.30, 2.1))) + 0.8 * math.sin(2 * math.pi * hold / 3.4) * ramp
            place(im, full, cx, self.LOGO_Y - float_y * 0.5, sx=s, sy=s, rot=rot)

        # camera: impact shake + slow push-in during the hold
        dx, dy = shake(t, [0.62, 0.80, 1.02, 1.55], amp=16)
        zoom = 1 + 0.025 * expo_out(seg(t, 1.9, self.duration))
        if abs(dx) > 0.2 or abs(dy) > 0.2 or zoom > 1.0005:
            im = im.transform((W, H), Image.AFFINE,
                              (1 / zoom, 0, W / 2 - W / 2 / zoom - dx, 0, 1 / zoom, H / 2 - H / 2 / zoom - dy),
                              resample=Image.BICUBIC, fillcolor=RED + (255,))
        return im

    def frame(self, n):
        t = n / FPS
        samples = 5 if 0.0 <= t <= 2.9 else 1          # motion blur while things fly
        if samples == 1:
            return np.asarray(self.draw(t).convert("RGB"))
        acc = np.zeros((H, W, 3), np.float32)
        for k in range(samples):
            acc += np.asarray(self.draw(t + (k / samples - 0.5) * 0.6 / FPS).convert("RGB"), np.float32)
        return (acc / samples + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=5.0)
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--out", default=str(ROOT / "export"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    o = Outro(args.duration)

    if args.still is not None:
        for t in args.still:
            p = out / f"outro_t{t:05.2f}.png"
            Image.fromarray(o.frame(int(round(t * FPS)))).save(p)
            print(p)
        return

    n = int(round(args.duration * FPS))
    dst = out / "Renfert_Outro_KOMM_INS_TEAM_9x16.mp4"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-profile:v", "high",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-movflags", "+faststart", str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(o.frame(i).tobytes())
        if i % 60 == 0:
            print(f"frame {i}/{n}", file=sys.stderr)
    proc.stdin.close()
    proc.wait()
    print(dst)


if __name__ == "__main__":
    main()
