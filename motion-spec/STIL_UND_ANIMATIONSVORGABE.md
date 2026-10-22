# Stil- und Animationsvorgabe für automatisierten Schnitt und Motion Graphics

Grundlage: 1 Bild und 3 Videos. Alle Videos wurden Frame für Frame ausgewertet:
Bewegungsenergie pro Frame, Schnittpunkte, doppelte Frames und Skalierungskurven.
Zusätzlich wurden Tempo und Onsets der Tonspur gemessen, um die Schnitte gegen
den Beat zu prüfen.
Die Farben sind Pixel-Messwerte. Kurven, die mit **gemessen** markiert sind, wurden
an echte Frame-Daten gefittet. Mit **abgeleitet** markierte Werte sind Empfehlungen,
die zum beobachteten Stil passen, aber nicht direkt messbar waren.

Die maschinenlesbare Fassung steht in [`motion-spec.json`](motion-spec.json).
Die Frame-Belege liegen in [`reference/`](reference/). Neue Referenzen lassen sich mit
[`tools/analyze_motion.py`](tools/analyze_motion.py) auf dieselbe Weise vermessen.

---

## 0. Referenzmaterial im Überblick

| ID | Quelle | Format | fps (Datei → effektiv) | Länge | Charakter |
|---|---|---|---|---|---|
| **A** | Bild (Web-Landingpage) | 736×981 | statisch | – | Neo-Brutalismus: Flat, schwarze Konturen, Bento-Grid |
| **B** | Video 1 | 720×1280 (9:16) | 30 → **15 (on twos)** | 5,27 s / 158 f | Weiche 3D-Gradients, Pastell, surreal, eine Einstellung ohne Schnitt |
| **C** | Video 2 | 720×1280 (9:16) | 29,97 → 30, Nebenelemente **8 fps gestuft** | 28,76 s / 862 f | Flat-Pop mit Stickern, Blob-Masken, Taktschnitt |
| **D** | Video 3 | 720×1280 (9:16) | 30 → **24** (jeder 5. Frame doppelt = Pulldown) | 15,80 s / 474 f | Kinetischer App-Promo, 3D-Phone, Farbflash-Schnitte |

Die vier Quellen sind vier eigenständige Stilmodule. Die **gemeinsame Grammatik**
(Kapitel 1) gilt für alle Module. Die **Stilmodule** (Kapitel 2–5) legen Look,
Farben und Timing des jeweiligen Moduls fest.

---

## 1. Gemeinsame Grammatik (gilt für alle Stile)

### 1.1 Format und Bildraten
- Master-Format **9:16, 1080×1920**. Die Referenzen liegen in 720×1280 vor; alle
  Pixelangaben unten beziehen sich auf **1080×1920**.
- Master-Timeline **30 fps** (bei Stil C 29,97).
- Die Bildrate der Animation ist eine Stilentscheidung und wird bewusst abgesenkt:
  - Stil B: **15 fps** (on twos), jeder Zeichnungsframe wird zweimal gehalten.
  - Stil C: Hauptbewegung in **30 fps**, Idle- und Nebenelemente in **8 fps** gestuft
    (gemessen: Wechsel alle 3–4 Frames, im Schnitt 3,75 f). Ein Teil der Ornamente
    springt im 6-Frame-Raster (5 fps).
  - Stil D: **24 fps**. Ein 30-fps-Export enthält dann zwangsläufig Pulldown-Dubletten.
- Umsetzung in After Effects: `posterizeTime(fps)`. In Remotion/Lottie: Frame
  quantisieren mit `floor(frame / step) * step`.

### 1.2 Schnittgrammatik
- **Fast nur harte Schnitte.** Die Videos C und D enthalten keine einzige echte
  Überblendung. Weiche Übergänge entstehen ausschließlich innerhalb einer Szene,
  durch Masken, Wipes oder Zoom.
- **Jede Szene hat drei Phasen:** Einstieg mit viel Energie (Masken-Reveal oder
  Pop), dann Aufbau der Elemente gestaffelt, dann ein ruhiger Halt mit leichter
  Bewegung oder gestuftem Idle-Wackeln.
