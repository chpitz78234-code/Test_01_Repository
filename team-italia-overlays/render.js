// Rendert index.html Frame für Frame (deterministisch über window.seek) zu MP4.
//   NODE_PATH=$(npm root -g) node render.js            -> renders/01_massimo.mp4 … 07_outro.mp4 + renders/komplett.mp4
//   NODE_PATH=$(npm root -g) node render.js anna       -> nur eine Szene
//   NODE_PATH=$(npm root -g) node render.js --stills 3.5 12 40   -> PNG-Standbilder (globale Sekunden) nach renders/stills/
const fs = require('fs');
const path = require('path');
const { spawn, execFileSync } = require('child_process');
const { chromium } = require('playwright');

const DIR = __dirname;
const OUT = path.join(DIR, 'renders');
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

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
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

  const meta = await (await openPage(browser)).evaluate(() => ({ fps: window.FPS, scenes: window.SCENES, total: window.TOTAL_FRAMES }));
  const fps = meta.fps;
  const jobs = meta.scenes.map((s, i) => ({ ...s, file: path.join(OUT, `${String(i + 1).padStart(2, '0')}_${s.id}.mp4`) }))
    .filter(j => !args.length || args.includes(j.id));
  const full = !args.length;
  // Vorlauf bis zur ersten Szene (nur Hintergrund), damit komplett.mp4 bei 00:00:00:00 beginnt
  if (full && meta.scenes[0].f0 > 0) jobs.unshift({ id: 'lead', f0: 0, f1: meta.scenes[0].f0, file: path.join(OUT, '_lead.mp4') });

  const queue = [...jobs].sort((a, b) => (b.f1 - b.f0) - (a.f1 - a.f0));
  await Promise.all(Array.from({ length: Math.min(WORKERS, queue.length) }, async () => {
    const page = await openPage(browser);
    for (let j; (j = queue.shift());) {
      const t0 = Date.now();
      await renderRange(page, j.f0, j.f1, fps, j.file);
      console.log(`${j.id}: ${j.f1 - j.f0} Frames in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    }
  }));
  await browser.close();

  if (full) {
    const list = path.join(OUT, '_concat.txt');
    fs.writeFileSync(list, jobs.sort((a, b) => a.f0 - b.f0).map(j => `file '${j.file}'`).join('\n'));
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', path.join(OUT, 'komplett.mp4')]);
    fs.unlinkSync(list);
    fs.unlinkSync(path.join(OUT, '_lead.mp4'));
    console.log('komplett.mp4 fertig');
  }
})();
