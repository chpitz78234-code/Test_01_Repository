// Titel-Loop „SCHÄTZELE MARKT – GRIFF KRAFT CHALLENGE“
// Läuft im Browser auf einem <canvas>. render(frame) zeichnet genau einen Frame (30 fps Master).
// Grammatik nach motion-spec/motion-spec.json, Stil D (kinetisch): harte Schnitte im
// 3-3-2-Achtelmuster bei 150 BPM, Animation auf 24 fps gestuft, Farbflash-Stakkato als Höhepunkt.
// Farbschema: Violett #5B09B8, Weiß #FFFFFF, Schwarz #121212.

(() => {
  const C = { violet: "#5B09B8", white: "#FFFFFF", black: "#121212" };
  const LOOP_FRAMES = 192; // 4 Takte à 48 f = 6,4 s

  // Shotliste (Frames @30). Aufeinanderfolgende Shots haben nie dieselbe Hintergrundfarbe,
  // auch nicht über die Loop-Naht (letzter Shot schwarz → erster Shot violett).
  const SHOTS = [
    { id: "schaetzele", in: 0, out: 17, bg: C.violet },
    { id: "staircase", in: 18, out: 34, bg: C.white },
    { id: "griff", in: 35, out: 47, bg: C.black },
    { id: "kraft", in: 48, out: 65, bg: C.violet },
    { id: "challenge", in: 66, out: 82, bg: C.black },
    { id: "gauge", in: 83, out: 95, bg: C.white },
    { id: "lockup_in", in: 96, out: 125, bg: C.black },
    { id: "flash", in: 126, out: 130, bg: C.violet },
    { id: "flash", in: 131, out: 135, bg: C.white },
    { id: "flash", in: 136, out: 140, bg: C.violet },
    { id: "lockup_hold", in: 141, out: 191, bg: C.black },
  ];

  // ---------- Easing (cubic-bezier, Tokens aus der Vorgabe) ----------
  function bezier(x1, y1, x2, y2) {
    const coord = (u, a, b) => 3 * (1 - u) * (1 - u) * u * a + 3 * (1 - u) * u * u * b + u * u * u;
    return (t) => {
      if (t <= 0) return 0;
      if (t >= 1) return 1;
      let lo = 0, hi = 1, u = t;
      for (let i = 0; i < 40; i++) {
        u = (lo + hi) / 2;
        if (coord(u, x1, x2) < t) lo = u; else hi = u;
      }
      return coord(u, y1, y2);
    };
  }
  const E = {
    snap: bezier(0.2, 0.2, 0.05, 1),
    counter: bezier(0, 0, 0, 1),
    expo: bezier(0.16, 1, 0.3, 1),
    whip: bezier(0.7, 0, 0.84, 0),
    back: bezier(0.34, 1.56, 0.64, 1),
    linear: (t) => t,
  };
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const prog = (lf, start, dur, ease) => ease(clamp01((lf - start) / dur));
  const lerp = (a, b, t) => a + (b - a) * t;
  // Animation auf 24 fps stufen (Stil D): lokale Frames @30 auf das 24er-Raster runden
  const q24 = (lf) => Math.floor(lf * 0.8) / 0.8;

  let canvas, ctx, W, H, portrait;

  // ---------- Text-Helfer ----------
  const font = (size) => `${size}px Anton, Impact, sans-serif`;
  const mono = (size) => `700 ${size}px SpaceMono, monospace`;
  function capH(size) {
    ctx.font = font(size);
    return ctx.measureText("H").actualBoundingBoxAscent;
  }
  function textW(text, size, f = font) {
    ctx.font = f(size);
    return ctx.measureText(text).width;
  }
  function fitSize(text, maxW, maxCap) {
    return Math.min((maxW / textW(text, 100)) * 100, (maxCap / capH(100)) * 100);
  }
  // Großbuchstaben optisch auf cy zentrieren, mit Stauchung sx/sy (Griff-Effekt)
  function drawCentered(text, cx, cy, size, color, sx = 1, sy = 1) {
    const ch = capH(size);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(sx, sy);
    ctx.font = font(size);
    ctx.fillStyle = color;
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(text, 0, ch / 2);
    ctx.restore();
  }

  // ---------- Ornamente ----------
  function heart(cx, cy, s, color) {
    // s = Breite des Herzens
    const w = s / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.beginPath();
    ctx.moveTo(0, w * 0.95);
    ctx.bezierCurveTo(-w * 1.25, w * 0.1, -w * 1.0, -w * 0.95, -w * 0.45, -w * 0.9);
    ctx.bezierCurveTo(-w * 0.15, -w * 0.88, 0, -w * 0.62, 0, -w * 0.45);
    ctx.bezierCurveTo(0, -w * 0.62, w * 0.15, -w * 0.88, w * 0.45, -w * 0.9);
    ctx.bezierCurveTo(w * 1.0, -w * 0.95, w * 1.25, w * 0.1, 0, w * 0.95);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  }
  function sparkle(cx, cy, r, color) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.beginPath();
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 - Math.PI / 2;
      const rr = i % 2 === 0 ? r : r * 0.22;
      ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
    }
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  }

  // ---------- Lockup: SCHÄTZELE / MARKT (Treppe) + violette Box mit GRIFF KRAFT CHALLENGE ----------
  const L1 = "SCHÄTZELE", L2 = "MARKT", BOX = "GRIFF KRAFT CHALLENGE";
  function lockupGeometry() {
    const c100 = capH(100);
    const w1_100 = textW(L1, 100);
    const umlaut = 0.16; // Platz für die Ä-Punkte über der Versalhöhe
    const units = umlaut + 1 + 0.16 + 1 + 0.24 + 0.66; // in Versalhöhen
    const maxW = portrait ? W - 2 * 90 : Math.min(W * 0.78, H * 1.1);
    const maxH = portrait ? (H - 180 - 320) * 0.62 : H * 0.7;
    const L = Math.min(maxW / w1_100, maxH / (units * c100)) * 100;
    const cap = capH(L);
    const w1 = textW(L1, L);
    const w2 = textW(L2, L);
    const totalH = units * cap;
    const x0 = (W - w1) / 2;
    const top = portrait ? 180 + (H - 500 - totalH) / 2 : (H - totalH) / 2;
    const b1 = top + umlaut * cap + cap;
    const b2 = b1 + 0.16 * cap + cap;
    const boxY = b2 + 0.24 * cap;
    const boxH = 0.66 * cap;
    const x2 = x0 + w1 - w2;
    const boxSize = fitSize(BOX, w1 * 0.86, boxH * 0.56);
    const gap = x2 - x0;
    return {
      L, cap, w1, w2, x0, x2, b1, b2, boxY, boxH, boxSize, totalH, top,
      heart: { x: x0 + gap * 0.48, y: b2 - cap * 0.5, s: Math.min(cap * 0.95, gap * 0.62) },
    };
  }

  // Zeichenpositionen der Box-Zeile (für zufälliges Buchstaben-Pop)
  function boxChars(g) {
    ctx.font = font(g.boxSize);
    const total = ctx.measureText(BOX).width;
    const start = W / 2 - total / 2;
    const out = [];
    for (let i = 0; i < BOX.length; i++) {
      out.push({ ch: BOX[i], x: start + ctx.measureText(BOX.slice(0, i)).width });
    }
    return out;
  }
  // Feste, „zufällige“ Reihenfolge für das Buchstaben-Pop (deterministisch, damit jeder Render gleich ist)
  const POP_ORDER = (() => {
    const idx = [...BOX].map((_, i) => i);
    let seed = 7;
    for (let i = idx.length - 1; i > 0; i--) {
      seed = (seed * 9301 + 49297) % 233280;
      const j = Math.floor((seed / 233280) * (i + 1));
      [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    const rank = [];
    idx.forEach((charIdx, r) => { rank[charIdx] = r; });
    return rank;
  })();

  function drawLockup(g, o) {
    // o: Farben + Animationszustand
    const col = o.colors;
    ctx.save();
    if (o.scale && o.scale !== 1) {
      const cy = g.top + g.totalH / 2;
      ctx.translate(W / 2, cy);
      ctx.scale(o.scale, o.scale);
      ctx.translate(-W / 2, -cy);
    }
    ctx.font = font(g.L);
    ctx.textBaseline = "alphabetic";
    ctx.textAlign = "left";

    // Zeile 1 und 2 steigen aus einer Maske auf
    const lines = [
      { text: L1, x: g.x0, b: g.b1, p: o.line1 ?? 1, color: col.title, maskTop: g.b1 - g.cap * 1.25 },
      { text: L2, x: g.x2, b: g.b2, p: o.line2 ?? 1, color: col.title2 ?? col.title, maskTop: g.b2 - g.cap * 1.05 },
    ];
    for (const ln of lines) {
      if (ln.p <= 0) continue;
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, ln.maskTop, W, ln.b - ln.maskTop + g.cap * 0.04);
      ctx.clip();
      ctx.fillStyle = ln.color;
      ctx.fillText(ln.text, ln.x + (o.lineDx ?? 0), ln.b + (1 - ln.p) * g.cap * 1.15);
      ctx.restore();
    }

    // Herz in der Treppenlücke
    const hs = o.heart ?? 1;
    if (hs > 0) {
      ctx.save();
      ctx.translate(g.heart.x, g.heart.y);
      ctx.rotate(((o.heartRot ?? 0) * Math.PI) / 180);
      heart(0, 0, g.heart.s * hs, col.heart);
      ctx.restore();
    }
    const sp = o.sparkles ?? 1;
    if (sp > 0) {
      const s = g.heart.s;
      sparkle(g.heart.x - s * 0.62, g.heart.y - s * 0.5, s * 0.2 * sp, col.heart);
      sparkle(g.heart.x - s * 0.58, g.heart.y + s * 0.46, s * 0.13 * sp, col.heart);
    }

    // Box wischt von links nach rechts auf
    const wipe = o.boxWipe ?? 1;
    if (wipe > 0) {
      ctx.fillStyle = col.box;
      ctx.fillRect(g.x0, g.boxY, g.w1 * wipe, g.boxH);
    }
    const shown = o.boxLetters ?? BOX.length;
    if (shown > 0) {
      const chars = boxChars(g);
      const ch = capH(g.boxSize);
      const sx = o.boxSqueeze ?? 1;
      ctx.save();
      // Stauchung um die Box-Mitte (Griff)
      ctx.translate(W / 2, g.boxY + g.boxH / 2);
      ctx.scale(sx, 2 - sx);
      ctx.translate(-W / 2, -(g.boxY + g.boxH / 2));
      ctx.font = font(g.boxSize);
      ctx.fillStyle = col.boxText;
      ctx.textAlign = "left";
      chars.forEach((c, i) => {
        if (POP_ORDER[i] < shown) ctx.fillText(c.ch, c.x, g.boxY + g.boxH / 2 + ch / 2);
      });
      ctx.restore();
    }
    ctx.restore();
  }

  const LOCKUP_COLORS = {
    [C.black]: { title: C.white, title2: C.white, heart: C.violet, box: C.violet, boxText: C.white },
    [C.violet]: { title: C.white, title2: C.white, heart: C.white, box: C.black, boxText: C.white },
    [C.white]: { title: C.black, title2: C.violet, heart: C.violet, box: C.violet, boxText: C.white },
  };

  // ---------- Griffkraft-Anzeige (Dynamometer) ----------
  function drawGauge(lf) {
    const MAX = 90, VALUE = 72;
    const R = portrait ? W * 0.36 : Math.min(W * 0.36, H * 0.4);
    const cx = W / 2;
    const cy = H / 2 + R * 0.12;
    const p = E.counter(clamp01(q24(lf) / 11));
    const value = Math.round(VALUE * p);
    const a0 = Math.PI, a1 = Math.PI * 2;
    const ang = lerp(a0, a1, (VALUE * p) / MAX);
    const thick = R * 0.13;

    ctx.lineCap = "butt";
    ctx.lineWidth = thick;
    ctx.strokeStyle = "rgba(18, 18, 18, 0.12)";
    ctx.beginPath();
    ctx.arc(cx, cy, R, a0, a1);
    ctx.stroke();
    ctx.strokeStyle = C.violet;
    ctx.beginPath();
    ctx.arc(cx, cy, R, a0, ang);
    ctx.stroke();

    // Skala in kg
    ctx.fillStyle = C.black;
    ctx.strokeStyle = C.black;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = mono(R * 0.085);
    for (let kg = 0; kg <= MAX; kg += 10) {
      const a = lerp(a0, a1, kg / MAX);
      const major = kg % 30 === 0;
      const r0 = R - thick / 2 - R * 0.04;
      const r1 = r0 - (major ? R * 0.1 : R * 0.05);
      ctx.lineWidth = major ? R * 0.018 : R * 0.01;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
      ctx.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
      ctx.stroke();
      if (major) {
        const rl = r1 - R * 0.09;
        ctx.fillText(String(kg), cx + Math.cos(a) * rl, cy + Math.sin(a) * rl);
      }
    }

    // Zeiger
    ctx.lineCap = "round";
    ctx.lineWidth = R * 0.035;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(ang) * R * 0.62, cy + Math.sin(ang) * R * 0.62);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.07, 0, Math.PI * 2);
    ctx.fill();

    // Anzeige
    const numSize = R * 0.5;
    const numY = cy + R * 0.5;
    ctx.font = font(numSize);
    const nw = ctx.measureText(String(VALUE)).width; // feste Breite, damit nichts springt
    ctx.textAlign = "right";
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = C.black;
    ctx.fillText(String(value), cx + nw * 0.32, numY + capH(numSize) / 2);
    ctx.font = mono(R * 0.15);
    ctx.textAlign = "left";
    ctx.fillStyle = C.violet;
    ctx.fillText("kg", cx + nw * 0.32 + R * 0.04, numY + capH(numSize) / 2);

    ctx.font = mono(R * 0.1);
    ctx.textAlign = "center";
    ctx.fillStyle = C.black;
    ctx.fillText("GRIFFKRAFT", cx, cy - R - thick - R * 0.1);
  }

  // ---------- Frame-Renderer ----------
  function render(frame) {
    const f = ((frame % LOOP_FRAMES) + LOOP_FRAMES) % LOOP_FRAMES;
    const shot = SHOTS.find((s) => f >= s.in && f <= s.out);
    const lf = f - shot.in;
    const t = q24(lf);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = shot.bg;
    ctx.fillRect(0, 0, W, H);
    const g = lockupGeometry();
    const maxW = portrait ? W - 2 * 80 : W * 0.86;

    switch (shot.id) {
      case "schaetzele": {
        // Titel-Scale 18 % → 100 %, snap_out, 17 f
        const size = fitSize(L1, maxW, portrait ? H * 0.16 : H * 0.42);
        const s = lerp(0.18, 1, prog(t, 0, 17, E.snap));
        drawCentered(L1, W / 2, H / 2, size, C.white, s, s);
        break;
      }
      case "staircase": {
        const dy = (g.boxH + g.cap * 0.24) / 2; // ohne Box vertikal zentrieren
        ctx.save();
        ctx.translate(0, dy);
        const p1 = prog(t, 0, 10, E.expo);
        const p2 = prog(t, 3, 10, E.expo);
        const drift = -lf * W * 0.0015; // linearer Push, Bewegung läuft in den Schnitt
        ctx.font = font(g.L);
        ctx.textAlign = "left";
        ctx.textBaseline = "alphabetic";
        ctx.fillStyle = C.black;
        ctx.fillText(L1, g.x0 + (1 - p1) * -W * 0.35 + drift, g.b1);
        ctx.fillStyle = C.violet;
        ctx.fillText(L2, g.x2 + (1 - p2) * W * 0.35 + drift, g.b2);
        ctx.restore();
        break;
      }
      case "griff": {
        const size = fitSize("GRIFF", maxW, portrait ? H * 0.2 : H * 0.5);
        const p = prog(t, 0, 8, E.expo);
        const sx = lerp(1.22, 0.9, p); // zupacken: schmaler und höher
        drawCentered("GRIFF", W / 2, H / 2, size, C.white, sx, lerp(0.92, 1.07, p));
        break;
      }
      case "kraft": {
        const size = fitSize("KRAFT", maxW, portrait ? H * 0.2 : H * 0.5);
        const s = lerp(1.3, 1, prog(t, 0, 8, E.expo));
        const squeeze = Math.sin(Math.PI * clamp01((t - 6) / 9)) * 0.12;
        drawCentered("KRAFT", W / 2, H / 2, size, C.white, s * (1 - squeeze), s * (1 + squeeze * 0.5));
        break;
      }
      case "challenge": {
        const word = "CHALLENGE";
        const size = fitSize(word, maxW * 0.86, portrait ? H * 0.09 : H * 0.24);
        const ch = capH(size);
        const tw = textW(word, size);
        const bw = tw + ch * 0.8, bh = ch * 1.6;
        const bx = (W - bw) / 2, by = H / 2 - bh / 2;
        ctx.fillStyle = C.violet;
        ctx.fillRect(bx, by, bw * prog(t, 0, 6, E.expo), bh);
        const n = Math.max(0, Math.floor(t - 4) + 1); // Schreibmaschine, 1 Zeichen pro Frame
        if (n > 0) {
          ctx.font = font(size);
          ctx.fillStyle = C.white;
          ctx.textAlign = "left";
          ctx.textBaseline = "alphabetic";
          ctx.fillText(word.slice(0, n), (W - tw) / 2, H / 2 + ch / 2);
        }
        break;
      }
      case "gauge":
        drawGauge(lf);
        break;
      case "lockup_in": {
        // Staffelung: Titel → Zeile 2 (+3 f) → Box (+8 f) → Herz (+9 f) → Buchstaben (+12 f) → Funken (+16 f)
        drawLockup(g, {
          colors: LOCKUP_COLORS[shot.bg],
          line1: prog(t, 0, 10, E.expo),
          line2: prog(t, 3, 10, E.expo),
          boxWipe: prog(t, 8, 6, E.expo),
          heart: prog(t, 9, 4, E.back),
          heartRot: lerp(30, 0, prog(t, 9, 4, E.back)),
          boxLetters: Math.floor(clamp01((t - 12) / 8) * BOX.length),
          sparkles: prog(t, 16, 4, E.back),
          scale: lerp(1, 1.015, prog(lf, 17, 13, E.linear)),
        });
        break;
      }
      case "flash":
        // Layout bleibt stehen, nur die Farben wechseln
        drawLockup(g, { colors: LOCKUP_COLORS[shot.bg], scale: 1.015 });
        break;
      case "lockup_hold": {
        // Herzschlag auf jedem Beat (Takt 4 beginnt bei f144, Beat = 12 f)
        let pulse = 0;
        for (const beat of [144, 156, 168, 180]) {
          if (f >= beat) pulse = 1 - prog(q24(f - beat), 0, 9, E.expo);
        }
        // Griff auf Beat 3: Box-Zeile wird kurz zusammengedrückt
        const grip = f >= 168 && f < 180 ? Math.sin(Math.PI * clamp01(q24(f - 168) / 10)) : 0;
        // Ausgang: whip_in in den Loop-Schnitt
        const out = prog(t, 44, 7, E.whip);
        drawLockup(g, {
          colors: LOCKUP_COLORS[shot.bg],
          heart: 1 + pulse * 0.12,
          boxSqueeze: 1 - grip * 0.08,
          scale: 1.015 + out * 0.5,
        });
        break;
      }
    }
  }

  window.titleLoop = {
    LOOP_FRAMES,
    init(el, width, height) {
      canvas = el;
      W = width;
      H = height;
      portrait = H > W;
      canvas.width = W;
      canvas.height = H;
      ctx = canvas.getContext("2d");
    },
    render,
  };
})();
