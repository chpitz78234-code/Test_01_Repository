# Captions „Merry Christmas – Renfert“ (Hochformat, Alphakanal)

Elegant animierte Untertitel in **Great Vibes** als transparentes Overlay für Premiere Pro.

| Datei | Inhalt |
|---|---|
| `captions_alpha_animation.mov` | **Overlay zum Einfügen**: 1080×1920, 30 fps, 24 s, QuickTime Animation (RGBA, verlustfrei, Alpha). Mit 108 MB zu groß fürs Repo (GitHub-Limit 100 MB), daher nicht eingecheckt: mit `render_captions.py --codec animation` in ca. 30 s neu erzeugen. |
| `preview_dark.mp4` | Vorschau auf dunklem Grund mit Voiceover (nur zum Ansehen) |
| `captions.srt` | Dieselben Zeilen als SRT (z. B. für Plattform-Untertitel) |
| `timing.json` | Wortgenaue Zeiten, die der Renderer verwendet |
| `render_captions.py` | Renderer (Python + Pillow + ffmpeg) |
| `audio/voiceover.mp3`, `fonts/GreatVibes-Regular.ttf` | Quellen |

## In Premiere Pro

1. `captions_alpha_animation.mov` importieren und auf eine Spur **über** dem Video ablegen.
2. Am Anfang des Voiceovers ausrichten: Frame 0 des Overlays = Sekunde 0 von `voiceover.mp3`.
3. Der Alphakanal wird automatisch erkannt. Falls nicht: Clip rechtsklicken → *Ändern → Filmmaterial interpretieren → Alphakanal: Straight*.
4. Position bzw. Größe bei Bedarf über *Bewegung* anpassen. Der Textblock sitzt um y ≈ 1390 px (unteres Drittel, über der UI-Zone von Reels/TikTok).

## Look & Animation

- Schrift: Great Vibes 112 px, Champagner-Gold-Verlauf (#FFFAF0 → #EED396), warmer Glow und weicher Schatten. Dadurch lesbar auf hellem wie dunklem Material.
- Jedes Wort erscheint synchron zur Stimme: Es steigt 22 px auf, wird von unscharf zu scharf und blendet ein (0,6 s, Ease-out). Jedes Wort startet 0,1 s vor dem gesprochenen Einsatz.
- Zeilenwechsel in den Sprechpausen: Die Zeile steigt leicht weiter auf, verschwimmt und blendet aus (0,34 s).
- Finale: „Merry Christmas and a bright new year / from all of us at Renfert.“ bleiben gemeinsam stehen. Ein Lichtschimmer läuft darüber, dann blendet alles bei 23,0–23,9 s aus.

## Text und Timing

| Start | Zeile |
|---|---|
| 0,10 s | To every hand that shapes a smile, |
| 3,12 s | in lab and practice, mile by mile. |
| 6,58 s | Your skill and trust have made us strong. |
| 9,76 s | It's you we've built for all year long. |
| 12,58 s | Now candles glow and work can rest. |
| 15,43 s | May this season bring the best. |
| 17,91 s | Merry Christmas and a bright new year |
| 20,52 s | from all of us at Renfert. |

Die Wortzeiten stammen aus einer Spracherkennung (Parakeet TDT 0.6B v3). Pro Zeile wurden sie an die mit ffmpeg `silencedetect` gemessenen Sprechpausen angeglichen.

## Neu rendern

```bash
pip install pillow
python3 render_captions.py --codec animation --preview   # Animation-.mov + Vorschau
python3 render_captions.py                               # ProRes 4444 + Alpha (~300 MB)
python3 render_captions.py --stills 2.0 9.0 22.9         # Kontrollbilder in stills/
```

Text oder Zeiten ändern: `timing.json` bearbeiten. Look ändern: Konstanten oben in `render_captions.py` (Schriftgröße, Farben, Position, Animationsdauern).
