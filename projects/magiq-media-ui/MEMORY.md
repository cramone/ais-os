# Memory — magiq-media-ui
_Last updated: 2026-08-12_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Q2 priorities**: TBD
- **UI design — state (2026-08-12)**: Branding discovered from springbrooksoftware.com + applied — navy #1D3455, Manrope font, cyan/green/teal accents. 19 screens designed + re-screenshotted on-brand (`screenshots/01–19-*.png`). Design system: `design-system/tokens.css` + `tokens.json` + `components.md`. Still ideal from marketing (non-blocking): SVG logo + favicon + palette sign-off (`design-system/brand-asset-request.md`). Product name = MAGIQ Media (Springbrook = owner co., using their scheme). Contract validated vs `swagger.json` → `design-system/contract-validation.md` (4 enum fixes applied). 28 screens now (added 20–28: create-item, version-compare, move, publish+reviewers, create-collection, confirm-dialogs, checkout-conflict, signing-exceptions, registration-rejected). 9 API gaps for backend → `Gaps/api-contract-gaps.md` (detail response, checkout, signing, audit, status enums, CR reviewers, users/roles, tenant provisioning, quota). Bridge artifacts in `design-system/` (tailwind.tokens.cjs, component-props.ts, build-sheets.md). No-API admin screens (Users/tenant/quota) NOT designed by choice — logged as gaps. Browsable prototype at `prototype/index.html` — single self-contained file, FULLY OFFLINE (Tabler subset + Manrope embedded as data-URI, 0 CDN), click-through flow between screens + live design-system page. Double-click to open, no server/internet.
- **REGENERATE (runbook: `screenshots/_build/REGENERATE.md`)** — all cmds from `screenshots/_build/`:
  - Screenshots: `node shot.js` (all) or `node shot.js 06` (one, filename substring). CDN/online.
  - Prototype: `node prototype.js`. Offline; reads `fonts-inline.css` + tokens.css + screens/.
  - Offline fonts (only if a NEW Tabler icon is used): `python subset-fonts.py` then `node prototype.js`.
  - Screen source = `screens/NN-name.html`; flow links = `FLOW` map in `prototype.js`; new screen → add to `groups[]` in prototype.js.
  - When Chase asks to "regenerate the screenshots/prototype" → run the matching cmd above. Medium = mockup-in-Claude. Resume steps in `notes.md` "⏸ RESUME POINT".
