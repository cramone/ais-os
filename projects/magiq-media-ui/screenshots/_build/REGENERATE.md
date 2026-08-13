# Regenerate — screenshots, prototype, fonts

All commands run from `screenshots/_build/`. Node 22 + Python 3 + Chrome installed.
Source of truth per screen: `screens/NN-name.html` (body-only fragment + inline script).
Design tokens: `../../design-system/tokens.css` (both pipelines read it).

```bash
cd "Z:/claudia/magiq/projects/magiq-media-ui/screenshots/_build"
```

## Screenshots (PNGs → `screenshots/*.png`)
Uses puppeteer-core driving installed Chrome, `fullPage`. Loads Tabler + Manrope from CDN (needs internet).
```bash
node shot.js            # re-render ALL screens
node shot.js 06         # re-render just matching screens (filename substring, e.g. "06" or "detail")
```

## Browsable prototype (`prototype/index.html`)
Single self-contained file: left-nav all 28 screens (iframe srcdoc) + click-through flow + live design-system page. FULLY OFFLINE (fonts embedded from `fonts-inline.css`).
```bash
node prototype.js
```
Flow links (Upload→upload, row→detail, etc.) are the `FLOW` map inside `prototype.js` — edit there to add/change navigation.

## Offline fonts (`fonts-inline.css`) — only if the icon set changes
Subsets Tabler to the icons actually used across `screens/` + embeds Manrope, as data-URI woff2. Needs internet (downloads fonts) + `pip install fonttools brotli`.
```bash
python subset-fonts.py     # then re-run: node prototype.js
```
Only needed when a screen starts using a Tabler icon not previously used. Normal screen edits don't require this.

## Common tasks
- **Edited a screen** → `node shot.js NN` + `node prototype.js`
- **Changed tokens/brand** (`design-system/tokens.css`) → `node shot.js` + `node prototype.js` (both auto-pick up tokens)
- **Added a new screen** → create `screens/NN-name.html`, add it to a group in `prototype.js` `groups[]` (+ optional `FLOW` links), then `node shot.js NN-` + `node prototype.js`
- **Used a new icon** → `python subset-fonts.py` then `node prototype.js`

## Notes
- `node_modules/` (puppeteer-core) is gitignored; if missing: `npm install puppeteer-core@23`.
- Chrome path in `shot.js`: `C:/Program Files/Google/Chrome/Application/chrome.exe`.
- shot.js is CDN/online (for crisp PNGs); prototype.js is fully offline (embedded fonts).