- **Musikalisches Raster (gegen die Tonspur gemessen):**
  - C: Tempo laut Audio **118 BPM** (Schlag = 0,508 s = 15,24 f). Szene =
    **61 f = 2,035 s = 1 Takt**, Flash-Schnitte = **15,25 f = 1 Schlag**.
  - C: Die Szenenschnitte liegen konstant **ca. 2 Frames (0,06 s) vor** dem
    Beat-Onset. Das ist typisch für Schnitte, die „auf den Punkt“ wirken sollen.
    Die Flash-Schnitte liegen dagegen 0–1,5 f nach dem Onset.
  - D: Tempo laut Audio **≈150–155 BPM**. Die Schnitte folgen einem
    **3-3-2-Achtelmuster** (Tresillo): 0,6 s + 0,57 s + 0,43 s = 1 Takt ≈ 1,6 s.
    Das wiederholt sich zweimal ab f0, danach kommen 1,0-s-Halte-Shots.
  - D: Flash = **5 f @30 = 4 f @24 = 0,167 s**, etwa 1 Achtel.
- **Schnittregel:** Jeder Schnitt liegt auf einem Beat. Bewegung **läuft über den
  Schnitt hinweg**: D beschleunigt in den Schnitt hinein, statt vorher auszuklingen.
- **Farbflash-Stakkato** als Höhepunkt (C und D): Layout bleibt identisch, nur
  Hintergrundfarbe und Inhalt wechseln, 4 bis 8 Mal hintereinander.
- **Outro:** Logo-Endcard, **3,2–4,2 s** statisch (C: 127 f, D: 95 f), nach dem
  Einblenden ohne weitere Bewegung.

### 1.3 Easing-Bibliothek

| Token | cubic-bezier | Herkunft | Einsatz |
|---|---|---|---|
| `snap_out` | (0.20, 0.20, 0.05, 1.00) | **gemessen**: C, Titel-Scale f51–68 | Titel-Reveals, Masken |
| `counter_out` | (0.00, 0.00, 0.00, 1.00) | **gemessen**: D, Saldo-Zähler f70–82 | Zahlen-Hochzählen, schnelle Pops |
| `expo_out` | (0.16, 1.00, 0.30, 1.00) | abgeleitet: Energieabfall nach Schnitten in C/D | Positionen, Kamerafahrten nach Schnitt |
| `whip_in` | (0.70, 0.00, 0.84, 0.00) | abgeleitet: D, Energie steigt vor dem Schnitt um 2–4× | Beschleunigung in den Schnitt |
| `back_out` | (0.34, 1.56, 0.64, 1.00) | abgeleitet | Sticker-Pops (max. 8 % Überschwinger) |
| `soft_inout` | (0.45, 0.00, 0.55, 1.00) | abgeleitet: B, langsamer Auf- und Abbau | Stil B: alle Bewegungen |
| `linear` | (0, 0, 1, 1) | gemessen: C, f210–243, konstante Energie 1,5 | Langsamer Drift oder Push im Halt |

**Speed-Ramp (Stil D):** Eine Szene startet mit `expo_out` (ca. 30 % der Shotdauer),
geht in ein Plateau mit konstantem Drift (ca. 40 %) und endet mit `whip_in` (ca. 30 %)
direkt in den Schnitt. Gemessene Energie f113–142: 76 → 25 → 12 (Plateau) → 6 → 31 → Schnitt.

### 1.4 Dauer-Tokens (in Frames @30 fps)

| Token | Frames | Sekunden | Beleg |
|---|---|---|---|
| `t_micro` | 2 | 0,07 | 1 Zeichen pro 2 f beim Typewriter (C, „20XX“) |
| `t_pop` | 6 | 0,20 | Sticker, Zahnrad, Sterne (C) |
| `t_wipe` | 6–8 | 0,20–0,27 | Label-Balken links → rechts (C) |
| `t_reveal` | 7–8 | 0,23–0,27 | Iris- oder Starburst-Maske (C f48–55, f131–137) |
| `t_title` | 17 | 0,57 | Titel-Scale 18 % → 100 % (C f51–68) |
| `t_flash` | 5 (C: 15) | 0,17 (0,51) | Farbflash-Schnitt D (C) |
| `t_shot_short` | 13–18 | 0,43–0,60 | Standardshot D (3-3-2-Muster: 18 / 17 / 13 f) |
| `t_scene` | 61 | 2,04 | Szene C (1 Takt) |
| `t_endcard` | 95–127 | 3,2–4,2 | Outro |

