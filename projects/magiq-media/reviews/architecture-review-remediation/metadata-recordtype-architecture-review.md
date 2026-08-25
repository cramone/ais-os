# RecordType — Module Architecture Review (Specification vs Repository)

_Context: **Metadata** · Aggregate: **RecordType** — magiq-media_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API)_
_Date: 2026-07-19_
_Scope: `src/modules/Metadata/**` (the RecordType slice — the module's only aggregate) vs `docs/spec/contexts/Metadata/**` (context-overview, business-scenarios, `aggregates/RecordType/{write-model,read-model,api,scenarios}`) + shared conventions (`api-conventions`, `error-catalog`, `security-scenarios`, `bulk-operations`, `media-types`) and `docs/adrs/**` (esp. `catalog-domain-invariants` §Metadata Collision / Aliases, `api-http-conventions`, `auth-and-security`, `persistence-and-eventing`)._

> Method: every production `.cs` file in the Metadata module was read (158 non-generated files across Domain, Contracts, WriteModel, WriteModel.Endpoints, WriteModel.Infrastructure, ReadModel, ReadModel.Endpoints, ReadModel.Infrastructure) and compared against the RecordType write-model, read-model, API and scenario specs plus the shared conventions and ADRs. Catalog (`MediaProfile`) and the `Magiq.Platform` SDK are referenced only where RecordType depends on them; findings that hinge on platform-base behaviour that could not be read directly are flagged as such. The `Z:\...\MEMORY.md` operating-memory file could not be staged from the device (network drive would not `stat`); it does not affect the architectural findings below.
>
> Filename note: the run template prescribed `catalog-{{aggregate}}-…`, which is Catalog-template residue. This review is filed as `metadata-recordtype-architecture-review.md` to match the context-based naming of the existing `assetmanagement-architecture-review.md` and the actual context under review.

---

## 1. Module Summary

Metadata is a single-aggregate bounded context. `RecordType` is a named, versioned metadata **schema** — a set of typed `FieldDefinition`s that `MediaProfile` (owned by Catalog) pins to validate `MediaItem` metadata. It follows a **Draft → Publish** model: `Create` opens the initial draft, structural mutations operate only on the draft, `Publish` snapshots the draft as the next immutable version, and `Deprecate` (advisory only) blocks new profile attachments while leaving existing pins valid. It is a configuration aggregate — no sagas, no transactional cross-aggregate work.

Structurally the module is clean and idiomatic: `EventSourced<RecordType, RecordTypeId>` with `[AggregateType("media.recordtype")]`, command-per-folder handlers returning `Result<T, DomainError>`, thin FastEndpoints, a per-module `RecordTypeDomainEventMapper` for the two published integration events, an in-process frozen `CapabilityRegistry`, four DynamoDB projectors, and four read models. The command surface is unusually rich for a config aggregate (17 write commands, 4 queries), and the aggregate's draft/publish/deprecate invariants are largely well modelled.

However, the module is **not production-ready**. The review surfaced **4 Critical** and a cluster of **High** issues concentrated — as in the AssetManagement review — in the **projection and handler-orchestration layer** around an otherwise-solid aggregate, plus one genuine aggregate-level data-loss bug. The dominant themes:

1. **The read model silently corrupts or drops state.** Discarding a draft flips a record type to *Deprecated* in the list projection; deprecating one field marks *every* field deprecated in the detail projection; `HasDraft` is never set in the summary projection; the entire **Aliases** feature is write-only and never surfaces in any read model or GET response.
2. **Authorization is absent.** No endpoint declares an owner/actor policy and no handler performs the spec-mandated `caller.owner_id == recordType.OwnerId` check. Any authenticated tenant user can mutate or read any owner's record types.
3. **One aggregate-level data-loss bug.** Removing the last field of a draft nulls the entire draft — silently discarding capabilities and, on the initial draft, bricking the aggregate permanently, defeating the very `CannotDiscardInitialDraft` guard that exists to prevent this.
4. **The error/HTTP contract is unmet.** Every domain guard collapses to generic `InvalidOperation` (422); the error catalog contains **zero** RecordType codes; `Discard` and `RemoveField` return `202` (reserved for sagas); the published deprecation event ships the wrong version number; read-model tables diverge from the single-table spec and from each other.

The aggregate itself is the strongest part of the module. Most Critical/High defects live in the projectors, handlers and integration mapper around it.

---

## 2. Aggregate Analysis

### `RecordType` (Aggregate Root) — `Metadata.Domain/Aggregates/RecordType.cs`

The sole aggregate in the context. `EventSourced<RecordType, RecordTypeId>`, `ITenantScoped`, `[AggregateType("media.recordtype")]`.

**Purpose & responsibilities:** own the definition and versioning lifecycle of a metadata schema, and all invariants governing draft mutation, publish, alias assignment and deprecation.

**Aggregate root:** `RecordType`. **Child entities:** none. **Value objects (used):** `RecordTypeId`, `RecordTypeName`, `RecordTypeAlias`, `PublisherId` (OwnerId), `FieldDefinition`, `FieldName`, `FieldType`, `FieldOrderEntry`, `RecordTypeDraft`. **Value objects (declared but unused — see §14):** `RecordTypeFieldName`, `RecordTypeStatus`, `RecordTypePublishedVersion`, `RecordTypeVersion` (VO; a same-named command result record is used).

**Key state:** `Name`, `DisplayName?`, `Description?`, `Aliases`, `OwnerId`, `Version` (0 pre-publish), `PublishedAt?`, `IsDeprecated`, `Draft?` (with `Fields`, `Capabilities`, `BasedOnVersion?`, `CreatedAt`), and private `PublishedFields` (the fork source for `CreateDraft`).

**Invariants enforced in the aggregate (correct):**
- Draft-gated mutations (`AddField`, `UpdateField`, `ReplaceField`, `RemoveField`, `ReorderFields`, `DeprecateField`, `AddCapability`, `RemoveCapability`) all require `Draft != null` and `!IsDeprecated`.
- `FieldType` immutable on `UpdateField` (`FieldTypeImmutable`); type change only via `ReplaceField` with a non-empty, ≤1000-char `MigrationNote`.
- `IsImmutable` may tighten (`false→true`) but not relax (`CannotRelaxImmutability`).
- `Publish` requires a non-empty draft; increments `Version`; clears `Draft`; pins the *current* alias set into the snapshot.
- Field/total count ≤ 100; field-name uniqueness within draft; `ReorderFields` requires the payload to be a set-exact cover of draft field names with distinct, positive orders.
- `SetAliases` rejects intra-request duplicates (`DuplicateAliasInRequest`) and no-ops on an unchanged set.

**Aggregate boundary assessment:** boundaries are appropriate. The aggregate correctly delegates name/alias cross-tenant uniqueness to the handler layer (via `INameReservationService`), capability field resolution to `ICapabilityRegistry`, and regex-complexity checks to `IFieldConstraintValidator`. `IsDeprecated` on the *reference* projection (blocking new profile attachments) correctly lives in Catalog, not here (per M-3). Size is reasonable.

**Aggregate-level defects (detailed in §12–13):**
- **RT-D1 (Critical).** `Apply(FieldRemovedFromRecordType)` nulls the whole draft when the last field is removed (`RecordType.cs:1059-1065`), silently discarding capabilities/`BasedOnVersion` and, on the initial draft, permanently bricking the aggregate.
- **RT-D2 (Medium).** `Deprecate` adds an undocumented `Draft != null → DraftInProgress` guard and returns `NothingToDeprecate` (generic 422) where the spec requires `RecordTypeNotPublished` (409).
- **RT-D3 (Medium).** Undocumented guards: `DeprecateField` blocks required fields (`CannotDeprecateRequiredField`); `ReplaceField`/`UpdateField` block already-deprecated fields (`FieldAlreadyDeprecated`). None appear in the spec's command/error tables.
- **RT-D4 (Medium).** `AddCapability` appends contributed fields without re-assigning or de-conflicting `Order`, so published snapshots can contain duplicate `Order` values (unlike `AddField`, which guards order).

---

## 3. Lifecycle Analysis

### State machine (reconstructed from `RecordType.cs` guards + `Apply` handlers)

```text
                    Create (opens initial draft)
                            │
                            ▼
                   Draft (Version = 0)  ◄────────────────┐
                   Draft != null                          │  AddField / UpdateField /
                            │                              │  ReplaceField / RemoveField* /
             ┌──────────────┼───────────────┐             │  ReorderFields / DeprecateField /
        Publish         (DiscardDraft        │  ───────────┘  AddCapability / RemoveCapability
             │           BLOCKED: v0)        │
             ▼                               │
     Published (Version = 1)                 │  *RemoveField of the LAST field →
             │                               │   Draft = null  (RT-D1: inert at v0)
   CreateRecordTypeDraft                     │
             │                               │
             ▼                               │
     Draft (Version = N, BasedOnVersion=N) ──┘
             │            │
        Publish      DiscardDraft
             │            │
             ▼            ▼
     Published(N+1)   Published(N)  ── Deprecate ──▶  Deprecated (terminal)
                                       (guard: Version>0 AND Draft==null [RT-D2])

  Root-level, NOT draft-gated (apply in Draft or Published, blocked once Deprecated):
     Rename · SetAliases · UpdateDisplayName · UpdateDescription
```

**Entry/exit conditions & events per state** are as documented in the write-model spec, with these deviations:
- **Impossible/unreachable:** `CreateDraft`'s `Version == 0 → NothingToRevise` branch is normally unreachable (an unpublished aggregate always has the initial draft open) — **except** via RT-D1, which is the only way to reach `Version == 0 && Draft == null`. So the two bugs interlock: RT-D1 produces the inert state, and every recovery command (`CreateDraft`, `Publish`, `Deprecate`, `DiscardDraft`) then fails.
- **Dead-end state:** the RT-D1 inert state (`Version 0`, `Draft null`) is a true dead end — no command can advance it.
- **Deprecate-with-open-draft:** the spec allows deprecation of a published type regardless of draft state; the code blocks it (RT-D2). This removes a legitimate transition (deprecate a published v3 while a v4 draft is in progress).
- **Recovery/compensation:** none required (config aggregate, no sagas, no timeouts) — correct.

---

## 4. Commands

17 commands, all wired in `Metadata.WriteModel.Infrastructure/ServiceCollectionExtensions.cs`. All reachable (Rename/UpdateDescription/UpdateDisplayName are dispatched by the `PATCH /record-types/{id}` endpoint; the empty `RenameRecordType` endpoint folder is residue, not a missing route).

| Command | Aggregate method | Domain event(s) | Handler-side services | Issues |
|---|---|---|---|---|
| `CreateRecordTypeCommand` | `Create` | `RecordTypeCreated` + `RecordTypeDraftCreated(null)` | `IFieldConstraintValidator`, `INameReservationService` (reserve `record-types`) | Name scope is **tenant-wide**, spec says owner-scoped (RT-Q2); no auth (RT-H1) |
| `CreateRecordTypeDraftCommand` | `CreateDraft` | `RecordTypeDraftCreated(N)` | — | `DraftAlreadyInProgress`/`NothingToRevise` are generic 422 (RT-ERR1) |
| `AddFieldToRecordTypeCommand` | `AddField` | `FieldAddedToRecordType` | `IFieldConstraintValidator` | Client may set `SourceCapability`/`IsDeprecated` (RT-VAL3) |
| `UpdateFieldInRecordTypeCommand` | `UpdateField` | `FieldDefinitionUpdated` | `IFieldConstraintValidator` | Undocumented deprecated-field block (RT-D3) |
| `ReplaceFieldInRecordTypeCommand` | `ReplaceField` | `FieldReplacedInRecordType` | `IFieldConstraintValidator` | Undocumented deprecated-field block (RT-D3) |
| `RemoveFieldFromRecordTypeCommand` | `RemoveField` | `FieldRemovedFromRecordType` | — | **RT-D1** last-field nulls draft; endpoint 202 (RT-A1) |
| `ReorderFieldsInRecordTypeCommand` | `ReorderFields` | `FieldsReorderedInRecordType` | — | OK |
| `AddCapabilityToRecordTypeCommand` | `AddCapability` | `CapabilityAddedToRecordType` | `ICapabilityRegistry` | No order de-confliction (RT-D4) |
| `RemoveCapabilityFromRecordTypeCommand` | `RemoveCapability` | `CapabilityRemovedFromRecordType` | — | OK |
| `DeprecateFieldInRecordTypeCommand` | `DeprecateField` | `FieldDeprecatedInRecordType` | — | Undocumented required-field guard (RT-D3) |
| `DiscardRecordTypeDraftCommand` | `DiscardDraft` | `RecordTypeDraftDiscarded` | — | Endpoint 202 (RT-A1); **RT-P1** projector corrupts summary |
| `PublishRecordTypeCommand` | `Publish` | `RecordTypePublished` | — (returns `RecordTypeVersion`) | OK |
| `RenameRecordTypeCommand` | `Rename` | `RecordTypeRenamed` | `INameReservationService` (Swap) | No auth; tenant-scope name (RT-Q2) |
| `SetRecordTypeAliasesCommand` | `SetAliases` | `RecordTypeAliasesUpdated` | `INameReservationService` (`record-type-aliases`) | **RT-RM1** never projected/returned; no auth |
| `UpdateRecordTypeDescriptionCommand` | `UpdateDescription` | `RecordTypeDescriptionUpdated` | — | OK |
| `UpdateRecordTypeDisplayNameCommand` | `UpdateDisplayName` | `RecordTypeDisplayNameUpdated` | — | OK |
| `DeprecateRecordTypeCommand` | `Deprecate` | `RecordTypeDeprecated` | `INameReservationService` (Release) | **RT-H3** releases name → duplicate-name risk; **RT-D2** wrong guard/error |

**Duplicate/redundant:** none. **Missing:** none material — the command set fully covers the spec's method table. **Naming:** consistent. The `PATCH` fan-out into three commands is the main structural concern (RT-H2, §12).

---

## 5. Queries

4 queries, all wired.

| Query | Reader / read model | Paging | Issues |
|---|---|---|---|
| `GetRecordTypeByIdQuery` | `IReadModelReader<RecordTypeDetailReadModel>` (table `media-record-type`) | — | Reads a **differently-named** table than the projector writes (RT-INF1); no owner/system read-scope check (RT-H1) |
| `GetRecordTypeVersionQuery` | `IReadModelReader<RecordTypeVersionDetailReadModel>` (table `media-record-types`) | — | Returns `FieldSnapshot` (correct, matches api.md); drops `Aliases` (RT-RM1) |
| `ListRecordTypesQuery` | `IReadModelReader<RecordTypeSummaryReadModel>` (table `media-record-types`, `RecordTypeByNameIndex`) | cursor | **Tenant-wide, not owner-scoped** (RT-Q1); reads corrupted summary rows (RT-P1/RT-P3) |
| `ListRecordTypeVersionsQuery` | `IReadModelReader<RecordTypeVersionSummaryReadModel>` (table `media-record-type-versions`) | cursor | Summary carries full `FieldSnapshot` (RT-RM2) |

**CQRS violations:** none in structure (handlers return DTOs, PK built by framework). **Missing query:** the spec's `ListRecordTypesByOwnerQuery` (owner + `owner_system` fallback) is effectively absent — implemented as a tenant-wide list (RT-Q1). **Reachability:** all four queries have endpoints.

---

## 6. API Endpoints

Routes match the spec's flat, `/v1/record-types` structure. `IExecutionContext` supplies `TenantId`/`Actor`. Idempotency is assumed handled by platform middleware (not visible in endpoints).

| Method / Route | Command / Query | Success | Issue |
|---|---|---|---|
| `POST /record-types` | Create | 201 `{id,name,createdAt}` | OK (body-only, no `Location` — matches ADR) |
| `POST /record-types/{id}/draft` | CreateDraft | 204 | OK |
| `POST /record-types/{id}/fields` | AddField | 204 | OK |
| `PATCH /record-types/{id}/fields/{fieldName}` | UpdateField | 204 | OK |
| `PUT /record-types/{id}/fields/{fieldName}` | ReplaceField | 204 | OK |
| `DELETE /record-types/{id}/fields/{fieldName}` | RemoveField | **202** | RT-A1 — should be 204 |
| `POST /record-types/{id}/fields/reorder` | ReorderFields | 204 | OK |
| `POST /record-types/{id}/capabilities` | AddCapability | 204 | OK |
| `DELETE /record-types/{id}/capabilities/{capabilityType}` | RemoveCapability | 204 | OK |
| `POST /record-types/{id}/draft/fields/{fieldName}/deprecate` | DeprecateField | 204 | OK |
| `DELETE /record-types/{id}/draft` | DiscardDraft | **202** | RT-A1 — should be 204 |
| `POST /record-types/{id}/publish` | Publish | 200 `{newVersion}` | OK |
| `PATCH /record-types/{id}` | Rename + UpdateDescription + UpdateDisplayName | 204 | RT-H2 — non-atomic 3-command fan-out |
| `PUT /record-types/{id}/aliases` | SetAliases | 204 | OK on write; RT-RM1 on read |
| `POST /record-types/{id}/deprecate` | Deprecate | 204 | OK (M-3 scenario's "202" is a spec error, RT-SPEC2) |
| `GET /record-types/{id}` | GetById | 200 | RT-INF1 table mismatch |
| `GET /record-types` | List | 200 | RT-Q1 not owner-scoped |
| `GET /record-types/{id}/versions` | ListVersions | 200 | RT-RM2 heavy payload |
| `GET /record-types/{id}/versions/{version}` | GetVersion | 200 | RT-RM1 alias omission |

**Auth:** every endpoint declares `ProducesProblem(403)` but **none enforces 403** — no policy, no owner check (RT-H1). **Verbs/URLs:** correct and RESTful. **Status codes:** two wrongful `202`s (RT-A1). **Versioning:** all `Version(1)` — correct.

---

## 7. Request DTO Review

- Field-create/update/replace models (`AddRecordTypeFieldModel`, `CreateRecordTypeFieldModel`, `UpdateRecordTypeFieldModel`, `ReplaceRecordTypeFieldModel`) are near-identical 20-property classes duplicated four times — acceptable but a maintenance smell; they mirror `FieldDefinition` faithfully.
- **RT-VAL3 (Medium):** these models expose **`SourceCapability`** and **`IsDeprecated`** as client-settable. A caller can post a manually-added field with `SourceCapability = "Governance"` (making it look capability-contributed, which changes what `RemoveCapability` deletes and how the field is attributed downstream) or pre-set `IsDeprecated = true`. Neither is validated or stripped server-side.
- **RT-DOC1 (Low):** `CreateRecordTypeDraftRequest` carries a stray `HasDraft { get; set; } = true` body property that the handler ignores (draft creation is parameterless). Confusing wire contract.
- `PatchRecordTypeRequest` + `PatchRecordTypeRequestConverter` correctly distinguish "field absent" from "field present and null" (tri-state) for description-clearing — good.
- No FluentValidation validators exist for any request; field-name/length constraints are therefore only whatever the (mostly unvalidated) `FieldName` VO enforces — see RT-VAL4.

---

## 8. Response DTO Review

- `CreateRecordTypeResponse` (`Id`, `Name`, `CreatedAt`) — own-id named `Id` per ADR-012 Rule 1. Good.
- `GetRecordTypeByIdResponse` — own-id `Id`, foreign `OwnerId`, includes `Capabilities`, `DraftFields`, `DraftBasedOnVersion`. **Missing `Aliases`** despite the api.md example showing them (RT-RM1). Also missing `UpdatedAt` (spec detail read model lists it; the read model has no `UpdatedAt` field either).
- `GetRecordTypeVersionResponse` — `RecordTypeId` (foreign, per ADR Rule 3), `Name`, `VersionNumber`, `FieldSnapshot`, `Capabilities`, `PublishedAt`. **Missing `Aliases`** despite api.md example (RT-RM1).
- `RecordTypeVersionSummaryModel` (list-versions item) exposes **full `FieldSnapshot`** — contradicts the spec's "lightweight, omits FieldSnapshot" (RT-RM2).
- `FieldDefinitionModel`/`FieldDefinitionDto` add `IsDeprecated`+`IsImmutable` beyond the spec's 7-field DTO — a reasonable *improvement*, but the spec's `FieldDefinitionDto` definition should be updated to match (RT-SPEC1).
- `ListRecordTypesResponse` includes `PageSize`; `ListRecordTypeVersionsResponse` **omits** it (RT-A2) — the pagination envelope is inconsistent and the versions response violates the mandated `{items, nextPageToken, pageSize}` shape.
- `DeprecateRecordTypeResponse` and `DeprecateFieldInRecordTypeResponse` are `[Obsolete]` dead code (RT-DEAD1).

---

## 9. Domain Events

17 domain events, all `IMetadataDomainEvent : IDomainEvent, ITenantScoped`, all with `TenantId` as the first field (matches the convention and the write-model footnote). `[DomainEvent(nameof(...))]` on each.

| Event | Trigger | Payload adequacy | Consumers | Issue |
|---|---|---|---|---|
| `RecordTypeCreated` | Create | OK (TenantId, Id, Name, Description?, OwnerId, OccurredAt) | Detail+Summary projectors; mapper (no) | — |
| `RecordTypeDraftCreated` | Create / CreateDraft | OK (BasedOnVersion?, InitialFields) | projectors | — |
| `FieldAddedToRecordType` | AddField | OK | Detail projector | — |
| `FieldDefinitionUpdated` | UpdateField | OK | Detail projector | — |
| `FieldReplacedInRecordType` | ReplaceField | OK (OldField, NewField, MigrationNote) | Detail projector | — |
| `FieldRemovedFromRecordType` | RemoveField | OK | Detail projector | RT-D1 apply logic |
| `FieldsReorderedInRecordType` | ReorderFields | OK (`FieldOrderEntry[]`) | Detail projector | — |
| `FieldDeprecatedInRecordType` | DeprecateField | OK (specific `FieldName`) | Detail projector | **RT-P2** projector ignores the field name |
| `CapabilityAddedToRecordType` | AddCapability | OK (ContributedFields) | Detail projector | — |
| `CapabilityRemovedFromRecordType` | RemoveCapability | OK | Detail projector | — |
| `RecordTypeDraftDiscarded` | DiscardDraft | OK | projectors | **RT-P1** summary projector corrupts state |
| `RecordTypePublished` | Publish | OK (Name, NewVersion, FieldSnapshot, Capabilities, **Aliases**) | 4 projectors; mapper | version projectors drop Aliases (RT-RM1) |
| `RecordTypeAliasesUpdated` | SetAliases | OK (Old/New aliases) | **no projector** | **RT-RM1** — unhandled |
| `RecordTypeDisplayNameUpdated` | UpdateDisplayName | OK | projectors | — |
| `RecordTypeDescriptionUpdated` | UpdateDescription | OK | projectors | — |
| `RecordTypeRenamed` | Rename | OK (OldName, NewName) | projectors | — |
| `RecordTypeDeprecated` | Deprecate | **omits published Version** | projectors; mapper | root cause of **RT-I1** |

**Timing:** all events are raised post-guard, pre-persist via `Emit` — correct. **Ownership:** all correctly owned by RecordType. **Missing payload:** `RecordTypeDeprecated` omits the published version, forcing the integration mapper to substitute the wrong value (RT-I1).

---

## 10. Integration Events

Two published, via `RecordTypeDomainEventMapper : IDomainEventMapper<RecordTypeDeprecated>, IDomainEventMapper<RecordTypePublished>` (matches ADR-005 per-module inline publisher; registered through `AddDomainEventMappers`). This context consumes none (Catalog reads `media-record-types` directly at command time).

| Integration event | Trigger | Payload | Issue |
|---|---|---|---|
| `RecordTypePublishedIntegrationEvent` (`media.recordtype.published`) | `RecordTypePublished` | TenantId, Id, Name, `RecordTypeVersion=NewVersion` ✓, Fields (`RecordTypeFieldSummaryDto[]`), Capabilities, **Aliases** ✓, PublishedAt, `EventVersion=AggregateVersion` | Correct. Note: adds richer per-field data than the context-overview's `RecordTypeFieldSummary` contract (extra Min/Max/Regex/Default fields) — spec contract should be updated. |
| `RecordTypeDeprecatedIntegrationEvent` (`media.recordtype.deprecated`) | `RecordTypeDeprecated` | TenantId, Id, Name, **`RecordTypeVersion = e.AggregateVersion`**, DeprecatedAt, `EventVersion = e.AggregateVersion` | **RT-I1 (High).** `RecordTypeVersion` is populated from the event-store aggregate version (total event count), **not** the published schema version. Also diverges from the context-overview's `RecordTypeDeprecatedMessage` contract, which has **no** version field at all. |

**Idempotency:** `EventId` is stamped deterministically by the platform from `(AggregateId, AggregateVersion, EventType)` per the persistence ADR — re-publication is safe. **Versioning:** both carry `EventVersion`. **Domain leakage:** none (published-language `media.*` DTOs). The one real defect is RT-I1.

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Discard-draft read projection | DraftDiscarded → `hasDraft=false` | Summary projector sets `IsDeprecated=true` | **Critical** | Fix `RecordTypeSummaryProjector.ApplyAsync(RecordTypeDraftDiscarded)` (RT-P1) |
| Field deprecation projection | Deprecate the named field | Detail projector marks **all** fields deprecated | **Critical** | Filter by `e.FieldName` (RT-P2) |
| Remove last field | Field removed from draft; draft persists | Whole draft nulled; aggregate can brick | **Critical** | Guard/keep empty draft (RT-D1) |
| Authorization | `caller.owner_id == recordType.OwnerId` on all writes; owner/`owner_system` on reads | No policy, no check anywhere | **Critical** | Add owner guard in handlers + endpoint policy (RT-H1) |
| Deprecated integration event version | `RecordTypeDeprecatedMessage` (no version) | `RecordTypeVersion = AggregateVersion` (wrong) | **High** | Add published version to the domain event; map it (RT-I1) |
| Read-model table | Single `media-record-types` table | 3 tables incl. `media-record-type` (singular, detail) | **High** | Consolidate/verify CDK table names (RT-INF1) |
| Aliases on reads | GET detail & version include `aliases` | No Aliases field/projector anywhere | **High** | Project & expose aliases (RT-RM1) |
| List by owner | `ListRecordTypesByOwnerQuery` + `OwnerIndex(OwnerId+Name)` | Tenant-wide list; summary has no OwnerId | **High** | Add owner scoping (RT-Q1) |
| Summary `HasDraft`/version | `HasDraft=true` on draft; version `0` pre-publish | `HasDraft` never set; `PublishedVersion=1` at create | **High** | Fix summary projector (RT-P3) |
| PATCH atomicity | Rename immediate | 3 separate load/save commands, partial-write on failure | **High** | Single command or documented ordering (RT-H2) |
| Deprecate + name reservation | not specified to release | Releases name → duplicate active name possible | **High** | Don't release, or clear/guard the name (RT-H3) |
| Deprecate guards | `Version>0` only (`RecordTypeNotPublished` 409) | also blocks open draft; `NothingToDeprecate` 422 | **Medium** | Align guard + error (RT-D2) |
| Error codes | Coded 409/422/400 per api.md + catalog | All generic `InvalidOperation` (422); no catalog entries | **Medium** | Introduce coded errors + catalog section (RT-ERR1) |
| Discard/RemoveField status | 204 (202 saga-only) | 202 with body | **Medium** | Return 204 (RT-A1) |
| Version summary payload | omits `FieldSnapshot` | includes full `FieldSnapshot` | **Medium** | Drop snapshot from summary (RT-RM2) |
| Name uniqueness scope | owner-scoped | tenant-wide (`ScopeKeys.RecordTypes`) | **Medium** | Reconcile scope (RT-Q2) |
| Field-deprecate / replace / update guards | not in spec | required-field & deprecated-field blocks | **Medium** | Add to spec or remove (RT-D3) |
| Capability field order | — | no order de-confliction | **Medium** | Re-assign orders on attach (RT-D4) |
| FieldType vocabulary | 3 contradictory sets in spec | one consistent enum | **Low** | Fix spec to match code (RT-SPEC1) |
| Deprecate status/error in scenarios | M-3 says 202 / 422 | api.md + code say 204 / 409 | **Low** | Fix spec (RT-SPEC2) |
| `RecordTypeVersionSnapshotReadModel` | named in read-model spec | code has VersionDetail + VersionSummary | **Low** | Reconcile naming (RT-SPEC3) |
| `IMetadataValidator` | listed as a Metadata responsibility | not implemented in this module | **Low** | Clarify ownership (likely Catalog) (RT-GAP1) |

---

## 12. Bugs

### Critical

**RT-P1 — Discarding a draft marks the record type as Deprecated in the list read model.**
`Metadata.ReadModel/Projectors/RecordTypeSummaryProjector.cs:399-402` — `ApplyAsync(RecordTypeDraftDiscarded)` does `current with { IsDeprecated = true, ... }`. This is a copy of the `RecordTypeDeprecated` handler. Because `ListRecordTypesHandler` reads `RecordTypeSummaryReadModel` (`ListRecordTypesHandler.cs:822`), any `DELETE /record-types/{id}/draft` permanently flips the type to *deprecated* in every `GET /record-types` result — and it never recovers (no event resets it). *Why it's a problem:* a routine, reversible editing action (abandon a revision draft) silently makes a live schema look retired to every consumer browsing the list, on a compliance-grade platform. *Impact:* data-integrity corruption of the primary discovery surface. *Recommendation:* set `HasDraft=false` (and clear nothing else) exactly as the detail projector does.

**RT-P2 — Deprecating one field marks every field deprecated in the detail read model.**
`Metadata.ReadModel/Projectors/RecordTypeDetailProjector.cs:161-168` — `ApplyAsync(FieldDeprecatedInRecordType)` maps `current.DraftFields?.Select(f => f with { IsDeprecated = true })` over **all** fields, ignoring `e.FieldName`. The event carries the specific field name; the projector discards it (the stale comment on `:163-164` even claims the DTO has no `IsDeprecated` field, which is false — `FieldDefinitionDto` has one and it is populated). *Impact:* after a single `POST .../fields/{name}/deprecate`, `GET /record-types/{id}` reports the entire draft schema as deprecated. *Recommendation:* `f.FieldName == e.FieldName ? f with { IsDeprecated = true } : f`.

**RT-D1 — Removing the last field nulls the draft and can permanently brick the aggregate.**
`Metadata.Domain/Aggregates/RecordType.cs:1059-1065` — `Apply(FieldRemovedFromRecordType)` does `Draft = fields.Count == 0 ? null : Draft with { Fields = fields }`. Removing the last field of a draft therefore destroys the draft object (losing `Capabilities`, `BasedOnVersion`, `CreatedAt`) with **no `RecordTypeDraftDiscarded` event**. Two failure modes: (a) on the **initial** draft (`Version == 0`), the aggregate becomes inert — `CreateDraft`, `Publish`, `Deprecate` and `DiscardDraft` all require `Version > 0` or a non-null draft, so nothing can advance it; this bypasses the explicit `CannotDiscardInitialDraft` guard whose entire purpose is to prevent exactly this. (b) on a **revision** draft, the write side thinks the draft is gone while the projectors (which only saw `FieldRemovedFromRecordType`) still show `HasDraft=true` with an empty field list — a write/read divergence. *Recommendation:* keep the (empty) draft on the last removal — let `Publish` reject the empty draft (`CannotPublishEmptyRecordType`) and `DiscardDraft` handle teardown — or reject removing the last field with a dedicated error. Do **not** null the draft as a side effect of `RemoveField`.

**RT-H1 — No authorization: any tenant user can read or mutate any owner's record type.**
No FastEndpoints endpoint declares an actor/owner policy, and no handler compares `context.Actor.Id` to `recordType.OwnerId`. The spec (`recordtype.api.md` §Authorization) requires `caller.owner_id == recordType.OwnerId` on all writes and owner-or-`owner_system` on reads; `security-scenarios.md` PERM-1 makes the owner check a platform invariant. `CreateRecordType`/`Rename`/`SetAliases` capture `Actor.Id` but only to stamp `OwnerId`/`RequestingUser` — it is never enforced on existing aggregates. *Impact:* cross-owner tamper and disclosure within a tenant on regulated metadata schemas. *Recommendation:* resolve `OwnerId` from aggregate state and return `DomainError.Forbidden` (403) when it differs from the actor for owner-scoped commands; gate reads to owner/`owner_system`.

### High

**RT-I1 — Deprecated integration event ships the event-store version, not the schema version.**
`Metadata.WriteModel/IntegrationEvents/Publishing/Mappers/RecordTypeDomainEventMapper.cs:971-974` passes `e.AggregateVersion` into the `RecordTypeVersion` slot of `RecordTypeDeprecatedIntegrationEvent`. `AggregateVersion` is the append-only event count (e.g. 20+ after a busy edit history), not the published schema version (e.g. 3). Downstream consumers (Notifications/Catalog reference projectors) that key off `RecordTypeVersion` receive a meaningless number. Root cause: the `RecordTypeDeprecated` **domain** event omits the published `Version`, so the mapper has no correct value to forward. *Recommendation:* add `int Version` to `RecordTypeDeprecated` (populated from `Version` in `Deprecate`) and map it; and reconcile with the context-overview contract, which currently declares no version field at all.

**RT-INF1 — Read-model tables are inconsistent and diverge from the single-table spec.**
`Metadata.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:1785-1788` registers: `RecordTypeDetailReadModel` → **`media-record-type`** (singular); `RecordTypeSummaryReadModel` → `media-record-types`; `RecordTypeVersionDetailReadModel` → `media-record-types`; `RecordTypeVersionSummaryReadModel` → **`media-record-type-versions`**. The spec mandates one physical `media-record-types` table for all row types. Beyond the spec divergence, `GetRecordTypeById` reads the detail model from the **singular** `media-record-type` table — if CDK does not provision that exact name (the context-overview only names `media-record-types`), the query fails at runtime with a missing-table error. *Recommendation:* consolidate onto `media-record-types` (or explicitly justify the split) and verify every table name against `cdk-magiq-media`.

**RT-RM1 — Aliases are write-only: never projected, never returned.**
`SetRecordTypeAliases` emits `RecordTypeAliasesUpdated` and reserves names, but: (a) neither `RecordTypeDetailProjector` nor `RecordTypeSummaryProjector` implements `IProjectionHandler<RecordTypeAliasesUpdated>` — the event is dropped; (b) `RecordTypeDetailReadModel` has no `Aliases` field; (c) the version projectors ignore the `Aliases` carried on `RecordTypePublished`. Yet `recordtype.api.md` shows `aliases` in both `GET /record-types/{id}` and `GET .../versions/{version}`. *Impact:* clients can set aliases but can never read them back; the api.md contract is unmet. (Cross-context compilation still works because the *integration* event carries aliases — but the query API is blind to them.) *Recommendation:* add `Aliases` to the detail read model + a projector handler for `RecordTypeAliasesUpdated`, and persist `Aliases` into the version read models from the publish snapshot.

**RT-Q1 — `ListRecordTypes` is tenant-wide, not owner-scoped.**
`ListRecordTypesQuery(TenantId, PagerParameters)` with `Matches(rm) => rm.TenantId == TenantId` (`ListRecordTypesQuery.cs:852`), backed by `RecordTypeByNameIndex` (PK `TENANT#{tid}#RECORD_TYPES`, SK `{name}#{id}` — no owner). `RecordTypeSummaryReadModel` has no `OwnerId` field, so the spec's `OwnerIndex(OwnerId+Name)` and the `OwnerId IN [ownerId, "owner_system"]` access pattern are unimplementable as written. *Impact:* every tenant user lists every owner's record types (a mild disclosure and a functional mismatch with the spec's owner-scoped list). *Recommendation:* add `OwnerId` to the summary model, project it, and scope the query/GSI by owner with the `owner_system` fallback.

**RT-P3 — Summary projection never sets `HasDraft` and reports version 1 for never-published types.**
`RecordTypeSummaryProjector.cs`: `ApplyAsync(RecordTypeCreated)` constructs the row with `PublishedVersion = 1` (`:365`) though the detail projector uses `0` and the spec says `0` pre-publish; `ApplyAsync(RecordTypeDraftCreated)` only bumps `ProjectedVersion` (never `HasDraft=true`, `:393-396`); `Publish` never clears it. *Impact:* `GET /record-types` always reports `HasDraft=false` and an off-by-one `publishedVersion` for unpublished types. *Recommendation:* set `HasDraft` on DraftCreated/DraftDiscarded/Publish and initialise `PublishedVersion=0`.

**RT-H2 — `PATCH /record-types/{id}` is non-atomic across up to three commands.**
`PatchRecordTypeEndpoint.cs:1952-1981` dispatches `RenameRecordTypeCommand`, then `UpdateRecordTypeDescriptionCommand`, then `UpdateRecordTypeDisplayNameCommand` as three independent load/guard/save cycles. If the second or third fails (e.g. a name reservation race, or a concurrency retry exhaustion), the earlier command has already persisted and published its event, but the client receives an error — a partial update with a failure response. It also performs three event-store round-trips for one request. *Recommendation:* either compose a single `UpdateRecordTypeCommand` that applies all three mutations to one loaded aggregate in one save, or document the endpoint as explicitly non-atomic and order the mutations so the most-likely-to-fail (rename/uniqueness) runs first (it already does), returning a partial-success indication.

**RT-H3 — Deprecation releases the name reservation, enabling a duplicate active name.**
`DeprecateRecordTypeHandler.cs:319-331` calls `nameReservationService.ReleaseAsync(..., ScopeKeys.RecordTypes, deprecatedName)`. The deprecated aggregate keeps its `Name` (nothing clears it) and cannot be renamed away (`Rename` returns `RecordTypeDeprecated`). Releasing the reservation lets a subsequent `CreateRecordType` claim the same name, yielding two record types with an identical `Name` in the tenant. *Impact:* breaks the name-uniqueness invariant the reservation exists to protect; `GET /record-types` can then show two same-named entries. *Recommendation:* do not release on deprecate (deprecation is advisory, the schema still exists), or if reuse is intended, clear the aggregate's `Name` and document the semantics.

### Medium

**RT-D2 — Deprecate guard/error diverge from spec.** `RecordType.Deprecate` (`:604-618`) returns `DraftInProgress` when a draft is open (not a spec guard) and `NothingToDeprecate` (generic `InvalidOperation` → 422) when `Version==0`, where api.md requires `RecordTypeNotPublished` (409). *Recommendation:* drop the draft guard (or spec it) and emit a coded `RecordTypeNotPublished` (409).

**RT-D3 — Undocumented aggregate guards.** `DeprecateField` blocks required fields (`CannotDeprecateRequiredField`, `:646-649`); `ReplaceField`/`UpdateField` block already-deprecated fields (`FieldAlreadyDeprecated`, `:840-843`, `:952-955`). None are in the spec's method/error tables or the api.md error lists. *Recommendation:* add to the spec (they are reasonable) or remove.

**RT-ERR1 — Generic errors; empty error catalog.** `DomainErrors.cs` funnels almost everything through `DomainError.InvalidOperation` (422) — including name conflicts and no-draft/never-published cases that api.md documents as 409, and alias-format as 400. `error-catalog.md` contains **no** RecordType/Metadata codes at all (`RecordTypeNameConflict`, `NoActiveDraft`, `FieldNameConflict`, `MigrationNoteRequired`, `RecordTypeNotPublished`, `InvalidRecordTypeAlias`, `FieldAlreadyDeprecated`, …). *Impact:* clients cannot machine-discriminate failures, and true conflicts (409) surface as 422, breaking the documented retry semantics. *Recommendation:* introduce coded `DomainError`s with correct HTTP mappings and add a Metadata section to the error catalog. (Name-conflict does return the platform `EntityAlreadyExists`, which likely maps to 409 — verify.)

**RT-A1 — Wrong `202` on Discard and RemoveField.** `DiscardRecordTypeDraftEndpoint.cs:1864` and `RemoveFieldFromRecordTypeEndpoint.cs:2297` return `202 Accepted` with a body. `api-conventions.md` reserves `202` exclusively for the two saga endpoints; synchronous mutations must use `204`. *Recommendation:* return `204 No Content`; delete the response DTOs.

**RT-RM2 — Version-summary carries full `FieldSnapshot`.** `RecordTypeVersionSummaryReadModel.cs:986` and `RecordTypeVersionSummaryModel` include `FieldSnapshot`; the projector writes it (`RecordTypeVersionSummaryProjector.cs:645`). The spec says the summary omits it "to keep list reads cheap." *Impact:* `GET .../versions` returns the entire schema for every version. *Recommendation:* drop `FieldSnapshot` from the version-summary read model and list response.

**RT-Q2 — Name uniqueness scope.** Handlers reserve/check under `ScopeKeys.RecordTypes` (`"record-types"`, tenant-wide) with no owner component, while api.md 409 text and the write-model Purpose say "within owner scope." *Recommendation:* pick one and reconcile spec + code (owner-scoped requires an owner-qualified scope key).

**RT-D4 — Capability field order not de-conflicted.** `AddCapability`/`Apply(CapabilityAddedToRecordType)` append contributed fields with their capability-local `Order` (1,2,…) without re-assignment or conflict checks, unlike `AddField`. Published `FieldSnapshot` can then contain duplicate `Order` values. *Recommendation:* re-base contributed-field orders to `max(existing)+1…` on attach.

**RT-VAL3 — Client-supplied `SourceCapability`/`IsDeprecated` on field create/update.** The field request models let a caller set `SourceCapability` and `IsDeprecated` directly (§7). A manual field can be mislabelled as capability-contributed (changing `RemoveCapability` deletion behaviour) or pre-deprecated. *Recommendation:* force `SourceCapability=null` and `IsDeprecated=false` for client-authored fields; only the registry sets `SourceCapability`.

### Low

**RT-VAL1 — SetAliases no-op is order-sensitive.** `RecordType.SetAliases` (`:880`) uses `SequenceEqual`, but the spec says no-op on a **set-equal** list. Reordering `["inv","invoice"] → ["invoice","inv"]` emits a spurious `RecordTypeAliasesUpdated`. *Recommendation:* compare as sets.

**RT-VAL2 — Regex validator scope/strength.** `FieldConstraintValidator` runs on any field carrying a `RegexPattern` (spec restricts `RegexPattern` to Text) and probes complexity with a single fixed string (`"a"*50 + "!"`), which a targeted ReDoS pattern can pass. *Recommendation:* gate on `FieldType == Text`; consider a stricter complexity heuristic.

**RT-VAL4 — Field names are unvalidated.** `FieldDefinition` uses the plain `FieldName` VO, which has **no** `Validate` override — any string is accepted (length/charset unchecked). The elaborate `RecordTypeFieldName` VO (regex, 64-char cap) is never referenced. `FieldName` equality is `Ordinal`, so `"Title"` and `"title"` are distinct fields. *Recommendation:* either use `RecordTypeFieldName` in `FieldDefinition` or add validation to `FieldName`; decide case sensitivity deliberately.

**RT-A2 — Pagination envelope inconsistency.** `ListRecordTypeVersionsResponse` omits `pageSize`; `ListRecordTypesResponse` includes it. The mandated envelope is `{items, nextPageToken, pageSize}`. *Recommendation:* add `pageSize` to the versions response.

**RT-DOC1 — Stray `HasDraft` in `CreateRecordTypeDraftRequest`.** Ignored body property; remove from the wire contract.

---

## 13. Design Flaws

- **Projector duplication without a shared base.** `RecordTypeDetailProjector` and `RecordTypeSummaryProjector` each hand-implement 16 `ApplyAsync` + 16 `ResolveKey` methods; the summary one bumps `ProjectedVersion` on every field event despite carrying no field data (needless writes) and is where RT-P1/RT-P3 crept in. The near-total duplication makes divergence bugs likely. *Consider* a shared projection base or deriving the summary from the detail model.
- **Read/write field-DTO sprawl.** Four almost-identical field request models plus `FieldDefinition`, `FieldDefinitionDto`, `FieldDefinitionModel`, `RecordTypeFieldSummaryDto` — five representations of one concept, mapped by hand in six places. High drift risk (RT-VAL3, RT-SPEC1 are symptoms).
- **Non-atomic PATCH orchestration (RT-H2)** treats three domain concepts (name, description, display name) as one HTTP resource but three transactions — an HTTP-layer convenience that leaks partial-failure semantics to clients.
- **Handler-owned name/alias reservation is a documented dual-write** (per ADR-006/catalog-domain-invariants). Acceptable per the accepted trade-off, but RT-H3 shows the release path was added without considering the still-live aggregate's name.
- **Table-name/model fan-out (RT-INF1)** couples four read models to three physical tables with no single source of truth for table names.

---

## 14. Design Gaps

- **Aliases have no read path (RT-RM1)** — the single largest capability gap: an entire write feature invisible to every query.
- **Owner-scoped listing (RT-Q1)** and **owner authorization (RT-H1)** — the owner dimension is essentially absent from the read + auth surface.
- **`IMetadataValidator` is unimplemented in this module (RT-GAP1).** The context-overview lists "Provide schema validation service (`IMetadataValidator`)" as a Metadata responsibility and the read-model spec calls the version snapshot rows its authoritative source, but no such service exists in `src/modules/Metadata`. Either it lives in Catalog (then the spec should say so) or it is missing.
- **No request validators** (FluentValidation) anywhere in the module — malformed field payloads rely on model binding + VO constructors; invalid enum/`Order` values are not surfaced as coded 400/422.
- **No observability specifics** — handlers use the platform `CommandHandler` base; no module-level structured logging of `TenantId`/`CorrelationId` is visible (assumed provided by the base; verify).
- **No idempotency evidence at the endpoint layer** — assumed handled by `Magiq.AspNetCore.Idempotency` middleware; not asserted here.

---

## 15. Missing Features

- **Read projection + response for `Aliases`** (detail and version) — RT-RM1.
- **Owner-scoped list query + `OwnerId` on the summary read model + `OwnerIndex`** — RT-Q1.
- **Owner authorization guard** on all write commands and owner/`owner_system` scoping on reads — RT-H1.
- **Coded domain errors + a Metadata section in `error-catalog.md`** — RT-ERR1.
- **Published version on `RecordTypeDeprecated`** (and corrected integration mapping) — RT-I1.
- **A guard/behaviour for removing the last draft field** that does not null the draft — RT-D1.
- **`IMetadataValidator`** (or an explicit spec statement that it is Catalog-owned) — RT-GAP1.
- **Correct `HasDraft`/`PublishedVersion` in the summary projection** — RT-P3.

---

## 16. Recommendations

Prioritised per the review rubric (Correctness → Data Integrity → Security → Domain → Lifecycle → API → Events → Maintainability → Performance → Scalability).

1. **[Correctness] Fix the three projection/aggregate data bugs (RT-P1, RT-P2, RT-D1).**
   *Justification:* each silently corrupts or destroys schema state a compliance platform must keep exact. *Approach:* RT-P1 → summary `DraftDiscarded` sets `HasDraft=false` only; RT-P2 → filter `FieldDeprecated` by `e.FieldName`; RT-D1 → keep the empty draft on last-field removal (let Publish/Discard handle it) and add a WriteModel unit test that removes all fields then publishes/discards. Add projector unit tests replaying each event against a seeded row.

2. **[Data Integrity] Correct the deprecated-event version and the name-reservation release (RT-I1, RT-H3).**
   *Justification:* a wrong published version and a silently-reusable name both corrupt cross-context and in-tenant invariants. *Approach:* add `int Version` to `RecordTypeDeprecated`; map it; stop releasing the name on deprecate (or clear `Name`). Update the context-overview `RecordTypeDeprecatedMessage` contract to include the version.

3. **[Security] Enforce owner authorization (RT-H1).**
   *Justification:* PERM-1 is a platform invariant; regulated metadata must not be cross-owner writable/readable. *Approach:* in each owner-scoped handler, after loading the aggregate, return `DomainError.Forbidden` when `context.Actor.Id != recordType.OwnerId`; scope reads to owner/`owner_system`. Add PERM-1-style negative tests.

4. **[Data Integrity/Read] Reconcile read-model tables and surface Aliases (RT-INF1, RT-RM1).**
   *Justification:* a mis-named table can 500 `GetRecordTypeById`; aliases are contractually required on reads. *Approach:* consolidate to `media-record-types` (verify against `cdk-magiq-media`); add `Aliases` to the detail read model + a `RecordTypeAliasesUpdated` projector handler; persist aliases into version read models from the publish snapshot.

5. **[Domain/Read] Owner-scope the list surface and fix summary flags (RT-Q1, RT-P3, RT-Q2).**
   *Justification:* aligns the list/GSI/uniqueness with the spec's owner model. *Approach:* add `OwnerId` to `RecordTypeSummaryReadModel`, project it, replace `RecordTypeByNameIndex` with an owner+name index, add the `owner_system` fallback; initialise `PublishedVersion=0` and maintain `HasDraft`; pick and enforce one name-uniqueness scope.

6. **[Lifecycle] Align deprecate and field guards with the spec (RT-D2, RT-D3).**
   *Justification:* restores the "deprecate a published type with an open draft" transition and documents added rules. *Approach:* remove the `DraftInProgress` deprecate guard (or spec it); either spec or drop the required-field / deprecated-field blocks.

7. **[API] Fix status codes, PATCH atomicity, and pagination envelope (RT-A1, RT-H2, RT-A2).**
   *Approach:* `204` for Discard/RemoveField; a single `UpdateRecordType` command (or an explicit partial-success contract) for PATCH; add `pageSize` to the versions response.

8. **[Events/Contracts] Coded errors + catalog + slim version summary (RT-ERR1, RT-RM2).**
   *Approach:* introduce coded `DomainError`s with correct HTTP mappings; add a Metadata section to `error-catalog.md`; drop `FieldSnapshot` from the version-summary read model.

9. **[Maintainability] Validate field DTOs and remove dead code (RT-VAL3, RT-VAL4, RT-DEAD1, RT-DOC1).**
   *Approach:* strip client-set `SourceCapability`/`IsDeprecated`; validate field names (adopt `RecordTypeFieldName` or add rules to `FieldName`); delete the `[Obsolete]` response DTOs, unused VOs (`RecordTypeStatus`, `RecordTypePublishedVersion`, `RecordTypeFieldName` if not adopted), the stray `HasDraft` request field, and the empty `RenameRecordType` endpoint folder; add FluentValidation validators.

10. **[Performance/Scalability] Reduce projector write amplification and field-DTO sprawl (RT design flaws).**
    *Approach:* share a projection base or derive summary from detail; collapse the four field request models behind one shared model; consider `de-`duplicating the summary projector's no-op field-event writes.

11. **[Spec hygiene] Reconcile the specification's internal contradictions (RT-SPEC1, RT-SPEC2, RT-SPEC3, RT-GAP1).**
    *Approach:* settle on the code's `FieldType` enum (delete the stray `MetadataFieldType`); fix M-3's `202`/`422`; rename `RecordTypeVersionSnapshotReadModel` references to the actual `VersionDetail`/`VersionSummary` models; state where `IMetadataValidator` lives.

---

## Top 5 Before Production

1. **RT-P1 / RT-P2 / RT-D1 — the data-corruption trio.** Discarding a draft de-lists a schema as *deprecated*; deprecating one field deprecates all; removing the last field can permanently brick the aggregate. Fix all three with replay/unit tests.
2. **RT-H1 — owner authorization is entirely absent.** Any tenant user can read/mutate any owner's schemas. Add the `caller.owner_id == OwnerId` guard and read scoping.
3. **RT-I1 + RT-H3 — deprecation corrupts two invariants.** The published event carries the wrong (event-count) version, and deprecation frees the name for a duplicate active schema.
4. **RT-INF1 + RT-RM1 — the read model is mis-wired and alias-blind.** `GetRecordTypeById` reads a differently-named table than the projector writes (potential runtime 500), and the entire Aliases feature never reaches any GET response.
5. **RT-Q1 + RT-ERR1 — owner-scoping and the error contract are unmet.** List is tenant-wide with no `OwnerId`, and every failure is a generic 422 with no catalogued `errorCode`, so true conflicts (409) are indistinguishable and un-retryable per the documented semantics.
