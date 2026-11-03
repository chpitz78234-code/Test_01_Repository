// Renders a procedural top-down snow texture (no AI imagery) with headless Chromium:
// SVG turbulence -> diffuse lighting -> cool/warm colour mapping + fine glitter specks.
//   node tools/gen_snow_texture.js  ->  hyperframes-mg/assets/snow.jpg (1080 x 6200)
const { chromium } = require("playwright");
const path = require("path");

const W = 1080, H = 6200;
const out = path.join(__dirname, "..", "hyperframes-mg", "assets", "snow.jpg");

const html = `<!doctype html><html><body style="margin:0;background:#fff">
<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="snow" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
      <!-- large soft drifts -->
      <feTurbulence type="fractalNoise" baseFrequency="0.0032 0.0042" numOctaves="3" seed="7" result="big"/>
      <!-- small grain -->
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="11" result="fine"/>
      <feComposite in="big" in2="fine" operator="arithmetic" k1="0" k2="0.95" k3="0.05" k4="0" result="height"/>
      <feDiffuseLighting in="height" surfaceScale="15" diffuseConstant="1.05" lighting-color="#ffffff" result="lit">
        <feDistantLight azimuth="235" elevation="34"/>
      </feDiffuseLighting>
      <!-- map light to snow colours: shadows night blue, highlights warm cream -->
      <feComponentTransfer in="lit" result="col">
        <feFuncR type="table" tableValues="0.40 0.64 0.86 0.97 1.00"/>
        <feFuncG type="table" tableValues="0.48 0.69 0.87 0.96 0.985"/>
        <feFuncB type="table" tableValues="0.70 0.84 0.93 0.96 0.94"/>
      </feComponentTransfer>
      <!-- glitter specks -->
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="23" result="g"/>
      <feColorMatrix in="g" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  9 0 0 0 -5.75" result="specks"/>
      <feComposite in="specks" in2="col" operator="over"/>
    </filter>
  </defs>
  <rect width="${W}" height="${H}" filter="url(#snow)"/>
</svg></body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.setContent(html);
  await page.waitForTimeout(500);
  await page.screenshot({ path: out, type: "jpeg", quality: 88, clip: { x: 0, y: 0, width: W, height: H } });
  await browser.close();
  console.log("snow texture ->", out);
})();
