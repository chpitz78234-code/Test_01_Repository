#!/usr/bin/env python3
"""Animierte Captions im Renfert-Look (weiß + Rot #C8102E, Netto Pro) mit Alphakanal.

Ausgabe: ProRes 4444 (.mov, yuva444p10le) für Premiere, 1080x1920, 30 fps.

  python3 render_captions.py --fonts <ordner mit NETTOPRO-*.OTF> \
      --words words_final.json --chunks chunks.txt --out out_dir [--preview audio.mp3]
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
RED = (200, 16, 46)          # #C8102E
WHITE = (255, 255, 255)
SAFE_X = 80                  # seitlicher Rand
MAX_W = W - 2 * SAFE_X
CENTER_Y = 1390              # vertikale Mitte des Caption-Blocks (unten 320 px frei)
FONT_SIZE = 86
KEEP_CASE = {"eLAB"}


# ---------------------------------------------------------------- easing
def bezier(x1, y1, x2, y2):
    def f(t):
        if t <= 0: return 0.0
        if t >= 1: return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(30):
            u = (lo + hi) / 2
            x = 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u ** 2 * x2 + u ** 3
            lo, hi = (u, hi) if x < t else (lo, u)
        u = (lo + hi) / 2
        return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u ** 2 * y2 + u ** 3
    return f

snap_out = bezier(0.20, 0.20, 0.05, 1.00)   # motion-spec: Titel-Reveals, Masken
expo_out = bezier(0.16, 1.00, 0.30, 1.00)
whip_in = bezier(0.70, 0.00, 0.84, 0.00)


# ---------------------------------------------------------------- helpers
def mask_layer(mask, color, opacity=1.0):
    if opacity < 1:
        mask = mask.point(lambda v: int(v * opacity))
    img = Image.new("RGBA", mask.size, color + (0,))
    img.putalpha(mask)
    return img


def blur_mask(mask, radius, pad):
    big = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0)
    big.paste(mask, (pad, pad))
    return big.filter(ImageFilter.GaussianBlur(radius))


def comp(frame, layer, x, y):
    """alpha_composite mit Clipping an den Bildrändern."""
    x, y = int(round(x)), int(round(y))
    l, t = max(0, -x), max(0, -y)
    r, b = min(layer.width, W - x), min(layer.height, H - y)
    if r <= l or b <= t:
        return
    if (l, t, r, b) != (0, 0, layer.width, layer.height):
        layer = layer.crop((l, t, r, b))
    frame.alpha_composite(layer, (x + l, y + t))


# ---------------------------------------------------------------- layout
def parse_chunks(path):
    chunks = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        toks = []
        for t in line.split():
            hl = t.startswith("*") and t.rstrip(".,!?").endswith("*")
            txt = re.sub(r"\*", "", t)
            toks.append((txt, hl))
        chunks.append(toks)
    return chunks


def disp(txt):
    txt = txt.rstrip(".,!")          # Satzzeichen am Wortende weglassen (Fragezeichen bleibt)
    return txt if txt in KEEP_CASE else txt.upper()


class Caption:
    def __init__(self, toks, times, font):
        self.font = font
        self.words = []
        size = font.size
        while True:
            f = font.font_variant(size=size)
            lens = [f.getlength(disp(t)) for t, _ in toks]
            sp = f.getlength(" ") * 1.05
            lines = self.wrap(lens, sp)
            if max(self.line_w(l, lens, sp) for l in lines) <= MAX_W or size < 40:
                break
            size -= 4
        self.f = f
        asc = f.getbbox("H")             # Versalhöhe
        cap_top, base = asc[1], asc[3]
        self.pad_x, self.pad_y = int(size * 0.20), int(size * 0.17)
        line_h = (base - cap_top) + 2 * self.pad_y
        pitch = line_h + int(size * 0.10)
        total_h = pitch * (len(lines) - 1) + line_h
        top = CENTER_Y - total_h / 2
        self.boxes = []
        for li, idxs in enumerate(lines):
            lw = self.line_w(idxs, lens, sp)
            x = W / 2 - lw / 2
            box_top = top + li * pitch
            y_text = box_top + self.pad_y - cap_top
            run = None
            for k, i in enumerate(idxs):
                txt, hl = toks[i]
                self.words.append(dict(i=i, txt=disp(txt), hl=hl, x=x, y=y_text,
                                       w=lens[i], t=times[i]))
                if hl:
                    if run is None:
                        run = dict(x0=x, x1=x + lens[i], y=box_top, h=line_h, t=times[i][0])
                    else:
                        run["x1"] = x + lens[i]
                if run is not None and (not hl or k == len(idxs) - 1):
                    self.boxes.append(run)
                    run = None
                x += lens[i] + sp
        self.start = times[0][0]
        self.last_end = times[-1][1]
        self._sprites()

    @staticmethod
    def line_w(idxs, lens, sp):
        return sum(lens[i] for i in idxs) + sp * (len(idxs) - 1)

    def wrap(self, lens, sp):
        n = len(lens)
        one = list(range(n))
        if self.line_w(one, lens, sp) <= MAX_W * 0.92 or n == 1:
            return [one]
        best = None
        for k in range(1, n):           # ausgewogene zwei Zeilen
            a, b = list(range(k)), list(range(k, n))
            m = max(self.line_w(a, lens, sp), self.line_w(b, lens, sp))
            # leicht bevorzugen: obere Zeile kürzer (Pyramide)
            score = m + (0 if self.line_w(a, lens, sp) <= self.line_w(b, lens, sp) else 20)
            if best is None or score < best[0]:
                best = (score, [a, b])
        return best[1]

    def _sprites(self):
        f = self.f
        for w in self.words:
            bb = f.getbbox(w["txt"])
            m = Image.new("L", (int(bb[2]) + 8, int(bb[3]) + 8), 0)
            ImageDraw.Draw(m).text((0, 0), w["txt"], font=f, fill=255)
            w["mask"] = m
            w["shadow"] = blur_mask(m, 7, 16)
        for b in self.boxes:
            bw = int(round(b["x1"] - b["x0"] + 2 * self.pad_x))
            b["w"], b["X"] = bw, b["x0"] - self.pad_x
            m = Image.new("L", (bw, int(b["h"])), 255)
            b["mask"] = m
            b["shadow"] = blur_mask(m, 12, 24)


# ---------------------------------------------------------------- draw
POP = 6       # t_pop
WIPE = 6      # t_wipe
EXIT = 4
LEAD = 2      # Frames vor Wortbeginn


def draw_caption(frame, cap, fi, f_in, f_out, hard_cut_out):
    if fi < f_in or fi >= f_out:
        return
    # Ausblenden
    ex_p = 0.0
    if not hard_cut_out and fi >= f_out - EXIT:
        ex_p = whip_in((fi - (f_out - EXIT) + 1) / EXIT)
    ex_op, ex_dy = 1 - ex_p, -22 * ex_p

    # Boxen (Wipe von links)
    for b in cap.boxes:
        fb = round(b["t"] * FPS) - LEAD - 1
        if fi < fb:
            continue
        p = snap_out((fi - fb + 1) / WIPE)
        bw = max(1, int(b["w"] * p))
        sh = b["shadow"].crop((0, 0, bw + 48, b["shadow"].height))
        comp(frame, mask_layer(sh, (0, 0, 0), 0.30 * ex_op), b["X"] - 24, b["y"] - 24 + 6 + ex_dy)
        comp(frame, mask_layer(b["mask"].crop((0, 0, bw, b["mask"].height)), RED, ex_op),
             b["X"], b["y"] + ex_dy)

    # Wörter (Pop: Scale 60→100 %, von unten, snap_out)
    for w in cap.words:
        fw = round(w["t"][0] * FPS) - LEAD
        if fi < fw:
            continue
        k = fi - fw
        p = snap_out((k + 1) / POP)
        s = 0.6 + 0.4 * p
        op = (0.55 if k == 0 else 1.0) * ex_op
        dy = 26 * (1 - p) + ex_dy
        m = w["mask"]
        if s < 0.999:
            m = m.resize((max(1, int(m.width * s)), max(1, int(m.height * s))), Image.BICUBIC)
        cx, by = w["x"] + w["mask"].width / 2, w["y"] + w["mask"].height * 0.8
        x, y = cx - m.width / 2, by - m.height * 0.8 + dy
        if not w["hl"]:
            sh = w["shadow"]
            if s < 0.999:
                sh = sh.resize((max(1, int(sh.width * s)), max(1, int(sh.height * s))), Image.BICUBIC)
            comp(frame, mask_layer(sh, (0, 0, 0), 0.55 * op), x - 16 * s, y - 16 * s + 4)
        comp(frame, mask_layer(m, WHITE, op), x, y)


# ---------------------------------------------------------------- name tags
class NameTag:
    def __init__(self, name, title, t0, t1, fonts):
        fn = ImageFont.truetype(fonts["black"], 66)
        ft = ImageFont.truetype(fonts["bold"], 40)
        self.t0, self.t1 = t0, t1
        self.bars = []
        for txt, f, bg, fg, padx, pady in ((name.upper(), fn, RED, WHITE, 26, 20),
                                          (title, ft, WHITE, RED, 26, 16)):
            bb = f.getbbox("H")
            tw = f.getlength(txt)
            bw, bh = int(tw + 2 * padx), int(bb[3] - bb[1] + 2 * pady)
            img = Image.new("RGBA", (bw, bh), bg + (255,))
            ImageDraw.Draw(img).text((padx, pady - bb[1]), txt, font=f, fill=fg + (255,))
            sh = blur_mask(Image.new("L", (bw, bh), 255), 12, 24)
            self.bars.append(dict(img=img, sh=sh))
        self.x, self.y = 70, 1000

    def draw(self, frame, fi):
        f0, f1 = round(self.t0 * FPS), round(self.t1 * FPS)
        y = self.y
        for n, b in enumerate(self.bars):
            a = f0 + 3 * n
            o = f1 - 6 - 3 * (1 - n)   # unterer Balken geht zuerst raus
            if fi < a or fi >= o + 6:
                y += b["img"].height
                continue
            p = snap_out((fi - a + 1) / 8)
            if fi >= o:
                p = 1 - whip_in((fi - o + 1) / 6)
            bw = max(1, int(b["img"].width * p))
            if p > 0.01:
                sh = b["sh"].crop((0, 0, bw + 48, b["sh"].height))
                comp(frame, mask_layer(sh, (0, 0, 0), 0.30), self.x - 24, y - 24 + 6)
                comp(frame, b["img"].crop((0, 0, bw, b["img"].height)), self.x, y)
            y += b["img"].height


# ---------------------------------------------------------------- main
def encode(out, n_frames, frame_fn):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           "-alpha_bits", "16", "-vendor", "apl0", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    empty = bytes(W * H * 4)
    for fi in range(n_frames):
        fr = frame_fn(fi)
        p.stdin.write(empty if fr is None else fr.tobytes())
        if fi % 150 == 0:
            print(f"  {out.name}: {fi}/{n_frames}", flush=True)
    p.stdin.close()
    p.wait()


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--words", required=True)
    ap.add_argument("--chunks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--only", default=None, help="Frame-Liste für Stills, z. B. 60,300")
    args = ap.parse_args()

    fdir = Path(args.fonts)
    fonts = {k: str(next(fdir.glob(p))) for k, p in
             (("black", "*NETTOPRO-BLACK.OTF"), ("bold", "*NETTOPRO-BOLD.OTF"))}
    font = ImageFont.truetype(fonts["black"], FONT_SIZE)

    words = json.load(open(args.words, encoding="utf-8"))
    chunks = parse_chunks(args.chunks)
    n_tok = sum(len(c) for c in chunks)
    if n_tok != len(words):
        sys.exit(f"Wortanzahl passt nicht: chunks={n_tok} whisper={len(words)}")

    caps, i = [], 0
    for c in chunks:
        times = [(w["s"], w["e"]) for w in words[i:i + len(c)]]
        caps.append(Caption(c, times, font))
        i += len(c)

    duration = args.duration or (words[-1]["e"] + 1.0)
    n_frames = int(round(duration * FPS))

    # Ein-/Ausstiegsframes
    sched = []
    for k, c in enumerate(caps):
        f_in = max(0, round(c.start * FPS) - LEAD)
        f_end_nat = round((c.last_end + 0.45) * FPS)
        if k + 1 < len(caps):
            f_next = round(caps[k + 1].start * FPS) - LEAD
            f_out = min(f_end_nat, f_next)
            hard = f_next - f_out <= 1
        else:
            f_out, hard = min(f_end_nat, n_frames), False
        sched.append((c, f_in, f_out, hard))

    tags = [NameTag("Søren Haag", "CEO Renfert", 0.15, 3.55, fonts),
            NameTag("Sascha Hein", "Inventor eLAB System", 3.80, 6.85, fonts)]

    def cap_frame(fi):
        act = [s for s in sched if s[1] <= fi < s[2]]
        if not act:
            return None
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for c, a, b, hard in act:
            draw_caption(fr, c, fi, a, b, hard)
        return fr

    def tag_frame(fi):
        if fi > round(tags[-1].t1 * FPS):
            return None
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for t in tags:
            t.draw(fr, fi)
        return fr

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.only:
        for fi in map(int, args.only.split(",")):
            fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for f in (tag_frame(fi), cap_frame(fi)):
                if f is not None:
                    fr.alpha_composite(f)
            fr.save(out / f"still_{fi:04d}.png")
        return

    # SRT
    with open(out / "Renfert_Captions.srt", "w", encoding="utf-8") as fh:
        for k, (c, a, b, _) in enumerate(sched, 1):
            txt = " ".join(w["txt"] for w in sorted(c.words, key=lambda w: w["i"]))
            fh.write(f"{k}\n{srt_time(a / FPS)} --> {srt_time(b / FPS)}\n{txt}\n\n")

    encode(out / "Renfert_Captions_1080x1920_alpha.mov", n_frames, cap_frame)
    encode(out / "Renfert_NameTags_1080x1920_alpha.mov", n_frames, tag_frame)


if __name__ == "__main__":
    main()
