# Logo „Videovollautomat“

Signet: ein Automat mit Bildschirm (Play), Zahnrad-Knopf und Ausgabeschacht, aus dem
ein fertiger Filmstreifen kommt. Wortmarke in Anton, „VIDEO“ auf pinkem Balken,
Claim in Space Mono. Stil A aus `motion-spec/` (Neo-Brutalismus): schwarze Kontur,
harter Versatzschatten, Volltonfarben.

| Datei | Einsatz |
|---|---|
| `videovollautomat_logo.svg` / `.png` | Hauptlogo quer, transparenter Hintergrund |
| `videovollautomat_logo_hell.svg` / `.png` | Hauptlogo auf Off-White `#F4F4F0` |
| `videovollautomat_logo_dunkel.svg` / `.png` | Negativ auf `#121212` |
| `videovollautomat_signet.svg` / `.png` | Signet allein (App-Icon, Avatar, Favicon) |
| `videovollautomat_endcard_9x16.svg` / `.png` | Outro-Endcard 1080×1920 |

Alle Schriften sind in Pfade umgewandelt, die SVGs brauchen also keine installierten Fonts.
PNGs sind in doppelter Auflösung gerendert.

## Farben

| Rolle | Hex |
|---|---|
| Kontur / Text | `#000000` |
| Gehäuse | `#FFC900` |
| Bildschirm, VIDEO-Balken | `#FF90E8` |
| Zahnrad | `#90A8ED` |
| Tasten | `#23A094`, `#FF7051` |
| Hintergrund hell / dunkel | `#F4F4F0` / `#121212` |

## Neu erzeugen

```
pip install fonttools brotli
python3 logo/build_logo.py
NODE_PATH=$(npm root -g) node logo/render_png.js logo 2
```
