# Outro „KOMM INS TEAM“ (Renfert Recruiting)

`export/Renfert_Outro_KOMM_INS_TEAM_9x16.mp4`: 1080×1920, 60 fps, 5,0 s, H.264 (BT.709)

## Ablauf

| Zeit | Was passiert |
|---|---|
| 0,00–0,45 s | Drei diagonale Farbbänder (dunkelrot, hellrot, Renfert-Rot) wischen durchs Bild, Rot bleibt stehen |
| 0,40–0,70 s | **KOMM** schießt von links rein: Skew, Motion Blur, leichter Überschwinger |
| 0,62–0,85 s | **INS** knallt aus 3-facher Größe rein, Kamera-Shake |
| 0,82–1,25 s | Weißer Kasten wischt von rechts auf, **TEAM** (rot) steigt darin hoch |
| 1,10–1,35 s | „///“-Akzent poppt auf |
| 1,35–1,95 s | Logo: Bögen ziehen sich von der Mitte nach außen auf, Schriftzug steigt hoch |
| ab 2,0 s | Stand mit subtiler Bewegung: Text schwebt und atmet, Hintergrundstreifen driften, langsamer Push-in |

- Farbe: Hintergrund `#C8102E`, Schrift Weiß, „TEAM“ in Rot auf Weiß
- Schrift: Netto Pro Black (aus `../captions-leon/fonts/`, wegen Lizenz nicht im Repo)
- Logo: aus `assets/renfert_logo_source.png` (562×355) extrahiert, 4-fach hochskaliert
  und mit geschärften Kanten neu aufgebaut. Mit einem Vektor-Logo (SVG/EPS) wird es noch exakter.

## Neu rendern

```bash
python3 tools/render_outro.py                  # 5 s
python3 tools/render_outro.py --duration 8     # längerer Stand am Ende
python3 tools/render_outro.py --still 1.0 3.0  # Einzelbilder prüfen
```
