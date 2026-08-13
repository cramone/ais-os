const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const SCREENS = path.join(__dirname, 'screens');
const OUT = path.resolve(__dirname, '..');

const TOKENS = fs.readFileSync(path.resolve(__dirname, '../../design-system/tokens.css'), 'utf8');

const HEAD = `<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.24.0/dist/tabler-icons.min.css">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap">
<style>
${TOKENS}
*{box-sizing:border-box}
body{margin:0;background:var(--surface-0);font-family:var(--font-sans);color:var(--text-primary);
-webkit-font-smoothing:antialiased;line-height:1.5}
h1,h2,h3{color:var(--text-primary);font-weight:500;margin:0}
button{font-family:inherit}
input,textarea,select{font-family:inherit;border:0.5px solid var(--border-strong);border-radius:8px;background:var(--surface-2);color:var(--text-primary);padding:0 10px;font-size:13px}
textarea{padding:8px 10px}
.page{width:720px;margin:0 auto;padding:26px 20px}
.page.wide{width:940px}
.sr-only{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
code{font-family:var(--font-mono)}
</style><script>function sendPrompt(){}function openLink(){}</script></head><body><div class="page CLS">`;
const FOOT = `</div></body></html>`;

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-color-profile=srgb']
  });
  const files = fs.readdirSync(SCREENS).filter(f => f.endsWith('.html')).sort();
  const only = process.argv[2];
  for (const f of files) {
    if (only && !f.includes(only)) continue;
    const name = f.replace(/\.html$/, '');
    const wide = /wide/.test(f);
    const body = fs.readFileSync(path.join(SCREENS, f), 'utf8');
    const html = HEAD.replace('CLS', wide ? 'wide' : '') + body + FOOT;
    const page = await browser.newPage();
    await page.setViewport({ width: wide ? 980 : 760, height: 900, deviceScaleFactor: 2 });
    await page.setContent(html, { waitUntil: 'networkidle0' });
    try { await page.evaluate(() => document.fonts.ready); } catch (e) {}
    await new Promise(r => setTimeout(r, 450));
    const outName = name.replace(/\.wide$/, '') + '.png';
    await page.screenshot({ path: path.join(OUT, outName), fullPage: true });
    console.log('shot', outName);
    await page.close();
  }
  await browser.close();
})();
