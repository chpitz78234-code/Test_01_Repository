# Team Italia – Overlay-Animationen

Animationen für die **obere Hälfte** eines 9:16-Videos (1080×1920) über den Talking Heads.
Format **1080×960**, **25 fps** (wie die Timecodes im Transkript), Hintergrund Weiß.

Look: weißes Grid, das sich langsam bewegt, mit weichen roten Farbflächen dahinter.
Inhalte in Schwarz und `#c8102e`, Milchglas-Karten (Backdrop-Blur) und weiche Schlagschatten.
Schrift: **Netto Pro** (Regular, Bold, Black).
Alle MP4s enthalten passende **Soundeffekte**, die zusätzlich als eigene Spur in `renders/sfx_komplett.wav` liegen.
Die Easing-Kurven stammen aus `motion-spec/motion-spec.json` (`expo_out`, `back_out`, `whip_in`).

## Dateien

| Datei | Inhalt |
|---|---|
| `renders/komplett.mp4` | Alle Szenen am Stück, 0:00–1:49.10. Auf Timecode 00:00:00:00 anlegen, dann passt das Timing zum Transkript. |
| `renders/01_massimo.mp4` … `07_outro.mp4` | Einzelne Szenen zum freien Platzieren |
| `renders/sfx_komplett.wav` | Nur die Soundeffekte, 48 kHz Stereo, ab 00:00:00:00, für eine eigene Spur im Schnitt |
| `index.html` | Quelle aller Animationen und Vorschau im Browser (Szenen-Buttons, Scrubber) |
| `render.js` | Rendert `index.html` Frame für Frame zu MP4 und legt den Ton an |
| `sfx.py` | Erzeugt die Soundeffekte synthetisch und mischt sie zur Tonspur |
| `fonts/` | Hier müssen die Netto-Pro-OTFs liegen (nicht im Repo, siehe unten) |

## Szenen und Timing

| # | Szene | In | Out | Inhalt |
|---|---|---|---|---|
| 1 | Massimo | 00:00:00:06 | 00:00:09:00 | Responsabile Commerciale · IT/MT · Netzwerk „I nostri concessionari“ |
| 2 | Maite | 00:00:09:00 | 00:00:28:21 | Coordinamento Sales & Marketing · da settembre → Kacheln Eventi / Incontri con i dealer / Corsi & Workshop |
| 3 | Valentina | 00:00:28:21 | 00:00:36:10 | Servizio Post-Vendita · Zähler „6 anni“ · Globus „Diversi mercati“ |
| 4 | Anna | 00:00:36:10 | 00:01:01:14 | Route Hilzingen ↔ Milano → Ruolo ibrido (Team Digitale ∩ Team Italia) → 3D-Drucker druckt einen Zahn Schicht für Schicht, „Supporto Team Italia“ |
| 5 | Svetlana | 00:01:01:14 | 00:01:15:13 | Squadra Italia · Hilzingen · Ordini (Checkliste) & Prezzi (Preisschild) |
| 6 | Davide | 00:01:15:13 | 00:01:41:10 | Direttore Vendite · Zähler „20+ anni“ · Zeitstrahl Ieri/Oggi → ab 00:01:35:10 Organigramm „La mia squadra“ |
| 7 | Outro | 00:01:41:10 | 00:01:49:10 | „Ci vediamo in fiera!“ · Team-Avatare · „Vi aspettiamo!“ · „A presto · Ciao!“ |

Die Schnittpunkte bei 00:00:28:21, 00:01:01:14 und 00:01:35:10 kommen aus dem Transkript.
Die Sprecherwechsel innerhalb eines Transkript-Blocks (Massimo → Maite, Valentina → Anna,
Svetlana → Davide) habe ich über die Wortmenge geschätzt. Diese Szenen am besten am echten
Sprecherwechsel anlegen. Jede Szene endet mit einem 0,5-s-Ausblenden, der Grid läuft
szenenübergreifend weiter.

## Annahmen aus dem Transkript (bitte prüfen)

Das Transkript ist automatisch erstellt. Folgende Stellen habe ich interpretiert:

- „ormai Rodriguez“ → **Maite** (nur der Vorname wird gezeigt)
- „coordinamento da sei e marketing“ → **Sales & Marketing**
- „qui a insegnare“ → **Hilzingen** (bei Anna als Route Hilzingen ↔ Milano, bei Svetlana als Standort)
- „Plana“ → **Svetlana** (korrigiert)
- Der Firmenname („Renfe“) erscheint absichtlich nirgends.

Namen und Texte stehen als Klartext in `index.html`. Jede Szene ist ein eigener
`<section id="…">`-Block. Zeitpunkte stehen inline als `--t:…s` (Sekunden ab Szenenstart).
Die Szenengrenzen stehen in Frames in `SCENES` im Script-Teil.

## Soundeffekte

Die Effekte werden nicht von Hand gesetzt, sondern aus den Animationen selbst abgeleitet.
`render.js` liest jede CSS-Animation mit ihrem Startzeitpunkt aus, und `sfx.py` erzeugt dazu
den passenden Klang. Das Stereo-Panorama folgt der Position des Elements im Bild.

| Animation | Klang |
|---|---|
| Buchstaben des Namens | feine Tipp-Ticks |
| Karte / Kachel fährt ein, Venn-Kreise | Whoosh |
| Karte fährt aus, Szenenende | kurzer Whoosh nach oben |
| Chips, Knoten, Avatare | Pop |
| rote Pills, Hub, „&“, Davide-Avatar | tieferer Pop mit Bass |
| Linien zeichnen sich | weicher Swipe |
| Balken wachsen | aufsteigende Blips (Pentatonik) |
| Zähler „6“ und „20+“ | Ticks im Takt der Zahlen, am Ende ein Glockenton |
| Häkchen (Svetlana), Kalendertage (Maite) | Glockentöne |
| 3D-Druck des Zahns | Schrittmotor-Surren pro Schicht |
| Glanz über den Glaskarten | leises Schimmern |
| „A presto · Ciao!“ | Schluss-Akkord |

Ein Element mit `data-sfx="chime"`, `"pop_big"` usw. bekommt einen anderen Klang. Mit `data-sfx="none"` bleibt es stumm.
Lautstärken und Klänge stehen in `sfx.py` in `build()`.

## Schrift

Netto Pro ist eine lizenzpflichtige Schrift und liegt deshalb **nicht** im Repository (`.gitignore`).
Zum Rendern die drei Dateien so ablegen:
`fonts/NettoPro-Regular.otf`, `fonts/NettoPro-Bold.otf`, `fonts/NettoPro-Black.otf`.

## Vorschau und neu rendern

`index.html` im Browser öffnen. `?scene=anna` zeigt eine einzelne Szene, `?t=42` friert bei Sekunde 42 ein.

```bash
NODE_PATH=$(npm root -g) node render.js
```

```bash
NODE_PATH=$(npm root -g) node render.js anna
```

```bash
NODE_PATH=$(npm root -g) node render.js --sfx
```

```bash
NODE_PATH=$(npm root -g) node render.js --stills 8 16.5 58.4
```

`--sfx` mischt nur den Ton neu und legt ihn in die vorhandenen Videos. Das geht schnell, setzt aber einen vorherigen vollen Render voraus.

Benötigt werden Node, Playwright mit Chromium, ffmpeg, Python 3 mit numpy und Netto Pro in `fonts/`.
Die Ausgabe ist H.264, yuv420p, CRF 14, mit AAC-Ton (256 kbit/s, 48 kHz).
