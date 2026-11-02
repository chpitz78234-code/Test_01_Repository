// Rendert den Titel-Loop als MP4 (H.264, 30 fps).
// Aufruf: node render.js [Breite] [Höhe] [Ausgabe.mp4]   Standard: 1080 1080 (quadratisch)
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const W = Number(process.argv[2] || 1080);
const H = Number(process.argv[3] || 1080);
const OUT = path.resolve(process.argv[4] || path.join(__dirname, `schaetzele-markt-titel-loop-${W}x${H}.mp4`));
const FONTS = path.resolve(__dirname, "../explainer-protein/styleframes/fonts");

(async () => {
  const frames = fs.mkdtempSync(path.join(os.tmpdir(), "titel-loop-"));
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    @font-face{font-family:Anton;src:url(file://${FONTS}/Anton-400.woff2)}
    @font-face{font-family:SpaceMono;font-weight:700;src:url(file://${FONTS}/SpaceMono-700.woff2)}
    html,body{margin:0;background:#121212}</style></head>
    <body><canvas id="c"></canvas><script src="file://${__dirname}/title-loop.js"></script></body></html>`;
  const htmlPath = path.join(frames, "page.html");
  fs.writeFileSync(htmlPath, html);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.goto("file://" + htmlPath);
  await page.evaluate(async ([w, h]) => {
    await Promise.all([document.fonts.load("100px Anton"), document.fonts.load("700 100px SpaceMono")]);
    window.titleLoop.init(document.getElementById("c"), w, h);
  }, [W, H]);
  const total = await page.evaluate(() => window.titleLoop.LOOP_FRAMES);
  for (let f = 0; f < total; f++) {
    const data = await page.evaluate((fr) => {
      window.titleLoop.render(fr);
      return document.getElementById("c").toDataURL("image/png");
    }, f);
    fs.writeFileSync(path.join(frames, `f${String(f).padStart(4, "0")}.png`), Buffer.from(data.split(",")[1], "base64"));
  }
  await browser.close();

  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", "30", "-i", path.join(frames, "f%04d.png"),
    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`${OUT} (${total} Frames, ${(total / 30).toFixed(1)} s)`);
})();
