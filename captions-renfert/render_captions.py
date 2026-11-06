#!/usr/bin/env python3
"""
Elegant animierte Captions (Great Vibes) als 1080x1920-Overlay mit Alphakanal.

Ausgabe: ProRes 4444 + Alpha oder QuickTime Animation (.mov) – direkt in Premiere
Pro über das Video legen.

  python3 render_captions.py                 # rendert captions_alpha_prores4444.mov
  python3 render_captions.py --codec animation   # QuickTime Animation (verlustfrei, RGBA)
  python3 render_captions.py --preview       # zusätzlich preview_dark.mp4 (mit Audio)
  python3 render_captions.py --stills 2.0 9.0 22.8   # einzelne Kontroll-PNGs

Timing kommt aus timing.json (Wortzeiten aus der Spracherkennung, an die
gemessenen Sprechpausen angeglichen).
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- Konfiguration
W, H, FPS = 1080, 1920, 30
DURATION = 24.0                 # s (Audio 22.44 s + Ausklang)
FONT_FILE = os.path.join(HERE, "fonts", "GreatVibes-Regular.ttf")
FONT_SIZE = 112
ROW_GAP = 1.02                  # Zeilenabstand in Vielfachen der Schriftgröße
MAX_ROW_W = 940                 # px, Satzspiegel (70 px Rand links/rechts)
BLOCK_CENTER_Y = 1390           # vertikale Mitte des Caption-Blocks
WORD_SPACE = 0.24               # Wortabstand in Vielfachen der Schriftgröße

# Farben (Champagner-Gold, warmes Weiß)
FILL_TOP = (255, 250, 240)
FILL_BOTTOM = (238, 211, 150)
GLOW = (255, 214, 140)
GLOW_ALPHA, GLOW_BLUR = 0.42, 16
SHADOW_ALPHA, SHADOW_BLUR, SHADOW_OFF = 0.55, 10, (0, 5)

# Animation
WORD_LEAD = 0.10                # Wort startet so viel vor dem gesprochenen Einsatz
WORD_IN = 0.60                  # Dauer des Einblendens
WORD_RISE = 22                  # px, Wort gleitet von unten nach oben
WORD_BLUR = 7.0                 # px Unschärfe zu Beginn
LINE_OUT = 0.34                 # Ausblenden einer Zeile
LINE_OUT_RISE = 16
LINE_OUT_BLUR = 6.0
FINAL_OUT = (23.0, 23.9)        # Ausblenden des Abschlussblocks
SHIMMER = (22.55, 23.45)        # Lichtschimmer über den Abschlussblock
PAD = 60                        # Rand um jedes Wort-Sprite (Glow/Schwünge)


def ease_out_cubic(x): return 1 - (1 - x) ** 3
def ease_out_expo(x): return 1 if x >= 1 else 1 - 2 ** (-10 * x)
def ease_in_out_sine(x): return -(math.cos(math.pi * x) - 1) / 2
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))


# ---------------------------------------------------------------- Sprites
class Word:
    def __init__(self, text, start, end, font):
        self.text, self.start, self.end = text, start, end
        self.adv = font.getlength(text)
        asc, desc = font.getmetrics()
        w = int(math.ceil(self.adv)) + 2 * PAD
        h = asc + desc + 2 * PAD
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).text((PAD, PAD), text, font=font, fill=255)
        self.mask = mask
        # Farbverlauf im Schriftzug
        grad = Image.new("RGB", (1, h))
        for y in range(h):
            t = clamp((y - PAD - asc * 0.25) / (asc + desc * 0.3))
            grad.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(FILL_TOP, FILL_BOTTOM)))
        grad = grad.resize((w, h))
        fill = Image.new("RGBA", (w, h)); fill.paste(grad, (0, 0)); fill.putalpha(mask)
        glow = Image.new("RGBA", (w, h), GLOW + (0,))
        glow.putalpha(mask.filter(ImageFilter.GaussianBlur(GLOW_BLUR)).point(lambda v: int(v * GLOW_ALPHA)))
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sm = Image.new("L", (w, h), 0); sm.paste(mask, SHADOW_OFF)
        shadow.putalpha(sm.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)).point(lambda v: int(v * SHADOW_ALPHA)))
        self.sprite = Image.alpha_composite(Image.alpha_composite(shadow, glow), fill)
        self.fill_only = fill
        self._blur_cache = {}
        self.x = self.y = 0  # Position (linke Grundlinie der Advance-Box) im Frame

    def blurred(self, r):
        r = round(r * 2) / 2
        if r <= 0:
            return self.sprite
        if r not in self._blur_cache:
            self._blur_cache[r] = self.sprite.filter(ImageFilter.GaussianBlur(r))
        return self._blur_cache[r]


def balanced_rows(words, space):
    """Zeilenumbruch, der die breiteste Reihe minimiert (max. 3 Reihen)."""
    n = len(words)
    width = lambda ws: sum(w.adv for w in ws) + space * (len(ws) - 1)
    if width(words) <= MAX_ROW_W:
        return [words]
    best = None
    for i in range(1, n):
        cand = [words[:i], words[i:]]
        mw = max(width(r) for r in cand)
        if mw <= MAX_ROW_W and (best is None or mw < best[0]):
            best = (mw, cand)
    if best:
        return best[1]
    for i in range(1, n - 1):
        for j in range(i + 1, n):
            cand = [words[:i], words[i:j], words[j:]]
            mw = max(width(r) for r in cand)
            if best is None or mw < best[0]:
                best = (mw, cand)
    return best[1]


def build_groups(timing, font):
    space = FONT_SIZE * WORD_SPACE
    row_h = FONT_SIZE * ROW_GAP
    groups = []
    for g in timing["groups"]:
        rows = []
        lines = []
        for line in g["lines"]:
            ws = [Word(w["w"], w["s"], w["e"], font) for w in line["words"]]
            lines.append(ws)
            rows += balanced_rows(ws, space)
        total_h = row_h * len(rows)
        top = BLOCK_CENTER_Y - total_h / 2
        asc, _ = font.getmetrics()
        for ri, row in enumerate(rows):
            rw = sum(w.adv for w in row) + space * (len(row) - 1)
            x = (W - rw) / 2
            # Grundlinie so, dass die x-Höhe mittig in der Reihe sitzt
            base = top + ri * row_h + row_h * 0.72
            for w in row:
                w.x, w.y = x, base - asc
                x += w.adv + space
        all_words = [w for l in lines for w in l]
        groups.append({"words": all_words, "rows": rows,
                       "start": all_words[0].start - WORD_LEAD})
    # Ausblendzeitpunkte: endet genau, wenn die nächste Gruppe beginnt
    for i, g in enumerate(groups):
        if i + 1 < len(groups):
            end = groups[i + 1]["start"]
            g["out"] = (end - LINE_OUT, end)
        else:
            g["out"] = FINAL_OUT
            g["shimmer"] = True
    return groups


def shimmer_overlay(word, t):
    """Weicher Lichtstreifen, der diagonal über den Schriftzug wandert."""
    p = clamp((t - SHIMMER[0]) / (SHIMMER[1] - SHIMMER[0]))
    if p <= 0 or p >= 1:
        return None
    band_x = -250 + ease_in_out_sine(p) * (W + 500)
    w, h = word.sprite.size
    band = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(band)
    gx = band_x - (word.x - PAD)
    for k in range(-60, 61, 4):
        a = int(255 * math.exp(-(k / 34) ** 2))
        d.line([(gx + k - h * 0.35, h), (gx + k + h * 0.35, 0)], fill=a, width=5)
    band = ImageChops.multiply(band, word.mask)
    over = Image.new("RGBA", (w, h), (255, 255, 250, 0))
    over.putalpha(band.point(lambda v: int(v * 0.85)))
    return over


def render_frame(groups, t):
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for g in groups:
        o0, o1 = g["out"]
        if t < g["start"] or t >= o1:
            continue
        po = ease_in_out_sine(clamp((t - o0) / (o1 - o0)))
        for w in g["words"]:
            pi = clamp((t - (w.start - WORD_LEAD)) / WORD_IN)
            if pi <= 0:
                continue
            a_in = ease_out_cubic(pi)
            dy = (1 - ease_out_expo(pi)) * WORD_RISE - po * LINE_OUT_RISE
            blur = (1 - ease_out_cubic(pi)) * WORD_BLUR + po * LINE_OUT_BLUR
            alpha = a_in * (1 - po)
            if alpha <= 0.002:
                continue
            spr = w.blurred(blur)
            if g.get("shimmer"):
                sh = shimmer_overlay(w, t)
                if sh is not None:
                    spr = Image.alpha_composite(spr, sh)
            if alpha < 0.999:
                spr = spr.copy()
                spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
            frame.alpha_composite(spr, (int(round(w.x - PAD)), int(round(w.y - PAD + dy))))
    return frame


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="zusätzlich Vorschau-MP4 auf dunklem Grund")
    ap.add_argument("--stills", nargs="*", type=float, help="nur Einzelbilder zu diesen Zeiten rendern")
    ap.add_argument("--codec", choices=["prores", "animation"], default="prores")
    ap.add_argument("--out", help="Zieldatei (.mov)")
    args = ap.parse_args()
    if not args.out:
        name = "captions_alpha_prores4444.mov" if args.codec == "prores" else "captions_alpha_animation.mov"
        args.out = os.path.join(HERE, name)

    timing = json.load(open(os.path.join(HERE, "timing.json"), encoding="utf-8"))
    font = ImageFont.truetype(FONT_FILE, FONT_SIZE)
    groups = build_groups(timing, font)

    if args.stills:
        os.makedirs(os.path.join(HERE, "stills"), exist_ok=True)
        for t in args.stills:
            f = render_frame(groups, t)
            bg = Image.new("RGBA", (W, H), (40, 46, 58, 255))
            Image.alpha_composite(bg, f).convert("RGB").save(os.path.join(HERE, "stills", f"still_{t:05.2f}s.png"))
        return

    tmp = tempfile.mkdtemp(prefix="caps_")
    n = int(round(DURATION * FPS))
    for i in range(n):
        render_frame(groups, i / FPS).save(os.path.join(tmp, f"f{i:05d}.png"), compress_level=1)
        if i % 60 == 0:
            print(f"frame {i}/{n}", file=sys.stderr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(tmp, "f%05d.png"),
                    *(["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                       "-alpha_bits", "16", "-vendor", "apl0"] if args.codec == "prores" else
                      ["-c:v", "qtrle", "-pix_fmt", "argb"]),
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                    args.out], check=True)
    if args.preview:
        audio = os.path.join(HERE, "audio", "voiceover.mp3")
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "lavfi", "-i", f"color=c=0x2a2f3a:s={W}x{H}:r={FPS}:d={DURATION}",
               "-framerate", str(FPS), "-i", os.path.join(tmp, "f%05d.png")]
        if os.path.exists(audio):
            cmd += ["-i", audio]
        cmd += ["-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]", "-map", "[v]"]
        if os.path.exists(audio):
            cmd += ["-map", "2:a", "-c:a", "aac", "-b:a", "160k"]
        cmd += ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-t", str(DURATION),
                "-movflags", "+faststart", os.path.join(HERE, "preview_dark.mp4")]
        subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