### 1.5 Staffelung
- Elemente erscheinen nacheinander, nie gleichzeitig. Abstand **2–3 Frames**.
- Reihenfolge in C: Maske/Hintergrund → Titel (gleichzeitig mit Maske) →
  Highlight-Box (+8 f) → Hauptsticker (+8–10 f) → Kleinornamente (+15–18 f).
- Buchstaben-Pop in **zufälliger Reihenfolge**, gesamt ca. 8 f (C f139–147,
  „BOLD IDEAS“): erst einzelne Buchstaben, dann der Rest.

---

## 2. Stil A: Neo-Brutalismus (Bild-Referenz)

`reference/A_bild_referenz.jpg`

### 2.1 Look
- **Hintergrund** Off-White `#F4F4F0` (gemessen `#F6F5F1`).
- **Konturen:** alle Karten, Buttons und Illustrationen mit schwarzer Kontur,
  **2 px** (UI) bzw. **3–4 px** (Illustration) bei 1080 px Breite. Keine
  Verläufe, keine weichen Schatten.
- **Hard Shadow:** Icons und Buttons mit schwarzem, scharfkantigem Versatzschatten
  **+4/+4 px** nach rechts unten.
- **Layout:** Bento-Grid aus Karten mit 1 px schwarzer Kontur, Radius **4–6 px**,
  Rinne ca. **12 px**. Header und Footer sind durch volle Linien getrennt.
- **Illustration:** Flat, 3–4 Füllfarben, schwarze Kontur. Eine gesichtslose,
  pinke Blob-Figur ist die wiederkehrende Figur. Comic-Sprechblasen mit
  Mono-Versalien, Münzen als extrudierte 3D-Scheiben mit „G“.

### 2.2 Farben

| Rolle | Hex | Hinweis |
|---|---|---|
| Hintergrund | `#F4F4F0` | gemessen `#F6F5F1` |
| Primär Pink | `#FF90E8` | JPEG-gemessen `#E58AD6` (stark komprimiert) |
| Gelb (KPI-Karte) | `#FFC900` | |
| Periwinkle (Flächen) | `#90A8ED` / hell `#BCC2FE` | gemessen `#BCC2FE` |
| Teal (Illustration) | `#23A094` | |
| Orange-Rot (Akzent) | `#FF7051` | |
| Text / Kontur / CTA | `#000000` | |

### 2.3 Typografie
- **Display:** extrem schmale, fette Grotesk in Versalien, Zeilenabstand ca. 0,9,
  zweizeilig, linksbündig („GO FROM / 0 TO $1“). Vergleichbar mit Druk Condensed,
  Anton oder Bebas Neue.
- **Labels und Kartentitel:** Mono-Versalien (Space Mono, IBM Plex Mono).
- **Fließtext:** schlichte Grotesk, Regular, 14–16 px @1080.
- **KPI-Zahl:** Mono, fett, groß („$2,048,262“).

### 2.4 Motion-Ableitung (abgeleitet, keine Videoquelle)
- Bewegungen **gestuft mit 12 fps**, damit es zum harten Print-Look passt.
- **Button-Press:** Element verschiebt sich um +4/+4 px, der Schatten verschwindet
  dabei (3 f), dann zurück (3 f).
- **Karten-Einstieg:** Slide aus 40 px Versatz mit `expo_out`, 8 f, 3 f Stagger
  in Leserichtung.
- **KPI-Balkendiagramm:** Balken wachsen nacheinander, je 4 f, `counter_out`. Zahl
  zählt parallel hoch (14 Schritte, siehe D).
- **Münzen:** Y-Rotation 360° in 24 f mit 12-fps-Stufung, Schatten-Ellipse
  skaliert gegenläufig.

