#!/usr/bin/env python3
"""Vermisst ein Video wie die Referenzen der Stilvorgabe.

Ausgabe (JSON): Bewegungsenergie pro Frame, erkannte Schnitte, Shotlaengen und
das Dubletten-Muster (on twos / 24->30 Pulldown / gestufte Elemente).

Benoetigt ffmpeg/ffprobe im PATH sowie numpy.
Aufruf: python3 analyze_motion.py video.mp4 [--cut-threshold 40] [--bpm 118]
"""
import argparse
import json
import subprocess

import numpy as np

W, H = 90, 160  # Analyseaufloesung reicht fuer Energie und Schnitte


def probe_fps(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=r_frame_rate", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()
    num, den = out.split("/")
    return float(num) / float(den)


def read_frames(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.int16)


def duplicate_pattern(energy, still=0.25):
    """Erkennt, in welchem Raster sich das Bild tatsaechlich aendert."""
    moving = energy > still
    if moving.sum() < 4:
        return {"pattern": "static"}
    dup_ratio = 1 - moving.mean()
    idx = np.where(moving)[0]
    steps = np.diff(idx)
    median_step = float(np.median(steps)) if len(steps) else 1.0
    # Pulldown: einzelne stille Frames mitten in Bewegung, immer an derselben 5er-Phase
    isolated = np.where(~moving[1:-1] & moving[:-2] & moving[2:])[0] + 1
    if len(isolated) >= 4:
        phase = np.bincount(isolated % 5, minlength=5)
        if phase.max() > 0.8 * len(isolated) and np.median(np.diff(isolated)) == 5:
            return {"pattern": "pulldown_24_in_30", "effective_fps_hint": 24, "dup_ratio": round(dup_ratio, 3)}
    if 1.8 <= median_step <= 2.2 and dup_ratio > 0.4:
        return {"pattern": "on_twos", "dup_ratio": round(dup_ratio, 3)}
    if median_step >= 2.5:
        return {"pattern": "stepped", "median_step_frames": median_step, "dup_ratio": round(dup_ratio, 3)}
    return {"pattern": "on_ones", "dup_ratio": round(dup_ratio, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--cut-threshold", type=float, default=40.0,
                    help="mittlere Pixeldifferenz (0-255), ab der ein Frame als Schnitt gilt")
    ap.add_argument("--bpm", type=float, help="optional: Abweichung der Schnitte vom Beat-Raster melden")
    args = ap.parse_args()

    fps = probe_fps(args.video)
    frames = read_frames(args.video)
    energy = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2, 3))
    energy = np.concatenate([[0.0], energy])

    over = energy > args.cut_threshold
    # Mehrere Frames in Folge ueber der Schwelle sind schnelle Bewegung (z. B. Zoom mit Motion Blur), kein Schnitt
    cuts = [int(i) for i in np.where(over)[0]
            if not over[max(i - 1, 0):i].any() and not over[i + 1:i + 2].any()]
    bounds = [0] + cuts + [len(frames)]
    shots = [{"in": a, "out": b - 1, "frames": b - a, "seconds": round((b - a) / fps, 3)}
             for a, b in zip(bounds[:-1], bounds[1:]) if b > a]

    # Schnittframes als Bewegung werten, damit die 5er-Phase fuer die Pulldown-Erkennung erhalten bleibt
    inner = energy.copy()
    inner[cuts] = 255.0
    result = {
        "file": args.video,
        "fps": round(fps, 3),
        "frames": len(frames),
        "duration_s": round(len(frames) / fps, 3),
        "frame_rate_pattern": duplicate_pattern(inner[1:]),
        "cuts": cuts,
        "shots": shots,
        "energy": [round(float(e), 2) for e in energy],
    }
    if args.bpm:
        beat = 60.0 / args.bpm * fps

        def offbeat(c, phase):
            r = (c - phase) % beat
            return min(r, beat - r)

        # Beat-Phase so waehlen, dass die Schnitte im Mittel am besten auf dem Raster liegen
        phase = min(np.arange(0, beat, 0.25), key=lambda ph: sum(offbeat(c, ph) for c in cuts))
        result["beat_frames"] = round(beat, 2)
        result["beat_phase_frames"] = round(float(phase), 2)
        result["cut_offbeat_frames"] = [round(offbeat(c, phase), 2) for c in cuts]
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
