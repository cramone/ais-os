---
id: MM-030
type: plan
project: magiq-media
workstream: WS-54-capability-field-groups
repo: magiq-media
tags: [magiq-media, catalog, capability-fields, classification, security-classification]
consumes: []
blocked-by-external: [MM-022]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-54 (no gap file; row-tracked); no separate review document.
---

# WS-54 — Capability field groups (`ICapabilityFieldRegistry` + schemes + route + metric)

**Target repo:** `magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media`
**Depends on:** MM-022 (WS-28a — versioned embedded resources alias path, shipped as aspnetcore-platform PR #41 `afaabf09`)
**Unblocks:** MM-064 WS-29 (`MediaProfileCreated.ProfileOrigin`) + anything downstream that gates on scheme discovery.

Delivers `ICapabilityFieldRegistry` + four embedded classification schemes + `/v1/capability-field-groups/{capability}` route + `Catalog/GovernanceGroupUnresolved` metric. Supersedes the former WS-54a (SDK) + WS-54b (host) split — the registry is Catalog-domain, not SDK, so the whole workstream lives in `magiq-media`.

## BC-agnostic scope correction (2026-10-13) — merged into one magiq-media plan

The former WS-54a plan was drafted targeting `aspnetcore-platform` SDK. That was wrong: `ICapabilityFieldRegistry` is keyed on `Capability` (nine-value MediaProfile capability enum — `Processing`, `Registration`, `Governance`, `CheckInOut`, `Retention`, `AssetDefinition`, `Review`, `Signing`, `ChangeRequests`) and returns `CapabilityFieldGroup` carrying `IReadOnlyList<FieldDefinition>` where `FieldDefinition` is MediaProfile's own metadata-schema type. `Capability` and `FieldDefinition` are Catalog domain types — the SDK has no concept of them, and shouldn't acquire one. The spec itself says *"The definitions ship with Catalog. Each group is an embedded, versioned resource in the Catalog assembly."* (`mediaprofile.write-model.md` § `security_classification`).

The reusable BC-agnostic primitive — versioned embedded-resource alias discovery — already shipped in SDK as MM-022 (WS-28a). `ICapabilityFieldRegistry` is Catalog's consumer of that primitive, not an extension of it.

Contrast with MM-024 WS-12a (erasure driver SDK, shipped 2026-10-13): there, SDK genuinely owns a cross-BC primitive (crypto-shred retry mechanism, KMS wrapper, transactional-write hook, scanner-pass base). Here, there is no cross-BC primitive — the registry is one Catalog lookup keyed on one Catalog enum returning one Catalog type.

**Repo flip:** `aspnetcore-platform` → `magiq-media`. **Theme stays:** `spec-divergence/` (not `platform-capabilities/`).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-54 (plan MM-030). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-54-capability-field-groups\WS-54-capability-field-groups-plan.md`.
>
> **All code in magiq-media Catalog module.** Nothing in `aspnetcore-platform` (that's MM-022, already shipped — this plan consumes the versioned-resource alias primitive from the SDK).
>
> Deliver `ICapabilityFieldRegistry.GetCurrent(Capability, ClassificationScheme?)` returning `CapabilityFieldGroup?`. `CapabilityFieldGroup { Capability, Scheme?, DefinitionVersion, Fields[] }`. Four embedded schemes (`au-pspf-2024`, `nz-psr-2024`, `us-cui-32cfr2002`, `dod-manual-5200`) under `src/modules/Catalog/Catalog.WriteModel/Resources/CapabilityFieldGroups/`. `Media:Catalog:ClassificationScheme` tenant setting. `GET /v1/capability-field-groups/{capability}?scheme=` FastEndpoint. `Catalog/GovernanceGroupUnresolved` metric when a route resolves to empty. Startup validation: no duplicate `(capability, scheme, version)`.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md` § Contributed field groups
- [ ] Read `docs/spec/shared/classification-schemes.md` for scheme shapes
- [ ] Read `docs/adrs/classification-schemes.md`
- [ ] Confirm MM-022 (WS-28a) shipped and the alias-path primitive is consumable
- [ ] Confirm Karen delivered scheme content for AU PSPF + NZ PSR (or treat as scope item here)

## Phase 1 — Registry contract + types (Catalog module)
- [ ] `Capability` enum in `Magiq.Media.Catalog.Domain` (nine values)
- [ ] `ClassificationScheme` value object or enum keying scheme id (`au-pspf-2024` / `nz-psr-2024` / `us-cui-32cfr2002` / `dod-manual-5200`)
- [ ] `CapabilityFieldGroup { Capability, Scheme?, DefinitionVersion, Fields }` record where `Fields` is `IReadOnlyList<FieldDefinition>`
- [ ] `ICapabilityFieldRegistry.GetCurrent(Capability, ClassificationScheme?)` → `CapabilityFieldGroup?`

## Phase 2 — Embedded-resource loader (consumes MM-022 alias path)
- [ ] Scheme definitions as embedded JSON per `(capability, scheme, version)` under `Catalog.WriteModel/Resources/CapabilityFieldGroups/`
- [ ] Loader resolves resources via the WS-28a alias path
- [ ] Startup validation: no duplicate `(capability, scheme, version)` → throws on container build
- [ ] `AddCapabilityFieldRegistry(this IServiceCollection, Action<CapabilityFieldRegistryOptions>?)` DI entry

## Phase 3 — Four embedded schemes
- [ ] `au-pspf-2024` — 6 markings, 3 Information Management caveats, releasability caveats, 2 dissemination controls, codeword compartments ≥ SECRET
- [ ] `nz-psr-2024` — 7 markings, releasability caveats (`REL_NZEO`, `REL_TO_*`), dissemination control (`DISS_ORCON`), codeword compartments ≥ SECRET
- [ ] `us-cui-32cfr2002` — 3 markings, CUI category caveats on `CUI_SPECIFIED`, dissemination controls, no compartments
- [ ] `dod-manual-5200` — 4 markings, releasability caveats ≥ CONFIDENTIAL, dissemination controls, SCI compartments on `TOP_SECRET`
- [ ] Each scheme pins marking ordinals per spec table (stored ordinal reads as specified marking regardless of later code changes)

## Phase 4 — Tenant setting
- [ ] Bind `Media:Catalog:ClassificationScheme` from `ITenantSettingsManager`
- [ ] Fallback: no setting → `null` scheme → `Governance` capability resolves no group (per spec)

## Phase 5 — Route
- [ ] `GET /v1/capability-field-groups/{capability}?scheme=` FastEndpoint
- [ ] Resolves scheme from tenant setting + optional query override (query overrides tenant)
- [ ] Returns ordered list of groups (one per matching definition version), or empty when `(capability, scheme)` resolves nothing
- [ ] Permission check per `docs/spec/shared/api-permissions.md`

## Phase 6 — Metric
- [ ] `Catalog/GovernanceGroupUnresolved` emitted when route resolves `Governance` capability to empty on the request's tenant scheme
- [ ] Register meter under `MagiqMedia/Catalog` namespace (per WS-58a EMF mapping)
- [ ] CloudWatch alarm wired through `cdk-magiq-media` (coordinate — not in this PR)

## Phase 7 — Handler wiring
- [ ] `SetCapabilitiesHandler` resolves current group per added capability via `ICapabilityFieldRegistry.GetCurrent(capability, tenantScheme)` and carries groups on `MediaProfileCapabilitiesSet`
- [ ] `Governance` with no tenant scheme set → warning log + metric emitted + no group added (spec scenario)

## Phase 8 — Tests
- [ ] Unit: registry resolves each scheme's groups by `(capability, scheme, version)`
- [ ] Unit: unknown `(capability, scheme)` → null
- [ ] Unit: duplicate registration at container build → `InvalidOperationException`
- [ ] Unit: route returns ordered groups for registered scheme
- [ ] Unit: unknown scheme on route → 200 empty + `Catalog/GovernanceGroupUnresolved` emitted
- [ ] Integration: round-trip with tenant-settings override
- [ ] Integration: `SetCapabilitiesHandler` emits `MediaProfileCapabilitiesSet` with `FieldGroups` matching registry's current for each capability

## Phase 9 — Ship
- [ ] PR to `develop`

## Phase 10 — Close
- [ ] spec-divergence/INDEX.md: WS-54 moves to § Shipped (single row — no a/b split)
- [ ] INTEGRATION-BACKLOG: MM-030 moves to § Shipped (single row — no a/b split)
- [ ] Remove `Capability field groups not built` bullet from magiq-media `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (originally two parts — WS-54a SDK + WS-54b host — blocked on MM-022)
- 2026-10-13: BC-agnostic scope correction — WS-54a + WS-54b merged into single WS-54 under magiq-media. Rationale: `ICapabilityFieldRegistry` is keyed on `Capability` (Catalog enum) returning `CapabilityFieldGroup.Fields = IReadOnlyList<FieldDefinition>` (MediaProfile metadata-schema type) — both are Catalog domain, not SDK. Spec itself says "ship with Catalog". Reusable BC-agnostic primitive (versioned embedded-resource alias path) already lives in SDK via MM-022 (WS-28a shipped). Pattern mirrors MM-024 scope correction, except in this case there is no cross-BC primitive to lift — the whole workstream collapses into magiq-media. MM-044 (former WS-54b) retired as superseded; MM-030 absorbs the full scope. Phase A count 29 → 28, Phase C count +1.