---

## 3. Stil B: Soft-Gradient-Surreal (Video 1)

`reference/B_video1_keyframes.jpg` (Frames 0 / 40 / 80 / 120 / 156)

### 3.1 Look
- **Pastell-Bühne** in Blush-Rosa, mit **Tiefenunschärfe**: große unscharfe Blobs
  in Altrosa an den Bildrändern (Vordergrund) und weiße Wolkenformen rechts
  (Hintergrund).
- **Milchglas-Panel:** Die rechte Bildhälfte liegt hinter einer milchig-weißen,
  halbtransparenten Scheibe mit **welliger senkrechter Kante**. An dieser Kante
  läuft eine dünne Perlenschnur. Objekte, die die Kante kreuzen, werden **geteilt**:
  rechts aufgehellt und leicht versetzt (Refraktion).
- **Objekte:** weich schattierte 3D-Primitive ohne Kontur mit Verlauf: Quader,
  Kugeln, Würmer. Charaktere haben doppelte „Googly Eyes“ (weiße Ovale, schwarze
  Pupillen). Kleine gelbe Funken-Rauten, Bläschen, eine Muschel.
- **Kein Text.**

### 3.2 Farben (gemessen, Verlaufsendpunkte teils geschätzt)

| Rolle | Hex |
|---|---|
| Bühne hell | `#FCDEDE` / `#FDDCD7` |
| Bühne mittel | `#FBCBC8` |
| Vordergrund-Blur dunkel | `#CB5861` |
| Milchglas / Wolken | `#FDFBFC` |
| Indigo-Violett (Quader) | `#5C6CFC` (Licht) → `#3D2F9E` (Schatten, geschätzt) |
| Cyan-Kugel | `#28C4E8` (geschätzt) → `#749CDC` |
| Sonnenuntergangs-Kugel | `#FCCC5C` → `#E8455A` → `#6A2C8C` (Mitte/Ende geschätzt) |
| Funken / gelbe Kugeln | `#FCEC2C` |

### 3.3 Timing (gemessen)
- **On twos:** Ungerade Frames sind exakte Kopien (Differenz 0,0–0,2). Es wird also
  mit 15 fps animiert.
- **Energiekurve:**
  - 0–1,3 s: Ruhephase (2,0)
  - 1,3–2,0 s: Peak (≈5,0)
  - 2,0–5,27 s: langes Ausklingen (3,6 → 1,3)
- **Kein Schnitt.** Eine Einstellung baut sich auf, ohne Loop (erster und letzter
  Frame unterscheiden sich deutlich).
- **Ereignisfolge:**
  1. Dauerhafte Pendelbewegungen (Kugel an Schnur, Augen) ab f0.
  2. f~40: Ein Wurm schlängelt sich aus dem Quader.
  3. f~80: Der Quader klappt zu einer 3D-Schublade auf, gelbe Kugeln rieseln heraus.
  4. Bläschen steigen auf, die Muschel öffnet sich.
- **Easing:** durchgehend `soft_inout`. Organisches Schlängeln über Sinus-Offsets
  entlang einer Kette (Phasenversatz pro Segment ca. 0,15 Periode). Keine harten
  Stopps.

---

## 4. Stil C: Flat-Pop-Sticker-Opener (Video 2)

Belege: `reference/C_*.jpg`

### 4.1 Look
- **Flächen:** satte Volltonfarben, keine Konturen, keine Verläufe, keine Schatten
  (Ausnahme: 3D-Sticker mit Extrusion).
- **Hintergrund in drei Ebenen:**
  1. Farbfläche
  2. **Raster** (weiße Linien, ca. 4 px, Raster ca. 90 px), überlagert von großen
     organischen **Blobs / Wellenbändern**
  3. Weißes **Textfeld als Formmaske**: Linse/Oval, Starburst-Kreis (Zackenrand)
     oder Wolkenband
- **Sticker-Set:** Auge (Mandel, pink mit schwarzer Iris, teils mit Wimpern und
  Herz-Pupille), 8-Zack-Stern, Zahnrad/Blume, 4-Zack-Funkelstern, 3D-Kreuz/X,
  3D-Ring/Münze, Konfetti-Stäbchen, Kleeblatt.
