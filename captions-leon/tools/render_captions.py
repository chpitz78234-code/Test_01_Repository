#!/usr/bin/env python3
"""Render dynamic captions (Renfert look) with an alpha channel.

    python3 tools/render_captions.py                       # 9:16, all exports
    python3 tools/render_captions.py --format 16x9
    python3 tools/render_captions.py --still 600 still.png # single frame check
    python3 tools/render_captions.py --font-bold fonts/NettoPro-Bold.otf \
                                     --font-regular fonts/NettoPro-Regular.otf

Fonts: every NettoPro*.otf/.ttf placed in ../fonts is picked up automatically
(Bold for Leon, Regular/Book for the interviewer).  If none is found, Inter is
used as a stand-in and a warning is printed.

Look
  Leon (answers)      white Bold text, soft shadow, a Renfert-red box that
                      jumps from word to word as it is spoken.
  Interviewer         smaller Regular text, dark on a white bar with a red
                      edge; the bar grows with every new word.
  All words pop in (fade + rise + slight scale, expo-out); pages fade out.
"""
import argparse
import glob
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- style -----
STYLE = {
    "red": (226, 0, 26),          # Renfert red (adjust to the exact CI value)
    "white": (255, 255, 255),
    "dark": (29, 29, 27),
    "shadow_alpha": 0.55,
    "shadow_blur": 7,
    "shadow_offset": (0, 4),
    "in_frames": 10,              # word pop-in
    "hl_frames": 7,               # red box travel time
    "out_frames": 7,              # page fade-out
    "rise_px": 26,
    "scale_from": 0.90,
}

FORMATS = {
    "9x16": {"w": 1080, "h": 1920, "size_a": 72, "size_q": 54, "max_w": 940, "bottom": 1500},
    "16x9": {"w": 1920, "h": 1080, "size_a": 64, "size_q": 48, "max_w": 1200, "bottom": 975},
    "1x1":  {"w": 1080, "h": 1080, "size_a": 66, "size_q": 48, "max_w": 900, "bottom": 960},
}


# ---------------------------------------------------------------- utils -----
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def expo_out(t):
    return 1.0 if t >= 1 else 1 - math.pow(2, -10 * t)


