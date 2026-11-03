#!/usr/bin/env python3
"""Automated pipeline for the Renfert Christmas reel.

Order (as in the storyboard): audio -> reference images -> keyframes -> video -> edit.

  python3 tools/pipeline.py resolve      # expand [STYLE]/[ORB]/... -> build/jobs.json + build/PROMPTS.md
  python3 tools/pipeline.py voiceover    # ElevenLabs TTS with timestamps -> build/voiceover.mp3 + build/timecodes.json
  python3 tools/pipeline.py retime       # scene lengths from build/timecodes.json -> build/timing.json (+ jobs.json updated)

`voiceover` needs ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in the environment.
If the voiceover is made by hand in the ElevenLabs UI, write build/timecodes.json yourself
(format: {"lines": [{"text": ..., "start": s, "end": s}, ...]}) and run `retime`.

Only the Python standard library is used.
"""

from __future__ import annotations

import base64
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scenes.json"
BUILD = ROOT / "build"
PLACEHOLDER = re.compile(r"\[(STYLE|ORB|STEP|ICON|NEGATIVE)\]")


def load() -> dict:
    return json.loads(SRC.read_text(encoding="utf-8"))


def expand(text: str, blocks: dict) -> str:
    return PLACEHOLDER.sub(lambda m: blocks[m.group(1)], text)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- resolve

def gen_duration(target: float, vmodel: dict) -> int:
    return int(min(vmodel["max_duration_s"], max(vmodel["min_duration_s"], math.ceil(target))))


def build_jobs(spec: dict, timing: dict | None = None) -> dict:
    blocks = spec["blocks"]
    img, vid = spec["models"]["image"], spec["models"]["video"]
    durations = {s["id"]: s["duration_s"] for s in spec["scenes"]}
    if timing:
        durations.update({s["id"]: s["duration_s"] for s in timing["scenes"]})

    jobs = []
    step = 0

    def add(job):
        nonlocal step
        step += 1
        job["step"] = step
        jobs.append(job)

    for r in spec["references"]:
        add({"id": r["id"], "phase": "2-referenzbilder", "kind": "image", "model": img["id"],
             "aspect_ratio": img["aspect_ratio"], "params": img["params"], "inputs": {},
             "prompt": expand(r["prompt"], blocks), "variants": 4, "depends_on": [],
             "output": f"refs/{r['id']}.png"})

    prev = None
    for k in spec["keyframes"]:
        refs = list(k["refs"])
        inputs = {img["reference_role"]: ([prev] if prev else []) + refs}
        add({"id": k["id"], "phase": "3-keyframes", "kind": "image", "model": img["id"],
             "aspect_ratio": img["aspect_ratio"], "params": img["params"], "inputs": inputs,
             "prompt": expand(k["prompt"], blocks), "variants": 2,
             "depends_on": inputs[img["reference_role"]],
             "note": "Image-to-Image aus dem vorherigen Keyframe" if prev else "Text-to-Image",
             "output": f"keyframes/{k['id']}.png"})
        prev = k["id"]

    warnings = []
    for s in spec["scenes"]:
        target = float(durations[s["id"]])
        gen = gen_duration(target, vid)
        speed = round(gen / target, 3)
        if speed > 1.35:
            warnings.append(f"{s['id']}: Ziel {target:.2f}s, Modell-Minimum {gen}s -> Faktor {speed}x schneller. "
                            "Im Schnitt eher kürzen/überblenden als stark beschleunigen.")
        add({"id": s["id"], "phase": "4-video", "kind": "video", "model": vid["id"],
             "aspect_ratio": vid["aspect_ratio"], "params": {**vid["params"], "duration": gen},
             "inputs": {"start_image": s["start_frame"], "end_image": s["end_frame"]},
             "prompt": expand(s["video_prompt"] + " " + "[NEGATIVE]", blocks),
             "variants": vid["variants"], "depends_on": sorted({s["start_frame"], s["end_frame"]}),
             "target_duration_s": round(target, 3), "speed_factor": speed,
             "line": s["line"], "output": f"video/{s['id']}_v{{n}}.mp4"})

    return {"project": spec["project"], "format": spec["format"],
            "timing_source": "voiceover" if timing else "storyboard-richtwerte",
            "total_target_s": round(sum(float(durations[s["id"]]) for s in spec["scenes"]), 2),
            "warnings": warnings, "jobs": jobs}


def prompts_md(plan: dict) -> str:
    lines = [f"# {plan['project']} – aufgelöste Prompts", "",
             f"Timing-Quelle: **{plan['timing_source']}** · Gesamtlänge Ziel: **{plan['total_target_s']} s** · "
             f"Format {plan['format']['aspect']} ({plan['format']['width']}×{plan['format']['height']})", "",
             "Generiert von `tools/pipeline.py resolve` aus `scenes.json` – nicht von Hand bearbeiten.", ""]
    if plan["warnings"]:
        lines += ["## Hinweise", ""] + [f"- {w}" for w in plan["warnings"]] + [""]
    phase = None
    for j in plan["jobs"]:
        if j["phase"] != phase:
            phase = j["phase"]
            lines += [f"## {phase}", ""]
        meta = [f"Modell `{j['model']}`", f"{j['aspect_ratio']}"]
        if j["kind"] == "video":
            meta += [f"Dauer {j['params']['duration']} s (Ziel {j['target_duration_s']} s)",
                     f"Start `{j['inputs']['start_image']}` → Ende `{j['inputs']['end_image']}`"]
        elif j["depends_on"]:
            meta.append("Referenzen: " + ", ".join(f"`{d}`" for d in j["depends_on"]))
        meta.append(f"{j['variants']} Varianten")
        lines += [f"### {j['step']}. {j['id']}" + (f" – „{j['line']}“" if j.get("line") else ""), "",
                  " · ".join(meta), "", "```text", j["prompt"], "```", ""]
    return "\n".join(lines)