- **3D-Sticker:** flache Form mit Extrusion in Violett/Magenta, die sich um die
  Y-Achse dreht.

### 4.2 Farben (gemessen)

| Rolle | Hex |
|---|---|
| Grün (Hauptfläche) | `#30A365` |
| Creme (Raster-Grund) | `#F1DCC4` / `#EEDDC3` |
| Rosa hell (Raster-Grund) | `#F0D2DB` |
| Pink | `#F38DAE` |
| Magenta (Konfetti, Sticker) | `#FC6CF4` |
| Indigo | `#3C34C4` |
| Orange | `#FB7B35` |
| Pfirsich (Variante) | `#FCD2B5` |
| Hintergrund Übersicht | `#FFF3E3` |
| Text | `#1D1D1D` |
| Weiß (Masken) | `#FCFCFC` |

Farbvarianten aus dem Stakkato (je 1 Schlag):

| Variante | Hintergrund | Box | Ornament |
|---|---|---|---|
| 1 | Grün | Orange | Indigo |
| 2 | Pfirsich + Magenta | Indigo | Orange |
| 3 | Orange | Grün | Indigo |

### 4.3 Typografie
- **Display:** geometrische Grotesk, ExtraBold/Black, Versalien, **Tracking −2 %**,
  Zeilenabstand **0,85–0,9**, zentriert. Vergleichbar mit Poppins ExtraBold.
- **Größe:** Der Titel füllt 80–100 % der Formmaske und **darf an der Maske
  anschneiden** (gewollt).
- **Tag/Kicker** über dem Titel in einer Vollton-Box (Orange, Magenta, Indigo),
  Höhe ca. 45 % der Titel-Versalhöhe.
- **Unterzeilen** in Label-Balken (Pink oder Indigo), kleine Versalien.

### 4.4 Szenenstruktur (gemessen, Frames @29,97)

| Szene | Frames | Dauer | Inhalt / Übergang |
|---|---|---|---|
| Vorspann | 0–47 | 1,60 s | Logo auf Weiß, statisch |
| S1 | 48–117 | 2,34 s | „COLORFUL BUSINESS OPENER“: Iris-Reveal |
| S2 | 118–182 | 2,17 s | „20XX BOLD IDEAS“: 12 f Weißhalt, dann Starburst-Zoom |
| S3 | 183–243 | 2,04 s | „CREATIVE“: Metaball-Wipe |
| S4 | 244–304 | 2,04 s | „STRATEGIC VISION“ |
| S5 | 305–365 | 2,04 s | „FUTURE FOCUS“: Iris-Reveal (Wiederholung S1) |
| S6 | 366–426 | 2,04 s | „BOLD & FUN“: Raster-Fade und Oval-Scale |
| S7 | 427–487 | 2,04 s | „BUSINESS NAME“: Pop und Typewriter |
| S8 | 488–612 | 4,17 s | Übersicht aller 8 Layouts, Drift, dann Zoom mit Motion Blur in eine Karte |
| S9 | 613–734 | 8 × 15,25 f | Farbvarianten-Stakkato |
| Endcard | 735–861 | 4,24 s | Logo statisch |

### 4.5 Animationsbausteine (gemessen)

1. **Iris-Reveal** (S1, S5; `C_video2_f046-069`)
   - Vollbild-Weiß zieht sich zur Linsenform zusammen und gibt Raster und Blobs
     frei: 8 f, `snap_out`.
   - Gleichzeitig skaliert der Titel von **18 % → 100 % in 17 f**, Kurve
     `cubic-bezier(0.20, 0.20, 0.05, 1.00)`, kein Überschwingen.
   - Zweizeilige Titel: Zeile 2 startet 2–3 f später und kleiner und holt auf.
2. **Highlight-Box-Wipe:** Box wächst ab +8 f hinter dem Kicker von links nach
   rechts, 4–6 f. Der Text sitzt bereits darüber.
