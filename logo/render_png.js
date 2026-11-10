const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const dir = process.argv[2], scale = +(process.argv[3]||1);
  const b = await chromium.launch();
  for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.svg'))) {
    const svg = fs.readFileSync(path.join(dir, f), 'utf8');
    const m = svg.match(/viewBox="0 0 (\d+) (\d+)"/);
    const p = await b.newPage({ viewport: { width: +m[1], height: +m[2] }, deviceScaleFactor: scale });
    await p.setContent(`<style>html,body{margin:0;background:transparent}</style>${svg}`);
    await p.screenshot({ path: path.join(dir, f.replace('.svg', '.png')), omitBackground: true });
    await p.close();
  }
  await b.close();
})();
