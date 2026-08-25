# MediaProfile — Aggregate Architecture Review (Specification vs Repository)

_Context: **Catalog** (bounded context) — magiq-media_
_Aggregate: **MediaProfile**_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API) and Senior Software Engineer_
_Date: 2026-07-19_
_Scope: `docs/spec/contexts/Catalog/aggregates/MediaProfile/**` (api, write-model, read-model, defaults, scenarios) + shared conventions (api-conventions, error-catalog, security-scenarios, bulk-operations, media-types), `docs/adrs/catalog-domain-invariants.md` (ADR-006/010/013), `docs/spec/contexts/Catalog/context-overview.md` vs `src/modules/Catalog/**` MediaProfile slice: `Catalog.Domain/Aggregates/MediaProfiles/**` (aggregate, 17 events, 2 mappers, snapshots, ~20 VOs incl. `CompiledMetadataField(+Converter)`, `CompiledMetadataTemplate`, `MetadataValue(+JsonConverter)`, `CapabilitySet`, `MediaProfileDraft`), `Catalog.Domain/ValueObjects/{MediaProfileId,MediaProfileVersion,RecordTypeId,RecordTypeVersion,MetadataFieldType}`, `Catalog.WriteModel/Commands/MediaProfiles/**` (17 command+handler folders), `Catalog.WriteModel/IntegrationEvents/{Publishing/Mappers/MediaProfileDomainEventMapper, Consuming/Handlers/{MediaProfilePublishedConformanceFanout, RecordTypePublished, RecordTypeDeprecated}, Consuming/Projectors/RecordTypeVersionDetailIndexProjector, Consuming/ReferenceModels/**}`, `Catalog.WriteModel/Services/MediaProfiles/**`, `Catalog.WriteModel/Seeding/**`, `Catalog.WriteModel.Endpoints/V1/MediaProfiles/**`, `Catalog.WriteModel.Infrastructure/{Repositories/MediaProfileRepository, Services/MediaProfiles/**}`, `Catalog.Contracts/Events/MediaProfiles/**`, `Catalog.ReadModel/{Projectors,ReadModels,Queries}/MediaProfiles/**`, `Catalog.ReadModel.Endpoints/V1/MediaProfiles/**`._

> **Method:** ~70 production `.cs` files across the MediaProfile slice were read and compared against the five MediaProfile spec files, the shared conventions/error-catalog/security-scenarios, and `catalog-domain-invariants.md` (ADR-006/010/013). The aggregate, both snapshot mappers and all JSON converters, every command handler, the domain service (`CompileTemplateAsync`/`CheckRevisionBreaksAsync`), the conformance fan-out and RecordType consumers/projector, the seeding service, all four read-model projectors, and the endpoints/DTOs were read in full; tiny VO/DTO records were skimmed for shape. MediaItem / Asset / RecordType (Metadata) code was consulted only where MediaProfile references it (profile snapshot on `MediaItemCreated`, the conformance fan-out, the record-type reference index, the asset-default guard). Findings that hinge on unread `Magiq.Platform` base behaviour (`CommandHandler` error-code→HTTP mapping, `ProjectionHandlerBase`/`ProjectedVersion` monotonicity, `IRepository` conditional-write concurrency, `INameReservationService` transactionality, `ProjectionKey` PK/SK semantics, `PagerParameters` cap) are flagged as such. Cross-references to the completed Collection / MediaItem / Folder aggregate reviews and the AssetManagement module review are used for shared cross-cutting findings rather than re-deriving rationale. Stable IDs are prefixed `MP-`.

---

## 1. Summary

`MediaProfile` is the Catalog context's processing/rendition **configuration** aggregate — the structural contract every `MediaItem` conforms to. It governs a draft→publish→deprecate **versioned** lifecycle, asset-role definitions (add/update/remove/reorder/set-default with dimension constraints), record-type attachment + version pinning that **compiles a metadata template** (ADR-013 collision/alias qualification), capability sets that gate cross-BC Asset uploads, review/checkout policies, an auto-submit flag, a **conformance fan-out to existing MediaItems on publish** (ADR-010), and six seeded platform-default profiles.

The aggregate itself (`MediaProfile.cs`, 787 lines) is, in several respects, the **strongest** part of the slice and materially better than the AssetManagement baseline: **every domain event carries a passed-in timestamp** (no wall-clock in event emission — the one `DateTimeOffset.UtcNow` is benign `TakeSnapshot` metadata), so replay is deterministic; **published-version immutability is genuinely enforced** (draft mutations only ever touch `Draft`; the published root fields are overwritten atomically only inside `Apply(MediaProfilePublished)`); the **ADR-010 publish guard** (capabilities count as content) is implemented exactly; and the **ADR-013 collision/alias compilation** in `MediaProfileDomainService.CompileTemplateAsync` is faithful. The RecordType reference consumers dispatch through the projection pipeline and let exceptions propagate (no swallow — contrast AssetManagement F-C1). The detail projector has near-total event coverage and stamps `ProjectedVersion` on every write.

However, the aggregate is **not production-ready**. The review surfaced **1 Critical** and **6 High** issues in five themes:

