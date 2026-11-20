# Renfert Captions – Teaser spectra / IDS 2027

Animierte Untertitel mit Alphakanal für Premiere, 1080×1920, 30 fps, 59,67 s.
Weiß + Renfert-Rot `#C8102E`, Schrift Netto Pro Black/Bold.

| Datei | Inhalt |
|---|---|
| `output/Renfert_Captions_1080x1920_alpha_PNG.mov` | Captions, verlustfrei, Alpha (PNG-Codec) |
| `output/Renfert_NameTags_1080x1920_alpha_PNG.mov` | Bauchbinden Sören Hug / Sascha Hein (0–7,5 s) |
| `output/Renfert_Captions.srt` | Gleicher Text als SRT |
| `output/Vorschau_mit_Ton_540x960.mp4` | Kontrollvorschau mit Ton |

ProRes-4444-Versionen werden lokal mit erzeugt, sind aber zu groß für GitHub (`.gitignore`).

**Premiere:** beide .mov auf Spuren über dem Video bei 00:00 anlegen, Ton-Start = 00:00.

## Anpassen
- Text, Umbruch-Blöcke und rote Boxen: `chunks.txt` (`*Wort*` = rote Box). Wortanzahl muss gleich bleiben.
- Timing: `words_final.json` (Whisper large-v3 Wortzeiten).
- Größe/Position: Konstanten oben in `render_captions.py` (`FONT_SIZE`, `CENTER_Y`).

```bash
python3 render_captions.py --fonts <ordner mit NETTOPRO-*.OTF> --words words_final.json --chunks chunks.txt --out output --duration 59.67
```
Die Schriftdateien liegen bewusst nicht im Repo (Lizenz).
