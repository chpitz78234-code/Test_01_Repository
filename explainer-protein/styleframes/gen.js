// Erzeugt 6 Styleframes (Stil A + B, je 3 Skriptstellen) als HTML/SVG und rendert sie als PNG.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT = process.argv[2] || __dirname;
const W = 1080, H = 1920;

// ---------- Stil A: Neo-Brutalismus ----------
const A = { bg: '#F4F4F0', pink: '#FF90E8', yellow: '#FFC900', peri: '#90A8ED', periL: '#BCC2FE', teal: '#23A094', orange: '#FF7051', ink: '#000', white: '#FFFFFF' };
const SW_UI = 3, SW_ILL = 4, SHADOW = 6;

const fontCss = `
@font-face{font-family:Anton;src:url(fonts/Anton-400.woff2)}
@font-face{font-family:SpaceMono;font-weight:400;src:url(fonts/SpaceMono-400.woff2)}
@font-face{font-family:SpaceMono;font-weight:700;src:url(fonts/SpaceMono-700.woff2)}
html,body{margin:0;padding:0;width:${W}px;height:${H}px;overflow:hidden}
svg{display:block}
.disp{font-family:Anton;text-transform:uppercase}
.mono{font-family:SpaceMono;font-weight:700}
.body{font-family:Inter;font-weight:400}`;

const page = (svg) => `<!doctype html><html><head><meta charset="utf-8"><style>${fontCss}</style></head><body>${svg}</body></html>`;

const card = (x, y, w, h, fill = A.bg, shadow = false) =>
  (shadow ? `<rect x="${x + SHADOW}" y="${y + SHADOW}" width="${w}" height="${h}" rx="6" fill="${A.ink}"/>` : '') +
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="6" fill="${fill}" stroke="${A.ink}" stroke-width="${SW_UI}"/>`;

const chapterTag = (label) =>
  card(60, 190, 24 + label.length * 17.2, 62, A.white) +
  `<text x="78" y="231" class="mono" font-size="28">${label}</text>`;

const headline = (l1, l2, y = 440, size = 196) =>
  `<text x="54" y="${y}" class="disp" font-size="${size}" letter-spacing="1">${l1}</text>` +
  `<text x="54" y="${y + size * 0.9}" class="disp" font-size="${size}" letter-spacing="1">${l2}</text>`;

const bodyLines = (lines, x, y, size = 40, lh = 1.3) =>
  lines.map((l, i) => `<text x="${x}" y="${y + i * size * lh}" class="body" font-size="${size}">${l}</text>`).join('');

const arrowNE = (x, y, s = 28, sw = 4) =>
  `<path d="M${x} ${y + s} L${x + s} ${y} M${x + s * 0.3} ${y} L${x + s} ${y} L${x + s} ${y + s * 0.7}" fill="none" stroke="${A.ink}" stroke-width="${sw}" stroke-linecap="square"/>`;

// Kreis-Union mit gemeinsamer Kontur: erst alle Kreise dick schwarz, dann gefüllt darüber
const blobUnion = (circles, fill, sw = SW_ILL) =>
  circles.map(([cx, cy, r]) => `<circle cx="${cx}" cy="${cy}" r="${r + sw / 2}" fill="${A.ink}"/>`).join('') +
  circles.map(([cx, cy, r]) => `<circle cx="${cx}" cy="${cy}" r="${r - sw / 2}" fill="${fill}"/>`).join('');

// Outline-Linie (Arme, Beine, Antikörper): schwarzer breiter Strich, Farbe darüber
const outlinedStroke = (d, color, w, sw = SW_ILL) =>
  `<path d="${d}" fill="none" stroke="${A.ink}" stroke-width="${w + sw * 2}" stroke-linecap="round" stroke-linejoin="round"/>` +
  `<path d="${d}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;

// Gesichtslose pinke Blob-Figur (wie die Figur der Bildreferenz)
function blobFigure(x, y, s = 1, shirt = A.yellow, armTo = null, mirror = false) {
  const k = (v) => v * s;
  let g = `<g transform="translate(${x} ${y})${mirror ? ' scale(-1 1)' : ''}">`;
  // Beine
  g += outlinedStroke(`M${k(-22)} ${k(150)} L${k(-28)} ${k(230)}`, A.pink, k(24));
  g += outlinedStroke(`M${k(22)} ${k(150)} L${k(30)} ${k(230)}`, A.pink, k(24));
  // Arme
  const arm = armTo ? `M${k(40)} ${k(70)} Q${k(80)} ${k(60)} ${armTo[0]} ${armTo[1]}` : `M${k(40)} ${k(70)} L${k(95)} ${k(20)}`;
  g += outlinedStroke(arm, A.pink, k(22));
  g += outlinedStroke(`M${k(-40)} ${k(70)} Q${k(-80)} ${k(110)} ${k(-70)} ${k(150)}`, A.pink, k(22));
  // Körper / Shirt
  g += `<path d="M${k(-52)} ${k(40)} Q${k(0)} ${k(20)} ${k(52)} ${k(40)} L${k(58)} ${k(160)} L${k(-58)} ${k(160)} Z" fill="${shirt}" stroke="${A.ink}" stroke-width="${SW_ILL}" stroke-linejoin="round"/>`;
  // Kopf: wolkige Kreis-Union
  g += blobUnion([[0, k(-40), k(58)], [k(-38), k(-80), k(34)], [k(4), k(-108), k(38)], [k(42), k(-78), k(32)], [k(-50), k(-30), k(28)], [k(48), k(-30), k(28)]], A.pink);
  return g + '</g>';
}

