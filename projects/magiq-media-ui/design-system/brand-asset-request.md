# Brand asset request — MAGIQ Media UI

> **UPDATE 2026-08-12 — most of this is now auto-discovered from springbrooksoftware.com and
> already applied to the design system + all 19 screens.** Applied: navy **#1D3455**, Manrope
> type (OFL — free, no licence needed), secondary accents (cyan #00A0D2, green #2DCD7C, teal
> #003B49, red #B80105). What still genuinely needs marketing is short — see below.

## Still needed from marketing (short list)
1. **Logo — SVG** (colour + white/reversed + mono). Site ships PNG only; SVG needed for crisp 26→44px scaling. Mockups use a placeholder "M" chip.
2. **Favicon** as SVG (or high-res PNG set 32 / 180).
3. **Palette sign-off** — confirm #1D3455 primary + the secondary accents are correct/complete, plus any WCAG-AA text-on-brand pairings.
4. **Product-name lockup** — exact casing for this app (mockups show "MAGIQ Media"; site brand is "Springbrook").
5. *(optional)* brand guidelines PDF; confirm Tabler-outline icon style is acceptable.

---

## Full reference (original request — most now satisfied from the site)

Formats in **bold** are required. Where a token is named, that's the value your asset confirms/replaces.

---

## 1. Logo

| # | Asset | Format | Why / where used |
|---|---|---|---|
| 1.1 | Primary logo / wordmark — full colour | **SVG** (vector) | Login screen header, marketing surfaces |
| 1.2 | Logo mark / icon only (no wordmark) | **SVG** | The square app-bar chip (currently a placeholder "M") + favicon base |
| 1.3 | Reversed / white logo + mark | **SVG** | The app bar and mobile header are **dark navy** — need a version that reads on dark |
| 1.4 | Monochrome (single-colour) logo + mark | **SVG** | Print, faxed/scanned gov docs, disabled states |
| 1.5 | Favicon set | **SVG** + PNG 32×32, 180×180 (apple-touch), ICO | Browser tab, home-screen icon |
| 1.6 | Clear-space + minimum-size rules | PDF or note | So the mark isn't cramped/shrunk below legibility |

> SVG (not PNG) for 1.1–1.4 — the UI scales the mark from 26px (app bar) to 44px (login) and it must stay crisp.

## 2. Colour

| # | Asset | Format | Replaces token |
|---|---|---|---|
| 2.1 | Primary brand colour | **HEX** | `--accent` (placeholder `#378ADD`) — primary buttons, active nav, links |
| 2.2 | App-bar / chrome colour (if an official dark exists) | **HEX** | `--chrome-bg` (placeholder navy `#182231`) |
| 2.3 | Full brand palette — primary, secondary, neutrals | **HEX list + usage** | Confirms/extends the accent + purple accents |
| 2.4 | Accessible text-on-brand pairings (WCAG 2.2 AA, 4.5:1) | note | Gov procurement requires AA — need approved fg/bg combos |

> Status colours (Published=teal, In review=amber, Failed=red) are **semantic** and standard — only override if brand has a specific opinion. If so, supply the 3 hues.

## 3. Typography

| # | Asset | Format | Replaces token |
|---|---|---|---|
| 3.1 | Official typeface name(s) — heading + body | note | `--font-sans` (placeholder system sans) |
| 3.2 | Licensed web-font files | **WOFF2** (+ WOFF fallback) | The actual embed files the SPA ships |
| 3.3 | Web-embedding licence confirmation | doc | Confirms we're licensed to self-host/serve the font in a web app |
| 3.4 | Weights licensed | note | UI uses **two only: 400 regular + 500 medium** — confirm both are covered |
| 3.5 | Fallback stack | note | What to render before the web font loads |
| 3.6 | Monospace face (only if brand mandates one) | WOFF2 | Field names / codes — otherwise we keep a system mono |

## 4. Iconography & illustration

| # | Asset | Format | Note |
|---|---|---|---|
| 4.1 | Icon-style sign-off | note | UI uses **Tabler outline** icons. Confirm acceptable, OR supply a brand icon set (SVG) |
| 4.2 | Empty-state / illustration style (optional) | SVG | If brand has an illustration language for empty screens |

## 5. Guidelines & naming

| # | Asset | Format | Note |
|---|---|---|---|
| 5.1 | Brand guidelines | PDF | Voice, do/don't, logo usage — if one exists |
| 5.2 | Product-name lockup | note | Exact casing/spacing: "MAGIQ Media" vs "Magiq Media" vs stylised |

---

## Minimum to unblock
If the full set takes time, these **four** alone let the design proceed and swap cleanly:
1. **Logo mark — SVG, colour + white** (1.2 + 1.3)
2. **Primary brand colour — hex** (2.1)
3. **App-bar colour — hex** (2.2, or confirm the current navy is fine)
4. **Typeface name + WOFF2 + web licence** (3.1–3.3)

With those four we replace ~6 token values and all 19 screens re-render on brand.
