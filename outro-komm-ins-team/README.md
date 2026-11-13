# Outro „KOMM INS TEAM“ (Renfert Recruiting)

`export/Renfert_Outro_KOMM_INS_TEAM_9x16.mp4`: 1080×1920, 60 fps, 5,0 s, H.264 (BT.709)

## Ablauf

| Zeit | Was passiert |
|---|---|
| 0,00–0,45 s | Drei diagonale Farbbänder (dunkelrot, hellrot, Renfert-Rot) wischen durchs Bild, Rot bleibt stehen |
| 0,40–0,70 s | **KOMM** schießt von links rein: Skew, Motion Blur, leichter Überschwinger, Konfetti-Burst |
| 0,62–0,85 s | **INS** knallt aus 3-facher Größe rein (mit Drehung), Kamera-Shake, Konfetti-Burst |
| 0,82–1,25 s | Gekippter weißer Kasten (−4°, federt ein) wischt von rechts auf, **TEAM** (rot) steigt darin hoch, Konfetti-Burst |
| 1,10–1,35 s | „///“-Akzent poppt auf |
| 1,30–2,00 s | Logo **immer im roten Kasten** mit Schlagschatten: Kasten poppt mit Wackler rein, Bögen ziehen sich auf, Schriftzug steigt hoch, Konfetti-Burst |
| Bursts | Sternchen (5- und 4-zackig), Konfetti-Kringel, Wellen, Punkte und Ringe in Weiß, Rosa und Dunkelrot fliegen weg, drehen sich und verschwinden bis ca. 2,9 s. Sie fliegen hinter dem Logo vorbei, nie darüber |
| ab 2,0 s | Stand mit subtiler Bewegung: Text schwebt und atmet, Hintergrundstreifen driften, langsamer Push-in |

- Farbe: Hintergrund `#C8102E`, Schrift Weiß, „TEAM“ in Rot auf Weiß
- Schrift: Netto Pro Black (aus `../captions-leon/fonts/`, wegen Lizenz nicht im Repo)
- Logo: aus `assets/renfert_logo_source.png` (562×355) mit rotem Kasten neu aufgebaut, 4-fach
  hochskaliert und mit geschärften Kanten. Die Logo-Elemente werden nie freigestellt. Mit einem Vektor-Logo (SVG/EPS) wird es noch exakter.

## Neu rendern

```bash
python3 tools/render_outro.py                  # 5 s
python3 tools/render_outro.py --duration 8     # längerer Stand am Ende
python3 tools/render_outro.py --still 1.0 3.0  # Einzelbilder prüfen
```