def cubic_inout(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2


def lerp(a, b, t):
    return a + (b - a) * t


def find_fonts(bold, regular):
    fdir = ROOT / "fonts"
    cand = sorted(glob.glob(str(fdir / "*Netto*.[ot]tf")) + glob.glob(str(fdir / "*netto*.[ot]tf")))

    def pick(keys, avoid=("Italic", "Ita", "Light", "Thin")):
        for k in keys:
            for c in cand:
                n = os.path.basename(c)
                if k.lower() in n.lower() and not any(a.lower() in n.lower() for a in avoid):
                    return c
        return None

    bold = bold or pick(["Bold"], avoid=("Italic", "Ita", "Semi", "Extra"))
    regular = regular or pick(["Regular", "Book", "Medium", "Rg"]) or (cand[0] if cand else None)
    stand_in = False
    if not bold:
        bold, stand_in = "/usr/share/fonts/opentype/inter/Inter-Bold.otf", True
    if not regular:
        regular, stand_in = "/usr/share/fonts/opentype/inter/Inter-Medium.otf", True
    return bold, regular, stand_in


# --------------------------------------------------------------- layout -----
class Word:
    __slots__ = ("text", "start", "x", "line", "w", "sprite")


class Page:
    pass


def split_words(chunk):
    toks = [t for t in chunk["text"].split(" ") if t]  # NBSP keeps words together
    total = sum(len(t) + 1 for t in toks)
    t, out = chunk["start"], []
    for tok in toks:
        out.append((tok, int(round(t)), id(chunk)))
        t += (chunk["end"] - chunk["start"]) * (len(tok) + 1) / total
    return out


def balance(words, font, gap, max_w):
    """Split a word list into 1-2 lines with the most even widths."""
    widths = [font.getlength(w) for w in words]

    def lw(a, b):
        return sum(widths[a:b]) + gap * max(0, b - a - 1)

    if lw(0, len(words)) <= max_w * 0.62 or len(words) == 1:
        return [list(range(len(words)))]
    best, best_k = None, 1
    for k in range(1, len(words)):
        m = max(lw(0, k), lw(k, len(words)))
        if lw(0, k) <= max_w and lw(k, len(words)) <= max_w and (best is None or m < best):
            best, best_k = m, k
    return [list(range(best_k)), list(range(best_k, len(words)))]


def paginate(turn, font, gap, max_w):
    """Group a speaker turn into pages of max. 2 lines.

    Pages break only between transcript chunks (natural speech phrases),
    always after . ? !, and after a comma once the page is reasonably full.
    """
    def fits(ws):
        texts = [w[0] for w in ws]
        lines = balance(texts, font, gap, max_w)
        if len(lines) > 2:
            return False
        for ln in lines:
            if sum(font.getlength(texts[i]) for i in ln) + gap * (len(ln) - 1) > max_w:
                return False
        return True

    def fill(ws):
        return sum(font.getlength(w[0]) for w in ws) + gap * (len(ws) - 1)

    pages, cur = [], []
    for c in turn["chunks"]:
        cw = split_words(c)
        if cur and not fits(cur + cw):
            pages.append(cur)
            cur = []
        for w in cw:                      # a chunk that alone is too long
            if cur and not fits(cur + [w]):
                pages.append(cur)
                cur = []
            cur.append(w)
        end = cur[-1][0][-1]
        if (end in ".?!" and len(cur) >= 2) or (end in ",:" and fill(cur) > max_w * 1.05):
            pages.append(cur)
            cur = []
    if cur:
        pages.append(cur)
    # no orphans: give a 1-2 word page some words of the page before it
    for i in range(1, len(pages)):
        prev, last = pages[i - 1], pages[i]
        if prev[-1][0][-1] in ".?!":
            continue
        while len(last) < 3:
            cid = prev[-1][2]                 # move the whole last chunk
            k = len(prev)
            while k > 0 and prev[k - 1][2] == cid:
                k -= 1
            if k < 3 or not fits(prev[k:] + last):
                break
            last[:0] = prev[k:]
            del prev[k:]
    return pages


def build_pages(data, fmt, fonts):
    gap_a = fonts["A"].getlength(" ") * 1.35
    gap_q = fonts["Q"].getlength(" ") * 1.15
    out = []
    for turn in data["turns"]:
        sp = turn["speaker"]
        font = fonts[sp]
        gap = gap_a if sp == "A" else gap_q
        size = fmt["size_a"] if sp == "A" else fmt["size_q"]
        max_w = fmt["max_w"] if sp == "A" else fmt["max_w"] - 80
        for pw in paginate(turn, font, gap, max_w):
            p = Page()
            p.speaker, p.font, p.size = sp, font, size
            texts = [w[0] for w in pw]
            lines = balance(texts, font, gap, max_w)
            p.line_h = int(size * (1.32 if sp == "A" else 1.62))
            p.n_lines = len(lines)
            p.words = []
            for li, ln in enumerate(lines):
                lw = sum(font.getlength(texts[i]) for i in ln) + gap * (len(ln) - 1)
                x = (fmt["w"] - lw) / 2
                for i in ln:
                    w = Word()
                    w.text, w.start, w.line = texts[i], pw[i][1], li
                    w.w = font.getlength(w.text)
                    w.x = x
                    x += w.w + gap
                    p.words.append(w)
            p.start = p.words[0].start
            p.last_word = p.words[-1].start
            out.append(p)

    # page end: up to next page start (or hold 0.6 s after the last word)
    fps = data["fps"]
    last_end = data["turns"][-1]["chunks"][-1]["end"]
    for i, p in enumerate(out):
        nxt = out[i + 1].start if i + 1 < len(out) else last_end + int(0.6 * fps)
        p.end = nxt
        if i + 1 < len(out):
            # chunk end of the page's last word
            p.end = max(nxt, p.last_word + 6)
    for p in out:
        top = fmt["bottom"] - p.n_lines * p.line_h
        p.top = top
    return out


# --------------------------------------------------------------- render -----
class Renderer:
    def __init__(self, fmt, fonts, pages):
        self.fmt, self.fonts, self.pages = fmt, fonts, pages
        self.cache = {}
        lh = max(p.line_h for p in pages)
        self.y0 = max(0, fmt["bottom"] - 2 * lh - 90)
        self.y1 = min(fmt["h"], fmt["bottom"] + 70)

    def sprite(self, text, font, color):
        key = (text, id(font), color)
        if key not in self.cache:
            asc, desc = font.getmetrics()
            pad = 8
            w = int(math.ceil(font.getlength(text))) + 2 * pad
            im = Image.new("RGBA", (w, asc + desc + 2 * pad), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((pad, pad), text, font=font, fill=color + (255,))
            self.cache[key] = (im, pad)
        return self.cache[key]

    @staticmethod
    def fade(im, a):
        if a >= 0.999:
            return im
        im = im.copy()
        lut = [int(v * a) for v in range(256)]
        im.putalpha(im.getchannel("A").point(lut))
        return im

    def word_box(self, p, w):
        asc, desc = p.font.getmetrics()
        y = p.top + w.line * p.line_h
        pad_x, pad_t, pad_b = p.size * 0.20, p.size * 0.10, p.size * 0.16
        cap_top = y + asc - p.size * 0.74          # approx. cap height
        return (w.x - pad_x, cap_top - pad_t, w.x + w.w + pad_x, y + asc + desc * 0.35 + pad_b)

    def draw_page(self, layer, p, f):
        S = STYLE
        oy = -self.y0
        out_a = clamp((p.end - f) / S["out_frames"])
        out_a = cubic_inout(out_a)
        if out_a <= 0:
            return
        vis = [w for w in p.words if w.start <= f]
        if not vis:
            return
        d = ImageDraw.Draw(layer)
        progress = {id(w): expo_out(clamp((f - w.start) / S["in_frames"])) for w in vis}

        if p.speaker == "A":
            # --- red highlight box travelling from word to word
            cur = vis[-1]
            prev = vis[-2] if len(vis) > 1 else None
            t = expo_out(clamp((f - cur.start) / S["hl_frames"]))
            b1 = self.word_box(p, cur)
            if prev is None:
                cx, cy = (b1[0] + b1[2]) / 2, (b1[1] + b1[3]) / 2
                s = lerp(0.6, 1.0, t)
                box = (cx - (b1[2] - b1[0]) / 2 * s, cy - (b1[3] - b1[1]) / 2 * s,
                       cx + (b1[2] - b1[0]) / 2 * s, cy + (b1[3] - b1[1]) / 2 * s)
                box_a = t
            else:
                b0 = self.word_box(p, prev)
                box = tuple(lerp(a, b, t) for a, b in zip(b0, b1))
                box_a = 1.0
            box = (box[0], box[1] + oy, box[2], box[3] + oy)
            r = int(p.size * 0.14)
            a = int(255 * box_a * out_a)
            if a > 0:
                tmp = Image.new("RGBA", layer.size, (0, 0, 0, 0))
                ImageDraw.Draw(tmp).rounded_rectangle(box, radius=r, fill=S["red"] + (a,))
                layer.alpha_composite(tmp)
            color = S["white"]
        else:
            # --- white bar per line, growing with the revealed words, red edge
            for li in range(p.n_lines):
                lw = [w for w in vis if w.line == li]
                if not lw:
                    continue
                first = [w for w in p.words if w.line == li][0]
                pr = progress[id(lw[-1])]
                right_prev = lw[-2].x + lw[-2].w if len(lw) > 1 else first.x
                right = lerp(right_prev, lw[-1].x + lw[-1].w, pr)
                y = p.top + li * p.line_h + oy
                asc, desc = p.font.getmetrics()
                pad_x = p.size * 0.42
                top = y + asc - p.size * 0.74 - p.size * 0.36
                bot = y + asc + p.size * 0.36
                a = int(255 * out_a * (pr if len(lw) == 1 else 1.0))
                edge = max(6, int(p.size * 0.12))
                tmp = Image.new("RGBA", layer.size, (0, 0, 0, 0))
                td = ImageDraw.Draw(tmp)
                td.rectangle((first.x - pad_x - edge, top, first.x - pad_x, bot), fill=S["red"] + (a,))
                td.rectangle((first.x - pad_x, top, right + pad_x, bot), fill=S["white"] + (a,))
                layer.alpha_composite(tmp)
            color = S["dark"]

        # --- words
        for w in vis:
            pr = progress[id(w)]
            spr, pad = self.sprite(w.text, p.font, color)
            sc = lerp(S["scale_from"], 1.0, pr)
            im = spr
            if sc < 0.999:
                im = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BICUBIC)
            im = self.fade(im, pr * out_a)
            cx = w.x - pad + spr.width / 2
            cy = p.top + w.line * p.line_h - pad + spr.height / 2 + (1 - pr) * S["rise_px"] + oy
            layer.alpha_composite(im, (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))))

    def frame(self, f):
        W = self.fmt["w"]
        layer = Image.new("RGBA", (W, self.y1 - self.y0), (0, 0, 0, 0))
        for p in self.pages:
            if p.start <= f < p.end:
                self.draw_page(layer, p, f)
        if layer.getbbox() is None:
            return layer
        # soft drop shadow from the combined alpha
        S = STYLE
        a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(S["shadow_blur"]))
        a = a.point([int(v * S["shadow_alpha"]) for v in range(256)])
        shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        shadow.putalpha(a)
        out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        out.alpha_composite(shadow, S["shadow_offset"])
        out.alpha_composite(layer)
        return out


