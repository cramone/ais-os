/**
 * MAGIQ Media — Tailwind theme extension (2026-08-12)
 *
 * Drop-in for the frontend repo. Maps Tailwind utilities onto the CSS-variable tokens
 * defined in `tokens.css`, so tokens.css stays the SINGLE source of truth and dark mode
 * flips automatically (no Tailwind rebuild needed).
 *
 * Usage in the repo's tailwind.config.{js,ts}:
 *   const magiq = require('./design-system/tailwind.tokens.cjs');
 *   module.exports = { theme: { extend: magiq.extend }, darkMode: ['selector', '[data-mode="dark"]'] };
 *
 * And import tokens.css once at the app entry (or copy its :root block into your global css).
 * Utilities you get: bg-surface-2, text-secondary, border-strong, bg-accent, text-success,
 * rounded-card, shadow-popover, font-sans, etc.
 */
const v = (name) => `var(--${name})`;

const extend = {
  colors: {
    // surfaces
    surface: { 0: v('surface-0'), 1: v('surface-1'), 2: v('surface-2') },
    // brand chrome (navy app bar)
    chrome: { DEFAULT: v('chrome-bg'), fg: v('chrome-fg'), 'fg-muted': v('chrome-fg-muted'), line: v('chrome-line') },
    // interactive accent (Springbrook navy)
    accent: { DEFAULT: v('accent'), hover: v('accent-hover'), on: v('on-accent'), text: v('text-accent'), bg: v('bg-accent'), border: v('border-accent') },
    // secondary brand pops
    brand: { cyan: v('brand-cyan'), green: v('brand-green'), teal: v('brand-teal'), red: v('brand-red') },
    // text
    text: { primary: v('text-primary'), secondary: v('text-secondary'), muted: v('text-muted'), accent: v('text-accent') },
    // status roles (semantic)
    success: { text: v('text-success'), bg: v('bg-success'), border: v('border-success'), icon: v('icon-success') },
    warning: { text: v('text-warning'), bg: v('bg-warning'), border: v('border-warning'), icon: v('icon-warning') },
    danger:  { text: v('text-danger'),  bg: v('bg-danger'),  border: v('border-danger'),  icon: v('icon-danger') },
    info:    { text: v('text-info'),    bg: v('bg-info') },
    purpleRole: { text: v('text-purple'), bg: v('bg-purple'), fill: v('fill-purple') },
    // search-hit highlight
    mark: { bg: v('mark-bg'), fg: v('mark-fg') },
  },
  borderColor: {
    DEFAULT: v('border'),
    strong: v('border-strong'),
    stronger: v('border-stronger'),
    accent: v('border-accent'),
    success: v('border-success'), warning: v('border-warning'), danger: v('border-danger'),
  },
  fontFamily: {
    sans: [v('font-sans')],
    display: [v('font-display')],
    mono: [v('font-mono')],
  },
  fontSize: {
    micro: [v('fs-micro'), { lineHeight: '1.4' }],
    cap:   [v('fs-cap'),   { lineHeight: '1.4' }],
    sec:   [v('fs-sec')],
    body:  [v('fs-body')],
    h3:    [v('fs-h3'),  { fontWeight: '500' }],
    h2:    [v('fs-h2'),  { fontWeight: '500' }],
    h1:    [v('fs-h1'),  { fontWeight: '500' }],
  },
  borderRadius: {
    sm: v('radius-sm'), DEFAULT: v('radius'), lg: v('radius-lg'),
    card: v('radius-card'), xl: v('radius-xl'), pill: v('radius-pill'), full: v('radius-full'),
  },
  boxShadow: { md: v('shadow-md'), popover: v('shadow-popover') },
  spacing: {
    // component-internal scale (see tokens.css --space-*)
    1: v('space-1'), 1.5: v('space-2'), 2: v('space-3'), 2.5: v('space-4'),
    3: v('space-5'), 3.5: v('space-6'), 4: v('space-7'), 4.5: v('space-8'), 5: v('space-9'),
  },
  height: { control: v('h-control'), 'control-sm': v('h-control-sm'), 'control-lg': v('h-control-lg') },
  width: { rail: v('rail-width'), 'rail-collapsed': v('rail-collapsed'), sidebar: v('sidebar-width') },
  maxWidth: { content: v('content-max') },
};

module.exports = { extend, v };
