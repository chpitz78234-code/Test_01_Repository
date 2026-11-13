#!/usr/bin/env python3
"""Renfert recruiting outro "KOMM INS TEAM" – 1080x1920, 60 fps, 5 s, MP4.

    python3 tools/render_outro.py                 # export/Renfert_Outro_KOMM_INS_TEAM_9x16.mp4
    python3 tools/render_outro.py --still 1.0     # single frame at t = 1.0 s
    python3 tools/render_outro.py --duration 8    # longer hold at the end

Timeline
  0.00–0.45  three diagonal bands whip across the frame, the red wins
  0.40–0.70  KOMM slams in from the left (skew + motion blur)
  0.62–0.85  INS smashes in from 3x scale
  0.82–1.25  white box wipes in, TEAM rises inside it (red text)
  1.10–1.35  "///" accent pops
  1.35–1.95  logo: swooshes draw from the centre outwards, wordmark rises
  2.00–end   hold: everything floats/breathes, background stripes drift
"""
import argparse
import math
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
WHITE = (255, 255, 255)


# ---------------------------------------------------------------- easing ----
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


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


def shake(t, hits, amp=16, freq=38, decay=14):
    dx = dy = 0.0
    for i, h in enumerate(hits):
        d = t - h
        if d >= 0:
            e = amp * math.exp(-decay * d)
            dx += e * math.sin(freq * d + i * 1.7)
            dy += e * math.cos(freq * 1.13 * d + i)
    return dx, dy


# ---------------------------------------------------------------- assets ----
def load_logo(target_w):
    """White logo parts (top swoosh, wordmark, bottom swoosh) as clean alpha
    masks, rebuilt from the small source PNG by 4x upscale + edge sharpening."""
    src = np.asarray(Image.open(ROOT / "assets" / "renfert_logo_source.png").convert("RGB")).astype(np.float32)
    white = np.clip((src.min(axis=2) - 60) / (235 - 60), 0, 1)
    m = Image.fromarray((white * 255).astype(np.uint8))
    m = m.crop((55, 85, 512, 265))                      # logo bbox + margin
    k = 4
    m = m.resize((m.width * k, m.height * k), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.2))
    a = np.asarray(m).astype(np.float32) / 255
    a = np.clip((a - 0.5) / 0.16 + 0.5, 0, 1)            # crisp, still anti-aliased
    a = a * a * (3 - 2 * a)
    full = Image.fromarray((a * 255).astype(np.uint8))
    scale = target_w / full.width
    full = full.resize((target_w, int(full.height * scale)), Image.LANCZOS)
    # split into the three bands (source rows 90-125 / 141-199 / 224-259)
    def band(y0, y1):
        y0 = int((y0 - 85) * k * scale)
        y1 = int((y1 - 85 + 1) * k * scale)
        part = Image.new("L", full.size, 0)
        part.paste(full.crop((0, y0, full.width, y1)), (0, y0))
        return part
    return {"top": band(84, 133), "word": band(134, 211), "bottom": band(212, 264)}, full.size


def text_sprite(text, font, color, pad=40):
    l, t, r, b = font.getbbox(text)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=color + (255,))
    return im, pad


def place(canvas, spr, cx, cy, sx=1.0, sy=1.0, skew=0.0, alpha=1.0):
    """Composite sprite centred on (cx, cy) with scale and horizontal skew."""
    if alpha <= 0.003 or sx <= 0.001 or sy <= 0.001:
        return
    w, h = spr.size
    # forward: X = sx*u + skew*sy*v,  Y = sy*v   (u, v, X, Y relative to centres)
    ow = int(w * sx + abs(skew) * h * sy) + 4
    oh = int(h * sy) + 4
    a, b = 1 / sx, -skew / sx
    c = w / 2 - ow / (2 * sx) + skew * oh / (2 * sx)
    d, e, f = 0, 1 / sy, h / 2 - oh / (2 * sy)
    im = spr.transform((ow, oh), Image.AFFINE, (a, b, c, d, e, f), resample=Image.BICUBIC)
    if alpha < 0.999:
        im.putalpha(im.getchannel("A").point([int(v * alpha) for v in range(256)]))
    canvas.alpha_composite(im, (int(round(cx - ow / 2)), int(round(cy - oh / 2))))


