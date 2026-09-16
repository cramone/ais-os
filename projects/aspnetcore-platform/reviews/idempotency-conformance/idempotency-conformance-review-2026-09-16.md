---
id: AP-001
type: review
project: aspnetcore-platform
workstream: idempotency-conformance
raised-by: [MM-001]
status: draft
outcome: pending
todo-id: f7899288-c1d1-58b9-b00c-6c9954c9d51e
created: 2026-09-16
---

# Idempotency — the store contract cannot express the standard

## Scope

**Read:** `Magiq.AspNetCore.Idempotency.Abstractions` (`IIdempotencyStore.cs`) and
`Magiq.AspNetCore.Idempotency` (`IdempotencyMiddleware.cs`, `IdempotencyOptions.cs`,
`DynamoDbIdempotencyStore.cs`, `DynamoDbIdempotencyStoreTableSchema.cs`), plus how magiq-media consumes
them (`Directory.Packages.props`, `src/hosts/Api/Api.csproj`).

**Not read:** every other package in this SDK. No other consumer was surveyed — see IC-7.

**Raised by [`MM-001`](../../../magiq-media/reviews/spec-baseline/spec-baseline-review-2026-09-16.md)**, the
magiq-media spec-baseline review. That review ruled (its Q9) that magiq-media's API conforms to
`draft-ietf-httpapi-idempotency-key-header-07`, then found the SDK cannot express it. The remediation is
here, not there.

**The reference.** `draft-ietf-httpapi-idempotency-key-header-07`, Standards Track, currently a draft.
Listed implementations include Stripe, Adyen, Worldpay, Dwolla and Yandex. §2.6 and §2.7 carry the
behaviour this review measures against:

| Case | Draft says |
|---|---|
| Retry **after** the original completed | respond with the result of the previous operation — success **or** error |
| Retry **while** the original is in flight | `409 Conflict` with a problem body |
| Same key, **different payload** | `422 Unprocessable Content` |
| Key missing on a documented idempotent operation | `400` with a link to the documentation |

**What this plugin does today:** `409` with an empty body for every repeat inside the window, and nothing
else. It is replay *rejection*, not idempotency — which magiq-media's spec already says in as many words.
That is an accurate description of the mechanism, not a defect in the description.

---

## Findings

Severity is `Critical | High | Medium | Low`.

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| IC-1 | **High** | **The store contract has nowhere to put a response.** `IIdempotencyStore` is two methods: `ExistsAsync(tenantId, ownerId, key) → bool` and `MarkAsync(tenantId, ownerId, key, expiresAt)`. No response parameter, no retrieval method. Cached replay is unreachable without changing the interface, so every consumer conforming to the draft is blocked on this repo. | `IIdempotencyStore.cs` |
| IC-2 | **High** | **The key is not scoped to the operation.** The composite is tenant + owner + key. The same `Idempotency-Key` sent to two *different* endpoints collides, and the second is refused `409` having never executed. The draft's uniqueness rule (§2.2) assumes a key identifies a request; here it does not identify the route either. A client library that generates one key per user action, and retries across a multi-call flow, silently loses calls. | `IIdempotencyStore.cs`, `DynamoDbIdempotencyStoreTableSchema.cs` |
| IC-3 | **High** | **`MarkAsync` runs before `next(context)`**, so a key is consumed by a request that never succeeded. A `4xx`, a `5xx` or a mid-flight kill leaves the key burnt for the rest of the window, and an honest retry is refused `409` having never executed. This converts a transient failure into a permanent one — worse than having no idempotency. magiq-media specified the fix (`2xx`-only consumption) and could not implement it here. | `IdempotencyMiddleware.cs` |
| IC-4 | Medium | **No fingerprint, so `422` cannot be expressed.** The draft (§2.4) uses a payload checksum stored with the key so a key replayed with a *different* body is refused rather than silently returning the wrong cached response. The draft treats this as a **security** consideration. There is no fingerprint concept in the contract or the store. | `IIdempotencyStore.cs`; draft §2.4, §2.7 |
| IC-5 | Medium | **No in-flight concept, so `409` means the wrong thing.** The draft reserves `409` for a retry arriving while the original is still processing. Here `409` means "seen before", with no way to distinguish the two, and the response carries no body at all — `context.Response.StatusCode = 409; return;`. | `IdempotencyMiddleware.cs` |
| IC-6 | Medium | **Expiry is a floor, not a window.** `ExistsAsync` tests key presence and never reads the stored expiry, so a key's lifetime is whatever DynamoDB's TTL sweeper decides — which AWS does not guarantee within 48 hours. `IdempotencyOptions.Window` is therefore a minimum, and the documented "24 hours" is not a bound. This matters more once response bodies are retained. | `DynamoDbIdempotencyStore.cs`, `IdempotencyOptions.cs` |
| IC-7 | Medium | **Blast radius across consumers is unknown.** This review surveyed one consumer. Any behaviour change to the middleware is a breaking change for every host that has the plugin registered, and the contract change is a breaking change for any consumer implementing `IIdempotencyStore` itself. No inventory of either exists. | scope limit of this review |
| IC-8 | Low | **Missing-key handling is unspecified rather than wrong.** A request without the header passes straight through. That is correct for opt-in use, but the draft specifies `400` where an operation documents the key as required, and the plugin offers no way to mark an operation as requiring one. | `IdempotencyMiddleware.cs`; draft §2.7 |