const motionDashes = (x, y, rot = 0) =>
  `<g transform="translate(${x} ${y}) rotate(${rot})" stroke="${A.ink}" stroke-width="5" stroke-linecap="round">` +
  `<line x1="0" y1="0" x2="34" y2="-8"/><line x1="4" y1="22" x2="30" y2="20"/><line x1="10" y1="-26" x2="26" y2="-34"/></g>`;

function speechBubble(x, y, w, h, lines, tailX, tailY) {
  return `<path d="M${x + 30} ${y + h} L${tailX} ${tailY} L${x + 80} ${y + h}" fill="${A.white}" stroke="${A.ink}" stroke-width="${SW_UI}" stroke-linejoin="round"/>` +
    card(x, y, w, h, A.white) +
    `<rect x="${x + 32}" y="${y + h - 4}" width="46" height="8" fill="${A.white}"/>` +
    lines.map((l, i) => `<text x="${x + w / 2}" y="${y + 46 + i * 36}" text-anchor="middle" class="mono" font-size="28">${l}</text>`).join('');
}

// ---------- A1: Aminosäuren-Kette (5–15 s) ----------
function A1() {
  let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="${A.bg}"/>`;
  s += chapterTag('02 — WAS SIND PROTEINE?');
  s += headline('BAUSTEINE', 'DES LEBENS');
  s += bodyLines(['Aminosäuren – aufgereiht', 'wie Perlen an einer Kette.'], 60, 712);
  // Stufen-Fläche wie im Hero der Referenz
  s += `<path d="M330 1340 L330 1060 L410 1060 L410 980 L490 980 L490 900 L1080 900 L1080 1340 Z" fill="${A.periL}" stroke="${A.ink}" stroke-width="${SW_UI}"/>`;
  const labels = ['LEU', 'GLY', 'LYS', 'MET', 'ALA', 'PHE', 'THR', 'TRP', 'SER', 'VAL', 'HIS', 'ILE'];
  const essential = new Set(['LEU', 'LYS', 'MET', 'PHE', 'THR', 'TRP', 'VAL', 'HIS', 'ILE']);
  const pts = [
    ...[0, 1, 2, 3, 4, 5].map((i) => [780 - i * 126, 990 + Math.sin(i * 1.3) * 16]),
    [178, 1118],
    ...[0, 1, 2, 3, 4].map((j) => [300 + j * 126, 1236 + Math.sin(j * 1.3) * 14]),
  ];
  s += `<polyline points="${pts.map((p) => p.join(',')).join(' ')}" fill="none" stroke="${A.ink}" stroke-width="7" stroke-linejoin="round"/>`;
  pts.forEach(([x, y], i) => {
    const fill = essential.has(labels[i]) ? A.pink : A.white;
    s += `<circle cx="${x + SHADOW}" cy="${y + SHADOW}" r="50" fill="${A.ink}"/>`;
    s += `<circle cx="${x}" cy="${y}" r="50" fill="${fill}" stroke="${A.ink}" stroke-width="${SW_ILL}"/>`;
    s += `<text x="${x}" y="${y + 9}" text-anchor="middle" class="mono" font-size="26">${labels[i]}</text>`;
  });
  s += blobFigure(950, 1060, 0.95, A.yellow, [950 - pts[0][0] - 46, pts[0][1] - 1060 + 4], true);
  s += motionDashes(60, 930, -10) + motionDashes(812, 872, -25);
  // Bento-Zeile
  s += card(60, 1388, 450, 206);
  s += `<text x="88" y="1444" class="mono" font-size="30">20 AMINOSÄUREN</text>`;
  s += bodyLines(['bauen alle Proteine', 'deines Körpers.'], 88, 1494, 32, 1.25);
  s += arrowNE(88, 1544, 24, 4);
  s += card(540, 1388, 480, 206, A.yellow);
  s += `<text x="568" y="1444" class="mono" font-size="26">ESSENZIELL.</text>`;
  s += `<text x="566" y="1580" class="disp" font-size="136">9</text>`;
  s += `<text x="660" y="1500" class="mono" font-size="25">MUSST DU</text><text x="660" y="1534" class="mono" font-size="25">ESSEN.</text>`;
  for (let i = 0; i < 9; i++) s += `<circle cx="${670 + i * 37}" cy="${1566}" r="13" fill="${A.pink}" stroke="${A.ink}" stroke-width="3"/>`;
  return s + '</svg>';
}

// ---------- A2: Antikörper (15–32 s) ----------
function A2() {
  let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="${A.bg}"/>`;
  s += chapterTag('03 — MULTITALENTE');
  s += headline('DEINE', 'LEIBWACHE');
  s += bodyLines(['Als Antikörper verteidigen', 'Proteine dich gegen Viren.'], 60, 712);
  const cx = 600, cy = 1100, R = 285;
  s += `<defs><clipPath id="vig"><circle cx="${cx}" cy="${cy}" r="${R}"/></clipPath></defs>`;
  s += `<circle cx="${cx + SHADOW}" cy="${cy + SHADOW}" r="${R}" fill="${A.ink}"/><circle cx="${cx}" cy="${cy}" r="${R}" fill="${A.yellow}"/>`;
  s += `<g clip-path="url(#vig)">`;
  s += `<path d="M${cx - R} ${cy + 150} L${cx - 120} ${cy + 150} L${cx - 120} ${cy + 110} L${cx + 40} ${cy + 110} L${cx + 40} ${cy + 170} L${cx + R} ${cy + 170} L${cx + R} ${cy + R} L${cx - R} ${cy + R} Z" fill="${A.periL}" stroke="${A.ink}" stroke-width="${SW_UI}"/>`;
  // Virus
  const vx = cx + 10, vy = cy - 10, vr = 92;
  const spikes = 11;
  for (let i = 0; i < spikes; i++) {
    const a = (i / spikes) * Math.PI * 2 + 0.2;
    const x1 = vx + Math.cos(a) * vr, y1 = vy + Math.sin(a) * vr;
    const x2 = vx + Math.cos(a) * (vr + 44), y2 = vy + Math.sin(a) * (vr + 44);
    s += outlinedStroke(`M${x1} ${y1} L${x2} ${y2}`, A.teal, 12);
    s += `<circle cx="${x2}" cy="${y2}" r="17" fill="${A.pink}" stroke="${A.ink}" stroke-width="${SW_ILL}"/>`;
  }
  s += `<circle cx="${vx}" cy="${vy}" r="${vr}" fill="${A.teal}" stroke="${A.ink}" stroke-width="${SW_ILL}"/>`;
  [[-30, -25, 16], [28, 20, 12], [-10, 40, 9], [35, -35, 8]].forEach(([dx, dy, r]) =>
    s += `<circle cx="${vx + dx}" cy="${vy + dy}" r="${r}" fill="${A.bg}" stroke="${A.ink}" stroke-width="3"/>`);
  // Antikörper (Y-Form), greifen zwischen die Spikes
  [-2.35, -0.55, 1.25, 2.6].forEach((a) => {
    const d = (r) => [vx + Math.cos(a) * r, vy + Math.sin(a) * r];
    const side = (r, off) => [vx + Math.cos(a + off) * r, vy + Math.sin(a + off) * r];
    const J = d(vr + 118), S = d(vr + 205), T1 = side(vr + 30, 0.33), T2 = side(vr + 30, -0.33);
    s += outlinedStroke(`M${S[0]} ${S[1]} L${J[0]} ${J[1]} M${T1[0]} ${T1[1]} L${J[0]} ${J[1]} L${T2[0]} ${T2[1]}`, A.peri, 24);
  });
  s += `</g><circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="${A.ink}" stroke-width="${SW_ILL}"/>`;
  s += motionDashes(cx + R + 10, cy - R + 60, 30) + motionDashes(cx + R - 30, cy + R - 20, 110);
  s += blobFigure(170, 1180, 0.9, A.peri, [-20 + 95, -50]);
  s += speechBubble(60, 842, 330, 118, ['KEIN ZUTRITT', 'FÜR VIREN!'], 150, 1020);
  // Bento 2×2: Aufgaben der Proteine, aktive Aufgabe hervorgehoben
  const items = [['MUSKELN & GEWEBE', false], ['SAUERSTOFF', false], ['ENZYME', false], ['ABWEHR', true]];
  items.forEach(([t, active], i) => {
    const x = 60 + (i % 2) * 495, y = 1418 + Math.floor(i / 2) * 104;
    s += card(x, y, 465, 86, active ? A.pink : A.bg, active);
    s += `<circle cx="${x + 40}" cy="${y + 43}" r="17" fill="${active ? A.white : A.pink}" stroke="${A.ink}" stroke-width="3"/>`;
    s += `<path d="M${x + 31} ${y + 43} L${x + 38} ${y + 51} L${x + 50} ${y + 35}" fill="none" stroke="${A.ink}" stroke-width="4"/>`;
    s += `<text x="${x + 74}" y="${y + 53}" class="mono" font-size="27">${t}</text>`;
    if (active) s += arrowNE(x + 418, y + 30, 24, 4);
  });
  return s + '</svg>';
}