def cmd_resolve(timing: dict | None = None) -> None:
    spec = load()
    if timing is None and (BUILD / "timing.json").exists():
        timing = json.loads((BUILD / "timing.json").read_text(encoding="utf-8"))
    plan = build_jobs(spec, timing)
    write_json(BUILD / "jobs.json", plan)
    (BUILD / "PROMPTS.md").write_text(prompts_md(plan), encoding="utf-8")
    print(f"{len(plan['jobs'])} Jobs -> {BUILD/'jobs.json'}  (Timing: {plan['timing_source']}, "
          f"{plan['total_target_s']} s)")
    for w in plan["warnings"]:
        print("  Hinweis:", w)


# --------------------------------------------------------------------------- voiceover

def cmd_voiceover() -> None:
    key, voice = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        sys.exit("ELEVENLABS_API_KEY und ELEVENLABS_VOICE_ID setzen (Stimme nach dem Profil in scenes.json wählen).")
    vo = load()["voiceover"]
    body = json.dumps({"text": vo["text"], "model_id": vo["model_id"],
                       "voice_settings": vo["voice_settings"]}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_192",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs {e.code}: {e.read().decode(errors='replace')[:500]}")

    BUILD.mkdir(exist_ok=True)
    (BUILD / "voiceover.mp3").write_bytes(base64.b64decode(data["audio_base64"]))
    align = data.get("normalized_alignment") or data["alignment"]
    tc = timecodes_from_alignment(vo["lines"], align)
    write_json(BUILD / "timecodes.json", tc)
    print(f"voiceover.mp3 + timecodes.json geschrieben ({len(tc['lines'])} Zeilen).")
    cmd_retime()


def timecodes_from_alignment(lines: list[str], align: dict) -> dict:
    chars = align["characters"]
    starts, ends = align["character_start_times_seconds"], align["character_end_times_seconds"]
    joined = "".join(chars)
    out, pos = [], 0
    for text in lines:
        i = joined.find(text, pos)
        if i < 0:
            raise ValueError(f"Zeile nicht in der Alignment-Antwort gefunden: {text!r}")
        j = i + len(text) - 1
        entry = {"text": text, "start": round(starts[i], 3), "end": round(ends[j], 3), "phrases": {}}
        k = joined.find("a smile", i, j + 1)
        if k >= 0:
            entry["phrases"]["a smile"] = round(starts[k], 3)
        out.append(entry)
        pos = j + 1
    return {"lines": out}


# --------------------------------------------------------------------------- retime

def cmd_retime() -> None:
    spec = load()
    path = BUILD / "timecodes.json"
    if not path.exists():
        sys.exit("build/timecodes.json fehlt – erst `voiceover` laufen lassen oder Datei von Hand anlegen.")
    lines = json.loads(path.read_text(encoding="utf-8"))["lines"]
    vo = spec["voiceover"]
    off = vo["first_line_at_s"] - lines[0]["start"]

    def at(cue: str) -> float:
        if cue == "start":
            return 0.0
        if cue == "mid_preroll":
            return vo["first_line_at_s"] / 2
        kind, *rest = cue.split(":")
        line = lines[int(rest[0])]
        if kind == "line":
            return line["start"] + off
        if kind == "phrase":  # fallback for hand-written timecodes: 60 % into the line
            t = line.get("phrases", {}).get(rest[1])
            return (t if t is not None else line["start"] + 0.6 * (line["end"] - line["start"])) + off
        raise ValueError(cue)

    starts = [at(s["cue"]) for s in spec["scenes"]]
    end = lines[-1]["end"] + off + vo["logo_tail_s"]
    scenes = []
    for n, s in enumerate(spec["scenes"]):
        stop = starts[n + 1] if n + 1 < len(starts) else end
        scenes.append({"id": s["id"], "start_s": round(starts[n], 3), "end_s": round(stop, 3),
                       "duration_s": round(stop - starts[n], 3)})
    timing = {"audio_offset_s": round(off, 3), "total_s": round(end, 3), "scenes": scenes}
    write_json(BUILD / "timing.json", timing)
    print(f"timing.json: Audio um {off:+.2f} s versetzt, Gesamtlänge {end:.2f} s")
    for s in scenes:
        print(f"  {s['id']}: {s['start_s']:6.2f} – {s['end_s']:6.2f}  ({s['duration_s']:.2f} s)")
    cmd_resolve(timing)


if __name__ == "__main__":
    cmds = {"resolve": cmd_resolve, "voiceover": cmd_voiceover, "retime": cmd_retime}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
