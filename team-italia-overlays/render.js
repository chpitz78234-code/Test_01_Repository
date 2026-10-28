// Rendert index.html Frame für Frame (deterministisch über window.seek) zu MP4 mit Soundeffekten.
//   NODE_PATH=$(npm root -g) node render.js            -> renders/01_massimo.mp4 … 07_outro.mp4, komplett.mp4, sfx_komplett.wav
//   NODE_PATH=$(npm root -g) node render.js anna       -> nur eine Szene neu (Ton wird immer komplett neu gemischt)
//   NODE_PATH=$(npm root -g) node render.js --sfx      -> nur Ton neu mischen und in die vorhandenen Videos legen
//   NODE_PATH=$(npm root -g) node render.js --stills 3.5 12 40   -> PNG-Standbilder (globale Sekunden) nach renders/stills/
const fs = require('fs');
const path = require('path');
const { spawn, execFileSync } = require('child_process');
const { chromium } = require('playwright');

const DIR = __dirname;
const OUT = path.join(DIR, 'renders');
const BUILD = path.join(OUT, '.build'); // stumme Video-Zwischenstände
const W = 1080, H = 960, WORKERS = 4;

function encoder(file, fps) {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', String(fps),
    '-video_track_timescale', '12800', '-movflags', '+faststart', file], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', c => (c ? rej(new Error('ffmpeg ' + c)) : res())));
  const write = buf => new Promise(res => (ff.stdin.write(buf) ? res() : ff.stdin.once('drain', res)));
  return { write, end: () => { ff.stdin.end(); return done; } };
}

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(DIR, 'index.html') + '?render=1');
  await page.evaluate(() => document.fonts.ready);
  return page;
}

async function renderRange(page, f0, f1, fps, file) {
  const enc = encoder(file, fps);
  for (let f = f0; f < f1; f++) {
    await page.evaluate(T => window.seek(T), f / fps);
    await enc.write(await page.screenshot({ type: 'png' }));
  }
  await enc.end();
}

// Liest die Sound-Cues direkt aus den CSS-Animationen jeder Szene (Name, Startzeit, Element).
function cuesFromPage() {
  const cues = [];
  for (const s of window.SCENES) {
    const start = s.f0 / window.FPS, dur = (s.f1 - s.f0) / window.FPS;
    window.seek(start + dur - 0.6);
    const el = document.getElementById(s.id);
    for (const a of el.getAnimations({ subtree: true })) {
      const tim = a.effect.getTiming();
      if (tim.iterations === Infinity) continue;
      const target = a.effect.target, pseudo = a.effect.pseudoElement;
      const r = target.getBoundingClientRect();
      const cue = { scene: s.id, t: start + tim.delay / 1000, pan: ((r.left + r.width / 2) / 1080) * 2 - 1 };
      const over = target.closest('[data-sfx]');
      const n = a.animationName;
      let type = null;
      if (over && n !== 'leave') type = over.dataset.sfx;
      else if (n === 'rise' || n === 'fromLeft' || n === 'fromRight') type = 'whoosh';
      else if (n === 'leave' || n === 'sceneOut') type = 'whoosh_out';
      else if (n === 'pop' && pseudo && target.classList.contains('chk')) type = 'check';
      else if (n === 'pop' && pseudo && target.classList.contains('ev')) type = 'cell';
      else if (n === 'pop') type = target.matches('.hub, .pill.red, .av.red') ? 'pop_big' : 'pop';
      else if (n === 'up') type = target.classList.contains('ch') ? 'letter' : 'soft';
      else if (n === 'draw') type = 'swipe';
      else if (n === 'grow') type = 'blip';
      else if (n === 'sheen') type = 'shimmer';
      else if (n === 'c6' || n === 'c20') Object.assign(cue, { to: n === 'c6' ? 6 : 20, dur: tim.duration / 1000 }), type = 'counter';
      else if (n === 'layer') Object.assign(cue, { i: +getComputedStyle(target).getPropertyValue('--i'), dur: tim.duration / 1000 }), type = 'print';
      if (type && type !== 'none') cues.push({ ...cue, type });
    }
  }
  // gleichzeitige weiche Ticks zusammenfassen
  cues.sort((a, b) => a.t - b.t);
  return cues.filter((c, i) => !(c.type === 'soft' && cues.slice(Math.max(0, i - 6), i).some(p => p.type === 'soft' && c.t - p.t < 0.15)));
}

function mux(video, wav, ss, dur, out) {
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, '-ss', String(ss), '-t', String(dur), '-i', wav,
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', out]);
}

(async () => {
  fs.mkdirSync(BUILD, { recursive: true });
  const args = process.argv.slice(2);
  const browser = await chromium.launch();

  if (args[0] === '--stills') {
    const page = await openPage(browser);
    const dir = path.join(OUT, 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of args.slice(1)) {
      await page.evaluate(T => window.seek(T), +s);
      await page.screenshot({ path: path.join(dir, `t${String(s).replace('.', '_')}.png`) });
    }
    await browser.close();
    return;
  }

  const first = await openPage(browser);
  const meta = await first.evaluate(() => ({ fps: window.FPS, scenes: window.SCENES, total: window.TOTAL_FRAMES }));
  const fps = meta.fps;
  const name = (s, i) => `${String(i + 1).padStart(2, '0')}_${s.id}.mp4`;
  const scenes = meta.scenes.map((s, i) => ({ ...s, name: name(s, i), video: path.join(BUILD, name(s, i)) }));

  // 1) Video (stumm) in renders/.build
  if (args[0] !== '--sfx') {
    const jobs = scenes.filter(j => !args.length || args.includes(j.id));
    if (!args.length) jobs.push({ id: 'lead', f0: 0, f1: scenes[0].f0, video: path.join(BUILD, '_lead.mp4') });
    const queue = [...jobs].sort((a, b) => (b.f1 - b.f0) - (a.f1 - a.f0));
    await Promise.all(Array.from({ length: Math.min(WORKERS, queue.length) }, async () => {
      const page = await openPage(browser);
      for (let j; (j = queue.shift());) {
        const t0 = Date.now();
        await renderRange(page, j.f0, j.f1, fps, j.video);
        console.log(`${j.id}: ${j.f1 - j.f0} Frames in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
      }
    }));
    const list = path.join(BUILD, 'concat.txt');
    fs.writeFileSync(list, [path.join(BUILD, '_lead.mp4'), ...scenes.map(s => s.video)].map(f => `file '${f}'`).join('\n'));
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(BUILD, 'komplett.mp4')]);
  }

  // 2) Soundeffekte aus den Animations-Cues
  const cues = await first.evaluate(cuesFromPage);
  await browser.close();
  const cueFile = path.join(BUILD, 'cues.json');
  fs.writeFileSync(cueFile, JSON.stringify({ total: meta.total / fps, cues }, null, 1));
  const wav = path.join(OUT, 'sfx_komplett.wav');
  console.log(execFileSync('python3', [path.join(DIR, 'sfx.py'), cueFile, wav]).toString().trim());

  // 3) Ton in die Videos legen
  for (const s of scenes) mux(s.video, wav, s.f0 / fps, (s.f1 - s.f0) / fps, path.join(OUT, s.name));
  mux(path.join(BUILD, 'komplett.mp4'), wav, 0, meta.total / fps, path.join(OUT, 'komplett.mp4'));
  console.log('fertig: renders/*.mp4 mit Ton, renders/sfx_komplett.wav');
})();
