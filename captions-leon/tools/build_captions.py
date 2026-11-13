#!/usr/bin/env python3
"""Turn the raw transcript (timecode chunks) into a cleaned caption script.

Input : transkript_leon.txt  (HH:MM:SS:FF - HH:MM:SS:FF / text, 60 fps timecode)
Output: captions.json         (speaker turns -> chunks with start/end frame + text)

All text corrections live in FIXES / DROP / SPEAKERS below, so they can be
reviewed and changed without touching the renderer.
"""
import json
import re
import sys
from pathlib import Path

FPS = 60  # frame field in the transcript runs 00..59

# chunk index -> corrected text (index = order in the transcript, 0-based)
FIXES = {
    5: "bei Renfert?",            # ASR: "Rennpferd"
    7: "Fachlageristen",          # "Fach" + "Lageristen" (8 is merged in)
    22: "Jedes Werk",
    27: "Werk\u00a05:",
    28: "Warenannahme,",
    29: "Werk\u00a01:",
    30: "Produktionslager.",
    32: "Welche Teile",
    37: "und wohin gehen",
    39: "die Teile?",
    47: "Die gehen",
    51: "Werkzeuge,",
    55: "Hauptsächlich",
    58: "und Hubwagen,",
    60: "Scanner.",
    61: "Im Laufe",
    65: "Staplerführerschein",
    69: "den Staplerschein",
    72: "den Hochregalstapler darf",
    75: "18\u00a0machen.",
    76: "Das ist jetzt",
    84: "hier\u00a018",
    78: "Hochregalstapler,",
    79: "das heißt,",
    91: "Ja.",
    94: "Spaß,",
    95: "bisher",
    96: "in der Ausbildung?",
    100: "alles.",
    107: "könnte.",
    115: "Man hat",
    119: "viel",
    124: "Teamarbeit.",
}

# chunks that are removed (stutters / duplicates).  Their time is merged into
# the neighbour named here: "next" or "prev".
DROP = {
    8: "prev",    # "Lageristen"      -> part of "Fachlageristen"
    31: "next",   # "Was, welche,"    -> stutter
    38: "prev",   # "Wohin gehen"     -> folded into "und wohin gehen"
    50: "next",   # "hier für"        -> keep "Was sind das ... für Werkzeuge"
    54: "next",   # "Hauptsächlich."  -> duplicate
    66: "prev",   # "Führerschein"    -> part of "Staplerführerschein"
    73: "prev",   # "Stapler darf"    -> part of "den Hochregalstapler darf"
    120: "prev",  # "viel" (2x)
    123: "next",  # "Team" (stutter before "Teamarbeit")
}
# 50 "hier für" is dropped, so 49 needs the word "hier"
FIXES[49] = "Was sind das hier für"

# speaker turns: (first chunk index, speaker)  Q = Interviewer, A = Leon
SPEAKERS = [
    (0, "Q"), (6, "A"), (12, "Q"), (17, "A"), (31, "Q"), (40, "A"),
    (49, "Q"), (54, "A"), (61, "Q"), (68, "A"), (76, "Q"), (91, "A"),
    (92, "Q"), (97, "A"),
]

TC = re.compile(r"(\d\d):(\d\d):(\d\d):(\d\d)\s*-\s*(\d\d):(\d\d):(\d\d):(\d\d)")


def tc_to_frame(h, m, s, f):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * FPS + int(f)


def parse(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    chunks, i = [], 0
    while i < len(lines):
        m = TC.match(lines[i].strip())
        if m:
            g = m.groups()
            text = lines[i + 1].strip() if i + 1 < len(lines) else ""
            chunks.append({"start": tc_to_frame(*g[:4]), "end": tc_to_frame(*g[4:]), "text": text})
            i += 2
        else:
            i += 1
    return chunks


def speaker_of(idx):
    who = SPEAKERS[0][1]
    for first, s in SPEAKERS:
        if idx >= first:
            who = s
    return who


def build(chunks):
    items = []
    for idx, c in enumerate(chunks):
        items.append({**c, "idx": idx, "speaker": speaker_of(idx),
                      "text": FIXES.get(idx, c["text"]), "drop": idx in DROP})
    # merge dropped chunk time into neighbour (same speaker turn)
    for k, it in enumerate(items):
        if not it["drop"]:
            continue
        direction = DROP[it["idx"]]
        step = 1 if direction == "next" else -1
        j = k + step
        while 0 <= j < len(items) and items[j]["drop"]:
            j += step
        tgt = items[j]
        tgt["start"] = min(tgt["start"], it["start"])
        tgt["end"] = max(tgt["end"], it["end"])
    kept = [it for it in items if not it["drop"]]

    turns = []
    for it in kept:
        if not turns or turns[-1]["speaker"] != it["speaker"]:
            turns.append({"speaker": it["speaker"],
                          "name": "Leon" if it["speaker"] == "A" else "Interviewer",
                          "chunks": []})
        turns[-1]["chunks"].append({"start": it["start"], "end": it["end"], "text": it["text"]})
    return {"fps": FPS, "source": "transkript_leon.txt", "turns": turns}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "transkript_leon.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "captions.json"
    data = build(parse(src))
    Path(dst).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for t in data["turns"]:
        print(f"[{t['name']:>11}] " + " ".join(c["text"] for c in t["chunks"]))