1. **Authorization is absent end-to-end.** No endpoint declares a policy; no handler performs the api.md `caller.owner_id == mediaProfile.OwnerId` check; mutating commands carry no caller identity to compare. Any authenticated tenant user can create, mutate, **publish, deprecate**, and read any other owner's profile — including the shared `owner_system` platform defaults, whose corruption affects every tenant.
2. **The compiled-metadata-template machinery loses ADR-013 data on serialization round-trip.** `CompiledMetadataFieldConverter` never (de)serializes `BareName`, and the snapshot records omit both `BareName` and `SuppressedFieldNames` — so after any event replay or snapshot restore the collision metadata is silently reset, and the GET detail contract that is supposed to expose `compiledMetadataFields`/`suppressedFieldNames` is never surfaced at all.
3. **The conformance model contradicts itself against ADR-010.** `CheckRevisionBreaksAsync` *blocks* publish on removed/reordered content (contradicting ADR-010's "flag, never block"), while the publish-driven conformance fan-out is unbounded, uncheckpointed, and swallows the `Result` it should observe.
4. **Read-model integrity gaps.** Summary `AssetDefinitionCount`/`RecordTypeCount` drift during a revision draft (and never roll back on discard); `DimensionConstraints` are never projected; `TenantId` leaks into GET/list responses; list/read are not owner-scoped.
5. **The error / validation / atomicity / seeding contracts are unmet.** Generic `InvalidOperation`/`EntityAlreadyExists` with no RFC 9457 `errorCode`; no request validators (→500); non-atomic name-reservation dual writes (Deprecate releases the reservation *before* save); and a non-resumable seeding sequence.

As with the sibling Catalog aggregates, the aggregate core is the strongest part; nearly every Critical/High defect lives in the **handler / projector / converter / seeding orchestration layer** around it.

---

## 2. Aggregate Analysis

### `MediaProfile` (Aggregate Root) — `Catalog.Domain/Aggregates/MediaProfiles/MediaProfile.cs`

`EventSourced<MediaProfile, MediaProfileId, MediaProfileAggregateSnapshot>`, `ITenantScoped`, `[AggregateType("media.profile")]`. Single aggregate; no child entities (asset-definition, capability, compiled-field, draft, record-type-ref are all value objects — correct). Healthy VO surface: `MediaProfileId`, `MediaProfileName`, `MemberId`(owner), `MediaProfileStatus`, `AssetDefinition`/`AssetDefinitionOrder`/`DimensionConstraints`, `Capability`/`CapabilitySet`, `RecordTypeVersion`/`RecordTypeId`, `ReviewPolicy`/`CheckoutPolicy`, `MediaProfileDraft`, `CompiledMetadataTemplate`/`CompiledMetadataField`, `MetadataValue`.

**Key state (all `private set`):** `TenantId` (first field of `MediaProfileCreated`, set once), `Name`, `Description?`, `OwnerId`, `Status`, `PublishedVersion` (0 before first publish), `AssetDefinitions`, `RecordTypeRefs`, `Capabilities`, `ReviewPolicy`, `CheckoutPolicy`, `AutoSubmitOnComplete`, `CompiledTemplate?` (null before first publish), `Draft?`, plus a redundant `Version` (see MP-L8).

**Invariants enforced in the aggregate (correct):**
- Draft-gated mutation: every mutator guards `Draft != null` and `Status != Deprecated`.
- **Published-version immutability** — all draft mutations (`Apply(AssetDefinition*/RecordType*/…Policy*/…CapabilitiesSet/AutoSubmit)`) operate on `Draft`; the published root fields are set only in `Apply(MediaProfilePublished)` (`:755-773`), which also nulls `Draft`. A revision-in-progress therefore never disturbs the live published version. This is the correct model.
- **Publish content guard (ADR-010):** `hasContent = AssetDefinitions.Any() || RecordTypeRefs.Count > 0 || Capabilities.Any()` (`:277-285`) — matches the ADR-010 correction exactly (capabilities count as content), superseding the stale write-model invariant "≥1 AssetDefinition or RecordTypeRef."
- `AddAssetDefinition`: role-name uniqueness, non-empty `AcceptedContentTypes`, display-order auto-assign + uniqueness, dimension-constraint validation (`:99-141`).
- `CreateRevision` guards `Status == Published && Draft == null` (`:177-192`); `DiscardDraft` blocks discarding the *initial* draft (`Status != Published` → error, `:240-254`) so a never-published profile can't be left in stateless limbo.
- Event timestamps are all passed in — deterministic replay. **A genuine strength** (contrast AssetManagement A-D2).

**Aggregate-level defects (detailed in §12–13):**
- **MP-D1 (High, correctness).** `Publish()` embeds `CompiledMetadataTemplate` directly in `MediaProfilePublished.PublishedSnapshot`; there is **no `MetadataTemplateCompiled` event** despite the write-model spec (`:194,217`) mandating it be "raised atomically before `MediaProfilePublished`" as "the sole mutation point for `CompiledTemplate`." The VO/property doc comments ("Set exclusively by `Apply(MetadataTemplateCompiled)`") are stale (see MP-M8). Functionally the template is set; the spec's two-event design is not implemented.
- **MP-D2 (Medium, generic errors).** Every guard returns `DomainError.InvalidOperation` (422) or `ValidationFailure`; none returns the catalog-coded errors the API advertises (`NoActiveDraft`, `DraftEmpty`, `RecordTypeVersionNotFound`→404, `RecordTypeDeprecated`, `MediaProfileNotPublished`, `DraftInProgress`, `RoleNameNotUnique`, `NotResourceOwner`→403). Loses the machine-discriminable `errorCode`.
- **MP-D3 (Medium, undocumented feature).** `SetAutoSubmitOnComplete` / `MediaProfileAutoSubmitOnCompleteSet` and the `AutoSubmitOnComplete` field exist in code (and are seeded `true` on five of six defaults) but appear in **none** of the write-model spec's command/event/property tables. Behaviorally load-bearing (auto-submit for review on role completion) yet unspecified (MP-M9).
- **MP-D4 (Low, payload).** `MediaProfileDeprecated` carries `DefaultAssetIds` (used to clean up AssetManagement's default-asset inverted index) — documented in scenarios but absent from the write-model event-payload table.
- **MP-D5 (Low, correctness).** `Publish()` recomputes `MaxFileSizeBytes = max(AssetDefinitions.MaxFileSizeBytes)` and injects it into the template; harmless, but this derived value lives in two places (template + AssetDefinitions) and is not in the write-model `CompiledMetadataField` contract.

---

## 3. Lifecycle Analysis

### State machine (reconstructed from `MediaProfile.cs` guards + `Apply` handlers)

```text
              Create(name, ownerId)          [handler: name unique via media-name-reservations]
                     │  emits MediaProfileCreated + MediaProfileDraftCreated(basedOnVersion=null)
                     ▼
         ┌─────────────────────────┐
         │  Status = Draft          │  ← initial draft (Draft != null, PublishedVersion = 0)
         │  (never published)       │
         │  ┌───────────────────┐   │   draft-edit sub-states (all guard Draft!=null, !Deprecated):
         │  │ AddAssetDefinition │  │     • Add/Update/Remove/Reorder/SetDefault AssetDefinition
         │  │ AttachRecordType   │  │     • Attach/Detach RecordType · UpdatePinnedRecordTypeVersion
         │  │ SetCapabilities    │  │     • Set Review/Checkout Policy · SetAutoSubmitOnComplete
         │  └───────────────────┘   │
         └───────┬──────────────────┘
                 │  Publish(compiledTemplate)   [handler: RT versions exist & not deprecated;
                 │  guard: ≥1 assetDef|recordType|capability   revision-break check; CompileTemplate]
                 ▼
         ┌─────────────────────────┐        DiscardDraft (Status must be Published)
         │  Status = Published      │◄──────────────────────────────┐
         │  PublishedVersion = N    │                                │
         │  Draft = null            │──CreateRevision──►┌────────────┴─────────────┐
         │  CompiledTemplate set    │  (guard Draft==null│  Published + Draft != null │
         └───────┬──────────────────┘   Status=Published)│  (revision in progress;    │
                 │                                        │   published vN still LIVE  │
                 │  Deprecate                             │   & immutable)             │
                 │  (guard Status=Published, Draft==null) │   ── draft-edit sub-states─┤
                 ▼                                        └────────────┬───────────────┘
         ┌─────────────────────────┐                        Publish(→ vN+1)  │
         │  Status = Deprecated     │  [terminal — no re-publish, no new draft]
         │  (name reservation freed)│
         └─────────────────────────┘

  Publish emits MetadataTemplateCompiled?  ✗ NOT emitted — template folded into MediaProfilePublished (MP-D1)
  Conformance fan-out to existing pinned MediaItems fires off MediaProfilePublished integration event (§10, MP-H3)
```

**Terminal state:** `Deprecated`. **Reversible:** `Published ⇄ (Published + revision Draft)` via `CreateRevision`/`DiscardDraft`. **Draft-discard:** only from `Published` (initial draft cannot be discarded).

### Lifecycle issues
- **MP-Life1 (High) — Revision-break detection blocks publish, contradicting ADR-010 (MP-H2).** `CheckRevisionBreaksAsync` returns a failure (→ publish rejected) when a revision removes/reorders a role, removes/reorders a RecordType, or removes a capability. ADR-010 explicitly decides conformance drift must **flag, never block** publish ("profile owners… shouldn't be held hostage"). Reordering `DisplayOrder` — a cosmetic change — is treated as a breaking change that blocks the whole publish (`MediaProfileDomainService.cs:47-67`).
- **MP-Life2 (Medium) — `Deprecated` is a dead-end with a name-reservation asymmetry.** On deprecate the handler frees the name reservation (`DeprecateMediaProfileHandler:35`) while the read-model row remains queryable as `Deprecated`. A new profile can immediately claim the freed name, so two profiles (one `Deprecated`, one active) can share a name — the read model no longer reflects a 1:1 name↔profile mapping (MP-L4). Acceptable per scenario MP-3 intent, but the freed-name-before-save ordering makes it unsafe on partial failure (MP-H5).
- **MP-Life3 (Low) — No lifecycle path resets `AutoSubmitOnComplete`/policies on discard in the read model** (see MP-M2): a discarded revision leaves summary counts inflated until the next publish.

---

## 4. Commands

17 command/handler pairs. `⚠` marks a command with at least one finding (detailed in §12–15). None carries a caller identity that any handler checks against `OwnerId`.

| Command | Handler | Trigger | Notes |
|---|---|---|---|
| CreateMediaProfileCommand | CreateMediaProfileHandler | API | ⚠ OwnerId = caller (correct at create); reserve-then-save non-atomic (compensating) |
| CreateMediaProfileRevisionCommand | CreateMediaProfileRevisionHandler | API | ⚠ no owner check (guard Published ✔) |
| AddAssetDefinitionCommand | AddAssetDefinitionHandler | API | ⚠ no owner check; no validator |
| UpdateAssetDefinitionCommand | UpdateAssetDefinitionHandler | API | ⚠ no owner check; allows role rename |
| RemoveAssetDefinitionCommand | RemoveAssetDefinitionHandler | API | ⚠ no owner check |
| ReorderAssetDefinitionsCommand | ReorderAssetDefinitionsHandler | API | ⚠ no owner check |
| SetAssetDefinitionDefaultCommand | SetAssetDefinitionDefaultHandler | API | ⚠ no owner check; asset Active + content-type checked ✔; asset-owner not checked |
| AttachRecordTypeToProfileCommand | AttachRecordTypeHandler | API | ⚠ no owner check; RT version-exists + not-deprecated ✔ |
| UpdatePinnedRecordTypeVersionCommand | UpdatePinnedRecordTypeVersionHandler | API | ⚠ no owner check; new version validated ✔ |
| DetachRecordTypeFromProfileCommand | DetachRecordTypeHandler | API | ⚠ no owner check |
| SetReviewPolicyCommand | SetReviewPolicyHandler | API | ⚠ no owner check |
| SetCheckoutPolicyCommand | SetCheckoutPolicyHandler | API | ⚠ no owner check |
| SetMediaProfileCapabilitiesCommand | SetCapabilitiesHandler | API | ⚠ no owner check |
| SetAutoSubmitOnCompleteCommand | SetAutoSubmitOnCompleteHandler | API | ⚠ no owner check; **undocumented in spec** (MP-D3) |
| DiscardMediaProfileDraftCommand | DiscardMediaProfileDraftHandler | API | ⚠ no owner check |
| PublishMediaProfileCommand | PublishMediaProfileHandler | API + seed | ⚠ **no owner check**; RT re-validation + compile ✔; name-swap-then-save non-atomic |
| DeprecateMediaProfileCommand | DeprecateMediaProfileHandler | API | ⚠ **no owner check**; **release-before-save** (MP-H5) |

**Cross-cutting command issues:**
- **No mutating command carries an owner-comparison identity that any handler checks.** `Create` sets `OwnerId = context.Actor.Id` (correct at creation), but `Publish`/`Deprecate`/all draft mutators receive only `(TenantId, MediaProfileId, …, OccurredAt)` — PERM-1 is impossible downstream (§12 MP-C1).
- **Handlers return generic errors** (`InvalidOperation`, `EntityAlreadyExists`, `ResourceNotFound`) — no catalog codes / `errorCode` (§12 MP-M1).
- **No duplicate/redundant commands** — the command set maps cleanly 1:1 to aggregate methods (plus the undocumented `SetAutoSubmitOnComplete`).

---

## 5. Queries

3 read paths in code — `GetMediaProfileById`, `ListMediaProfiles`, `GetMediaProfileVersion`, plus an undocumented `ListMediaProfileVersions` (spec read-model lists only the first three; `ListMediaProfilesByOwnerQuery` is realised as `ListMediaProfilesQuery`).

| Query | Paging | Auth / Scope | Notes |
|---|---|---|---|
| GetMediaProfileByIdQuery | n/a | ⚠ none | no owner-or-system scoping; response leaks `TenantId` (MP-M5); **omits `compiledMetadataFields`/`suppressedFieldNames`** (MP-H4) |
| ListMediaProfilesQuery | cursor (ADR-014 ✔) | ⚠ **none — TenantId only** | spec is `OwnerId IN [owner, owner_system]` via `OwnerStatusIndex`; impl returns **all** profiles in the tenant regardless of owner (MP-M6); reads the heavy Detail model, not Summary (MP-L7) |
| GetMediaProfileVersionQuery | n/a | ⚠ none | immutable version snapshot; no owner scoping |
| ListMediaProfileVersionsQuery | cursor (ADR-014 ✔) | ⚠ none | not in read-model spec (extra) |

**Query issues:**
- **CQRS boundary is clean** — handlers return read-model DTOs via `IReadModelReader`; no aggregates/event payloads cross the boundary; cursor pagination with no total count (ADR-014 ✔). Good.
- **No owner/visibility scoping** on any read (§12 MP-C1/MP-M6). The spec's read authorization ("owner or `owner_system`") is not enforced; `ListMediaProfilesQuery.Matches` filters on `TenantId` (+ optional exact name) only.
- **The Summary read model + Summary projector are unused by any query** — the list endpoint reads `MediaProfileDetailReadModel` (full draft included). Built-but-unused, and a heavier list payload than necessary (MP-L7).

---

## 6. API Endpoints

Spec (`mediaprofile.api.md`) vs implementation. All 20 routes are implemented and `Version(1)`.

| Spec route | Verb | Impl? | Impl status | Spec status | Note |
|---|---|---|---|---|---|
| /v1/profiles | POST | ✔ | 201 | 201 | OwnerId = Actor.Id ✔ |
| /v1/profiles/{id}/draft | POST | ✔ (CreateMediaProfileDraft) | 204 | 204 | ok |
| /v1/profiles/{id}/asset-definitions | POST | ✔ | 204 | 204 | route todo-comment "should be assets" (cosmetic) |
| /v1/profiles/{id}/asset-definitions/{role} | PATCH | ✔ | 204 | 204 | allows role rename |
| /v1/profiles/{id}/asset-definitions/{role} | DELETE | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/asset-definitions/reorder | POST | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/asset-definitions/{role}/default | PUT | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/record-types/{rtId} | POST | ✔ | 204 | 204 | 404 on missing version ✔ |
| /v1/profiles/{id}/record-types/{rtId}/version | PUT | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/record-types/{rtId} | DELETE | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/review-policy | PUT | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/checkout-policy | PUT | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/capabilities | PUT | ✔ | 204 | 204 | api.md lists invalid value "DigitalSigning" (enum = "Signing") (MP-L6) |
| /v1/profiles/{id}/auto-submit | PUT | ✔ | 204 | — | **not in api.md route table** (MP-D3/MP-M9) |
| /v1/profiles/{id}/draft | DELETE | ✔ | 204 | 204 | ok |
| /v1/profiles/{id}/publish | POST | ✔ | 200 {newVersion} | 200 | ok |
| /v1/profiles/{id}/deprecate | POST | ✔ | 204 | 204 (scenario MP-3 says 202) | scenario/endpoint drift (MP-L6) |
| /v1/profiles/{id} | GET | ✔ | 200 | 200 | leaks `TenantId`; **omits compiledMetadataFields/suppressedFieldNames** (MP-H4/MP-M5) |
| /v1/profiles | GET | ✔ | 200 | 200 | not owner-scoped; leaks `TenantId` (MP-M6/MP-M5) |
| /v1/profiles/{id}/versions | GET | ✔ | 200 | 200 | ok |
| /v1/profiles/{id}/versions/{v} | GET | ✔ | 200 | 200 | version snapshot omits DimensionConstraints (MP-M3) & compiled fields |

**Endpoint issues:**
- **No endpoint declares authorization.** Every endpoint's Swagger advertises `ProducesProblem(403)` "does not have permission…" that **no code path can emit** — `PublishMediaProfileEndpoint`/`DeprecateMediaProfileEndpoint` explicitly document a 403 that is never enforced (§12 MP-C1).
- **RFC 9457 `errorCode` not emitted / read side flattens** — write endpoints call `SendDomainErrorAsync`, read endpoints `SendQueryErrorAsync`; neither surfaces the catalog `errorCode` extension (§12 MP-M1), same base-class behaviour as the Collection/MediaItem reviews.
- **No request validators** (FluentValidation) on any request DTO (§7).

---

## 7. Request DTO Review

| DTO | Findings |
|---|---|
| CreateMediaProfileRequest | `Name` via `MediaProfileName.From` throws on malformed → 500; no length/pattern validator at the boundary |
| AddAssetDefinitionRequest | `RoleName.From`/`AssetId.From(DefaultAssetId)` throw on malformed → 500; `AcceptedContentTypes: List<MediaCategory>` enum-bound (invalid → 400/500); `DisplayName` defaults to `RoleName` if null (OK); `DisplayOrder ?? 0` triggers aggregate auto-assign |
| UpdateAssetDefinitionRequest | permits role rename (`newRoleName`) — no uniqueness re-check against other roles in the aggregate `UpdateAssetDefinition` |
| SetCapabilitiesRequest | `Capabilities: List<Capability>` enum-bound; api.md documents a non-existent `DigitalSigning` value |
| AttachRecordTypeRequest / UpdatePinnedRecordTypeVersionRequest | `{ version:int }`; `RecordTypeId` from route via `RecordTypeId.From` throws → 500 |
| ReorderAssetDefinitionsRequest | array of `{roleName, displayOrder}`; no dup/id validation at boundary |

**Cross-cutting:**
- **No FluentValidation validators anywhere** in the slice (grep confirms). `MediaProfileId.From`/`RoleName.From`/`AssetId.From`/`RecordTypeId.From`/`MediaProfileName.From` call `Guid.Parse`/`ValueOf` constructors that **throw on malformed input → 500** where the spec expects 400/404/422 (§12 MP-M4).
- **`UpdateAssetDefinition` role rename** is an under-guarded surface — the aggregate updates by old role name and sets `RoleName = newRoleName` without checking the new name doesn't already exist on another definition (`MediaProfile.cs:527-534`).

---

## 8. Response DTO Review

| DTO | Findings |
|---|---|
| CreateMediaProfileResponse | `{ id, timestamp }` — matches spec 201 body ✔ |
| GetMediaProfileByIdResponse | **leaks `TenantId`** (`:8`); exposes `OwnerId` (spec shows `ownerId` ✔); **omits `compiledMetadataFields`/`suppressedFieldNames`** the api.md GET body requires (MP-H4); `DimensionConstraints` always null (MP-M3) |
| AssetDefinitionModel | no `IsDefault` (consistent with VO); `DimensionConstraints` sourced from a projector that never populates it (MP-M3) |
| PublishMediaProfileResponse | `{ profileId, newVersion, timestamp }` — matches spec `{ newVersion }` ✔ |
| GetMediaProfileVersionResponse / MediaProfileSnapshotModel | version snapshot; omits DimensionConstraints & compiled fields |
| ListMediaProfilesResponse | implicit-converts `PagedResult<MediaProfileDetailReadModel>` → leaks `TenantId`/full draft for every row |

**Cross-cutting:**
- **`TenantId` leakage** in `GetMediaProfileByIdResponse` and the list response — a multi-tenancy boundary value that must never round-trip to clients (MP-M5), identical to Collection COL-M4 / MediaItem MI-M10.
- **`compiledMetadataFields` / `suppressedFieldNames` missing** — the read model doesn't store them and the response doesn't expose them, so the ADR-013 client-discovery contract (api.md GET example) is unfulfillable (MP-H4).

---

## 9. Domain Events

17 domain events, all registered in `MediaProfile`'s `When<>` block. Publisher = `MediaProfile` aggregate.

**Projection coverage (verified against all four projectors):**

| Domain event | Detail | Summary | VersionDetail | VersionSummary | Notes |
|---|---|---|---|---|---|
| `MediaProfileCreated` | ✔ INSERT | ✔ INSERT | — | — | ok |
| `MediaProfileDraftCreated` | ✔ HasDraft+snapshot | ✔ HasDraft | — | — | ok |
| `AssetDefinitionAdded` | ✔ draft | ⚠ count+1 | — | — | Summary count drift (MP-M2) |
| `AssetDefinitionUpdated` | ✔ draft | — | — | — | ok (count unaffected) |
| `AssetDefinitionRemoved` | ✔ draft | ⚠ count-1 | — | — | Summary count drift (MP-M2) |
| `AssetDefinitionsReordered` | ✔ draft | — | — | — | ok |
| `AssetDefinitionDefaultSet` | ✔ draft | — | — | — | ok |
| `RecordTypeAttachedToProfile` | ✔ draft | ⚠ count+1 | — | — | Summary count drift (MP-M2) |
| `RecordTypeVersionPinnedOnProfile` | ✔ draft | — | — | — | ok |
| `RecordTypeDetachedFromProfile` | ✔ draft | ⚠ count-1 | — | — | Summary count drift (MP-M2) |
| `MediaProfileReviewPolicySet` | ✔ draft | ✔ | — | — | ok |
| `MediaProfileCheckoutPolicySet` | ✔ draft | ✔ | — | — | ok |
| `MediaProfileCapabilitiesSet` | ✔ draft | ✔ | — | — | ok |
| `MediaProfileAutoSubmitOnCompleteSet` | ✔ draft | ✔ | — | — | ok |
| `MediaProfileDraftDiscarded` | ✔ HasDraft=false | ✔ HasDraft=false | — | — | ⚠ Summary counts NOT rolled back (MP-M2) |
| `MediaProfilePublished` | ✔ overwrite+clear draft | ✔ reset counts | ✔ INSERT-once | ✔ INSERT-once | ⚠ DimensionConstraints/compiled fields dropped (MP-M3/MP-H4); VersionDetail `DefaultAssetId.ToString()` malformed (MP-L2) |
| `MediaProfileDeprecated` | ✔ status | ✔ status | — | — | ok |

Other notes:
- **Timing correct** — no wall-clock in any event emission (a genuine strength; the sole `UtcNow` is `TakeSnapshot` metadata).
- **Projection strength:** the **Detail** projector has essentially complete coverage; out-of-order safety via `MissingCurrentAsync()`; every upsert stamps `ProjectedVersion = e.AggregateVersion` (idempotent under duplicate SQS delivery). The version projectors are correctly insert-once (`UnchangedAsync` if present).
- **No `MetadataTemplateCompiled` event** exists (MP-D1); the read-model spec's single `MediaProfileProjector` is realised as four projectors — the detail projector's class comment ("no `MediaProfileVersionReadModel` exists") is now stale (MP-L6).
- **Compiled template is not projected anywhere** — no projector reads `PublishedSnapshot.CompiledTemplate`, so `compiledMetadataFields`/`suppressedFieldNames` never reach a read model (MP-H4).

---

## 10. Integration Events

### Published (mapper `MediaProfileDomainEventMapper.cs`)

Two mappings — `MediaProfilePublished → MediaProfilePublishedIntegrationEvent` and `MediaProfileDeprecated → MediaProfileDeprecatedIntegrationEvent`. Both carry `TenantId` + `EventVersion = AggregateVersion`. Both spec-listed events are published.

| Issue | Severity | Detail |
|---|---|---|
| MP-FP1 | High | **`MediaProfilePublishedIntegrationEvent` does not carry the full `MediaProfilePublishedSnapshot`.** The write-model + context-overview say the published event "Carries the full `MediaProfilePublishedSnapshot`… consumed by… AssetManagement (`media-item-capability-refs`), DocumentSigning, and Registration to refresh their local media-profile reference models." The actual event carries `Name, Description, VersionNumber, Capabilities(string[]), ReviewPolicy, CheckoutPolicy, PublishedAt, DefaultAssetIds` — **no `AssetDefinitions`, no `CompiledTemplate`, no per-role `MaxFileSizeBytes`.** Downstream reference models that need asset-role/size data cannot rebuild from this event. (Three-way inconsistency: context-overview's `MediaProfilePublishedMessage` lists an even smaller `(TenantId, MediaProfileId, Name, Version, Capabilities, PublishedAt)`.) |
| MP-FP2 | Low (doc) | Code record names are `*IntegrationEvent`; context-overview/write-model contracts call them `*Message`. Reconcile before wiki publish (mirrors Collection COL-FP1 / MediaItem MI-FP4). |

### Consumed

**Conformance fan-out (publishing side of ADR-010) — `MediaProfilePublishedConformanceFanoutHandler`:**

| Issue | Severity | Detail |
|---|---|---|
| MP-FC1 | High | **Unbounded, uncheckpointed, result-swallowing fan-out (MP-H3).** On `MediaProfilePublishedIntegrationEvent` it loads **all** pinned item ids into memory (`profileItemQuery.GetMediaItemIdsAsync`, no pagination — only a >1000 log warning, matching ADR-010's "pagination not yet implemented"), then a **serial** load→`UpdateConformanceStatus`→`SaveAsync` loop. It **ignores the `Result` of `UpdateConformanceStatus`** and has **no per-item try/catch**, so any single `SaveAsync` throw (concurrency/throttle) aborts the entire fan-out; SQS redelivery reprocesses from the top. For a platform-default profile (pinned by potentially thousands of items across the tenant) this is a Lambda-timeout / OOM risk. |
| MP-FC2 | Medium | **`TenantId` sourced from the payload body** (`TenantId.From(e.TenantId)`), not the SNS message attribute — violates the "never from payload body" convention (mirrors AssetManagement F-C4 / MediaItem MI-FC2). |
| MP-FC-pos | — | **Correct:** the fan-out *does* exist and *is* wired to `MediaProfilePublishedIntegrationEvent`, correctly skips archived items, and recomputes required-asset-role + required-metadata-field gaps. The publish therefore *does* drive conformance — it is just unbounded and failure-fragile. |

**RecordType reference consumers (the RecordType consuming side):**

| Issue | Severity | Detail |
|---|---|---|
| MP-FC3 | — (correct) | `RecordTypePublishedEventHandler` / `RecordTypeDeprecatedEventHandler` `return pipeline.DispatchAsync(e)` — exceptions propagate to SQS (no swallow — **better than AssetManagement F-C1**). `RecordTypeVersionDetailIndexProjector` maintains per-version `RecordTypeVersionReference` rows + a per-RecordType deprecation sentinel; `IRecordTypeVersionReadModel.VersionExistsAsync`/`IsDeprecatedAsync` read them, and `CompileTemplateAsync` reads them for template compilation. Pins stay valid at publish because `PublishMediaProfileHandler` re-checks every `RecordTypeRef` (exists + not deprecated) before compile. |
| MP-FC4 | Low | The reference projector consumes `RecordTypePublished`/`RecordTypeDeprecated` but not `RecordTypeCreated` (write-model reference table lists it). Benign if v1 also emits `RecordTypePublished`; confirm. `RecordTypeVersionReference.CreateProjectionKey(tenant, version, recordTypeId)` uses a different argument order than `CreateDeprecatedProjectionKey(tenant, recordTypeId, "DEPRECATED")` — low-confidence PK/SK modelling concern (depends on unread `ProjectionKey` semantics). |

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Ownership guard (PERM-1) | All write = `caller.owner_id == mediaProfile.OwnerId`; read = owner-or-`owner_system` (`mediaprofile.api.md:47-52`, `security-scenarios.md:67`) | Not enforced anywhere; commands carry no comparison identity; reads TenantId-only | Critical | Thread & enforce `Actor.Id == OwnerId` on writes; owner-or-system on reads; 403 `NotResourceOwner` |
| CompiledField `BareName` / `SuppressedFieldNames` persistence | Baked immutably into snapshot at publish (ADR-013) | `CompiledMetadataFieldConverter` drops `BareName`; snapshots drop both | High | (De)serialize `BareName`; add `SuppressedFieldNames`/`BareName` to snapshot records |
| Revision breaks | ADR-010: conformance drift flags, never blocks publish | `CheckRevisionBreaksAsync` blocks publish (incl. on reorder) | High | Remove publish block; drive via the conformance fan-out only |
| Conformance fan-out | Paginated `media-item-profile-index`, warn >1000 (ADR-010) | Loads all ids, serial loop, no checkpoint, swallows Result | High | Paginate + checkpoint; observe Result; ACK idempotent, rethrow transient |
| `compiledMetadataFields`/`suppressedFieldNames` on GET | Present in GET detail (api.md:282-315) | Not projected, not in response DTO | High | Project CompiledTemplate; surface both fields |
| Published integration event | Full `MediaProfilePublishedSnapshot` (write-model:254) | Summary only (no AssetDefinitions/CompiledTemplate) | High | Carry the snapshot (or the fields downstream ref-models need) |
| Reservation ↔ event atomicity | `Save`+reservation via ambient `ITransactionScope`/`TransactionBehavior` (write-model:420) | Sequential awaits; Deprecate releases **before** save | High | Ambient transaction; order guard→event→reservation; idempotent/compensating |
| `MetadataTemplateCompiled` event | Separate event, sole `CompiledTemplate` mutation (write-model:194,217) | No such event; folded into `MediaProfilePublished` | Medium | Reconcile spec to code (or add the event) |
| Error contract | RFC 9457 + `errorCode`; catalog codes | Generic `InvalidOperation`/`EntityAlreadyExists`; no `errorCode` | Medium | Emit `errorCode`; map catalog codes |
| DimensionConstraints in read model | Present on AssetDefinitionDto (read-model:161) | Projector passes `null` ("deferred") | Medium | Map dimension constraints in projectors |
| Summary counts | Reflect published state | Drift during draft; not rolled back on discard | Medium | Base counts on draft/published snapshot, not deltas |
| List scope | `OwnerId IN [owner, owner_system]` via `OwnerStatusIndex` | TenantId-only; all owners visible | Medium | Owner-scope the list query/index |
| `TenantId` in responses | Not in GET/list body (api.md GET example) | Present in detail + list DTOs | Medium | Remove `TenantId` from response DTOs |
| Seeding idempotency | Deterministic per-command `IdempotencyKey = Uuid5(...)` (defaults.md:218) | `SendAsync` without key; `MediaProfileId.New()`; skip-if-name-exists | Medium | Use deterministic keys; make the sequence resumable |
| `AutoSubmitOnComplete` | absent from write-model spec | full command/event/field/endpoint in code | Medium | Document (or remove) |
| `AssetDefinition.IsDefault` / `SetDefaultAssetDefinition` (sets IsDefault) | write-model:131,186 | Not implemented; code sets `DefaultAssetId` (agrees with defaults.md) | Low | Fix write-model spec (defaults.md + code are the truth) |
| Default profile count | context-overview: 5 | defaults.md + code: 6 (adds "Media Set") | Low | Reconcile context-overview |
| Deprecate status code | scenario MP-3: 202; api.md/endpoint: 204 | 204 | Low | Reconcile scenario |
| Capabilities enum values | api.md: "DigitalSigning" | enum: "Signing" | Low | Fix api.md |
| VersionDetail `DefaultAssetId` | GUID string | `AssetId.ToString()` → `"AssetId { Value = … }"` | Low | Use `.Value.ToString()` |

---

## 12. Bugs

### Critical

**MP-C1 — No ownership/authorization on any endpoint, handler, or query (intra-tenant tampering + shared-default corruption).**
Verified: zero auth attributes across all MediaProfile endpoints; no mutating handler compares the caller to `mediaProfile.OwnerId`; `Publish`/`Deprecate`/all draft-mutation commands carry only `(TenantId, MediaProfileId, …, OccurredAt)`; read handlers apply no owner/`owner_system` scoping. `mediaprofile.api.md:47-52` requires `caller.owner_id == mediaProfile.OwnerId` on writes and owner-or-`owner_system` on reads; `security-scenarios.md` PERM-1 makes the guard uniform across `MediaProfile`.
*Why it's a problem:* MediaProfile is the structural contract that governs every conforming MediaItem's asset slots, metadata schema, capabilities, and review/checkout policy. *Impact:* any authenticated tenant user can rename, re-schema, add/remove capabilities on, **publish, or deprecate** any other owner's profile — and because platform defaults are shared `OwnerId = "owner_system"` rows in each tenant partition, a single user can deprecate or mutate a default that all other users depend on (deprecation blocks new MediaItem creation against it; a malicious capability change alters processing/registration behaviour across the tenant). *Recommendation:* thread `Actor.Id`/`ActorType` into every mutating command; enforce `actor.Id == mediaProfile.OwnerId` (System actor exempt, so the seeder still works) in write handlers and owner-or-`owner_system` in read handlers; return `NotResourceOwner`/`Forbidden` → 403 with `errorCode`.

### High

**MP-H1 — `CompiledMetadataFieldConverter` and the snapshot records silently drop ADR-013 collision data on round-trip.**
`CompiledMetadataFieldConverter.Write`/`Read` (`:99-152`, `:30-72`) never (de)serialize `BareName`; on read the field is reconstructed with `BareName` defaulting to `Name`. Separately, `CompiledTemplateFieldSnapshot` has no `BareName` field and `CompiledMetadataTemplateSnapshot` has no `SuppressedFieldNames` field (`ValueObjectToSnapshotMapper`/`SnapshotToValueObjectMapper` therefore cannot carry them). `MediaProfileDomainService.CompileTemplateAsync` correctly sets `BareName` (≠ `Name` for collided fields) and `SuppressedFieldNames`, but:
- On **any event replay / read-model projection** of `MediaProfilePublished`, each collided `CompiledMetadataField.BareName` reverts to its qualified `Name`.
- On **any aggregate-snapshot restore**, `SuppressedFieldNames` becomes `[]` and every `BareName` reverts to `Name`.
*Why it's a problem:* `CompiledMetadataTemplate.ToSnapshot()` maps `field.BareName → MediaProfileSnapshotField.UnqualifiedName` (embedded in `MediaItemCreated`) — the exact key ADR-013's governed-metadata bare-name resolution on `MediaItem` depends on — and the api.md GET `bareName`/`suppressedFieldNames` are documented client-discovery data. After a round-trip both are corrupted for any profile with colliding RecordType field names. *Impact:* wrong `bareName` reported to clients; `SuppressedFieldNames` lost after snapshot restore; latent ADR-013 resolution drift for MediaItems created from a rehydrated/snapshot-restored profile. *Recommendation:* serialize `BareName` in the converter; add `BareName` to `CompiledTemplateFieldSnapshot` and `SuppressedFieldNames` (+`ProcessingTimeoutMinutes`) to `CompiledMetadataTemplateSnapshot`; add a round-trip unit test with a collision.

**MP-H2 — Revision-break detection blocks publish, contradicting ADR-010.**
`MediaProfileDomainService.CheckRevisionBreaksAsync` (`:21-86`) collects "breaks" for removed/reordered RecordTypes, removed/reordered AssetDefinition roles, and removed capabilities, and returns `DomainError.InvalidOperation` when any exist — which `PublishMediaProfileHandler:61-68` propagates, rejecting the publish. ADR-010 ("Conformance drift: flag, never block") explicitly decides that a profile revision must **not** be blocked and that existing non-conforming items are flagged `PendingConformance` instead. Reordering `DisplayOrder` — cosmetic — is also treated as breaking.
*Why it's a problem:* the whole point of ADR-010's flag-never-block model is that profile owners can revise freely; this handler re-introduces the blocking behaviour the ADR rejected, and over-broadly (reorder). *Impact:* legitimate revisions (drop an optional role, reorder display, remove an unused capability) are blocked at publish; the conformance fan-out that should absorb this is bypassed. *Recommendation:* remove the publish block (or downgrade to a non-blocking warning); rely on the conformance fan-out for drift.

**MP-H3 — Conformance fan-out is unbounded, uncheckpointed, and swallows the command `Result`.**
`MediaProfilePublishedConformanceFanoutHandler.HandleAsync` (`:29-67`) loads **all** pinned item ids (`GetMediaItemIdsAsync`, no pagination beyond a >1000 log line), then serially `GetByIdAsync`→`UpdateConformanceStatus`→`SaveAsync` per item with **no per-item try/catch** and **no inspection of the `UpdateConformanceStatus` result**. ADR-010 specifies a paginated `media-item-profile-index` walk; the code is the "not yet implemented" path.
*Why it's a problem:* a platform-default profile is pinned by many MediaItems tenant-wide; a single-message serial loop over thousands of aggregates risks Lambda timeout/OOM, and any one `SaveAsync` throw fails the whole message with no checkpoint (SQS redelivery re-does everything). *Impact:* conformance re-evaluation may never complete for large profiles; partial progress is repeated on retry; transient faults are indistinguishable from success. *Recommendation:* paginate the index; process in bounded batches with checkpointing; observe the `UpdateConformanceStatus` result; source `TenantId` from the message attribute (MP-FC2).

**MP-H4 — `compiledMetadataFields` / `suppressedFieldNames` are never projected or surfaced (ADR-013 client discovery missing).**
No projector reads `MediaProfilePublished.PublishedSnapshot.CompiledTemplate`; `MediaProfileDetailReadModel` has no compiled-field fields; `GetMediaProfileByIdResponse` omits them. The api.md GET detail body (`:282-315`) documents both, and ADR-013 relies on them so clients can discover the qualified keys for collided fields before a write is rejected.
*Why it's a problem:* the documented API contract cannot be met; clients writing governed metadata against a profile with colliding RecordTypes have no way to learn the valid qualified keys except by trial-and-error rejection. *Impact:* ADR-013's "discover valid qualified field names ahead of time" consequence is unrealisable. *Recommendation:* project `CompiledTemplate.Fields` (name, bareName, fieldType, isRequired, isImmutable, recordTypeId/version) and `SuppressedFieldNames` into the detail read model and GET response.

**MP-H5 — Non-atomic name-reservation dual writes; Deprecate frees the name before persisting.**
`DeprecateMediaProfileHandler:35-37` calls `nameReservationService.ReleaseAsync(...)` **before** `repository.SaveAsync(...)`. `CreateMediaProfileHandler:37-38` reserves then saves (compensating release on save-fail). `PublishMediaProfileHandler:91-115` swaps the name reservation then saves (compensating release of the *new* name on save-fail — but the *old* name is already released by `SwapAsync` and is not restored). The write-model spec (`:420`) mandates these register with an ambient `ITransactionScope` committed atomically by `TransactionBehavior`; the code uses manual sequential awaits.
*Why it's a problem:* on Deprecate, if `SaveAsync` throws, the name is already freed while the profile stays `Published` — another profile can immediately claim a name still held by a live profile. On rename-publish, a save failure leaves *both* names unreserved. *Impact:* reservation/aggregate divergence and duplicate-name windows on any partial failure (mirrors Collection COL-H6 / MediaItem MI-H4; Deprecate's release-before-save is the acute variant, like `ArchiveMediaItemHandler`). *Recommendation:* adopt the ambient-transaction pattern; where unavailable, order guard→event-persisted→reservation-mutation and make the reservation op idempotent/compensating.

**MP-H6 — Published integration event omits the snapshot downstream reference models consume (MP-FP1).**
See §10. `MediaProfilePublishedIntegrationEvent` carries capabilities/policies/defaults but not `AssetDefinitions`, per-role `MaxFileSizeBytes`, or `CompiledTemplate`, contradicting the write-model claim that it carries the full `MediaProfilePublishedSnapshot` for AssetManagement's `media-item-capability-refs` and other reference-model refreshes. *Recommendation:* carry the full snapshot (or at minimum the asset-role/size/capability data the consuming ref-models need), and reconcile the three diverging contract descriptions.

### Medium

- **MP-M1** — Generic errors, no `errorCode` (MP-D2). Handlers return `InvalidOperation`/`EntityAlreadyExists`/`ResourceNotFound`; the catalog's `ProfileNameConflict`/`NoActiveDraft`/`RecordTypeVersionNotFound`(404)/`RecordTypeDeprecated`/`MediaProfileNotPublished`/`DraftInProgress`/`DraftEmpty`/`NotResourceOwner`(403) are never emitted with an `errorCode` extension.
- **MP-M2** — Summary count drift. `MediaProfileSummaryProjector` increments/decrements `AssetDefinitionCount`/`RecordTypeCount` on **draft** add/remove/attach/detach (`:97-146`), does not reset them when a revision draft opens, and does **not** roll them back on `MediaProfileDraftDiscarded`. Counts are only corrected at the next `MediaProfilePublished`. A profile with an open/discarded revision reports wrong counts.
- **MP-M3** — DimensionConstraints never projected. `MediaProfileDetailProjector.MapAssetDefinition` and `MediaProfileVersionDetailProjector` both pass `null` for `DimensionConstraints` ("mapping deferred"), so GET detail and version snapshot never return dimension constraints even when set on the draft/published definition.
- **MP-M4** — No request validators → malformed `roleName`/`assetId`/`profileId`/`name` reach `ValueOf`/`Guid.Parse` and throw → 500 where 400/404/422 is expected (§7).
- **MP-M5** — `TenantId` leaked in `GetMediaProfileByIdResponse` and the list response (multi-tenancy boundary value).
- **MP-M6** — List/read not owner-scoped. `ListMediaProfilesQuery.Matches` filters `TenantId` only (`:20-24`); spec is owner-or-`owner_system` via `OwnerStatusIndex`. Users see all owners' profiles; `GetMediaProfileById` returns any owner's profile.
- **MP-M7** — Seeding not resumable/idempotent on partial failure. `SeedDefaultProfilesService.SeedProfileAsync` dispatches Create→AddAssetDef×N→SetCaps→SetReview→SetCheckout→[AutoSubmit]→Publish with **no `IdempotencyKey`** (`SendAsync` calls) and a fresh `MediaProfileId.New()`, guarding only with `IsNameAvailableAsync` up front. If any step after Create fails (`ThrowOnFailure`), the profile exists + name is reserved but is left unpublished; a re-run sees the name taken and **skips** it forever — a permanently-broken `Draft` default. The spec's deterministic `Uuid5` per-command idempotency key is not implemented.
- **MP-M8** — Spec/impl divergence: `MetadataTemplateCompiled` event (spec: separate, sole `CompiledTemplate` mutation) does not exist; template folded into `MediaProfilePublished`. VO/property doc comments referencing it are stale (MP-D1).
- **MP-M9** — `AutoSubmitOnComplete` command/event/endpoint/field entirely undocumented in the write-model spec (MP-D3); it drives review-lifecycle behaviour (auto-submit on required-role completion) and is seeded `true` on five of six defaults.

### Low

- **MP-L1** — `AssetDefinition.IsDefault` + `SetDefaultAssetDefinition` (sets IsDefault) from write-model.md are unimplemented; code has only `DefaultAssetId` and `SetAssetDefinitionDefault(role, assetId)`. defaults.md and the code agree there is no default-*role* flag; the write-model spec is the stale/inconsistent one.
- **MP-L2** — `MediaProfileVersionDetailProjector:37` uses `a.DefaultAssetId?.ToString()` (not `.Value.ToString()` as the detail projector does), emitting `"AssetId { Value = … }"` into the version snapshot.
- **MP-L3** — The 3-RecordType cap (`MediaProfile.cs:164`) is enforced in the aggregate but is absent from the spec invariant table; error is generic `InvalidOperation`.
- **MP-L4** — Deprecate frees the name reservation while the `Deprecated` read-model row remains → name↔profile no longer 1:1 (compounded by MP-H5's ordering).
- **MP-L5** — Integration events named `*IntegrationEvent` vs spec `*Message`; `MediaProfileDeprecated` domain event carries extra `DefaultAssetIds` not in the write-model payload table (documented only in scenarios).
- **MP-L6** — Spec inconsistencies: context-overview lists 5 defaults vs 6 in defaults.md/code; api.md capabilities value "DigitalSigning" ≠ enum "Signing"; deprecate scenario says 202 vs 204 endpoint; detail projector's "no `MediaProfileVersionReadModel` exists" comment is stale.
- **MP-L7** — `MediaProfileSummaryReadModel` + `MediaProfileSummaryProjector` are built but unused — the list query reads the Detail model.
- **MP-L8** — Aggregate carries both `PublishedVersion` and a redundant `Version` (both set to `newVersion` on publish; `Version` also mirrored from the snapshot) — confusing duplication.
- **MP-L9** — `UpdateAssetDefinition` permits a role rename with no uniqueness re-check against other draft roles (`MediaProfile.cs:527-534`).

---

## 13. Design Flaws

1. **Authorization is entirely absent** for the aggregate that configures every MediaItem's structural contract, and the shared `owner_system` platform-default rows make the blast radius tenant-wide (MP-C1). This is the single largest gap.
2. **The compiled-metadata-template is over-engineered yet lossy.** A custom `CompiledMetadataFieldConverter`, a parallel snapshot type hierarchy, and a full `MetadataValue` type-discriminated JSON converter exist — but the converter and snapshot records silently omit the two fields (`BareName`, `SuppressedFieldNames`) that carry the ADR-013 collision semantics they exist to serve (MP-H1). Complexity without the correctness it was built for. Consider serializing the VO with default STJ (which already round-trips `SuppressedFieldNames`) rather than a hand-rolled converter, or complete the converter/snapshot.
3. **The conformance model is internally contradictory against ADR-010** — one path blocks publish on drift (`CheckRevisionBreaksAsync`, MP-H2) while another (the fan-out, MP-H3) flags it. The two encode opposite decisions; only the fan-out matches the ADR.
4. **Non-transactional reservation dual writes** with inconsistent ordering (Deprecate release-before-save; Publish swap-before-save) repeat the Collection/MediaItem partial-failure windows (MP-H5).
5. **The published integration event is a lossy summary** of the snapshot the spec says downstream reference models consume, forcing either a follow-up query or stale reference models (MP-H6).
6. **The read/publish surface silently diverges from the compiled template it computes** — the template is compiled at publish, embedded in the event, and then never projected, so the API contract that exposes it is dead (MP-H4).

---

## 14. Design Gaps

- **No authorization layer** (endpoints or handlers) — the largest gap.
- **No request-validation layer** (no FluentValidation), so the API cannot return 400/422 for malformed input.
- **No RFC 9457 `errorCode` emission** from the module's error helpers.
- **No projection of the compiled metadata template** → `compiledMetadataFields`/`suppressedFieldNames` unavailable.
- **No pagination/checkpointing** in the conformance fan-out (ADR-010 acknowledged but unbuilt).
- **No ambient transaction** around reservation + event append.
- **No resumable/idempotent seeding** (deterministic per-command idempotency keys absent).
- **No owner-scoped list index** (`OwnerStatusIndex` design not used by the query).
- **`DimensionConstraints` mapping "deferred"** in both detail and version projectors.

---

## 15. Missing Features

- **Ownership enforcement** on every write and read (commands lack a caller-comparison identity).
- **`compiledMetadataFields` / `suppressedFieldNames`** in the detail read model and GET response (ADR-013 client discovery).
- **Full snapshot** (or asset-role/size/capability payload) on `MediaProfilePublishedIntegrationEvent` for downstream reference models.
- **Paginated + checkpointed conformance fan-out** with result observation.
- **Coded domain errors** (`ProfileNameConflict`→409, `NoActiveDraft`, `DraftEmpty`, `RecordTypeVersionNotFound`→404, `RecordTypeDeprecated`, `MediaProfileNotPublished`, `DraftInProgress`, `NotResourceOwner`→403) mapped to catalog status codes.
- **DimensionConstraints projection** into detail/version read models.
- **`BareName`/`SuppressedFieldNames` serialization** (converter + snapshot records).
- **FastEndpoints request validators** (id/name/role well-formedness, capability enum, pageSize cap).
- **Owner-scoped list** (`OwnerId IN [owner, owner_system]`).
- **Spec documentation** for `AutoSubmitOnComplete`.

---

## 16. Recommendations (prioritised)

### 1 — Security
- **R1 (Critical).** Implement PERM-1: thread `Actor.Id`/`ActorType` into every mutating command; enforce `actor.Id == mediaProfile.OwnerId` in write handlers (System actor exempt so the seeder works); enforce owner-or-`owner_system` scoping in read handlers/queries; return 403 `NotResourceOwner`/`Forbidden` with `errorCode` (MP-C1).

### 2 — Correctness / ADR-013
- **R2 (High).** Serialize `BareName` in `CompiledMetadataFieldConverter`; add `BareName` to `CompiledTemplateFieldSnapshot` and `SuppressedFieldNames`(+`ProcessingTimeoutMinutes`) to `CompiledMetadataTemplateSnapshot`; add a collision round-trip test (MP-H1).
- **R3 (High).** Project `CompiledTemplate.Fields` + `SuppressedFieldNames` into the detail read model and GET response (MP-H4).

### 3 — Conformance (ADR-010)
- **R4 (High).** Remove the publish block in `CheckRevisionBreaksAsync` (or make it a non-blocking warning); rely on the fan-out (MP-H2).
- **R5 (High).** Paginate + checkpoint the conformance fan-out; observe the `UpdateConformanceStatus` result; source `TenantId` from the message attribute (MP-H3/MP-FC2).

### 4 — Data Integrity
- **R6 (Medium).** Base summary `AssetDefinitionCount`/`RecordTypeCount` on the draft/published snapshot rather than deltas, and roll back on discard (MP-M2); map `DimensionConstraints` in both projectors (MP-M3); fix VersionDetail `DefaultAssetId.Value.ToString()` (MP-L2); remove `TenantId` from responses (MP-M5); owner-scope the list (MP-M6).

### 5 — Integration
- **R7 (High).** Carry the full `MediaProfilePublishedSnapshot` (or the fields downstream ref-models need) on the published integration event, and reconcile the three contract descriptions (MP-H6/MP-FP1).

### 6 — Atomicity / Seeding
- **R8 (High).** Adopt the ambient-transaction pattern for reservation + save; fix Deprecate/Publish ordering (MP-H5).
- **R9 (Medium).** Give the seeder deterministic per-command idempotency keys and make the sequence resumable (don't skip a name whose profile is an unpublished Draft) (MP-M7).

### 7 — API / Domain contract
- **R10 (Medium).** Emit RFC 9457 `errorCode` and map catalog-coded errors (MP-M1/MP-D2); add FastEndpoints validators (MP-M4); reconcile the `MetadataTemplateCompiled` event and `AutoSubmitOnComplete` with the spec (MP-M8/MP-M9).

### 8 — Maintainability
- **R11 (Low).** Fix write-model `IsDefault`/`SetDefaultAssetDefinition` vs code+defaults.md; reconcile the 5-vs-6 default count, `DigitalSigning`/`Signing`, deprecate 202/204, and stale projector comments; remove the unused Summary read model/projector or wire the list to it; drop the redundant aggregate `Version` field (MP-L1/L6/L7/L8).

---

### Top 5 before production
1. **MP-C1 / R1** — ownership authorization (nothing today stops a tenant user from publishing/deprecating/mutating any profile, including the shared `owner_system` platform defaults).
2. **MP-H1 / R2** — compiled-template `BareName`/`SuppressedFieldNames` lost on every event/snapshot round-trip → ADR-013 collision data corrupted.
3. **MP-H2 + MP-H3 / R4–R5** — revision-break block contradicts ADR-010 *and* the conformance fan-out is unbounded, uncheckpointed, and result-swallowing.
4. **MP-H4 / R3** — `compiledMetadataFields`/`suppressedFieldNames` never projected → GET detail contract (ADR-013 discovery) unfulfillable.
5. **MP-H5 / R8** — non-atomic name reservation; Deprecate frees the name before persisting (duplicate-name window on partial failure).
