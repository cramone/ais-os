# MAGIQ Media — component catalog

Recurring primitives extracted from the 19 mockups (2026-08-12). Canonical reference so
future mockups and the real React/Tailwind build stop re-deriving these. All values are
token names from [`tokens.css`](tokens.css) — never hardcode hex.

Voice/content rules (from CDS + CLAUDE.md): sentence case everywhere, no terminal
punctuation on labels/buttons, verb-first CTAs, one accent action per view, errors say
*what happened + what to do*, empty states are invitations not apologies.

---

## 1. App chrome (top bar)
Navy bar (`--chrome-bg`), 52px tall. Left→right: logo chip (26px, `--accent`, initial "M") +
wordmark · divider · **tenant selector** · centered global search + `⌘K` hint · notifications
(bell + danger dot) · help · user avatar (30px, `--fill-purple`, initials).
- Mobile variant: 44–52px, hamburger + title/tenant stack + search + avatar.
- a11y: icon-only buttons need `aria-label`; search is a real control.
- Used: shell, tenant-switch, 403, mobile, notifications.

## 2. Left nav rail
`--rail-width` (212px) expanded, `--rail-collapsed` (56px) collapsed, `--surface-2`, right hairline.
Items 36px, icon 18px + label + optional count badge. Active = `--bg-accent`/`--text-accent`,
medium weight. Section dividers = uppercase 11px `--text-muted`. Collapse hides `.lbl` spans.
- Sections: Library · Search · Uploads · Change requests · Registrations · Signing · **Admin** group.
- Mobile: becomes a drawer with scrim + user header.
- a11y: `<nav>`, current item `aria-current="page"`.

## 3. Status chip
Inline-flex, `--radius-sm`, `--fs-cap` medium, icon 12–13px + label. Color by domain status:

| Status | token trio | icon |
|---|---|---|
| Published | success | `ti-circle-check` |
| In review (PendingApproval) | warning | `ti-clock-hour-4` |
| Revising | info | `ti-git-branch` |
| Draft | surface + `--text-secondary` | `ti-pencil` |
| Archived | surface + `--text-muted` | `ti-archive` |
| Failed | danger | `ti-alert-triangle` |

Companion **flag icons** (no label): checkout `ti-lock` (`--icon-warning`), conformance gap
`ti-alert-triangle` (`--icon-warning`). Text on tint uses the same ramp's text token, never black.

## 4. Button
Height `--h-control` (34px), `--radius`, `--fs-body`, icon 15px optional.
- **Primary**: `--accent` bg, `--on-accent`. One per view.
- **Secondary**: transparent, `--border-strong`, `--text-primary`.
- **Destructive**: `--text-danger` on transparent, or `--icon-danger` fill for confirm.
- **On-chrome**: `--chrome-field-bg` + `--chrome-field-border`, white text.
- Disabled: `--surface-1`/`--border`/`--text-muted`, `not-allowed` — avoid; prefer respond-on-use.

## 5. Card / panel / list tile
`--surface-2`, `0.5px --border`, `--radius-card`, padding ~`--space-5/7`. Media grid tile =
type-aware preview header (image tint / PDF icon / processing placeholder) + status chip
overlay + corner flags + title (2-line clamp) + meta row. Dense lists use bordered rows, not
rounded cards (CDS restraint rule).

## 6. Data table / list row
Header row: `--fs-cap` uppercase `--text-muted`, `0.5px --border` bottom. Body rows:
grid columns, 11px hairline dividers, hover affordance. No zebra. Right-aligned meta
(version, date, relevance). Cursor pagination only — "Load more", no page numbers/totals.

## 7. Stepper (lifecycle)
Horizontal stages: 32–34px circle + label (+ optional actor sub-label). States:
done (`--bg-success`/`--text-success`/`ti-check`), current (`--bg-accent`/`ti-loader-2` spin),
todo (`--surface-2`/`--border`/`ti-circle`). Connector line = success color up to current, `--border` after.
- Used: registration (owner↔authority actors), signing (envelope stages).

## 8. Activity / event timeline
Vertical: 26–28px node + connecting line, title + actor · time. Distinguish system/authority
events (`--bg-accent` node) from user events (`--surface-2` node).
- Used: registration, signing, (audit is the flat-list cousin).

## 9. Banner / inline alert
Full-width, `--radius-lg`, tint bg + same-ramp text + leading icon. Roles: accent (review /
processing / info), warning (design-ahead-of-spec, checkout held), danger (archive cascade).
Processing/async banners get `role="status" aria-live="polite"`.

## 10. Toast / live region
Bottom-anchored accent banner, `ti-loader-2` + message + dismiss. Always `aria-live="polite"`.
Reserved for async/eventual-consistency messaging ("N assets processing… read model lags").

## 11. Metadata field row (current vs draft)
Grid `label | value`. Label = mono field name + origin tag (Governed/General). Changed value =
old value strikethrough `--text-muted` → `--text-accent` new + "draft" pill. Conformance gap
surfaced as a warning banner below.

## 12. Facet filter
Left rail, `--surface-2`. Sections: uppercase caption + checkbox rows with counts. Tags section
has AND/OR segmented toggle. Selected filters echo as removable chips above results. Search
input debounced 300ms. Results carry `<mark>` highlight (`--mark-*`) + relevance bar.

## 13. Empty / error state
Centered card, min-height ~184px: 46px tinted icon square + title + one-line body + CTA(s).
Empty = invitation + verb CTA (may include "did you mean"). Error = cause + retry. Processing =
spinner + "appears when ready". Error/processing wrapped in `aria-live="polite"`.

## 14. Avatar
`--radius-full`, initials, `--fill-purple` bg / white text (people). 26–44px. Asset/role icons
use `--surface-0` bg + neutral glyph, not avatars.

## 15. Segmented toggle
Inline, `0.5px --border`, `--radius`; active segment = `--bg-accent`/`--text-accent` medium.
Used for view switches (list/grid), panel switches (record types/media profiles), option
toggles (onError, onDuplicate, tag AND/OR).

---

## Cross-cutting
- **Icons**: Tabler outline webfont (`ti ti-*`), 12–30px, inherit color. Decorative → `aria-hidden`.
- **Radii pairing**: single-side borders (`border-left` accents) get `border-radius:0`.
- **Density**: gov/records users are keyboard- and status-driven → list defaults over grid,
  dense rows, visible focus rings, real `<label>`s.
- **Processing model**: every async surface models `pending → processing → available | failed`;
  client upload % (real) is visually distinct from server-polled states (spinner + "polling…").
