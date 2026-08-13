/**
 * MAGIQ Media — component prop contracts (2026-08-12)
 *
 * TypeScript interfaces for the 15 primitives catalogued in `components.md`. This is the
 * design→code contract: implement these in the frontend repo under `components/` (shared,
 * no domain knowledge). Domain types come from the generated client
 * (`components['schemas']['…']` via openapi-typescript on swagger.json) — never hand-duplicated.
 *
 * React 19: `ref` is a plain prop (no forwardRef). No useMemo/useCallback/React.memo.
 * Reference only — not wired into a build here (frontend repo is separate).
 */

import type { ReactNode } from 'react';

/* ---- shared ---- */
export type Size = 'sm' | 'md' | 'lg';
export type StatusRole = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

/** Domain status → visual role (map in the feature layer, not the component). */
export type MediaItemStatus = 'Draft' | 'PendingApproval' | 'Published' | 'Revising' | 'Archived';

/* ---- 1. App chrome ---- */
export interface TopBarProps {
  tenantName: string;
  onSearchFocus?: () => void;
  notificationCount?: number;
  user: { initials: string; name: string };
  /** shown only when the user belongs to >1 tenant */
  tenants?: { id: string; name: string; role: string }[];
  onTenantSwitch?: (tenantId: string) => void;
}

/* ---- 2. Left nav rail ---- */
export interface NavRailProps {
  items: NavItem[];
  activeKey: string;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}
export interface NavItem {
  key: string;
  label: string;
  icon: string;            // Tabler name, e.g. 'ti-photo'
  badge?: number;
  section?: string;        // group header, e.g. 'Admin'
  href: string;
}

/* ---- 3. Status chip ---- */
export interface StatusChipProps {
  label: string;
  role: StatusRole;
  icon?: string;
}
/** Row-level flags (checkout, conformance) — icon-only, need aria-label. */
export interface FlagIconProps {
  kind: 'checkout' | 'conformance';
  label: string;           // accessible name
}

/* ---- 4. Button ---- */
export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'destructive' | 'ghost';
  icon?: string;
  onChrome?: boolean;      // navy-bar styling
  loading?: boolean;
  children: ReactNode;
}

/* ---- 5. Card / media tile ---- */
export interface MediaTileProps {
  title: string;
  status: MediaItemStatus;
  version: number;         // 0 => not yet published
  preview: 'image' | 'pdf' | 'processing' | 'generic';
  checkedOut?: boolean;    // NB: not in contract yet — see Gaps/api-contract-gaps.md GAP-2
  conformanceGap?: boolean;
  onOpen?: () => void;
}

/* ---- 6. Data table / list row ---- */
export interface DataListProps<T> {
  columns: { key: keyof T | string; header: string; width?: string; align?: 'left' | 'right' }[];
  rows: T[];
  renderCell: (row: T, key: string) => ReactNode;
  /** cursor pagination — no page numbers/totals (ADR-014) */
  nextCursor?: string | null;
  onLoadMore?: () => void;
  view?: 'list' | 'grid';
  onViewChange?: (v: 'list' | 'grid') => void;
}

/* ---- 7. Stepper ---- */
export interface StepperProps {
  steps: StepItem[];
}
export interface StepItem {
  label: string;
  state: 'done' | 'current' | 'todo';
  actor?: string;          // e.g. 'Owner' | 'Authority'
}

/* ---- 8. Activity timeline ---- */
export interface TimelineProps {
  events: TimelineEvent[];
}
export interface TimelineEvent {
  icon: string;
  title: string;
  actor: string;
  when: string;
  system?: boolean;        // system/authority-sourced vs user
}

/* ---- 9. Banner / inline alert ---- */
export interface BannerProps {
  role: 'accent' | 'warning' | 'danger';
  icon?: string;
  children: ReactNode;
  action?: { label: string; onClick: () => void };
  /** async/processing banners announce politely */
  live?: boolean;
}

/* ---- 10. Toast / live region ---- */
export interface ProcessingToastProps {
  message: ReactNode;
  onDismiss?: () => void;  // always role=status aria-live=polite
}

/* ---- 11. Metadata field row (current vs draft) ---- */
export interface MetadataRowProps {
  fieldName: string;
  origin: 'Governed' | 'General';
  current: string;
  draft?: string;          // present => render strikethrough→draft diff
}

/* ---- 12. Facet filter ---- */
export interface FacetPanelProps {
  facets: Facet[];
  applied: AppliedFilter[];
  onToggle: (facetKey: string, value: string) => void;
  onClearAll?: () => void;
  tagMode?: 'AND' | 'OR';
  onTagModeChange?: (m: 'AND' | 'OR') => void;
}
export interface Facet { key: string; header: string; options: { value: string; count: number; selected: boolean }[]; }
export interface AppliedFilter { key: string; label: string; role: StatusRole; }

/* ---- 13. Empty / error state ---- */
export interface StateCardProps {
  tone: 'empty' | 'error' | 'processing';
  icon: string;
  title: string;
  body: string;
  cta?: { label: string; onClick: () => void };
  secondaryCta?: { label: string; onClick: () => void };
  hint?: { label: string; onClick: () => void };   // e.g. "did you mean…"
}

/* ---- 14. Avatar ---- */
export interface AvatarProps {
  initials: string;
  size?: Size;
  name: string;            // accessible
}

/* ---- 15. Segmented toggle ---- */
export interface SegmentedProps<V extends string> {
  options: { value: V; label: string; icon?: string }[];
  value: V;
  onChange: (v: V) => void;
}