# ------------------------------------------------------------------ srt -----
def write_srt(pages, fps, path):
    def ts(fr):
        ms = int(round(fr / fps * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    lines = []
    for i, p in enumerate(pages, 1):
        rows = {}
        for w in p.words:
            rows.setdefault(w.line, []).append(w.text)
        txt = "\n".join(" ".join(rows[k]) for k in sorted(rows))
        lines.append(f"{i}\n{ts(p.start)} --> {ts(p.end)}\n{txt}\n")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


# ----------------------------------------------------------------- main -----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--captions", default=str(ROOT / "captions.json"))
    ap.add_argument("--format", default="9x16", choices=FORMATS)
    ap.add_argument("--font-bold")
    ap.add_argument("--font-regular")
    ap.add_argument("--out", default=str(ROOT / "export"))
    ap.add_argument("--still", type=int, nargs="*", help="frame number(s) to save as PNG")
    ap.add_argument("--still-bg", action="store_true", help="put stills on a grey test background")
    ap.add_argument("--no-webm", action="store_true")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    data = json.loads(Path(args.captions).read_text(encoding="utf-8"))
    fps = data["fps"]
    fmt = FORMATS[args.format]
    fb, fr, stand_in = find_fonts(args.font_bold, args.font_regular)
    if stand_in:
        print("WARNING: Netto Pro not found in fonts/ – rendering with Inter as stand-in.", file=sys.stderr)
    print(f"fonts: {fb} | {fr}", file=sys.stderr)
    fonts = {"A": ImageFont.truetype(fb, fmt["size_a"]), "Q": ImageFont.truetype(fr, fmt["size_q"])}
    pages = build_pages(data, fmt, fonts)
    R = Renderer(fmt, fonts, pages)
    total = pages[-1].end
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = f"Leon_Captions_{args.format}"

    if args.still is not None:
        for f in args.still:
            crop = R.frame(f)
            full = Image.new("RGBA", (fmt["w"], fmt["h"]), (0, 0, 0, 0))
            full.alpha_composite(crop, (0, R.y0))
            if args.still_bg:
                bg = Image.new("RGBA", full.size, (96, 104, 112, 255))
                bg.alpha_composite(full)
                full = bg
            p = out / f"{tag}_f{f:05}.png"
            full.save(p)
            print(p)
        return

    write_srt(pages, fps, out / "Leon_Captions.srt")
    W, H = fmt["w"], fmt["h"]
    mov = out / f"{tag}_ProRes4444.mov"
    webm = out / f"{tag}_alpha.webm"
    prev = out / f"{tag}_preview.mp4"
    n_out = 1 + (not args.no_webm) + (not args.no_preview)
    fc = f"[0:v]split={n_out}" + "".join(f"[v{i}]" for i in range(n_out)) + ";"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    maps, i = [], 0
    maps += ["-map", f"[v{i}]", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
             "-alpha_bits", "16", "-vendor", "apl0", "-r", str(fps), str(mov)]
    i += 1
    if not args.no_webm:
        maps += ["-map", f"[v{i}]", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "32",
                 "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1", "-auto-alt-ref", "0",
                 "-r", str(fps), str(webm)]
        i += 1
    if not args.no_preview:
        cmd += ["-f", "lavfi", "-i", f"color=c=0x5f666e:s={W}x{H}:r={fps}"]
        fc += f"[1:v][v{i}]overlay=shortest=1,format=yuv420p[pv];"
        maps += ["-map", "[pv]", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", str(prev)]
    cmd += ["-filter_complex", fc.rstrip(";")] + maps

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    buf = np.zeros((H, W, 4), dtype=np.uint8)
    for f in range(total):
        crop = np.asarray(R.frame(f))
        buf[:] = 0
        buf[R.y0:R.y0 + crop.shape[0]] = crop
        proc.stdin.write(buf.tobytes())
        if f % 300 == 0:
            print(f"frame {f}/{total}", file=sys.stderr)
    proc.stdin.close()
    proc.wait()
    print("done:", mov, file=sys.stderr)


if __name__ == "__main__":
    main()