3. **Starburst-Zoom** (S2, `f129-152`)
   - 12 f reines Weiß halten.
   - Zackenkreis skaliert von Vollbild auf ca. 55 % Breite, 7 f, `expo_out`.
   - Gleichzeitig wird grünes Feld mit Konfetti sichtbar.
4. **Buchstaben-Pop:** einzelne Glyphen erscheinen in Zufallsreihenfolge ohne
   Tween (hart an), insgesamt ca. 8 f.
5. **Typewriter in Box:** Box ist bereits da. 1 Zeichen pro 2 f (C, „20XX“) bzw.
   1 Zeichen pro 1 f (Labels). Variante S7: das neue Zeichen erscheint 1 f lang mit
   50 % Deckkraft (Ghost), dann voll.
6. **Metaball-Wipe** (S3, `f182-205`)
   - Weiße Kreise wachsen aus Punkten und verschmelzen zu einem Wolkenband
     (Gooey-Effekt), ca. 17 f.
   - Der Titel wird dabei durch die wachsende Form freigelegt („AT“ → „EATI“ →
     „CREATIVE“).
   - Danach linearer Push (`linear`) bis zum Szenenende.
7. **Raster-Fade** (S6, `f365-388`)
   - Einzige weiche Blende: Raster und Blobs blenden in ca. 6 f auf.
   - Weißes Oval skaliert mit Titel von ca. 35 % auf 100 %, ca. 10 f.
8. **Sticker-Einstieg**
   - Zahnrad, Sterne: Scale 0 → 100 % in 2–4 f, dazu ca. 30° Rotation.
   - 3D-Kreuz: Y-Rotation 90° → 0° (dreht sich „auf“), 10 f.
   - Auge: Lid öffnet sich von Strich über Halbmond zu Mandel, 6 f.
9. **Idle:** Konfetti, Sticker und Wimpern springen gestuft mit 8 fps (alle
   3–4 f) um ±2–6 px bzw. ±5°. **Keine** weiche Idle-Bewegung.
10. **Übersicht → Zoom** (S8, `f586-609`)
    - Gitter der 8 Szenen-Thumbnails (Querformat-Varianten) auf Creme, ca. 3 s
      ruhiger Drift.
    - Danach skaliert eine Karte in **18 f** auf Vollbild, mit kräftigem
      **Motion Blur** (Peak f593–596). Die anderen Karten werden aus dem Bild
      geschoben.
11. **Farbvarianten-Stakkato** (S9): identisches Layout, pro Schlag (15 f) neue
    Farbkombination. Innerhalb eines Schlags nur gestufte Idle-Bewegung.

---

## 5. Stil D: Kinetischer App-Promo (Video 3)

Belege: `reference/D_*.jpg`

### 5.1 Look
- **Volltonhintergründe**, randlos, ohne Textur. Dazu Weiß und Fast-Schwarz.
- **3D-Smartphone-Mockup** (realistisch, Titanrahmen, leichter Glanz) in wechselnden
  Perspektiven: frontal, Y ±25°, X-Kippung, von unten.
- **UI-Karten brechen aus dem Display** in den Raum: Saldo-Karte, Portfolio-Karten,
  Pills. Sie haben weiche Schlagschatten (ca. 20 % Schwarz, Blur 30 px, Versatz
  nach unten).
- **Flache, geometrische Illustrationen** im Stil von Scherenschnitt/Bauhaus:
  Rot, Blau, Gelb, Pink, Grün. Glitzer-Sterne als 4-Zack-Funkeln.
- **Headline-Layout „Treppe“:**
  - zwei Zeilen, riesig (Versalhöhe ca. 7 % der Bildhöhe)
  - Zeile 1 linksbündig und **links angeschnitten**
  - Zeile 2 eingerückt und **rechts angeschnitten**
  - Phone überlappt die untere Zeile

### 5.2 Farben (gemessen)

| Rolle | Hex | Textfarbe darauf |
|---|---|---|
| Pink | `#FF99C3` | Weiß |
| Blau | `#024DD7` | Weiß |
| Rot | `#E6380A` | Weiß |
| Gelb | `#FFD833` | Schwarz |
| Grün | `#00A94B` | Weiß |
| Fast-Schwarz | `#121212` | Weiß / Pink |
| Weiß | `#FDFDFD` | – |

