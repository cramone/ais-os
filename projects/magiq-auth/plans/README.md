# Plans — magiq-auth

**A plan sequences findings a review already argued.** Plans mirror `reviews/`, one subfolder per
workstream, and the plan is named after its primary review — same filename, different tree. See
`CLAUDE.md § Review → Plan`.

**Status vocabulary** — `active` · `blocked` (derived from unmet dependencies, never set by hand) ·
`parked` · `superseded` · `done`. A plan is not `done` without Chase's explicit agreement plus at least
one recorded branch.

## Under the cycle

| Id | Workstream | Plan | Status | Consumes |
|---|---|---|---|---|
| MA-002 | `claims-normalization/` | `claims-normalization-plan.md` | **Done** | *(none — `exception:`)* |
| MA-003 | `client-credentials/` | `client-credentials-plan.md` | **Done** | *(none — `exception:`)* |
| MA-004 | `tenant-switching/` | `tenant-switching-plan.md` | **Active** | *(none — `exception:`)* |
| MA-005 | `customer-deletion/` | `customer-deletion-plan.md` | **Active** | *(none — `exception:`)* |
| MA-006 | `external-providers/` | `external-providers-plan.md` | **Active** | *(none — `exception:`)* |
| — | `validateuser-lockout/` | *(not written)* | — | MA-001 — **gate shut**, 7 open questions and review not yet at `findings-agreed` |

**Restructured 2026-08-31.** All five predated the cycle and sat loose at the `plans/` root, which
`cycle.check()` flags — a plan outside a workstream folder has nothing to pair with. Each now has its
own workstream folder, an `MA-nnn` id and front-matter, so each appears on the Control Tower board.

The two `.done` files were renamed to `.md`. The suffix was the old status convention; front-matter
carries status now, and the odd extension kept them out of every glob that looks for documents.

**None has a separate review, and none is getting one retrofitted.** Each carries its own argument in
its Problem / Background section — the reasoning a review would hold is already in the file — so each
takes an `exception:` line saying exactly that. Splitting them retrospectively would move text, not
add rigour.

**Statuses were verified against `develop` in the code repo on 2026-08-31**, not just transcribed:

| Id | What the repo shows |
|---|---|
| MA-002 | `IMagiqJwtTokenFactory` + `MagiqJwtTokenFactory` exist, registered, used by both JWT controllers. Landed `ed026f3 … AB#33710 (#253)`. |
| MA-003 | `ApiClient`, `ApiClientsController`, EF mappings all exist. Landed `431f954 (#254)`. **Two residues — see below.** |
| MA-004 | v1 cookie switch on `features/chase/tenant-switching-v1`. The v2 RFC 8693 token-exchange grant is **not built** — no `TokenExchange` anywhere in `develop`. |
| MA-005 | No branch, no code. Four decisions unresolved. |
| MA-006 | `ExternalProviderConfig.cs` still `appsettings.json`-driven; no DB-backed table. |

> **MA-003's residues, worth reading before anyone calls the hardcoded-secret issue closed.**
> `MagiqClientStore.cs:32` still holds `_legacyFallbackSecret = new("secret".Sha256())` and returns it
> when a client has no secret hash. That is deliberate and TODO-guarded — it goes once every
> `AppRegistration`/`Customer` client has a real secret, and **that confirmation has not been done**.
> Separately, `DefaultMagiqClientStore.cs:127` hardcodes the same secret with **no** guard and no TODO;
> it is `internal` and the only `IClientStore` registration is `MagiqClientStore`
> (`ServiceCollectionExtensions.cs:115`), so it reads as dead code. Confirm and delete it rather than
> leaving a second hardcoded secret in the tree.

> **MA-005 and MA-006 are filed `active` because `CLAUDE.md` and this file both say *Open*.** Neither
> has a branch or a line of code. If they are not actually being worked, `parked` with the reason is
> the truer status — that is a call to make, not one to infer.

Three analysis documents live in the code repo and remain outside the cycle:
`PRODUCTION_CODE_AUDIT_REPORT.md`, `AuditLogging-Separation-Plan.md`, `sync-to-async-review-plan.md`.
