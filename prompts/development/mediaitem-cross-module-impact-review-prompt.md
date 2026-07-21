# Prompt — Cross-Module Impact Review of the MediaItem Architecture Review

> Paste everything below the line into a fresh Claude (Cowork) session for the
> **magiq-media** project. It takes the completed MediaItem aggregate review as
> input and produces a report of the changes required in **other** modules.

---

You are a Principal Domain Architect for **magiq-media** (C# .NET 8, DDD / CQRS /
event sourcing, AWS-native). Your job in this session is **not** to re-review the
MediaItem aggregate. It is to read one completed review and trace every finding
that forces work **outside** the MediaItem slice — a missing integration-event
subscription in another module, an event another module mishandles, an event whose
design makes a downstream module take the wrong action, or a flow that is invalid
once you follow it across a bounded-context boundary.

## Input

Primary source of truth (read it in full first):
`D:\source\github\magiq-media\docs\reviews\catalog-mediaitem-architecture-review.md`

Supporting context, read only as needed:
- `D:\source\github\magiq-media\CLAUDE.md` — stack, conventions, module/host layout.
- The other reviews in `docs\reviews\` — especially
  `cross-module-integration-review.md`, `assetmanagement-architecture-review.md`,
  `catalog-folder-architecture-review.md`, `catalog-collection-architecture-review.md`,
  `catalog-mediaprofile-architecture-review.md`,
  `registration-registration-architecture-review.md` — for the counterpart
  module's own findings.
- `D:\source\github\magiq-media\docs\spec\` and `docs\adrs\` — the spec and ADRs
  (ADR-006 active-items counter, ADR-010 conformance, ADR-013 metadata origin).

## Method — doc-first, spot-check code

1. **Extract the cross-module surface from the review.** Go through the MediaItem
   review and pull out every finding that has an effect reaching beyond the
   MediaItem slice. A finding is in scope if it involves any of:
   - an **integration event** MediaItem publishes or consumes (see the review's §10);
   - a **command dispatched across a BC boundary** (e.g. Attach/DetachAssetToMediaItem);
   - a **shared counter / registry** another aggregate reads (e.g. the ADR-006
     `active-items` counter that `ArchiveFolderHandler` gates on);
   - a **downstream physical effect** in another module (e.g. version purge
     releasing VersionArtifact S3 protection in AssetManagement);
   - a **fan-in flow** where another module's event drives MediaItem
     (RegistrationInitiated/Cancelled/Rejected, MediaProfilePublished conformance
     fanout, RecordTypePublished/Deprecated, Collection archive fan-out).

   Deliberately re-derive these rather than trusting only the review's own labels —
   a finding tagged "Low / doc" in the review can still have a real cross-module
   consequence, and a finding tagged aggregate-local may leak across a boundary.

2. **For each in-scope finding, classify the cross-module failure mode** into one of:
   - **Missing subscription** — an event is published but no other module consumes it,
     or a module should react and has no handler.
   - **Event not emitted** — the downstream module has (or needs) a handler, but
     MediaItem never publishes the event that would drive it (e.g. no
     `AssetUnassignedFromRole` / `AssetReplacedInRole` integration event).
   - **Mishandled event** — a consumer exists but swallows failures, ACKs on
     transient faults, sources tenant from the payload body, ignores the command
     `Result`, or is unbounded/non-checkpointed.
   - **Bad event design → wrong downstream action** — the event fires in a state or
     with a payload that makes the consumer do the wrong thing (e.g. immediate
     publish emitting `MediaItemSubmittedForReview` with an empty reviewer list;
     purge releasing S3 protection with no auth gate upstream).
   - **Invalid cross-module flow** — following the flow end-to-end reaches an
     inconsistent or unrecoverable state (e.g. Collection archive hard-archiving
     child MediaItems irreversibly; folder archived while it still holds active
     items because the counter was never maintained).

3. **Name the counterpart module and its expected behaviour.** For each finding,
   state which module must change and what it currently does vs. must do. Work from
   the review and the other reviews' findings first.

4. **Spot-check the code only for high-severity or non-obvious cross-module claims.**
   Do not exhaustively re-read other modules. Open the actual code only to confirm
   claims where being wrong would be expensive or where the review is inferential —
   at minimum verify these:
   - **AssetManagement** — does a consumer of `AssetAssignedToRoleIntegrationEvent`
     exist, and is there genuinely no handler for unassign/replace? Does
     `MediaItemVersionPurgedIntegrationEvent` actually release VersionArtifact /
     S3-original protection? (`src/modules/AssetManagement/**`)
   - **Folder** — does `ArchiveFolderHandler` gate on
     `CounterIsZeroAsync("active-items")`, confirming the never-maintained counter
     is load-bearing? (`src/modules/Catalog/**` Folder slice)
   - **Notifications / checkout saga** — is there a consumer of
     `MediaItemSubmittedForReviewIntegrationEvent` that would misfire on the
     empty-reviewer immediate-publish path?
   - **Registration** — what does Registration expect back after
     `RegistrationInitiated/Cancelled/Rejected`, and what breaks when the MediaItem
     consumer silently drops the ref + `active-registrations` counter change?
   Use `Grep`/`Read` (or the azure-devops repo tools) narrowly; cite file+line for
   anything you confirm or refute in code. If a spot-check contradicts the review,
   say so explicitly — the code wins.

5. **Do not fix anything.** This is analysis only. No edits, no PRs.

## Constraints

- Stay strictly on **cross-module** impact. Findings whose blast radius is entirely
  inside the MediaItem slice (e.g. summary-projector tag duplication, missing
  validators, response-DTO `TenantId` leak) are **out of scope** unless they change
  what another module receives or does.
- Route by the project's folder map: code in `D:\source\github\magiq-media`, spec/ADRs
  in its `docs\`, deploy in `cdk-magiq-media`, platform SDK in `aspnetcore-platform`.
  Don't hand-edit the `Media.wiki`.
- Preserve the review's finding IDs (MI-C2, MI-H1, MI-H2, MI-FP1, MI-FC1, …) so the
  report is traceable back to the source review.
- Prefer prose and tables over long bullet lists.

## Output — structured findings report (Markdown)

Produce a single Markdown report suitable to drop into `docs/reviews/`. Structure:

1. **Summary** — one paragraph, plus a count of cross-module changes by target module
   and by severity.

2. **Findings, grouped by target module** (AssetManagement, Folder, Collection,
   Registration, MediaProfile, RecordType, Notifications/Saga, DocumentSigning —
   include only modules that actually need changes). For each finding a subsection with:
   - **ID & title** — reuse the MediaItem finding ID; add a short cross-module title.
   - **Failure mode** — one of the five classes above.
   - **Triggering MediaItem finding** — what in the review causes this.
   - **Failure flow** — concrete: the sequence of events/commands and the wrong end
     state a real request would reach (e.g. "user unassigns asset A from role → no
     integration event → AssetManagement still shows A bound → `Asset.Delete` blocked
     forever").
   - **Counterpart today vs. required** — what the other module does now vs. must do.
   - **Verification** — `doc-only` or `code-confirmed`/`code-refuted` with file:line.
   - **Severity** — Critical / High / Medium / Low, and whether it's a data-integrity,
     reliability, security, or destructive-action risk.

3. **Cross-module dependency map** — a compact table or list: MediaItem event/command
   ⇄ consuming/producing module ⇄ status (missing / mishandled / bad-design / ok).

4. **Sequenced recommendations** — the cross-module changes in the order they should
   land, noting any that must ship together (e.g. emit unassign/replace events **and**
   add the AssetManagement consumer), and which are prerequisites for others.

5. **Open questions / spec gaps** — anything where the correct cross-module behaviour
   isn't pinned down by spec or ADR and needs a decision.

Begin by reading the MediaItem review in full, then produce the report.
