# Reviews — aspnetcore-platform

**Work goes through a review before it gets a plan.** The review argues the findings; the plan sequences
them and tracks execution. The adoption marker is in [`../CLAUDE.md`](../CLAUDE.md) § Review → Plan cycle;
the convention in full lives in `projects/magiq-media/CLAUDE.md` § Review → Plan and is not duplicated here.

One subfolder per workstream. `reviews/<workstream>/` pairs with `plans/<workstream>/` — **the folder name
is the link**, and it is what survives archiving.

---

## Live

| Id | Workstream | Review | Status | Outcome | Plan |
|---|---|---|---|---|---|
| AP-001 | `idempotency-conformance` | [Idempotency — the store contract cannot express the standard](./idempotency-conformance/idempotency-conformance-review-2026-09-16.md) | Draft | pending | — |

### AP-001 — what it covers

Raised by magiq-media's `MM-001`, which ruled that its API conforms to
`draft-ietf-httpapi-idempotency-key-header-07` and then found the SDK cannot express it.

Eight findings against `Magiq.AspNetCore.Idempotency` and its abstractions. The three High ones:
`IIdempotencyStore` has no response parameter and no retrieval method, so cached replay is unreachable
without a contract change (IC-1); the key composite is tenant + owner + key, so the same key on two
different endpoints collides (IC-2); and `MarkAsync` runs *before* the pipeline, so a failed request burns
its key and an honest retry is refused having never executed (IC-3).

Four open questions. Q2 (is `IIdempotencyStore` a published extension point?) and Q3 (route-scoping versus
payload fingerprinting) decide the contract's shape and precede any code.

**Delivery constraint:** this SDK is consumed as NuGet, not by project reference. A change here is done when
the packages are published and the consumer bumps `$(MagiqPlatformVersion)` — not when it merges.

---

## Archived

None. `AP-001` is the first id minted in this project; the cycle marker was adopted 2026-09-16.

---

## Conventions, in short

- **Ids** — `AP-<nnn>`, monotonic, never reused, never renumbered. One id space covers reviews, feature
  requests, plans and gates. Cross-references are ids, never paths. `MM` is magiq-media, `MA` is magiq-auth.
- **Review status** — `draft` → `findings-agreed` → `done` | `parked` | `superseded`. Front-matter is
  authoritative; the Control Tower board is a projection of it and cannot be edited.
- **`findings-agreed` is Chase's call**, not an inference. Until he makes it, no plan.
- **Severity** — `Critical | High | Medium | Low`. 🔴/🟠 belong to `type: gate` documents only.
- **A review must reach a terminal `outcome`.** `pending` is not a resting state.
- **Index everything from creation, including `draft`.** A review that exists and is not indexed here is
  invisible to the next session, which is the exact failure this convention prevents.
