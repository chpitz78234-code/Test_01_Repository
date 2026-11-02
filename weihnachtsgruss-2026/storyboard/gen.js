// Rendert das Storyboard-Sheet (9 Panels, 9:16) aus ../storyboard.json als PNG.
// Aufruf: NODE_PATH=$(npm root -g) node gen.js [ausgabeordner]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT = process.argv[2] || __dirname;
const SB = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'storyboard.json'), 'utf8'));
const FPS = SB.global.fps;
const COPY = SB.copy.de;
const P = Object.fromEntries(Object.entries(SB.brand.palette).map(([k, v]) => [k, v.hex]));
const WARM = '#FFD39A';

// ---------- Hilfsfunktionen (Panel-Koordinaten 1080x1920) ----------
const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const tc = (f) => { const s = f / FPS; return `0:${String(Math.floor(s)).padStart(2, '0')},${Math.floor((s % 1) * 10)}`; };

function wrap(text, maxChars) {
  const lines = []; let cur = '';
  for (const w of text.split(' ')) {
    if ((cur + ' ' + w).trim().length > maxChars && cur) { lines.push(cur); cur = w; } else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  return lines;
}

const overlayText = (text, y = 560, size = 84, color = P.snow) =>
  wrap(text, 19).map((l, i) =>
    `<text x="540" y="${y + i * size * 1.1}" text-anchor="middle" font-size="${size}" font-weight="700" fill="${color}" filter="url(#tshadow)">${esc(l)}</text>`).join('');

const safeArea = () => {
  const s = SB.global.safe_area_px;
  return `<rect x="${s.left}" y="${s.top}" width="${1080 - s.left - s.right}" height="${1920 - s.top - s.bottom}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="4" stroke-dasharray="18 14"/>`;
};

const flake = (x, y, r, color = P.snow, op = 1) => {
  let d = '';
  for (let a = 0; a < 3; a++) {
    const t = (a * Math.PI) / 3;
    d += `M${x - r * Math.cos(t)} ${y - r * Math.sin(t)}L${x + r * Math.cos(t)} ${y + r * Math.sin(t)}`;
  }
  return `<path d="${d}" stroke="${color}" stroke-opacity="${op}" stroke-width="${Math.max(2, r / 4)}" stroke-linecap="round"/>`;
};

// deterministischer Zufall, damit das Sheet reproduzierbar ist
let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const snowfall = (n, y0 = 0, y1 = 1920, rMin = 6, rMax = 18, op = 0.85) =>
  Array.from({ length: n }, () => flake(60 + rnd() * 960, y0 + rnd() * (y1 - y0), rMin + rnd() * (rMax - rMin), P.snow, op * (0.5 + rnd() * 0.5))).join('');
const bokeh = (n, color = WARM) =>
  Array.from({ length: n }, () => `<circle cx="${rnd() * 1080}" cy="${700 + rnd() * 700}" r="${30 + rnd() * 70}" fill="${color}" opacity="${0.08 + rnd() * 0.12}"/>`).join('');

const arrow = (x1, y1, x2, y2, label, lx, ly) =>
  `<g stroke="${P.gold}" stroke-width="8" fill="none" stroke-linecap="round"><path d="M${x1} ${y1}L${x2} ${y2}" marker-end="url(#ah)"/></g>` +
  (label ? `<text x="${lx}" y="${ly}" font-size="44" font-weight="600" fill="${P.gold}">${esc(label)}</text>` : '');

const tag = (txt, x = 80, y = 1660, bg = P.gold, fg = P.ink) => {
  const w = 30 + txt.length * 27;
  return `<rect x="${x}" y="${y}" width="${w}" height="72" rx="36" fill="${bg}"/><text x="${x + w / 2}" y="${y + 49}" text-anchor="middle" font-size="40" font-weight="700" fill="${fg}">${esc(txt)}</text>`;
};

const defs = `<defs>
  <linearGradient id="night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16263C"/><stop offset="1" stop-color="${P.night}"/></linearGradient>
  <linearGradient id="blue" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1F3A5F"/><stop offset=".6" stop-color="#2E5279"/><stop offset="1" stop-color="#4A6E94"/></linearGradient>
  <linearGradient id="cone" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${WARM}" stop-opacity=".55"/><stop offset="1" stop-color="${WARM}" stop-opacity="0"/></linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="#FFB347"/><stop offset=".4" stop-color="#FF7A1A" stop-opacity=".7"/><stop offset="1" stop-color="#FF7A1A" stop-opacity="0"/></radialGradient>
  <radialGradient id="glass" cx=".35" cy=".3"><stop offset="0" stop-color="#fff" stop-opacity=".25"/><stop offset="1" stop-color="#9CC3E8" stop-opacity=".06"/></radialGradient>
  <filter id="tshadow" x="-20%" y="-50%" width="140%" height="200%"><feDropShadow dx="0" dy="4" stdDeviation="10" flood-color="#000" flood-opacity=".45"/></filter>
  <marker id="ah" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0 0L10 5L0 10z" fill="${P.gold}"/></marker>
</defs>`;

// ---------- Panels ----------
const bench = (y = 1450, fill = '#1C2633') => `<rect x="0" y="${y}" width="1080" height="${1920 - y}" fill="${fill}"/><rect x="0" y="${y}" width="1080" height="6" fill="#2D3B4D"/>`;
const handpiece = () =>
  `<g transform="rotate(-38 330 1420)"><rect x="80" y="1380" width="520" height="80" rx="40" fill="#8E9AA8"/><rect x="560" y="1398" width="90" height="44" rx="14" fill="#B8C2CD"/><rect x="640" y="1412" width="60" height="16" rx="8" fill="#D8DEE5"/></g>` +
  `<path d="M90 1920 L150 1640 Q200 1560 290 1590 L360 1640 L300 1920Z" fill="#3E6FB0" opacity=".9"/>`;
const crown = (x = 600, y = 1100) => `<path d="M${x - 50} ${y + 40} Q${x - 60} ${y - 30} ${x - 25} ${y - 40} Q${x} ${y - 20} ${x + 25} ${y - 40} Q${x + 60} ${y - 30} ${x + 50} ${y + 40} Z" fill="#F4F1EA"/>`;
const nozzle = (op = 1) => `<g opacity="${op}"><path d="M1080 760 L880 820 L800 1000 L1080 1010 Z" fill="#59636F"/><path d="M880 820 L800 1000" stroke="#7B8794" stroke-width="10"/><ellipse cx="842" cy="912" rx="36" ry="96" transform="rotate(20 842 912)" fill="#1A1F26"/></g>`;
const dustStream = (n = 70) => Array.from({ length: n }, (_, i) => {
  const t = i / n, x = 610 + (850 - 610) * t + Math.sin(t * 9) * 18 * (1 - t), y = 1060 - (1060 - 920) * t - Math.sin(t * Math.PI) * 120;
  return `<circle cx="${x + (rnd() - 0.5) * 40 * (1 - t)}" cy="${y + (rnd() - 0.5) * 40 * (1 - t)}" r="${3 + rnd() * 5}" fill="#fff" opacity="${0.5 + rnd() * 0.5}"/>`;
}).join('');
const cornersIn = () => [[120, 260, 200, 340], [960, 260, 880, 340], [120, 1560, 200, 1480], [960, 1560, 880, 1480]]
  .map(([a, b, c, d]) => `<path d="M${a} ${b}L${c} ${d}" stroke="${P.gold}" stroke-width="8" stroke-linecap="round" marker-end="url(#ah)"/>`).join('');

const panels = {
  S1: () => `<rect width="1080" height="1920" fill="url(#night)"/><polygon points="0,0 420,0 900,1450 0,1450" fill="url(#cone)"/>` +
    bench() + nozzle() + dustStream() + crown() + handpiece() + cornersIn() +
    overlayText(COPY.s1) + `<text x="540" y="1555" text-anchor="middle" font-size="40" fill="${P.gold}" font-weight="600">Dolly-in</text>`,

  S2: () => `<rect width="1080" height="1920" fill="url(#night)"/><polygon points="0,0 420,0 900,1450 0,1450" fill="url(#cone)" opacity=".5"/>` +
    bench() + nozzle() + crown() + handpiece() +
    Array.from({ length: 14 }, (_, i) => flake(800 - i * 22 + (rnd() - 0.5) * 120, 900 - i * 14 + (rnd() - 0.5) * 50, 10 + rnd() * 12)).join('') +
    `<path d="M820 960 Q700 920 600 760" stroke="${P.gold}" stroke-width="8" fill="none" stroke-dasharray="20 14" marker-end="url(#ah)"/>` +
    tag('B1 Freeze → B2 Umkehr', 80, 1180) + overlayText(COPY.s2),

  S3: () => {
    const casts = [[150, 1250, 1.25], [420, 1230, 1.5], [720, 1250, 1.35], [970, 1240, 1.15]].map(([x, y, s]) => {
      let d = `M${x - 120 * s} ${y + 40 * s}`;
      for (let k = 0; k < 6; k++) { const bx = x - 120 * s + k * 40 * s; d += ` Q${bx + 20 * s} ${y - (70 + (k % 2) * 30) * s} ${bx + 40 * s} ${y + 10 * s}`; }
      return `<path d="${d} L${x + 120 * s} ${y + 60 * s} L${x - 120 * s} ${y + 60 * s} Z" fill="#F2F4F7" stroke="#C9D3DE" stroke-width="4"/>`;
    }).join('');
    return `<rect width="1080" height="1920" fill="url(#blue)"/>` + bokeh(9) + casts +
      `<path d="M0 1360 Q270 1330 540 1365 T1080 1350 V1920 H0Z" fill="#EEF3F8"/>` +
      `<rect x="250" y="1420" width="180" height="16" rx="8" fill="#9AA6B2" transform="rotate(-8 340 1428)"/>` +
      snowfall(40, 200, 1400) + arrow(240, 1560, 840, 1560, 'Dolly L → R', 350, 1530);
  },

  S4: () => {
    const R = 210, cx = 520, cy = 1330;
    const pts = Array.from({ length: 10 }, (_, i) => { const a = -Math.PI / 2 + (i * Math.PI) / 5, r = i % 2 ? R * 0.42 : R; return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`; });
    return `<rect width="1080" height="1920" fill="url(#night)"/>` + bokeh(6) +
      `<rect x="0" y="1480" width="1080" height="440" fill="#151C26"/>` +
      `<path d="M1080 1720 L700 1060" stroke="#9AA6B2" stroke-width="26" stroke-linecap="round"/><path d="M1080 1720 L900 1410" stroke="#3B4552" stroke-width="54" stroke-linecap="round"/>` +
      `<circle cx="700" cy="1060" r="90" fill="url(#glow)"/>` +
      `<polygon points="${pts.join(' ')}" fill="${P.gold}" opacity=".35"/>` +
      `<polygon points="${pts.join(' ')}" fill="none" stroke="${P.gold}" stroke-width="12" stroke-linejoin="round" stroke-dasharray="1400 400"/>` +
      flake(cx + 130, cy - 200, 26, '#FFF6D8') + tag('MG: Stroke-Draw + Glint', 80, 1680) + overlayText(COPY.s4);
  },

  S5: () => {
    const cx = 540, cy = 1180, r = 360;
    return `<rect width="1080" height="1920" fill="url(#night)"/>` +
      `<clipPath id="g"><circle cx="${cx}" cy="${cy}" r="${r}"/></clipPath>` +
      `<g clip-path="url(#g)"><rect x="0" y="0" width="1080" height="1920" fill="#1D3553"/>` +
      `<path d="M150 1330 Q540 1270 930 1330 V1600 H150Z" fill="#EEF3F8"/>` +
      `<rect x="430" y="1170" width="220" height="140" fill="#D9DEE5"/><polygon points="410,1175 540,1100 670,1175" fill="#F5F7FA"/>` +
      [450, 500, 550, 600].map((x) => `<rect x="${x}" y="1210" width="28" height="36" fill="${WARM}"/>`).join('') +
      `<polygon points="740,1320 810,1320 775,1170" fill="#2F6B4F"/><circle cx="775" cy="1165" r="10" fill="${P.gold}"/>` +
      [0, 1, 2].map((k) => `<path d="M${cx - 300 + k * 40} ${cy - 120 + k * 50} Q${cx} ${cy - 330 + k * 60} ${cx + 300 - k * 40} ${cy - 120 + k * 50}" stroke="#fff" stroke-opacity=".35" stroke-width="6" fill="none"/>`).join('') +
      snowfall(28, 840, 1500, 6, 14) + `</g>` +
      `<circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#glass)" stroke="#BFD6EE" stroke-width="10"/>` +
      `<path d="M180 1620 Q540 1760 900 1620" stroke="${P.gold}" stroke-width="8" fill="none" marker-end="url(#ah)"/>` +
      `<text x="540" y="1740" text-anchor="middle" font-size="40" font-weight="600" fill="${P.gold}">Orbit 20° + Push-in</text>` +
      overlayText(COPY.s5);
  },

  S6: () => {
    const fl = SB.scenes.find((s) => s.id === 'S6').flash_sequence.flashes;
    return fl.map((f, i) => {
      const y = i * 480, bg = P[f.background], fg = P[f.text_color];
      return `<rect x="0" y="${y}" width="1080" height="480" fill="${bg}"/>` +
        `<text x="540" y="${y + 270}" text-anchor="middle" font-size="104" font-weight="800" letter-spacing="-2" fill="${fg}">${esc(COPY.s6[f.copy_index])}</text>` +
        flake(130, y + 110, 26, fg, 0.4) + flake(950, y + 380, 22, fg, 0.4) +
        `<text x="1040" y="${y + 60}" text-anchor="end" font-size="36" font-weight="600" fill="${fg}" opacity=".7">f${f.frame_in} · 20 f</text>`;
    }).join('');
  },

  S7: () => `<rect width="1080" height="1920" fill="url(#blue)"/>` +
    `<rect x="0" y="880" width="1080" height="70" fill="#9FC2E3" opacity=".55"/>` +
    `<path d="M0 960 L150 930 L260 820 L330 900 L520 880 L640 760 L720 870 L1080 900 V1920 H0Z" fill="#C8D6E5"/>` +
    `<path d="M0 1120 Q300 1040 560 1100 T1080 1080 V1920 H0Z" fill="#DCE6F0"/>` +
    `<path d="M0 1350 Q400 1270 700 1330 T1080 1300 V1920 H0Z" fill="#EEF3F8"/>` +
    Array.from({ length: 60 }, () => `<circle cx="${80 + rnd() * 920}" cy="${1420 + rnd() * 380}" r="${4 + rnd() * 6}" fill="${WARM}" opacity="${0.6 + rnd() * 0.4}"/>`).join('') +
    snowfall(30, 200, 1800, 4, 10, 0.6) + arrow(540, 1120, 540, 980, 'Drohne steigt', 580, 1060) +
    tag('Weißes Gestöber reißt auf (12 f)', 80, 1660) + overlayText(COPY.s7),

  S8: () => {
    const person = (x, h, wave, hat) => `<g transform="translate(${x} 0)">` +
      `<path d="M-70 1700 Q-70 ${1700 - h} 0 ${1700 - h} Q70 ${1700 - h} 70 1700Z" fill="#2B3E57"/>` +
      `<circle cx="0" cy="${1700 - h - 70}" r="62" fill="#E7C9A9"/>` +
      (hat ? `<path d="M-62 ${1700 - h - 95} Q0 ${1700 - h - 230} 70 ${1700 - h - 150} L62 ${1700 - h - 95}Z" fill="#C8102E"/><circle cx="72" cy="${1700 - h - 150}" r="16" fill="#fff"/><rect x="-66" y="${1700 - h - 110}" width="132" height="26" rx="13" fill="#fff"/>` : '') +
      (wave ? `<path d="M55 ${1700 - h + 40} L120 ${1700 - h - 120}" stroke="#2B3E57" stroke-width="40" stroke-linecap="round"/><circle cx="125" cy="${1700 - h - 135}" r="26" fill="#E7C9A9"/>` : '') + `</g>`;
    return `<rect width="1080" height="1920" fill="url(#blue)"/>` +
      `<rect x="120" y="760" width="840" height="560" fill="#2A3B52"/>` +
      Array.from({ length: 12 }, (_, i) => `<rect x="${170 + (i % 6) * 130}" y="${820 + Math.floor(i / 6) * 220}" width="80" height="120" fill="${WARM}" opacity=".75"/>`).join('') +
      `<path d="M0 1320 H1080 V1920 H0Z" fill="#EEF3F8"/>` +
      person(200, 380, true, true) + person(400, 420, false, false) + person(600, 400, true, true) + person(820, 370, true, false) +
      snowfall(24, 200, 1300, 5, 12, 0.7) + tag('REALDREH · Smartphone hochkant', 80, 1740, P.snow, P.ink) + overlayText(COPY.s8);
  },

  S9: () => `<rect width="1080" height="1920" fill="${P.night}"/>` + snowfall(36, 180, 1900, 4, 10, 0.45) +
    `<rect x="280" y="600" width="520" height="160" rx="12" fill="none" stroke="${P.snow}" stroke-width="6" stroke-dasharray="20 12"/>` +
    `<text x="540" y="702" text-anchor="middle" font-size="64" font-weight="800" letter-spacing="6" fill="${P.snow}">LOGO</text>` +
    `<text x="540" y="960" text-anchor="middle" font-size="96" font-weight="700" fill="${P.snow}">${esc(COPY.end_1)}</text>` +
    `<text x="540" y="1050" text-anchor="middle" font-size="54" font-weight="500" fill="${P.snow}">${esc(COPY.end_2)}</text>` +
    `<text x="540" y="1200" text-anchor="middle" font-size="52" font-weight="500" letter-spacing="2" fill="${P.gold}">${esc(COPY.claim)}</text>` +
    `<text x="540" y="1290" text-anchor="middle" font-size="54" font-weight="500" fill="${P.snow}">${esc(COPY.sign)}</text>`,
};

// Kurzbeschreibungen fürs Sheet (Details in STORYBOARD.md)
const notes = {
  S1: { bild: 'Makro Werkbank bei Nacht: Schleifstaub strömt sauber in die Absaugdüse.', ton: 'Laborraumton, Absaug-Rauschen, Pizzicato-Puls', quelle: 'generativ (Keyframe → Video)' },
  S2: { bild: 'B1 Freeze, Licht dimmt. Dann kehrt der Strom um: Staub steigt auf und wird zu Schnee.', ton: 'Klick, Musik setzt 1 Schlag aus, Glitzer-Riser', quelle: 'Freeze (Remotion) + generativ + Schnee-Layer' },
  S3: { bild: 'Werkbank unter Schnee, Gipsmodelle als verschneite Bergkette, Tilt-Shift.', ton: 'Downbeat: volle Musik, Schlittenglöckchen', quelle: 'generativ' },
  S4: { bild: 'Glühendes Wachsmesser zeichnet einen goldenen Stern, der erstarrt und aufblitzt.', ton: 'Wachs-Zischen, Glint-„Ting“ auf f300', quelle: 'generativ + MG-Linie' },
  S5: { bild: 'Wirbel im Anmischbecher wird zur Schneekugel mit Winterdorf.', ton: 'Glas-Whoosh, „Ting“ auf f380', quelle: 'generativ, Produktfoto als Referenz' },
  S6: { bild: 'Farbflash-Stakkato: pro Schlag neue Farbe und Sprache, Layout identisch.', ton: 'Glocken-Hit auf jedem Schlag, steigend', quelle: 'Motion Graphics' },
  S7: { bild: 'Schneegestöber reißt auf: Luftbild Hegau/Bodensee zur blauen Stunde.', ton: 'Whoosh, Wind, Streicher-Pad', quelle: 'echtes Drohnenmaterial, sonst generativ' },
  S8: { bild: 'Echtes Renfert-Team winkt im Schnee bzw. im Labor mit Lichterkette.', ton: 'optional O-Ton „Frohe Weihnachten!“', quelle: 'Realdreh (Fallback: Hände mit Tassen)' },
  S9: { bild: 'Endcard auf Nachtblau, feiner Schnee, gestaffelter Aufbau, dann statisch.', ton: 'Finaler Glockenschlag, Ausklang, Fade', quelle: 'Motion Graphics' },
};

const textFor = (s) => {
  if (s.id === 'S6') return COPY.s6.join(' · ');
  if (s.id === 'S9') return `${COPY.end_1} / ${COPY.end_2} / ${COPY.claim}`;
  const o = (s.overlays || []).find((x) => x.type === 'text');
  return o ? COPY[o.copy] : '–';
};

// ---------- Sheet ----------
const PW = 300, PH = 533, CW = 640, GAP = 36, COLS = 3, MX = 56;
const SW = MX * 2 + COLS * CW + (COLS - 1) * GAP;
const cells = SB.scenes.map((s) => {
  const n = notes[s.id];
  const svg = `<svg viewBox="0 0 1080 1920" width="${PW}" height="${PH}" xmlns="http://www.w3.org/2000/svg" font-family="Inter">${defs}${panels[s.id]()}${s.id === 'S6' ? '' : safeArea()}</svg>`;
  return `<div class="cell"><div class="panel">${svg}</div><div class="cap">
    <div class="id">${s.id}</div><div class="title">${esc(s.title.replace('Praezision', 'Präzision').replace('Hoehepunkt: Gruesse', 'Höhepunkt: Grüße'))}</div>
    <div class="time">f${s.frame_in}–${s.frame_out} · ${tc(s.frame_in)}–${tc(s.frame_out)} · Takt ${s.bar}</div>
    <dl><dt>Bild</dt><dd>${esc(n.bild)}</dd><dt>Text</dt><dd class="copy">${esc(textFor(s))}</dd><dt>Ton</dt><dd>${esc(n.ton)}</dd><dt>Quelle</dt><dd>${esc(n.quelle)}</dd></dl></div></div>`;
}).join('');

const total = SB.global.duration_frames;
const tlW = SW - MX * 2;
const timeline = SB.scenes.map((s, i) => {
  const x = (s.frame_in / total) * tlW, w = ((s.frame_out - s.frame_in) / total) * tlW;
  return `<div class="seg" style="left:${x}px;width:${w - 3}px;background:${['#2E5279', '#3A6390'][i % 2]}">${s.id}</div>`;
}).join('') + Array.from({ length: total / 20 + 1 }, (_, b) => `<div class="tick ${b % 4 ? '' : 'bar'}" style="left:${(b * 20 / total) * tlW}px"></div>`).join('');

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;background:#F3F1EC;font-family:Inter;color:#121212;width:${SW}px}
header{padding:48px ${MX}px 24px;display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid #121212;margin:0 0 32px}
h1{font-size:46px;margin:0;letter-spacing:-1px}h1 span{color:#8A6A2A}
.meta{font-size:21px;text-align:right;line-height:1.5;color:#333}
.grid{display:grid;grid-template-columns:repeat(${COLS},${CW}px);gap:${GAP}px;padding:0 ${MX}px}
.cell{display:flex;gap:22px;background:#fff;border:2px solid #121212;border-radius:10px;padding:16px}
.panel svg{display:block;border-radius:6px}
.cap{flex:1;font-size:18px;line-height:1.38}
.id{font-size:40px;font-weight:800;letter-spacing:-1px}.title{font-size:22px;font-weight:700;margin-bottom:4px}
.time{font-family:monospace;font-size:16px;color:#555;margin-bottom:12px}
dl{margin:0}dt{font-weight:700;font-size:14px;text-transform:uppercase;letter-spacing:1px;color:#8A6A2A;margin-top:9px}dd{margin:2px 0 0}
dd.copy{font-weight:600}
.tl{position:relative;height:64px;margin:40px ${MX}px 12px}
.seg{position:absolute;top:0;height:44px;border-radius:4px;color:#fff;font-weight:700;font-size:18px;display:flex;align-items:center;justify-content:center}
.tick{position:absolute;top:46px;width:2px;height:8px;background:#999}.tick.bar{height:16px;background:#121212}
footer{padding:0 ${MX}px 44px;font-size:17px;color:#555;display:flex;justify-content:space-between}
</style></head><body>
<header><h1>Renfert GmbH · Weihnachtsgruß 2026 · <span>„Heute darf es stauben“</span></h1>
<div class="meta">9:16 · 1080×1920 · 30 fps · ${(total / FPS).toFixed(1).replace('.', ',')} s<br>${SB.music.bpm} BPM · 1 Schlag = ${SB.music.frames_per_beat} f · 1 Takt = ${SB.music.frames_per_bar} f</div></header>
<div class="grid">${cells}</div>
<div class="tl">${timeline}</div>
<footer><span>Timeline: kleine Striche = Schläge (20 f), große = Takte (80 f). Gestrichelter Rahmen = Safe Area.</span><span>Farben und Schrift sind Platzhalter bis zur Renfert-CI · Details: STORYBOARD.md / storyboard.json</span></footer>
</body></html>`;

(async () => {
  fs.writeFileSync(path.join(OUT, 'storyboard_sheet.html'), html);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: SW, height: 1000 }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'load' });
  await page.screenshot({ path: path.join(OUT, 'storyboard_sheet.png'), fullPage: true });
  await browser.close();
  fs.unlinkSync(path.join(OUT, 'storyboard_sheet.html'));
  console.log('ok', path.join(OUT, 'storyboard_sheet.png'));
})();
