---
id: MM-038
type: review
project: magiq-media
workstream: document-signing
raised-by: [MM-022]
status: parked
outcome: pending
todo-id: -
created: 2026-09-01
---

> **Split out of `plans/spec-drift-review/spec-repo-drift-review.md` § H on 2026-09-01**, carrying
> **DS-1 … DS-12** plus the two DocumentSigning rows that had drifted into § I.4 Tables & infra
> (**X-11.12**, **X-11.13**). They are removed there, not duplicated — this file is their only home.
>
> **Status is `parked` on arrival, and that is deliberate.** The drift review recorded DocumentSigning as
> *"parked by your decision, not by oversight."* Splitting it out does not restart it; it gives the parked
> work a place to sit where it stops being counted as unfinished business in a review whose spec work is
> otherwise complete.

# DocumentSigning — a specced bounded context that is a skeleton

_Scope: the whole `DocumentSigning` module — 7 spec files, **1,537 lines**, describing 12 routes, 9
commands, an aggregate, a saga and a timeout scanner. **None of it is implemented.**_

_**Eleven findings, numbered DS-1 … DS-12** — the sequence skips **DS-4** (constructor argument order),
which was verified by direct inspection, closed, and archived on the drift review's side. Written
2026-08-21, and they have had **no remediation pass**._

_**X-11.12 and X-11.13** were opened 2026-08-25 by W21 of the DDD coverage plan and came across with them.
The file inventory below was re-counted against the repo on 2026-09-01 and **corrects the count the drift
review carried.**_

---

## The verdict, up front

**The documentation problem here is sharper than the code gap**, and that framing is the drift review's,
kept because it is right.

`write-model.md` and `read-model.md` both self-flag that the aggregate does not exist. **`api.md` and
`context-overview.md` carry no such caveat and read as shipped contract** — 12 routes, request and
response bodies, error codes, a traceability table. A consumer team reading `docs/spec/` at HEAD would
have no way to know that **not one of those routes is served**.

The code gap itself is unambiguous and stable: this module is the events-and-value-objects skeleton and
nothing else.

### What exists, re-counted 2026-09-01

**31 non-generated `.cs` files across 5 projects** — the drift review said 27, counted before W21's pass
and never updated. Corrected here:

| Present | Count |
|---|---|
| Domain event records | 9 (+ `ISigningDomainEvent`, + `SignerInfo` payload record) |
| Value objects | 7 |
| Read models | 2 (+ `SignerDto`) |
| Projectors | 1 |
| DI registration extensions | 2 |
| WriteModel service types | 4 — **2 interfaces and 2 records**, not "4 service interfaces" |

**Absent: the aggregate, all 9 commands, all 9 handlers, the repository, all 12 endpoints, 2 of 3
projectors, all 3 query handlers, the saga, the timeout scanner, and the webhook implementation.**

> **The nine domain events are orphaned.** Nothing raises them, and
> `DomainEventPublishingMiddleware` explicitly excludes `ISigningDomainEvent` from publishing. That
> exclusion is what makes X-11.12 harmless today — and what will make it easy to miss when the module is
> picked up.

---

## Findings — carried over intact