// ---------- A3: Praxis-Tipps (40–52 s) ----------
function food(kind, x, y) {
  const o = `stroke="${A.ink}" stroke-width="${SW_ILL}" stroke-linejoin="round"`;
  switch (kind) {
    case 'EIER':
      return `<ellipse cx="${x - 40}" cy="${y + 4}" rx="44" ry="56" fill="${A.white}" ${o}/>` +
        `<path d="M${x + 6} ${y + 30} Q${x - 10} ${y - 40} ${x + 50} ${y - 30} Q${x + 110} ${y - 30} ${x + 100} ${y + 30} Q${x + 60} ${y + 60} ${x + 6} ${y + 30} Z" fill="${A.white}" ${o}/>` +
        `<circle cx="${x + 54}" cy="${y + 4}" r="22" fill="${A.yellow}" ${o}/>`;
    case 'QUARK':
      return `<path d="M${x - 70} ${y - 20} L${x + 70} ${y - 20} L${x + 56} ${y + 56} L${x - 56} ${y + 56} Z" fill="${A.peri}" ${o}/>` +
        `<path d="M${x - 64} ${y - 20} Q${x - 40} ${y - 70} ${x} ${y - 52} Q${x + 40} ${y - 74} ${x + 64} ${y - 20} Z" fill="${A.white}" ${o}/>` +
        `<rect x="${x - 34}" y="${y + 6}" width="68" height="24" fill="${A.white}" ${o}/>`;
    case 'FISCH':
      return `<path d="M${x + 50} ${y} L${x + 100} ${y - 34} L${x + 100} ${y + 34} Z" fill="${A.teal}" ${o}/>` +
        `<ellipse cx="${x - 10}" cy="${y}" rx="72" ry="40" fill="${A.teal}" ${o}/>` +
        `<path d="M${x + 6} ${y - 30} Q${x - 4} ${y} ${x + 6} ${y + 30}" fill="none" ${o}/>` +
        `<circle cx="${x - 48}" cy="${y - 8}" r="8" fill="${A.ink}"/>`;
    case 'LINSEN': {
      let g = `<path d="M${x - 78} ${y - 4} Q${x} ${y + 100} ${x + 78} ${y - 4} Z" fill="${A.peri}" ${o}/>`;
      const pts = [[-52, -14], [-26, -22], [0, -26], [26, -22], [52, -14], [-38, -38], [-12, -46], [14, -46], [38, -38], [-24, -62], [2, -68], [26, -60]];
      pts.forEach(([dx, dy]) => g += `<ellipse cx="${x + dx}" cy="${y + dy}" rx="15" ry="11" fill="${A.yellow}" stroke="${A.ink}" stroke-width="3"/>`);
      return g;
    }
    case 'BOHNEN': {
      const bean = (bx, by, r) => `<g transform="translate(${bx} ${by}) rotate(${r})"><path d="M-46 2 C-48 -22 -26 -26 -12 -18 C-4 -14 4 -14 12 -18 C26 -26 48 -22 46 2 C44 24 22 26 0 26 C-22 26 -44 24 -46 2 Z" fill="${A.orange}" ${o}/>` +
        `<ellipse cx="0" cy="-10" rx="7" ry="4" fill="${A.white}" stroke="${A.ink}" stroke-width="2.5"/></g>`;
      return bean(x - 44, y - 16, -12) + bean(x + 42, y - 22, 16) + bean(x + 2, y + 30, 4);
    }
    case 'TOFU':
      return `<path d="M${x - 60} ${y - 22} L${x} ${y - 52} L${x + 66} ${y - 26} L${x + 6} ${y + 6} Z" fill="${A.white}" ${o}/>` +
        `<path d="M${x - 60} ${y - 22} L${x + 6} ${y + 6} L${x + 6} ${y + 66} L${x - 60} ${y + 38} Z" fill="${A.bg}" ${o}/>` +
        `<path d="M${x + 6} ${y + 6} L${x + 66} ${y - 26} L${x + 66} ${y + 36} L${x + 6} ${y + 66} Z" fill="${A.periL}" ${o}/>`;
  }
}