---

## Open Questions

1. **Does response storage belong in this plugin at all?** — **Open.** Storing response envelopes in
   DynamoDB brings size limits (400 KB per item), a PII question — bodies retained for 24 hours in a
   table nobody currently treats as sensitive — and a serialisation contract. The alternative is that the
   plugin stores only the status and a correlation reference, and the consumer's own read model answers
   "what happened". That is less conformant and much cheaper, and it is a genuine design choice rather
   than an obvious one.
2. **Is `IIdempotencyStore` a published extension point?** — **Open.** If any consumer implements it,
   changing the interface is a breaking change to them and not only to this repo. If it is effectively
   internal, the contract can move freely. Settles the shape of IC-1 and most of IC-7.
3. **Does the key composite become tenant + owner + operation + key, or tenant + owner + key + fingerprint?**
   — **Open.** Route-scoping (IC-2) and payload-fingerprinting (IC-4) overlap: a fingerprint over
   method + path + body addresses both, where a route segment in the partition key addresses only the
   first. One decision, not two.
4. **Is one release enough?** — **Open.** IC-3 alone is a behaviour change consumers will notice — keys
   that used to be consumed on failure no longer are. Shipping IC-3 separately gets the safety fix out
   early; shipping everything together means one migration for consumers. The DynamoDB schema change for
   response storage may force the answer.

---

## Dependencies

**Documents:** none inbound. This review is raised by `MM-001` and blocks part of it; `MM-001` names this
id in its `## Dependencies`, to be promoted to its plan's `depends-on` when that plan is written.

**External blockers:** none. This repo owns every line the findings touch.

**Consumer coupling — the constraint that shapes delivery.** magiq-media consumes this SDK as NuGet, not
by project reference: `Directory.Packages.props` pins `$(MagiqPlatformVersion)`, currently resolving
`1.1.3.5`. **A change here is not done when it merges — it is done when the packages are published and the
consumer bumps.** magiq-media's own `todos.md` records that this chain is awkward: ten packages pull
`Magiq.Platform.Core` transitively, `CentralPackageTransitivePinningEnabled` is `false`, so publishing one
package alone changes nothing downstream. Any plan from this review states the release step explicitly.

---

## Recommended sequencing

Rough; the plan refines it.

1. **Answer the four open questions**, in order — Q2 and Q3 decide the contract's shape, so they precede
   any code.
2. **Ship IC-3 on its own** — move `MarkAsync` after `next(context)`, consuming the key only on `2xx`.
   It is small, it is a strict safety improvement, and it needs no contract change. Consumers get the fix
   without waiting for the rest.
3. **Change the contract** for response storage and fingerprint/route scoping (IC-1, IC-2, IC-4), per Q3's
   answer. One breaking change, not three.
4. **Bring the middleware to the draft** — `409` for in-flight only and with a problem body, `422` on
   fingerprint mismatch, replay of the stored result on a completed retry (IC-5).
5. **Fix expiry** so `ExistsAsync` honours the stored value rather than trusting the sweeper (IC-6).
6. **Publish and bump**, and confirm magiq-media's spec matches what shipped. Until this step lands,
   `MM-001`'s SB-20 stays open however complete its spec text is.