Flash-Reihenfolge, die zweimal identisch vorkommt:
**Blau → Pink → Rot → Gelb → Grün → Blau → Pink → (Endcard Rot)**.

### 5.3 Typografie
- **Display:** geometrische Grotesk Bold, Groß-/Kleinschreibung, **Tracking −3 %**,
  Zeilenabstand **0,85**. Vergleichbar mit Circular Bold, Gilroy Bold oder
  Satoshi Bold.
- **Intro-Wort** („Introducing“) mittig, klein, mit Farbverlauf-Wipe Pink → Weiß.
- **Wortmarke** mit Maskottchen (Schwein, Münze) als Endcard, Tagline darunter in
  Pink.

### 5.4 Shot-Liste (gemessen, Frames @30, Animation 24 fps)

| Frames | Dauer | Hintergrund | Inhalt / Bewegung |
|---|---|---|---|
| 0–17 | 0,60 s | Schwarz | „Introducing“: Scale 100 % → ca. 60 % (linear), Farbwipe Pink → Weiß L→R in 11 f |
| 18–34 | 0,57 s | Weiß | Logo, langsamer Push +5 %, Münze fällt ins Schwein |
| 35–47 | 0,43 s | Pink | Phone-Close-up, Notification-Karte |
| 48–64 | 0,57 s | Weiß | Phone gekippt (Lockscreen), Notification hebt ab (Z) |
| 65–82 | 0,60 s | Weiß | Saldo-Karte springt aus dem Display, Zähler £0 → £5.438 (`counter_out`), Phone dreht in die Frontale |
| 83–95 | 0,43 s | Schwarz | Phone klein, Pull-out |
| 96–112 | 0,57 s | Weiß | Illustration (Einkaufstüten) als Insert |
| 113–142 | 1,00 s | Weiß | Budget-Screen, Speed-Ramp |
| 143–159 | 0,57 s | Blau | Headline „Your new / money app“ + Phone |
| 160–174 | 3 × 5 f | Pink / Rot / Gelb | Flash: gleiche Headline, neuer Screen |
| 175–189 | 0,50 s | Grün | Ende der Flash-Serie |
| 190–207 | 0,60 s | Weiß | 4 Portfolio-Karten als 3D-Stapel, gefächert |
| 208–237 | 3 Shots | Pink / Weiß / Weiß | Karte gleitet ins Phone zurück |
| 238–254 | 0,57 s | Weiß | Invest-Screen, Karte schwebt |
| 255–283 | 11 / 5 / 13 f | Blau / Pink / Gelb | Headline „Invest / effortlessly“ |
| 284–300 | 0,57 s | Weiß | Pills fliegen gestreut ein, Rotation ±20°, Ease-out, sammeln sich |
| 301–330 | 1,00 s | Weiß | Pills im schwarzen Phone-Screen |
| 331–348 | 0,60 s | Blau | Headline „Tailored / to you“ |
| 349–378 | 6 × 5 f | Pink / Rot / Gelb / Grün / Blau / Pink | Flash-Serie, letzter Screen = Logo |
| 379–473 | 3,17 s | Rot | Endcard: Schwein ploppt (f379), Wortmarke nach +2 f, Tagline, Halt |

### 5.5 Animationsbausteine
1. **Speed-Ramp-Shot** (gemessen, siehe 1.3): `expo_out` → Plateau → `whip_in` →
   Schnitt. Kamera und Phone bewegen sich über jeden Schnitt hinweg (Match on
   Action).
2. **3D-Phone-Rotation:** Y-Rotation 20–30° auf 0° bzw. umgekehrt, über die volle
   Shotlänge. Dazu Scale 92 → 100 % und leichte X-Kippung (5–10°).
3. **Card-Breakout:** UI-Karte löst sich aus dem Screen.
   - Z-Offset 0 → 120 px, Rotation Z −6°, Scale 1,0 → 1,12
   - Dauer 6–8 f, `expo_out`
   - Schatten wächst mit
