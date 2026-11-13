# Dynamische Captions: Azubi-Interview Leon (Renfert)

Animierte Untertitel mit Alpha-Kanal, direkt über das Interview-Video legbar.

## Downloads (`export/`)

| Datei | Wofür |
|---|---|
| `Leon_Captions_9x16_ProRes4444.mov` | **Schnitt-Master 9:16** (1080×1920, 60 fps, ProRes 4444 mit Alpha). Premiere, After Effects, Resolve, Final Cut |
| `Leon_Captions_16x9_ProRes4444.mov` | dasselbe in 16:9 (1920×1080) |
| `Leon_Captions_*_ProRes4444_compact.mov` | ProRes 4444, stärker komprimiert (~290 MB statt ~500 MB), optisch identisch |
| `Leon_Captions_*_Animation_alpha.mov` | QuickTime Animation (RLE), verlustfrei, ~120 MB |
| `Leon_Captions_*_alpha.webm` | VP9 mit Alpha, klein, für Web/Browser/CapCut |
| `Leon_Captions_*_preview.mp4` | nur zur Ansicht: Captions auf grauem Hintergrund (ohne Alpha) |
| `Leon_Captions.srt` | bereinigter Text als SRT, z. B. für YouTube/LinkedIn |

> Die `.mov`-Dateien sind wegen des GitHub-Limits von 100 MB pro Datei nicht im Repo.
> Neu erzeugen mit `tools/render_captions.py` und den ffmpeg-Befehlen unten.

Timing: Die Timecodes im Transkript sind 60-fps-Timecodes (Frame-Feld 00–59).
Die Caption-Datei startet bei 00:00:00:00 und gehört an den Anfang des Interview-Clips.

## Look

- **Leon (Antworten):** Netto Pro Bold, weiß mit weichem Schatten. Ein
  Renfert-roter Kasten springt von Wort zu Wort, synchron zum Sprechen.
- **Interviewer (Fragen):** Netto Pro Regular, kleiner, dunkel auf weißem Balken
  mit roter Kante. Der Balken wächst Wort für Wort mit.
- Wörter erscheinen mit Fade, kurzem Anstieg und leichtem Scale (Expo-Out,
  10 Frames). Seiten blenden in 7 Frames aus. Max. 2 Zeilen, Umbrüche an
  Sprechpausen und Satzzeichen.

Farben, Größen und Timings stehen oben in `tools/render_captions.py` (`STYLE`,
`FORMATS`). Rot ist aktuell `#E2001A` und muss mit dem CI-Wert abgeglichen werden.

## Schrift Netto Pro

Netto Pro ist eine lizenzpflichtige Schrift und liegt nicht im Repo. Wenn
`fonts/` keine Netto-Dateien enthält, rendert das Skript mit **Inter** als
Ersatz und gibt eine Warnung aus.

Für den finalen Export: `NettoPro-Bold.otf` und `NettoPro-Regular.otf` (oder
Book) nach `fonts/` legen und neu rendern. Die Dateien werden automatisch erkannt.

## Neu rendern

```bash
python3 tools/build_captions.py transkript_leon.txt captions.json   # Text/Timing aus Transkript
python3 tools/render_captions.py --format 9x16                      # oder 16x9 / 1x1
python3 tools/render_captions.py --still 600 --still-bg             # Einzelbild prüfen
```

Kompakte Master aus dem ProRes-Export:

```bash
ffmpeg -i export/Leon_Captions_9x16_ProRes4444.mov -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -alpha_bits 8 -qscale:v 13 -vendor apl0 export/Leon_Captions_9x16_ProRes4444_compact.mov
```

```bash
ffmpeg -i export/Leon_Captions_9x16_ProRes4444.mov -c:v qtrle -pix_fmt argb export/Leon_Captions_9x16_Animation_alpha.mov
```

Benötigt: Python 3 mit Pillow und NumPy sowie ffmpeg (prores_ks, libvpx-vp9, libx264).

## Textkorrekturen gegenüber dem Rohtranskript

Alle Korrekturen stehen in `tools/build_captions.py` (`FIXES`, `DROP`, `SPEAKERS`):

- „Rennpferd“ → **Renfert**
- „Fach Lageristen“ → Fachlageristen, „Waren Annahme“ → Warenannahme,
  „Stapler Führerschein“ → Staplerführerschein, „Hochregal Stapler“ → Hochregalstapler
- Stotterer und Doppelungen entfernt („Was, welche, welche“, „Hauptsächlich. Hauptsächlich“,
  „für für“, „viel, viel“, „Team Teamarbeit“); die Zeit geht an das Nachbarwort
- Sprecherwechsel Interviewer/Leon von Hand zugeordnet. Der Schlussteil
  („Also zusammenfassend …“) ist Leon zugeordnet.