function A3() {
  let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="${A.bg}"/>`;
  s += chapterTag('05 — PRAXIS-TIPPS');
  s += headline('WIE VIEL', 'PROTEIN?', 420, 180);
  // KPI-Karte wie „Real creators. Real income.“
  const ky = 620, kh = 360;
  s += card(60, ky, 960, kh, A.yellow);
  s += `<text x="96" y="${ky + 62}" class="mono" font-size="30">FAUSTREGEL FÜR</text><text x="96" y="${ky + 100}" class="mono" font-size="30">ERWACHSENE.</text>`;
  s += `<text x="90" y="${ky + 260}" class="disp" font-size="170">0,8 G</text>`;
  s += `<text x="96" y="${ky + 306}" class="mono" font-size="26">PRO KG KÖRPERGEWICHT</text><text x="96" y="${ky + 340}" class="mono" font-size="26">AM TAG.</text>`;
  const kg = [50, 60, 70, 80, 90];
  kg.forEach((k, i) => {
    const h = k * 0.8 * 3.4, x = 600 + i * 80, base = ky + kh - 52;
    s += `<rect x="${x}" y="${base - h}" width="64" height="${h}" fill="${A.ink}"/>`;
    s += `<text x="${x + 32}" y="${base - h - 12}" text-anchor="middle" class="mono" font-size="20">${Math.round(k * 0.8)}G</text>`;
    s += `<text x="${x + 32}" y="${base + 32}" text-anchor="middle" class="mono" font-size="20">${k}KG</text>`;
  });
  // Lebensmittel-Bento
  const foods = ['EIER', 'QUARK', 'FISCH', 'LINSEN', 'BOHNEN', 'TOFU'];
  foods.forEach((f, i) => {
    const x = 60 + (i % 3) * 330, y = 1012 + Math.floor(i / 3) * 236;
    s += card(x, y, 300, 216, A.bg);
    s += `<g>${food(f, x + 150, y + 92)}</g>`;
    s += `<text x="${x + 22}" y="${y + 196}" class="mono" font-size="26">${f}</text>`;
  });
  // CTA-Button Profi-Tipp
  const by = 1494;
  s += `<rect x="60" y="${by}" width="960" height="96" rx="6" fill="${A.ink}"/>`;
  s += `<text x="96" y="${by + 60}" class="mono" font-size="30" fill="${A.white}">PROFI-TIPP: LINSEN + REIS</text>`;
  s += `<path d="M960 ${by + 64} L988 ${by + 36} M970 ${by + 36} L988 ${by + 36} L988 ${by + 54}" stroke="${A.white}" stroke-width="4" fill="none"/>`;
  return s + '</svg>';
}

// ---------- Stil B: Soft-Gradient-Surreal ----------
const seamX = (y) => 640 + 38 * Math.sin(y / 230 + 0.6);
const seamPts = () => { const p = []; for (let y = -20; y <= H + 20; y += 20) p.push([seamX(y), y]); return p; };
const rightPoly = () => [...seamPts(), [W + 40, H + 20], [W + 40, -20]].map((p) => p.join(',')).join(' ');
const leftPoly = () => [[-40, -20], ...seamPts(), [-40, H + 20]].map((p) => p.join(',')).join(' ');

const bDefs = `
<linearGradient id="stage" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FDDCD7"/><stop offset=".55" stop-color="#FBCBC8"/><stop offset="1" stop-color="#FCDEDE"/></linearGradient>
<radialGradient id="g-sunset" cx=".42" cy=".38" r=".7" fx=".33" fy=".28"><stop offset="0" stop-color="#FFF0B0"/><stop offset=".22" stop-color="#FCCC5C"/><stop offset=".6" stop-color="#E8455A"/><stop offset="1" stop-color="#6A2C8C"/></radialGradient>
<radialGradient id="g-cyan" cx=".42" cy=".38" r=".7" fx=".33" fy=".28"><stop offset="0" stop-color="#C8F8FF"/><stop offset=".35" stop-color="#28C4E8"/><stop offset=".8" stop-color="#749CDC"/><stop offset="1" stop-color="#7E7FD0"/></radialGradient>
<radialGradient id="g-indigo" cx=".42" cy=".38" r=".7" fx=".33" fy=".28"><stop offset="0" stop-color="#B4BCFF"/><stop offset=".45" stop-color="#5C6CFC"/><stop offset="1" stop-color="#3D2F9E"/></radialGradient>
<radialGradient id="g-yellow" cx=".42" cy=".38" r=".7" fx=".33" fy=".28"><stop offset="0" stop-color="#FFFCD8"/><stop offset=".4" stop-color="#FCEC2C"/><stop offset="1" stop-color="#F0A21B"/></radialGradient>
<radialGradient id="g-pink" cx=".42" cy=".38" r=".7" fx=".33" fy=".28"><stop offset="0" stop-color="#FFEFF3"/><stop offset=".5" stop-color="#F7A1B5"/><stop offset="1" stop-color="#C95A78"/></radialGradient>
<radialGradient id="g-egg" cx=".4" cy=".35" r=".75" fx=".32" fy=".25"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".6" stop-color="#FFF3E6"/><stop offset="1" stop-color="#E9C2B6"/></radialGradient>
<linearGradient id="box-front" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3E3FC4"/><stop offset=".32" stop-color="#4B52DC"/><stop offset=".33" stop-color="#5A66F2"/><stop offset="1" stop-color="#7C88FF"/></linearGradient>
<linearGradient id="box-top" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8D97FF"/><stop offset="1" stop-color="#6670F0"/></linearGradient>
<linearGradient id="box-side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3A2F9E"/><stop offset="1" stop-color="#2B2580"/></linearGradient>
<linearGradient id="tofu-front" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFBF2"/><stop offset="1" stop-color="#EEDFCF"/></linearGradient>
<linearGradient id="tofu-side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#E3CDBB"/><stop offset="1" stop-color="#D2B8A6"/></linearGradient>
<filter id="dof" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="46"/></filter>
<filter id="dof-s" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="22"/></filter>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.2"/><feColorMatrix type="saturate" values=".82"/></filter>
<filter id="shade" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
<clipPath id="right"><polygon points="${rightPoly()}"/></clipPath>
<clipPath id="left"><polygon points="${leftPoly()}"/></clipPath>`;

const sphere = (cx, cy, r, g) =>
  `<circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#${g})"/>` +
  `<ellipse cx="${cx - r * 0.34}" cy="${cy - r * 0.4}" rx="${r * 0.22}" ry="${r * 0.13}" fill="#fff" opacity=".55" transform="rotate(-30 ${cx - r * 0.34} ${cy - r * 0.4})"/>`;

// Doppelte „Googly Eyes“: zwei weiße Ovale, schwarze Pupillen in Blickrichtung
const eyes = (cx, cy, s = 1, look = [0.3, 0.2]) => {
  const e = (x) => `<ellipse cx="${x}" cy="${cy}" rx="${24 * s}" ry="${29 * s}" fill="#fff"/>` +
    `<circle cx="${x + look[0] * 12 * s}" cy="${cy + look[1] * 14 * s}" r="${13 * s}" fill="#1B1730"/>` +
    `<circle cx="${x + look[0] * 12 * s - 4 * s}" cy="${cy + look[1] * 14 * s - 5 * s}" r="${3.5 * s}" fill="#fff"/>`;
  return `<ellipse cx="${cx + 2}" cy="${cy + 6 * s}" rx="${50 * s}" ry="${30 * s}" fill="#2A1E5C" opacity=".18" filter="url(#dof-s)"/>` + e(cx - 23 * s) + e(cx + 23 * s);
};

const tube = (d, w = 46) =>
  `<path d="${d}" fill="none" stroke="#3D2F9E" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" transform="translate(5 7)"/>` +
  `<path d="${d}" fill="none" stroke="#5C6CFC" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>` +
  `<path d="${d}" fill="none" stroke="#A3ADFF" stroke-width="${w * 0.28}" stroke-linecap="round" stroke-linejoin="round" opacity=".75" transform="translate(-${w * 0.18} -${w * 0.18})"/>`;

const sparkle = (x, y, s = 1) => `<path d="M${x} ${y - 16 * s} Q${x + 3 * s} ${y - 3 * s} ${x + 9 * s} ${y} Q${x + 3 * s} ${y + 3 * s} ${x} ${y + 16 * s} Q${x - 3 * s} ${y + 3 * s} ${x - 9 * s} ${y} Q${x - 3 * s} ${y - 3 * s} ${x} ${y - 16 * s} Z" fill="#FCEC2C" opacity=".9"/>`;
const bubble = (x, y, r) => `<circle cx="${x}" cy="${y}" r="${r}" fill="none" stroke="#fff" stroke-width="2.5" opacity=".85"/>`;
const tinySquare = (x, y, r = 0) => `<rect x="${x}" y="${y}" width="16" height="16" fill="none" stroke="#fff" stroke-width="2.5" opacity=".8" transform="rotate(${r} ${x + 8} ${y + 8})"/>`;
const squiggle = (x1, y1, x2, y2, amp = 18, waves = 5) => {
  let d = `M${x1} ${y1}`; const n = 60;
  for (let i = 1; i <= n; i++) {
    const t = i / n, x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
    const nx = -(y2 - y1), ny = x2 - x1, l = Math.hypot(nx, ny);
    const o = Math.sin(t * Math.PI * 2 * waves) * amp;
    d += ` L${(x + nx / l * o).toFixed(1)} ${(y + ny / l * o).toFixed(1)}`;
  }
  return `<path d="${d}" fill="none" stroke="#3446B8" stroke-width="4" stroke-linecap="round"/>`;
};

function box(x, y, w, h, d) {
  return `<ellipse cx="${x + w / 2 + 20}" cy="${y + h + 26}" rx="${w * 0.62}" ry="26" fill="#9E3D5A" opacity=".22" filter="url(#shade)"/>` +
    `<path d="M${x} ${y} L${x + d} ${y - d * 0.7} L${x + w + d} ${y - d * 0.7} L${x + w} ${y} Z" fill="url(#box-top)"/>` +
    `<path d="M${x + w} ${y} L${x + w + d} ${y - d * 0.7} L${x + w + d} ${y + h - d * 0.7} L${x + w} ${y + h} Z" fill="url(#box-side)"/>` +
    `<path d="M${x} ${y} L${x + w} ${y} L${x + w} ${y + h} Q${x + w / 2} ${y + h + 18} ${x} ${y + h} Z" fill="url(#box-front)"/>`;
}

// Hintergrund-Bühne mit Tiefenunschärfe und Wolken rechts
function stage() {
  return `<rect width="${W}" height="${H}" fill="url(#stage)"/>` +
    `<g filter="url(#dof-s)" fill="#FDFBFC" opacity=".95">` +
    [[880, 420, 170], [1010, 640, 190], [860, 900, 160], [1000, 1180, 200], [880, 1460, 170], [1020, 1720, 200]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}"/>`).join('') + `</g>` +
    `<g filter="url(#dof-s)" fill="#F6B9B7" opacity=".55"><ellipse cx="300" cy="1200" rx="260" ry="520"/></g>`;
}

function foregroundBlur() {
  return `<g filter="url(#dof)">` +
    `<ellipse cx="60" cy="40" rx="420" ry="260" fill="#CB5861" opacity=".9"/>` +
    `<ellipse cx="560" cy="-40" rx="300" ry="150" fill="#E07C83" opacity=".8"/>` +
    `<ellipse cx="-20" cy="1860" rx="320" ry="220" fill="#CB5861" opacity=".75"/>` +
    `<ellipse cx="760" cy="1980" rx="360" ry="170" fill="#E9A3A6" opacity=".8"/></g>`;
}

// Milchglas: links Originalobjekte, rechts versetzte, entsättigte Kopie unter weißem Schleier
function frostedComposite(objects) {
  const seam = seamPts();
  const beads = [];
  for (let y = 40; y < H; y += 74) beads.push(`<circle cx="${seamX(y)}" cy="${y}" r="4.5" fill="#F3C7CB"/>`);
  return `<g id="objs-left" clip-path="url(#left)">${objects}</g>` +
    `<g clip-path="url(#right)"><rect width="${W}" height="${H}" fill="#fff" opacity=".32"/>` +
    `<g transform="translate(18 -10)" filter="url(#soft)" opacity=".92">${objects}</g>` +
    `<rect width="${W}" height="${H}" fill="#fff" opacity=".18"/></g>` +
    `<polyline points="${seam.map((p) => p.join(',')).join(' ')}" fill="none" stroke="#E9B5BB" stroke-width="2.5"/>` + beads.join('');
}

const bSvg = (objects, extraFront = '') =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><defs>${bDefs}</defs>` +
  stage() + frostedComposite(objects) + extraFront + foregroundBlur() + '</svg>';

// ---------- B1: Aminosäuren-Kette entsteht aus der Box ----------
function B1() {
  let o = '';
  o += squiggle(560, -20, 548, 300, 14, 3) + sphere(548, 330, 50, 'g-sunset');
  o += box(110, 600, 270, 320, 70);
  o += eyes(305, 800, 1.05, [-0.6, 0.5]);
  // Kette aus „Perlen“ (Aminosäuren) schlängelt sich aus der Box
  const grads = ['g-sunset', 'g-cyan', 'g-yellow', 'g-pink', 'g-indigo', 'g-sunset', 'g-cyan', 'g-yellow', 'g-pink', 'g-cyan', 'g-sunset', 'g-indigo'];
  const radii = grads.map((_, i) => (i === grads.length - 1 ? 70 : 32 + (i % 3) * 6));
  const curve = (t) => [395 + t * 430 + Math.sin(t * Math.PI * 2.6) * 150, 830 + t * 780];
  const samples = Array.from({ length: 2001 }, (_, i) => curve(i / 2000));
  const pts = []; let k = 0, need = radii[0];
  for (let i = 1, acc = 0; i < samples.length && pts.length < radii.length; i++) {
    acc += Math.hypot(samples[i][0] - samples[i - 1][0], samples[i][1] - samples[i - 1][1]);
    if (acc >= need) { pts.push(samples[i]); k++; need = acc + radii[k - 1] + (radii[k] || 0) + 10; }
  }
  o += `<polyline points="${[curve(0), ...pts].map((p) => p.join(',')).join(' ')}" fill="none" stroke="#3446B8" stroke-width="4"/>`;
  pts.forEach(([x, y], i) => {
    const r = radii[i];
    o += `<ellipse cx="${x + 10}" cy="${y + r * 0.9}" rx="${r * 0.8}" ry="${r * 0.25}" fill="#9E3D5A" opacity=".18" filter="url(#shade)"/>`;
    o += sphere(x, y, r, grads[i]);
  });
  const h = pts[pts.length - 1];
  o += eyes(h[0], h[1] - 8, 1.1, [-0.4, -0.6]);
  o += sparkle(470, 560, 1.2) + sparkle(160, 1080, 0.9) + sparkle(720, 760, 0.8) + sparkle(300, 1420, 1);
  o += bubble(470, 470, 14) + bubble(500, 420, 9) + bubble(230, 1220, 12) + tinySquare(780, 1180, 20) + tinySquare(180, 1320, -15) + tinySquare(600, 1700, 10);
  return bSvg(o);
}

// ---------- B2: Antikörper umzingeln das Virus ----------
function B2() {
  let o = '';
  // Zelle (Cyan) halb hinter dem Milchglas
  o += sphere(760, 520, 140, 'g-cyan') + eyes(700, 520, 1, [-0.8, 0.3]);
  // Virus mit Noppen
  const vx = 430, vy = 1050, vr = 165;
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 + 0.15;
    const x = vx + Math.cos(a) * (vr + 26), y = vy + Math.sin(a) * (vr + 26);
    o += `<path d="M${vx + Math.cos(a) * vr} ${vy + Math.sin(a) * vr} L${x} ${y}" stroke="#8C3A6E" stroke-width="16" stroke-linecap="round"/>`;
    o += sphere(x, y, 26, 'g-sunset');
  }
  o += `<ellipse cx="${vx + 20}" cy="${vy + vr + 50}" rx="${vr}" ry="34" fill="#9E3D5A" opacity=".2" filter="url(#shade)"/>`;
  o += sphere(vx, vy, vr, 'g-sunset') + eyes(vx + 10, vy - 10, 1.25, [0.7, -0.3]);
  // Antikörper als weiche 3D-Röhren in Y-Form
  [[-0.95, 1], [0.15, 1], [1.45, 1], [2.75, 0.95]].forEach(([a, sc]) => {
    const d = (r, off = 0) => [vx + Math.cos(a + off) * r, vy + Math.sin(a + off) * r];
    const T1 = d(vr + 70, 0.2), T2 = d(vr + 70, -0.2), J = d(vr + 175), S = d(vr + 300);
    o += tube(`M${T1[0]} ${T1[1]} L${J[0]} ${J[1]} L${T2[0]} ${T2[1]} M${J[0]} ${J[1]} L${S[0]} ${S[1]}`, 44 * sc);
    o += eyes(J[0], J[1], 0.62, [-Math.cos(a), -Math.sin(a)]);
  });
  o += sparkle(820, 860, 1.1) + sparkle(140, 700, 0.9) + sparkle(700, 1500, 1.2) + sparkle(260, 1560, 0.8);
  o += bubble(860, 1300, 16) + bubble(900, 1250, 9) + bubble(120, 1300, 12) + tinySquare(620, 760, 25) + tinySquare(200, 520, -10);
  return bSvg(o);
}

// ---------- B3: Proteinquellen – Box schüttet Linsen aus, Ei und Tofu ----------
function B3() {
  let o = '';
  // gekippte, offene Box (wie die Schublade im Referenzvideo)
  o += `<g transform="rotate(-14 260 620)">${box(120, 520, 260, 220, 70)}` +
    `<path d="M120 520 L190 471 L450 471 L380 520 Z" fill="#2B2580"/>` + `</g>`;
  o += eyes(250, 690, 0.95, [0.7, 0.6]);
  // Linsen-Kaskade
  let seed = 7; const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
  for (let i = 0; i < 46; i++) {
    const t = rnd();
    const x = 400 + t * 420 + (rnd() - 0.5) * 120, y = 600 + t * 760 + (rnd() - 0.5) * 140;
    o += sphere(x, y, 12 + rnd() * 10, rnd() > 0.25 ? 'g-yellow' : 'g-sunset');
  }
  // Ei-Charakter über der Naht
  const ex = 690, ey = 1010;
  o += `<ellipse cx="${ex + 20}" cy="${ey + 205}" rx="150" ry="30" fill="#9E3D5A" opacity=".2" filter="url(#shade)"/>`;
  o += `<path d="M${ex} ${ey - 200} C${ex + 130} ${ey - 200} ${ex + 170} ${ey + 40} ${ex + 150} ${ey + 110} C${ex + 120} ${ey + 210} ${ex - 120} ${ey + 210} ${ex - 150} ${ey + 110} C${ex - 170} ${ey + 40} ${ex - 130} ${ey - 200} ${ex} ${ey - 200} Z" fill="url(#g-egg)"/>`;
  o += `<ellipse cx="${ex - 60}" cy="${ey - 110}" rx="30" ry="16" fill="#fff" opacity=".8" transform="rotate(-35 ${ex - 60} ${ey - 110})"/>`;
  o += eyes(ex - 10, ey - 20, 1.2, [-0.7, -0.2]);
  // Tofu-Würfel
  const tx = 150, ty = 1300, tw = 230, th = 190, td = 80;
  o += `<ellipse cx="${tx + tw / 2 + 30}" cy="${ty + th + 24}" rx="${tw * 0.7}" ry="26" fill="#9E3D5A" opacity=".2" filter="url(#shade)"/>`;
  o += `<path d="M${tx} ${ty} L${tx + td} ${ty - td * 0.6} L${tx + tw + td} ${ty - td * 0.6} L${tx + tw} ${ty} Z" fill="#FFFDF8"/>`;
  o += `<path d="M${tx + tw} ${ty} L${tx + tw + td} ${ty - td * 0.6} L${tx + tw + td} ${ty + th - td * 0.6} L${tx + tw} ${ty + th} Z" fill="url(#tofu-side)"/>`;
  o += `<rect x="${tx}" y="${ty}" width="${tw}" height="${th}" fill="url(#tofu-front)"/>`;
  // Bohne
  o += `<g transform="translate(560 1560) rotate(-18)"><path d="M-90 -10 C-96 -70 -30 -66 -6 -44 C14 -66 92 -72 92 0 C92 60 30 70 0 70 C-60 70 -86 40 -90 -10 Z" fill="url(#g-pink)"/>` +
    `<ellipse cx="-40" cy="-30" rx="22" ry="10" fill="#fff" opacity=".6" transform="rotate(-20 -40 -30)"/></g>`;
  o += squiggle(900, -20, 880, 260, 12, 3) + sphere(880, 290, 44, 'g-cyan');
  o += sparkle(560, 420, 1.1) + sparkle(130, 1050, 0.9) + sparkle(900, 1500, 1) + bubble(470, 330, 12) + bubble(820, 700, 15) + tinySquare(420, 1660, 15) + tinySquare(140, 900, -20);
  return bSvg(o);
}

(async () => {
  const frames = { A1_aminosaeuren: A1, A2_antikoerper: A2, A3_praxis: A3, B1_aminosaeuren: B1, B2_antikoerper: B2, B3_praxis: B3 };
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  const pg = await browser.newPage({ viewport: { width: W, height: H } });
  for (const [name, fn] of Object.entries(frames)) {
    const html = path.join(__dirname, `${name}.html`);
    fs.writeFileSync(html, page(fn()));
    await pg.goto('file://' + html);
    await pg.evaluate(() => document.fonts.ready);
    await pg.screenshot({ path: path.join(OUT, `${name}.png`) });
    console.log('rendered', name);
  }
  await browser.close();
})();