4. **Zähler** (gemessen): 14 Stufen bei 24 fps (ca. 0,58 s), Kurve
   `cubic-bezier(0, 0, 0, 1)`, Endwert springt im nächsten Shot auf den
   Zielwert. Werte f65 ff.: 0 · 2031 · 2904 · 3511 · 3970 · 4328 · 4612 · 4839 ·
   5019 · 5160 · 5268 · 5346 · 5399 · 5429 · (5438).
5. **Pill-Scatter** (`f280-303`)
   - 6 Pills fliegen aus verschiedenen Richtungen ein und rotieren dabei.
   - Sie überlappen sich und setzen sich in ca. 8 f mit `expo_out`.
   - Danach Drift und Zusammenziehen zum nächsten Schnitt (`whip_in`).
6. **Farbflash-Serie:** Layout, Headline und Phone-Position bleiben pixelgleich.
   Pro 5 f (@30) wechseln Hintergrundfarbe, Textfarbe (Kontrastregel) und
   Screen-Inhalt. Keine Bewegung innerhalb eines Flashs außer minimalem Drift.
7. **Endcard:**
   - Hard Cut auf Rot.
   - Maskottchen ploppt ohne Tween.
   - +2 f Wortmarke (zuerst Pink, nach 3 f Weiß).
   - +4 f Tagline in Pink.
   - Danach statisch.

---

## 6. Regeln für den automatisierten Schnitt

1. **Beat-Analyse zuerst.** BPM ermitteln und Raster setzen:
   - Stil C: Szene = 1 Takt, Flash = 1 Schlag
   - Stil D: Shots im 3-3-2-Achtelmuster pro Takt, Flash = 1 Achtel
2. **Schnitt nur auf Rasterpunkten.** Toleranz ±1 Frame. Szenenwechsel dürfen
   bewusst **2 Frames vor** dem Beat liegen (gemessen in C).
3. **Shotlängen-Verteilung Stil D:**
   - 65 % kurz (13–18 f)
   - 15 % Flash (5 f)
   - 10 % Halte-Shot (30 f)
   - 10 % Mikro (7–11 f)
   - Nie zwei Halte-Shots hintereinander.
4. **Farbfolge:** Zwei aufeinanderfolgende Shots haben nie dieselbe
   Hintergrundfarbe. Weiß und Schwarz gelten als Neutral-Reset zwischen
   Farbsequenzen.
5. **Text-Kontrast:** Gelb und Pfirsich bekommen schwarzen Text, alle anderen
   Volltöne weißen. In Stil C steht Text immer auf weißer Maske.
6. **Rhythmuskurve des Gesamtvideos:**
   - ruhiger Einstieg (Intro 0,6 s bzw. 1,6 s)
   - Aufbau mit Shots von 0,4–0,6 s
   - zwei Flash-Serien als Höhepunkte, die zweite unmittelbar vor der Endcard
   - Endcard 3–4 s
7. **Bewegungskontinuität (D):** Der ausgehende Shot endet in Bewegung (`whip_in`),
   der eingehende startet in Bewegung (`expo_out`). Bewegungsrichtung über den
   Schnitt beibehalten.
8. **Bildraten-Konsistenz:** Pro Stilmodul gilt eine Animations-Bildrate (B 15,
   C 30/8, D 24). Nicht mischen.
9. **Safe Area (9:16):**
   - oben 180 px und unten 320 px frei von wichtigem Text (UI-Overlays sozialer
     Plattformen)
   - seitlich 60 px
   - Ausnahme: Treppen-Headlines in D, die absichtlich anschneiden

---

## 7. Werkzeug

`tools/analyze_motion.py <video>` gibt als JSON aus:
- Bewegungsenergie pro Frame
- erkannte Schnitte
- Dubletten-Muster (on twos / Pulldown / gestufte Elemente)
- Shotlängen

Damit lassen sich neue Referenzen vermessen und automatisch generierte Clips gegen
diese Vorgabe prüfen, zum Beispiel ob Schnitte auf dem Raster liegen und ob die
Bildrate stimmt.
