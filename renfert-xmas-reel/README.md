# Renfert Weihnachtsreel – Pipeline

Automatisierung zum Storyboard „Renfert Weihnachtsreel – Storyboard & Prompt Sheet“ (Claude Docs).
Reihenfolge wie im Dokument: **Audio → Referenzbilder → Keyframes → Video → Schnitt**.

| Datei | Inhalt |
| --- | --- |
| `scenes.json` | Quelle: Stilblöcke, Modelle, Voiceover, Referenzbilder, Keyframes K0–K8, Szenen S1–S9 (mit Platzhaltern) |
| `tools/pipeline.py` | `resolve`, `voiceover`, `retime` (nur Python-Standardbibliothek) |
| `build/jobs.json` | 24 Jobs in Ausführungsreihenfolge mit Modell, Parametern, Abhängigkeiten, aufgelöstem Prompt |
| `build/PROMPTS.md` | dieselben Prompts zum Kopieren |
| `build/refs/`, `build/keyframes/` | Referenzbilder und Keyframes K0–K8 (Vorschauen, Higgsfield-Job-IDs) |
| `build/video/` | ausgewählte Clips (Seedance 1.5 Pro, 720p) + `cut.json` (Auswahl, Ziellängen, Überblendungen) |
| `tools/rough_cut.py` | baut `build/rohschnitt.mp4` aus `cut.json` |
| `build/rohschnitt.mp4` | Rohschnitt ohne Ton |
| `hyperframes/` | Endschnitt als HyperFrames-Projekt: Clips, Ton-Mix, Titel, Wort-für-Wort-Captions, Goldpartikel, Abschluss |
| `tools/prepare_hyperframes.py` | schneidet Clips auf die Musiklänge, mischt Stimme + Musik, berechnet Caption-Timing aus den Sprechpausen |
| `build/renfert_weihnachtsreel.mp4` | fertiges Reel (1080×1920, 31,8 s, mit Ton) |

## Endschnitt (HyperFrames)

```bash
python3 tools/prepare_hyperframes.py --voice hyperframes/assets/audio/voiceover_charlotte.mp3 \
  --music hyperframes/assets/audio/music_snowball_festival_preview.mp3
cd hyperframes && npx hyperframes@0.9.8 check . && npx hyperframes@0.9.8 render -o ../build/renfert_weihnachtsreel.mp4
```

Szenenschnitte und Caption-Text stehen oben in `tools/prepare_hyperframes.py`; Gestaltung und Animation in `hyperframes/index.html`.

## Ablauf

```bash
python3 tools/pipeline.py voiceover   # braucht ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID
```

Erzeugt `build/voiceover.mp3` und `build/timecodes.json` (Zeitstempel pro Zeile über den
`with-timestamps`-Endpunkt) und ruft danach automatisch `retime` auf: Szenenlängen folgen der
Sprache, die erste Zeile liegt bei 6,0 s, nach der letzten Zeile 4 s Logo-Stand.
Voiceover von Hand in ElevenLabs erstellt? `build/timecodes.json` selbst anlegen und
`python3 tools/pipeline.py retime` ausführen.

Danach die Jobs aus `build/jobs.json` der Reihe nach in Higgsfield abarbeiten:

1. **Referenzbilder** R_STEP, R_ORB, R_ICON1–4 (`nano_banana_pro`, 9:16) – bestes Bild je Element festlegen.
2. **Keyframes** K0–K8 – K1–K8 jeweils mit dem vorherigen Keyframe + den genannten Referenzen als `image_references`.
3. **Video** S1–S9 (`seedance_2_0`, 9:16, 1080p, ohne Ton) mit `start_image`/`end_image`, 3 Varianten pro Szene.
4. **Schnitt**: 4–6 Frames überblenden, Clips per `speed_factor` an `target_duration_s` anpassen,
   Rot in allen Clips auf Renfert-Rot **#C8102E** (RGB 200, 16, 46) angleichen.

## Offene Punkte

- S3 und S4 sind am gesprochenen Text gemessen kürzer als die 4 s Mindestlänge von `seedance_2_0`.
  Im Schnitt kürzen statt stark beschleunigen, oder S3+S4 als einen Clip K1→K3 generieren.
- Aussprache „Renfert“ nach dem ersten Voiceover prüfen.