_Row bodies are unchanged from the drift review; only their home has moved._

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☐ | DS-1 | High | 12 routes | **Zero endpoints.** No `DocumentSigning.*.Endpoints` project; neither `Api` nor `QueryApi` references the module at all | `documentsigningsession.api.md § Route Structure` / `Api.csproj`, `QueryApi.csproj` |
| ☐ | DS-2 | High | Webhook with HMAC-SHA256 over raw body, `X-SecuredSigning-Signature`, SSM secret, envelope→tenant lookup | Handler logs and returns **501 "not yet implemented"**. No HMAC, no header read, no SSM, no lookup. Also not routed | `api-conventions.md:426-437` / `SecuredSigningWebhookHandler.cs:29-41` |
| ☐ | DS-3 | High | `POST /v1/items/{id}/signing-sessions` is one of only two endpoints allowed to return 202 | Endpoint does not exist — the reserved-202 contract is unimplementable | `api-conventions.md:365` |
| ☐ | DS-5 | High | `ProjectedVersion` dedup guard on all writes | Set only on the initial insert. All 8 update paths use `current with { … }` and never touch it — pinned at v1, so duplicate delivery is unguarded | `read-model.md`; `CLAUDE.md § Key conventions` / `SigningSessionDetailProjector.cs:53-114` |
| ☐ | DS-6 | High | Three projectors incl. `SigningEnvelopeLookupProjector` (the webhook's tenant-resolution path) | Only the detail projector exists. The other two are an inline `// todo`. `media-signing-sessions` has a schema nothing writes; `media-signing-envelope-lookup` has neither | `read-model.md § Projection Handlers` / `ServiceCollectionExtensions.cs:78-82` |
| ☐ | DS-7 | High | 9 methods, 9 commands, 9 events on the aggregate | **Aggregate class does not exist.** `WriteModel` holds 4 files, all interfaces/DTOs. The events exist but nothing raises them | `write-model.md § Methods` / `DocumentSigning.WriteModel/Services/` |
| ☐ | DS-8 | High | `DocumentSigningSaga` coordinates the checkout lock and compensates via `ForceReleaseCheckout` | **The class does not exist anywhere in `src/` or `tests/`.** `SagaOrchestrator.DocumentSigning` registers one handler whose body is a TODO block | `write-model.md § Purpose` / `SecuredSigningRegistrations.cs:62-65` |
| ☐ | DS-9 | High | `SagaTimeoutScanner` scans `AwaitingSigners` for expiry | Not implemented. `TimeoutScanner` registers only the asset-ingestion and lease-expiry scanners; the DocumentSigning row survives as an XML `<description>` self-annotated "(not yet implemented)" | `read-model.md § Status Lifecycle` / `TimeoutScanner/ServiceCollectionExtensions.cs:34-35` |
| ☐ | DS-10 | Med | Summary and detail both carry `OwnerId` | Detail has **no `OwnerId`** — the field every "caller is session owner" check depends on. Summary has it but is never written | `read-model.md` / `SigningSessionDetailReadModel.cs:8-27` |
| ☐ | DS-11 | Med | Seven named error codes | `error-catalog.md` has **no DocumentSigning section**; six of seven are undefined and unimplemented | `write-model.md § Invariants` vs `error-catalog.md` |
| ☐ | DS-12 | Low | `api.md` route structure is post-migration flat | `scenarios.md:76,79` and `context-overview.md` still name the pre-migration surface (`POST /media-items/{id}/media-signing-sessions` → **201**, `/webhooks/secured-signing`). Code implements none, so no `/signing/` prefix survives | `documentsigningsession.scenarios.md:76,79` |

### The two rows that had drifted into § I.4

Both are DocumentSigning-only and were tracked under Tables & infra, where they would have been the last
DS findings left in the drift review once § H moved. Brought here.

| ✓ | # | Sev | Claim | Reality | Ref |
|---|---|---|---|---|---|
| ☐ | **X-11.12** | Low | `SigningSessionDetailProjector` is complete and never registered | *Opened 2026-08-25 by W21.* The projector handles all nine signing events and keys every one correctly, but `AddDocumentSigningReadModelProjectors()` is **called by no host** — grep returns only the definition. Dead alongside `AddDocumentSigningReadModelQueries()`. Harmless while nothing emits signing events, but **it is finished work that will be forgotten when the module is picked up** | `DocumentSigning.ReadModel.Infrastructure/ServiceCollectionExtensions.cs` |
| ☐ | **X-11.13** | Low | Webhook tenant-lookup table named two different ways | *Opened 2026-08-25 by W21.* `SagaOrchestrator.DocumentSigning.csproj`'s comment says webhook `TenantId` resolution uses `media-signing-sessions`; the code comments beside it say `media-signing-envelope-lookup`, keyed by `EnvelopeId`, written by `SigningEnvelopeLookupProjector`. **Neither the table nor the projector exists**, so nothing arbitrates. The code comment is the coherent one — SecuredSigning webhooks carry no `TenantId`, so the lookup must be `EnvelopeId → TenantId`, which `media-signing-sessions` (keyed by `SigningSessionId`) cannot answer | `SagaOrchestrator.DocumentSigning.csproj` · `SecuredSigningWebhookHandler.cs` |

> **X-11.13 is DS-2 and DS-6 seen from the code side.** All three are the same missing piece: the webhook
> cannot resolve a tenant, because the lookup table, its projector and the handler body are all absent.
> Whoever picks this up should treat them as one item, not three.

---

## What W21 established, and why it changes the shape of this

W21 of the DDD coverage plan specified `documentsigningsaga.md` as **design only** and killed three spec
claims in the process. They are recorded here because they are the difference between *"deferred"* and
*"further from done than the word deferred suggests."*

1. **There is no `DocumentSigningSession` aggregate either.** `DocumentSigning.Domain/Aggregates/` holds
   an `Events/` folder and nothing else. The docs project's `CLAUDE.md` was right and the repo's was
   wrong — raised as **X-11.11** and fixed, and the repo `CLAUDE.md` now reads *"⚠️ none — no aggregate
   class exists."*
2. **The host is misnamed.** Nothing in `SagaOrchestrator.DocumentSigning` is a saga — it is an
   anti-corruption adapter, and both its handlers are `NotImplementedException` / HTTP 501.
3. **Three spec claims have no source in code.** The **72-hour timeout** has none — no scanner, no
   options class, no config section, no `72` anywhere. `TimeoutScanner` hard-codes
   `SagaType = "ASSET_INGESTION"`, so a signing scanner is **new code, not configuration** (this is
   DS-9's real cost). And **the checkout story was backwards**: `ActiveSigningSessionId` is a
   mutual-exclusion flag that *blocks* checkout, not a lock signing acquires — so compensation is
   `UnlinkSigningSession`, and **`ForceReleaseCheckout` has no connection to signing at all**, which
   contradicts DS-8's spec side.
4. **Correlation key settled as `SigningSessionId`** on evidence: it is the only id on all nine events,
   the projector keys on it, and `EnvelopeId` does not exist at saga creation and is a *tenant-resolution*
   lookup rather than a correlation key.

> **DS-8's row still states the spec's claim, not the corrected one.** That is intentional — the row
> records the drift, and W21's finding is the resolution. Anyone planning this work should take the saga
> design from `documentsigningsaga.md`, which is current, not from DS-8's "spec says" column.

---

## The decision this review is parked on

**It is not "fix these twelve findings."** Eleven of the twelve resolve the moment the module is either
built or withdrawn, and none of them can be closed independently while the module is a skeleton.

The real fork:

| | Build the module | Withdraw the published contract |
|---|---|---|
| **What happens to the 7 spec files** | They become the implementation target; DS-12's route drift and DS-11's error codes get fixed as part of the build | `api.md` and `context-overview.md` gain the unbuilt banner that `write-model.md` and `read-model.md` already carry, or the tree moves under a `design/` marker |
| **Cost** | A bounded context: aggregate, 9 commands and handlers, 12 endpoints, 2 projectors, 3 query handlers, the saga, a new timeout scanner, the webhook with HMAC and the envelope lookup table | Hours |
| **What it stops** | — | A consumer team building against 12 routes that return nothing |

**The cheap half is worth doing either way, and it is the one thing here that should not wait for the
decision:** DS-1 and DS-12 are publish-honesty, and the fix is two banners. The drift review classified
them under *"caveat or relocate the spec files that describe absent code, so published contracts stop
reading as shipped."* That is still the right call, and it does not pre-empt anything.

---

## Related

- `plans/spec-drift-review/spec-repo-drift-review.md` — where DS-1…DS-12, X-11.12 and X-11.13 lived until
  2026-09-01. **X-1.2 and X-1.7** (closed) are the DocumentSigning doc claims already corrected there
- `docs/spec/contexts/DocumentSigning/sagas/documentsigningsaga.md` — W21's design-only spec; **current,
  and the authority where it and DS-8 differ**
- `plans/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md` § 8, W21 — the session that established
  items 1–4 above
- `docs/spec/shared/error-catalog.md` — has no DocumentSigning section (DS-11)
- `src/hosts/SagaOrchestrator.DocumentSigning` — built and pushed every commit; **nothing deploys it**
