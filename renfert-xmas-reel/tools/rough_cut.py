#!/usr/bin/env python3
"""Rough cut: joins the selected clips into one 9:16 video with soft crossfades.

  python3 tools/rough_cut.py            # -> build/rohschnitt.mp4

Clip selection and target lengths live in build/video/cut.json. If build/timing.json
exists (from the voiceover step), its scene lengths win over the ones in cut.json.
Each clip is retimed to its target length (setpts); the overlap of the following crossfade
(default crossfade_s, per clip "crossfade_in_s") is added, so cuts stay on the target timeline.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUT = ROOT / "build" / "video" / "cut.json"
TIMING = ROOT / "build" / "timing.json"
OUT = ROOT / "build" / "rohschnitt.mp4"


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main() -> None:
    cut = json.loads(CUT.read_text(encoding="utf-8"))
    fade = cut.get("crossfade_s", 0.25)
    fps, w, h = cut.get("fps", 24), cut.get("width", 720), cut.get("height", 1280)
    targets = {c["scene"]: c["target_s"] for c in cut["clips"]}
    if TIMING.exists():
        targets.update({s["id"]: s["duration_s"] for s in json.loads(TIMING.read_text())["scenes"]})

    inputs, chains, lengths = [], [], []
    clips = cut["clips"]
    for i, c in enumerate(clips):
        src = ROOT / "build" / "video" / c["file"]
        if not src.exists():
            sys.exit(f"fehlt: {src}")
        nxt = clips[i + 1].get("crossfade_in_s", fade) if i < len(clips) - 1 else 0
        length = targets[c["scene"]] + nxt
        factor = length / duration(src)
        inputs += ["-i", str(src)]
        chains.append(f"[{i}:v]setpts={factor:.5f}*(PTS-STARTPTS),fps={fps},scale={w}:{h},"
                      f"setsar=1,trim=duration={length:.3f},setpts=PTS-STARTPTS[v{i}]")
        lengths.append(length)
        print(f"{c['scene']}: {c['file']:<22} {duration(src):5.2f}s -> {length:5.2f}s (x{factor:.2f})")

    graph, prev, offset = list(chains), "v0", 0.0
    for i in range(1, len(clips)):
        d = clips[i].get("crossfade_in_s", fade)
        offset += lengths[i - 1] - d
        out = f"x{i}"
        graph.append(f"[{prev}][v{i}]xfade=transition=fade:duration={d}:offset={offset:.3f}[{out}]")
        prev = out

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph),
           "-map", f"[{prev}]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print(f"-> {OUT} ({duration(OUT):.2f}s)")


if __name__ == "__main__":
    main()
