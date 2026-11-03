#!/usr/bin/env python3
"""Prepares the HyperFrames project in ../hyperframes:

  * retimes the selected Seedance clips onto the film timeline and scales them to 1080x1920
  * mixes music + voiceover (voice delayed, music ducked under the voice, faded out at the end)
  * writes assets/timeline.js (scene spans, caption lines with per-word times) for index.html

  python3 tools/prepare_hyperframes.py --voice VO.mp3 --music MUSIC.mp3

Caption timing comes from the voiceover's own pauses (ffmpeg silencedetect): one spoken block
per poem line. Words inside a line are spread by their length.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HF = ROOT / "hyperframes"
CLIPS = ROOT / "build" / "video"

FILM_S = 31.8          # = music length
VO_OFFSET = 3.6        # film time where the voice starts (before: intro on S2)

LINES = [
    "To every hand that shapes a smile,",
    "in lab and practice, mile by mile,",
    "your skill and trust have made us strong,",
    "it's you we've built for all year long.",
    "Now candles glow and work can rest,",
    "may this season bring the best.",
    "Merry Christmas and a bright New Year,",
    "from all of us at Renfert.",
]

# scene cut points on the film timeline; fade_in = crossfade from the previous scene
SCENES = [
    {"id": "S2", "file": "S2_v2.mp4", "start": 0.0, "end": 3.6, "fade_in": 0.0},
    {"id": "S3", "file": "S3_v1.mp4", "start": 3.6, "end": 6.6, "fade_in": 0.35},
    {"id": "S4", "file": "S4_v2.mp4", "start": 6.6, "end": 9.8, "fade_in": 0.35},
    {"id": "S6", "file": "S6_v2.mp4", "start": 9.8, "end": 13.6, "fade_in": 0.9},
    {"id": "S7", "file": "S7_v2.mp4", "start": 13.6, "end": 19.4, "fade_in": 0.35},
    {"id": "S8", "file": "S8_v1.mp4", "start": 19.4, "end": 22.8, "fade_in": 0.35},
    {"id": "S9", "file": "S9_v1.mp4", "start": 22.8, "end": FILM_S, "fade_in": 0.35},
]


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration(path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(path)]).stdout)


def speech_blocks(voice: Path, n: int):
    """Spoken blocks between pauses >= 0.25 s; merges the shortest gaps until n blocks remain."""
    log = subprocess.run(["ffmpeg", "-v", "info", "-i", str(voice), "-af",
                          "silencedetect=noise=-38dB:d=0.25", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    total = duration(voice)
    # sound regions = complement of silences
    onset = ends[0] if starts and starts[0] < 0.05 else 0.0
    if starts and starts[0] < 0.05:
        starts, ends = starts[1:], ends[1:]
    blocks, cur = [], onset
    for s, e in zip(starts, ends):
        blocks.append([cur, s])
        cur = e
    if cur < total - 0.05:
        blocks.append([cur, total])
    while len(blocks) > n:  # merge across the shortest pause
        gaps = [blocks[i + 1][0] - blocks[i][1] for i in range(len(blocks) - 1)]
        i = gaps.index(min(gaps))
        blocks[i:i + 2] = [[blocks[i][0], blocks[i + 1][1]]]
    if len(blocks) != n:
        sys.exit(f"{len(blocks)} Sprechblöcke gefunden, erwartet {n} – Captions bitte manuell timen.")
    return blocks


def word_times(text, start, end):
    words = text.split()
    weights = [len(re.sub(r"[^\w']", "", w)) + 1.5 for w in words]
    span, t, out = end - start, start, []
    for w, k in zip(words, weights):
        d = span * k / sum(weights)
        out.append({"w": w, "t": round(t, 3)})
        t += d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True, type=Path)
    ap.add_argument("--music", required=True, type=Path)
    a = ap.parse_args()

    (HF / "assets" / "video").mkdir(parents=True, exist_ok=True)
    (HF / "assets" / "audio").mkdir(parents=True, exist_ok=True)

    # --- video: retime each clip to its span (incl. the incoming crossfade) ---
    scenes_out = []
    for s in SCENES:
        src = CLIPS / s["file"]
        span = (s["end"] - s["start"]) + s["fade_in"]
        factor = span / duration(src)
        dst = HF / "assets" / "video" / f"{s['id']}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-vf",
             f"setpts={factor:.5f}*(PTS-STARTPTS),fps=30,scale=1080:1920:flags=lanczos,setsar=1",
             "-t", f"{span:.3f}", "-c:v", "libx264", "-crf", "16", "-g", "30", "-keyint_min", "30",
             "-pix_fmt", "yuv420p",
             "-preset", "slow", "-movflags", "+faststart", str(dst)])
        scenes_out.append({"id": s["id"], "src": f"assets/video/{s['id']}.mp4",
                           "start": round(s["start"] - s["fade_in"], 3), "duration": round(span, 3),
                           "fade_in": s["fade_in"]})
        print(f"{s['id']}: {span:5.2f}s (Tempo x{1 / factor:.2f})")

    # --- captions from the voiceover's pauses ---
    blocks = speech_blocks(a.voice, len(LINES))
    captions = []
    for text, (b0, b1) in zip(LINES, blocks):
        s0, s1 = VO_OFFSET + b0, VO_OFFSET + b1
        captions.append({"text": text, "start": round(s0, 3), "end": round(s1, 3),
                         "words": word_times(text, s0, s1)})
        print(f"{s0:6.2f}–{s1:6.2f}  {text}")

    # --- audio mix: voice +5 dB, delayed; music ducked to 0.38 under the voice ---
    vo_start, vo_end = VO_OFFSET + blocks[0][0], VO_OFFSET + blocks[-1][1]
    duck = (f"if(lt(t,{vo_start - 0.5:.2f}),0.85,"
            f"if(lt(t,{vo_start:.2f}),0.85-0.47*(t-{vo_start - 0.5:.2f})/0.5,"
            f"if(lt(t,{vo_end + 0.2:.2f}),0.38,"
            f"if(lt(t,{vo_end + 1.2:.2f}),0.38+0.47*(t-{vo_end + 0.2:.2f}),0.85))))")
    mix = HF / "assets" / "audio" / "mix.wav"
    delay_ms = int(VO_OFFSET * 1000)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(a.music), "-i", str(a.voice), "-filter_complex",
         f"[0:a]aresample=48000,volume='{duck}':eval=frame,afade=t=out:st={FILM_S - 2.8:.2f}:d=2.8[m];"
         f"[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.78,adelay={delay_ms}|{delay_ms}[v];"
         f"[m][v]amix=inputs=2:normalize=0,alimiter=limit=0.89,atrim=0:{FILM_S}[o]",
         "-map", "[o]", "-c:a", "pcm_s16le", str(mix)])
    print(f"Mix -> {mix}")

    # --- keep the <video> tags in index.html in step with the scene spans ---
    index = HF / "index.html"
    if index.exists():
        html = index.read_text(encoding="utf-8")
        tags = "\n".join(
            f'      <video id="v-{s["id"]}" class="clip scene" src="{s["src"]}" data-start="{s["start"]:g}" '
            f'data-duration="{s["duration"]:g}" data-track-index="{i % 2}" muted playsinline style="z-index:{i + 1}"></video>'
            for i, s in enumerate(scenes_out))
        html = re.sub(r"(<!-- VIDEOS:BEGIN[^>]*-->\n).*?(\n\s*<!-- VIDEOS:END -->)",
                      lambda m: m.group(1) + tags + m.group(2), html, flags=re.S)
        index.write_text(html, encoding="utf-8")

    (HF / "assets" / "timeline.js").write_text(
        "// generated by tools/prepare_hyperframes.py – do not edit by hand\n"
        f"window.FILM = {json.dumps({'duration': FILM_S, 'scenes': scenes_out, 'captions': captions}, indent=1)};\n",
        encoding="utf-8")
    print("timeline.js geschrieben")


if __name__ == "__main__":
    main()