def band_poly(front, width, angle_deg=-18, extent=4000):
    """Half-plane strip along a diagonal: points with  front-width < u < front,
    u = projection on the sweep direction."""
    a = math.radians(angle_deg)
    nx, ny = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)   # sweep direction
    tx, ty = math.cos(a), math.sin(a)                               # band direction
    cx, cy = W / 2, H / 2

    def pt(u, v):
        return (cx + nx * u + tx * v, cy + ny * u + ty * v)
    u0, u1 = front - width, front
    return [pt(u0, -extent), pt(u1, -extent), pt(u1, extent), pt(u0, extent)]


# ---------------------------------------------------------------- scene -----
class Outro:
    def __init__(self, duration):
        self.duration = duration
        black = ImageFont.truetype(str(FONT_DIR / "NettoPro-Black.otf"), 280)
        self.komm, _ = text_sprite("KOMM", black, WHITE)
        self.ins, _ = text_sprite("INS", black, WHITE)
        self.team, _ = text_sprite("TEAM", black, RED)
        self.team_w = black.getlength("TEAM")
        self.cap = black.getbbox("TEAM")[3] - black.getbbox("TEAM")[1]
        slash = ImageFont.truetype(str(FONT_DIR / "NettoPro-BlackItalic.otf"), 120)
        self.slash = [text_sprite("/", slash, WHITE, pad=20)[0] for _ in range(3)]
        self.logo, self.logo_size = load_logo(680)

    # -------------------------------------------------------------------
    def background(self, t):
        im = Image.new("RGBA", (W, H), WHITE + (255,))
        d = ImageDraw.Draw(im)
        diag = math.hypot(W, H)
        # intro sweep: dark, light, main red; the main red ends up covering all
        for i, col in enumerate([RED_DARK, RED_LIGHT, RED]):
            p = expo_inout(seg(t, -0.10 + i * 0.07, 0.40 + i * 0.05))
            front = -diag / 2 - 200 + p * (diag + 600)
            width = 4000
            d.polygon(band_poly(front, width), fill=col + (255,))
        # drifting stripes (appear after the sweep)
        k = expo_out(seg(t, 0.35, 1.0))
        if k > 0:
            drift = 22 * t
            for j, (off, wdt, col, al) in enumerate([(-520, 150, RED_DARK, 0.35),
                                                     (-330, 46, RED_LIGHT, 0.30),
                                                     (420, 210, RED_DARK, 0.28),
                                                     (650, 34, RED_LIGHT, 0.25)]):
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                fr = off + drift * (1 if j % 2 else 0.6) + (1 - k) * 900
                ImageDraw.Draw(layer).polygon(band_poly(fr, wdt), fill=col + (int(255 * al * k),))
                im.alpha_composite(layer)
        return im

    # -------------------------------------------------------------------
    def draw(self, t):
        im = self.background(t)
        fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hold = max(0.0, t - 1.9)
        float_y = 7 * math.sin(2 * math.pi * hold / 2.6) * min(1, hold * 2)
        cx = W / 2
        y_komm, y_ins, y_team = 560, 790, 1030

        # KOMM: from the left, skewed, back-out landing
        p = seg(t, 0.40, 0.68)
        if p > 0:
            e = back_out(p, 1.2)
            x = lerp(-900, cx, e)
            skew = lerp(0.55, 0.0, expo_out(p))
            sx = lerp(1.35, 1.0, expo_out(p))
            place(fg, self.komm, x, y_komm + float_y, sx=sx, sy=1.0, skew=skew)

        # INS: smash from big scale
        p = seg(t, 0.62, 0.84)
        if p > 0:
            e = expo_out(p)
            s = lerp(3.2, 1.0, e)
            place(fg, self.ins, cx, y_ins + float_y * 0.8, sx=s, sy=s, alpha=clamp(p * 3))

        # TEAM: white box wipes in from the right, red text rises inside
        p = seg(t, 0.82, 1.04)
        if p > 0:
            e = expo_out(p)
            breathe = 1 + 0.012 * math.sin(2 * math.pi * hold / 2.6 + 1.2) * min(1, hold * 2)
            bw = (self.team_w + 90) * breathe
            bh = (self.cap + 70) * breathe
            yb = y_team + float_y * 0.6
            x1 = cx + bw / 2
            x0 = lerp(x1, cx - bw / 2, e)
            box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(box).rectangle((x0, yb - bh / 2, x1, yb + bh / 2), fill=WHITE + (255,))
            q = seg(t, 0.95, 1.22)
            if q > 0:
                eq = expo_out(q)
                txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                place(txt, self.team, cx, yb + (1 - eq) * bh * 0.9, sx=breathe, sy=breathe)
                # mask text to the box
                mask = Image.new("L", (W, H), 0)
                ImageDraw.Draw(mask).rectangle((x0, yb - bh / 2, x1, yb + bh / 2), fill=255)
                ta = np.minimum(np.asarray(txt.getchannel("A")), np.asarray(mask))
                txt.putalpha(Image.fromarray(ta))
                box.alpha_composite(txt)
            fg.alpha_composite(box)

            # "///" accent, top right of the box
            for i, spr in enumerate(self.slash):
                ps = seg(t, 1.10 + i * 0.06, 1.32 + i * 0.06)
                if ps > 0:
                    es = back_out(ps, 2.2)
                    wig = 4 * math.sin(2 * math.pi * (hold / 1.3) + i) * min(1, hold * 2)
                    place(fg, spr, cx + bw / 2 - 40 + i * 52, yb - bh / 2 - 70 + wig,
                          sx=es, sy=es, alpha=clamp(ps * 4))

        # logo
        lw, lh = self.logo_size
        ly = 1430 - float_y * 0.5
        lx = cx - lw / 2
        for name, t0, t1 in (("top", 1.35, 1.80), ("bottom", 1.45, 1.90)):
            p = expo_out(seg(t, t0, t1))
            if p > 0:
                m = self.logo[name]
                half = lw / 2 * p
                rev = Image.new("L", m.size, 0)
                ImageDraw.Draw(rev).rectangle((lw / 2 - half, 0, lw / 2 + half, lh), fill=255)
                a = Image.fromarray(np.minimum(np.asarray(m), np.asarray(rev)))
                layer = Image.new("RGBA", m.size, WHITE + (0,))
                layer.putalpha(a)
                fg.alpha_composite(layer, (int(lx), int(ly - lh / 2)))
        p = seg(t, 1.50, 1.95)
        if p > 0:
            e = expo_out(p)
            m = self.logo["word"]
            layer = Image.new("RGBA", m.size, WHITE + (0,))
            layer.putalpha(m.point([int(v * clamp(p * 2.5)) for v in range(256)]))
            s = lerp(0.86, 1.0, e)
            place(fg, layer, cx, ly + (1 - e) * 50, sx=s, sy=s)

        # soft shadow under all foreground elements for depth
        sh = fg.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point([int(v * 0.28) for v in range(256)])
        shadow = Image.new("RGBA", (W, H), (60, 0, 10, 0))
        shadow.putalpha(sh)
        im.alpha_composite(shadow, (0, 10))
        im.alpha_composite(fg)

        # camera: impact shake + slow push-in during the hold
        dx, dy = shake(t, [0.62, 0.80, 1.02], amp=18)
        zoom = 1 + 0.025 * expo_out(seg(t, 1.9, self.duration)) * 1.0
        if abs(dx) > 0.2 or abs(dy) > 0.2 or zoom > 1.0005:
            im = im.transform((W, H), Image.AFFINE,
                              (1 / zoom, 0, W / 2 - W / 2 / zoom - dx, 0, 1 / zoom, H / 2 - H / 2 / zoom - dy),
                              resample=Image.BICUBIC, fillcolor=RED + (255,))
        return im

    def frame(self, n):
        t = n / FPS
        fast = 0.0 <= t <= 2.0
        samples = 5 if fast else 1                      # motion blur in the action part
        if samples == 1:
            return np.asarray(self.draw(t).convert("RGB"))
        acc = np.zeros((H, W, 3), np.float32)
        for k in range(samples):
            acc += np.asarray(self.draw(t + (k / samples - 0.5) * 0.6 / FPS).convert("RGB"), np.float32)
        return (acc / samples + 0.5).astype(np.uint8)


def lerp(a, b, t):
    return a + (b - a) * t


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
