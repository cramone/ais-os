# Todos — magiq-media

_Reset 2026-09-15. The `reviews/` and `plans/` trees were removed, so every workstream table, `MM-` id
and review/plan pointer has been stripped. What remains is the work itself — carried forward verbatim,
with dead file references removed._

Standing reports that are **not** todos and are not indexed here live in `adhoc/`:
Catalog, Processing, Registration and DocumentSigning code defects and open decisions (2026-09-07/08).

---

## Verify and ship the X-9.7 / X-9.8 fixes
_Captured: 2026-08-24_
_Status: todo — code written, never executed_

Both are **written but not built or run** — no .NET toolchain in the session that wrote them.

1. **X-9.7 — `MoveMediaItem` (app repo, on `feature/change-requests`).** Handler called `SwapAsync`
   where it needed `MoveAsync`, so every folder-to-folder move failed with a spurious 409. Fixed, plus
   intent-asserting unit tests (`NameReservationIntentRecorder` in `Catalog.WriteModel.Tests/Shared`)
   and an end-to-end move test. Run:
   `dotnet test tests/modules/Catalog/Catalog.WriteModel.Tests/` and
   `dotnet test tests/integration/modules/Catalog/Catalog.IntegrationTests/ -v normal`.
2. **X-9.8 — `GuidFactory` byte order (platform repo).** `(Guid)Medo.Uuid7` converted big-endian, so
   the version nibble landed on the wrong byte and **no id in the system was time-sortable**. Fixed with
   an explicit byte swap plus `GuidFactoryTests`. Run `dotnet test tests/Magiq.AspNetCore.Tests/`.
   **Then a package release** — `GuidFactory` ships in `Magiq.Platform.Core`, which magiq-media never
   references directly: ten packages pull it in transitively at 1.1.3.5 and
   `CentralPackageTransitivePinningEnabled` is `false`, so publishing Core alone changes nothing.
   Either republish the chain at a new `VersionPrefix` (1.1.3.6 and 1.1.3.7 are taken) and bump
   `MagiqPlatformVersion`, or enable transitive pinning here and pin Core — which fixes this repo only.
3. **Permanent consequence, no migration:** ids written before the fix stay unordered. Comment threads
   in `media-change-request-comments` rely on `SK` order being creation order, so pre-fix threads list
   arbitrarily. If that matters to a customer, the answer is a real `{CreatedAt}#{id}` sort key.

---

## RESOLVED: deploy mechanism = cross-repo dispatch to cdk-magiq-media
_Captured: 2026-07-03 · Resolved: 2026-07-03_
_Status: todo — outstanding items below_

Deploy is done by **`magiqsoftware/cdk-magiq-media`** (separate CDK/TypeScript repo),
not a step in magiq-media. `.github/workflows/build-and-push.yml` builds + pushes images
to the shared ECR (738608577325), then dispatches to the CDK repo.

**Integration contract** (implemented):
- magiq-media `dispatch-deploy` / `dispatch-staging` jobs send `repository_dispatch`
  (`event_type: deploy`) to cdk-magiq-media with `client_payload = { env, imageTag: <sha> }`.
- cdk `deploy.yml` listens on that dispatch, resolves `environment` from payload, assumes
  per-env `AWS_DEPLOY_ROLE_ARN` (secret) + `CDK_DEFAULT_ACCOUNT` (var), runs
  `cdk deploy --all --context env=… imageTag=… migrationsEnabled=true`.
- cdk pulls `<prefix>-<sha>` from shared ECR → build-once/deploy-that-artifact holds.

**OUTSTANDING — required before deploys actually run:**
1. **Create repo secret `CDK_DISPATCH_TOKEN`** in magiq-media — fine-grained PAT or GitHub
   App token with `contents: write` (dispatch) on cdk-magiq-media. Until set, the dispatch
   steps are skipped (guarded on token presence) — builds stay green, no deploy fires.
2. Cross-account ECR pull: each env's deploy role needs pull rights on the 738608577325 ECR.
3. cdk deploys only **8** hosts — `SagaOrchestrator.DocumentSigning` (`saga-document-signing`)
   is built by magiq-media but has no `ecrCode(...)` in cdk `magiq-media-stack.ts`. Wire it
   when the signing host is ready to deploy.
4. (Done) The per-env `AWS_DEPLOY_ROLE_ARN` **vars** on magiq-media environments were
   redundant — deploy role lives in cdk-magiq-media (secrets). Removed; magiq-media envs
   now carry no env-level vars.

See `docs/spec/architecture/branching-and-deployment.md` → "Open questions".

---

## Review: enable staging deploy (Model A — dedicated AWS account)
_Captured: 2026-07-03_

Chose **Model A** (one AWS account per environment). Staging AWS account is not
provisioned yet, so the `deploy-staging` job in `.github/workflows/build-and-push.yml`
is provisioned but **dormant** — guarded by `vars.STAGING_ENABLED == 'true'` (unset =
skipped) and a placeholder step that `exit 1`s if run.

To enable when the account is ready:
1. Create staging AWS account + `GitHubOidcMagiqMediaRole` OIDC role in it.
2. (Done) Env-level `AWS_DEPLOY_ROLE_ARN` on `staging` =
   `arn:aws:iam::727517389921:role/GitHubOidcMagiqMediaRole`. Grant it cross-account pull
   on the shared ECR in `738608577325`.
3. Add required-reviewer protection rule on the `staging` environment (Model B gate).
4. Implement the real promote-to-staging deploy step (depends on the deploy-step gap above).
5. Set `STAGING_ENABLED = 'true'`.

Note: Model A implies dedicated accounts for **all** envs — dev/qa/prod still share
`738608577325` today. Prod-in-shared-account is the higher-risk piece. Worth an ADR +
decision-log entry for the full multi-account rollout.

---

## DISABLED until ready + Tom-approved: prod & staging deploys
_Captured: 2026-07-03_

ECR stays central in account `738608577325` (repo-level `AWS_ECR_ROLE_ARN`) — all envs
push images there. Per-env account bound as **env-level `AWS_DEPLOY_ROLE_ARN`** (role
`GitHubOidcMagiqMediaRole`), used by the future deploy step. Each env account's deploy
role needs cross-account pull rights on the `738608577325` ECR (repo policy + trust).

| Env     | Account name | Account ID     | Trigger status |
|---------|--------------|----------------|----------------|
| dev     | Development  | 989143135668   | **active** (push `develop`) |
| qa      | QA           | 835494934465   | **active** (push `release/**`) |
| staging | Demo         | 727517389921   | **DISABLED** (`STAGING_ENABLED=false`) |
| prod    | Prod         | 614323302920   | **DISABLED** (`PROD_ENABLED=false`) |

**prod** and **staging** deploys are OFF until: (a) their AWS accounts are ready to
accept deploys, and (b) **Tom approves**.

Re-enable checklist:
- prod: confirm account 614323302920 has `GitHubOidcMagiqMediaRole` OIDC role + ECR →
  Tom approval → set repo var `PROD_ENABLED='true'`. Add required-reviewer rule on the
  `prod` environment.
- staging: confirm account 727517389921 ready + real deploy step wired → Tom approval →
  set `STAGING_ENABLED='true'`. Add required-reviewer rule on `staging`.

Assumption to verify: OIDC role name is `GitHubOidcMagiqMediaRole` in every account.
The old repo-level default (`738608577325`) is now unused — all envs override per-account.

---

## Production readiness gate
_Captured: 2026-08-25_
_Status: todo — check before setting `PROD_ENABLED` or `STAGING_ENABLED` to `true`_

**Nothing is in production today** (both flags unset, only dev/qa deploy), so nothing is exploitable — the
risk is that these ship silently when the flags flip. Note `STAGING_ENABLED` does not de-risk prod: staging
runs as `Development`, so it never exercises the async projection path or the queue behaviour prod uses.

**Two 🔴 security blockers:** **X-11.31** — an unprivileged tenant member can disable the guards tenant-wide
via the policy setters; **five handlers, the smallest fix and the largest effect, do this first**. Then
**X-11.30** — 86 of 132 write commands have no authorization at all.

**Six 🟠 blockers** on data loss and compliance: X-11.6 (saga DLQ unreachable, events lost — *since fixed;
verified 2026-09-08*), X-11.44 (no outbox), X-11.16 (fan-out failures discarded), X-11.17 ⚖️
(registration-locked folders archived anyway), X-11.41 (moved items archived under their old folder),
X-11.21 (idempotency header name).

---

## Two decisions blocking code work
_Captured: 2026-08-25_
_Status: todo — no research left; both need a call, not investigation_

**1. Idempotency — adopt or retire (X-11.21, 🟠).** The middleware is deployed and works: global on the
`Api` host, table provisioned by CDK, covering every write endpoint. **Nothing sends the header.** Three
code comments claim the feature does not exist. And the header is **`Idempotency-Key`** while every
document said `IdempotencyKey` — so a client following the published contract got **zero replay protection,
silently, with a 2xx**. *Recommendation: adopt* — it is built and paid for, and only the name and the
OpenAPI declaration are missing. Note it is replay **rejection** (bare 409), not replay, and the key is
burnt **before** execution, so a failed request blocks its own retry for 24h.

**2. BI-1 — the bulk-import spec.** Two fully specified aggregates with **no class, no command, no
projector, no queue, no table, no route**. They own **all 16** remaining CI warnings and those warnings are
correct — the missing sections cannot honestly be written. Build / delete / badge-as-design. *The question
is not whether the design is good but whether it is being built, and roughly when.* If badging, put the
deadline in the exemption comment.

**Neither blocks the two 🔴 security items** — those are independent and should start regardless.

---

## Authorization
_Captured: 2026-08-25_
_Status: todo — both 🔴_

X-11.30, X-11.31, X-11.34, X-11.35, X-11.23.

**X-11.31 first: five handlers.** The open question — *does magiq-auth issue roles?* — changes the shape of
everything else. Answer it early, but do not wait for it to fix the five setters.

Related, from the Catalog report: **no Collection, Folder, MediaItem or MediaProfile command performs an
ownership check at any layer.** The five MediaProfile governance routes are the only guarded commands.

---

## Archive cascade
_Captured: 2026-08-25_
_Status: todo — four 🟠_

X-11.15–11.19, X-11.41.

**X-11.16 first — it closes X-11.18.** The design decision the work turns on: on a per-child failure,
abort the level or continue and report?

---

## Event reliability
_Captured: 2026-08-25_
_Status: todo — two 🟠_

X-11.5, X-11.6, X-11.44.

**X-11.6 was the one losing events; verified fixed 2026-09-08** — all five `AssetIngestion` handlers now
catch and return `MessageProcessStatus.Failed()`, so the `media-sagas` DLQ is reachable. Do not re-raise it.

Remaining open question — **outbox or documented deviation** — gates X-11.44.

---

## Asset custody
_Captured: 2026-08-25_
_Status: parked — separate session_

**Decision:** `docs/adrs/ownership-and-authorization.md` in the magiq-media repo — already written.

**Why parked:** raised while classifying `Asset` for the ownership ADR. Split out because it **changes
code** rather than documentation.

**The short version.** `Asset` needs a third concept the codebase lacks — **custody**, which unlike
provenance *transfers*, and unlike authorization attaches to the resource. Split `Asset.OwnerId` into
`UploadedBy` (immutable) and `CustodianId` (transfers to whoever detaches the asset from a role).

**Blocked by X-11.32 (High).** Detach never reaches the Asset aggregate: `DetachFromMediaItem` exists
but nothing dispatches it, there is no unassign consumer, and `ApplyAssetAssignmentCommand` is
attach-only. So after the first assignment an asset can never return to standalone and **can never be
reassigned to a different MediaItem**. Custody has no transfer point to hang on.

**Sequencing is fixed:** wire detach (X-11.32) → model custody → authorization replaces the interim
owner checks. **Do not remove `AssetOwnership.CheckOwner` before the last step** — it currently guards
8 commands including delete, and removing it early widens X-11.30.

**Settle before coding:** the Asset-side handler runs in `EventConsumers` with no HTTP actor, so the
**detaching user's identity must travel on the integration event**. Cheap to decide now, expensive later.

**Not blocking the spec work.** The rule applied throughout: the spec describes what the code does
today, the ADR holds the decision. No spec file was renamed — including the four provenance aggregates
(`Collection`, `Folder`, `MediaItem`, `MediaProfile`) whose rename to `CreatedBy` is decided but unbuilt.

---

## Projection rebuild
_Captured: 2026-08-25_
_Status: parked — separate session_

**Why parked:** raised while writing the consistency model. Changes code — same split as asset custody.

**The short version.** **Seven write-side reference indexes cannot be rebuilt by replay at all** — they are
fed by integration events from another module and **nothing re-emits integration events**. Replaying the
source aggregate leaves them exactly as broken. Each backs a **guard** (asset status, checkout gating,
RecordType deprecation, profile defaults, registration capability), so staleness is a wrong authorization
decision rather than a wrong screen. **The two uniqueness counters are worse** — written by command
handlers, not events, so nothing reproduces them, and they already drift (X-11.39, X-11.43).

**Why it matters more than it looks:** it compounds with **X-11.44** (no outbox — a publish that fails
after commit is only repairable by rebuild), and with there being **no lag metric at all**, so divergence
is discovered rather than detected. The blue-green rebuild runbook has also only ever been run against dev,
which projects synchronously and therefore has neither lag nor a queue.

**Start with divergence detection, not the rebuild tool.** Comparing `ProjectedVersion` against aggregate
version is small, and it tells you whether the rest is urgent. **Do not start by building a bespoke rebuild
for seven tables**: if they become versioned manifest tables, the existing blue-green rotation already does
the work.

---

## Projection tables — schema-versioned rotation
_Captured: 2026-08-25_
_Status: proposed_

Supersedes the hot-swap rotation approach. Related open items that may already belong here:
- Registration summary rows all land in one partition per tenant (`TENANT#{tenantId}#REGISTRATIONS`).
- Processing summary rows do the same (`TENANT#{TenantId}#PROCESSING_JOBS`).
- `media-processing-asset-index` is registered `schemaVersion: null`, which the replay tooling refuses.
- No CLI rebuild verb exists for `ProcessingJob` or `Registration`.

---

## Four leftovers found while writing the deployment-naming ADR
_Captured: 2026-09-01_
_Status: todo — found during the ADR's closing fact-check_

1. **`EnvironmentResetCommand.cs:201` still derives `media-migrations-{env}` from `ENVIRONMENT_NAME`.**
   The exact suffix pattern that was removed, surviving in the CLI. Against a current deploy it
   computes a table name that does not exist, so `EnvironmentReset` fails to exclude the migrations
   table it is trying to protect. Small fix, real consequence. Recorded in the ADR as a known leftover.
2. **App-side bucket defaults don't match anything provisioned.** `S3AssetStorageOptions` defaults to
   `media-originals` / `media-renditions`; the real buckets are `magiq-media-originals-{account}-{region}-an`.
   Harmless in Lambda (CDK injects the resolved names) but a local/CLI fallback points at nothing.
   `MediaResourceNaming.cs`'s docblock also claims it emits `originals-{account}-{region}` — it emits nothing.
   Same for the commented bucket example in `.env.example:101`, still written with `${ENVIRONMENT_NAME}`.
3. **`docs-guard.yml` triggers on `docs/**` but only scans `docs/spec`.** `docs/adrs` is unguarded — and
   **two ADRs are in fact truncated**: `api-http-conventions.md:99` and `asset-storage-and-processing.md:128`
   both end on an unterminated table row with no trailing newline. Recover the tails per `CLAUDE.md`, then
   widen the guard to `docs/`.
4. **`bucketName()` in `cdk-magiq-media/lib/config.ts` is dead code** — zero call sites since the bucket
   construct moved to CloudFormation-generated names on 2026-07-24. Keep it (documents the intended
   shape for a future explicitly-named bucket) or delete it, but it currently reads as the thing that
   names the buckets and isn't. The CDK test hedges on both forms, so it wouldn't catch a regression.

---

## Remove environment-name suffix from resource naming
_Captured: 2026-07-21_
_Status: **done 2026-09-01** — code landed 2026-07/08; the ADR, the last item, is written_

All four decisions were resolved (1 keep env-named · 2 inject `''` explicitly · 3 discard + reseed ·
4 **kept and repurposed**, not removed — `ENVIRONMENT_NAME` now selects the Secrets Manager overlay only).
The key risk and the one-account invariant are recorded in
`docs/adrs/deployment-and-resource-naming.md`.

**Not yet done:** the ADR edit is uncommitted on `feature/change-requests`, and `cdk diff` (dev + prod),
`dotnet test` and the post-deploy `/healthz` probe still need your environment.

**Key risk, for the record:** removing the suffix renames every non-prod stateful resource →
CloudFormation *replace* (data loss on dev/qa/staging; prod unaffected — already unsuffixed). Safe only
while no two environments share one AWS account+region.

---

## RESOLVED: metadata shape breaking-change versioning gate
_Captured: 2026-07-08 · Resolved: 2026-07-08_

Checked before `PUT /v1/catalog/items/{itemId}/metadata` and `POST /v1/catalog/items/bulk/metadata`
ship any further: does the `fields` map→array shape change (`docs/adrs/catalog-domain-invariants.md
§Metadata Collision Prevention and General Fields`, accepted as a no-migration-path breaking change
on the premise that "the platform has no released version yet") still hold that premise, or has a
client integrated against the old map shape in the meantime?

**Answer: premise still holds — shipped in place, no `/v2` needed.**
- Code already implements the array shape (`SetMetadataBatchRequest.Fields`, `SetMetadataFieldRequest.Origin`)
  and has since commit `e4c8af88` ("Add MetadataFieldOrigin and RecordTypeAlias options. (#128)"),
  merged 2026-06-25 — ~2 weeks before this check. No commit since has touched it or any client
  consuming it.
- ADO board (`Media` project) shows no work items indicating a UI/client consumer exists yet for
  either shape.
- No action needed. Re-check this if UI/integration work against `PUT/POST .../metadata` starts
  before the array shape is fully stable.

---

## Add bulk delete media item command
_Captured: 2026-06-02T04:52:00Z_

The bulk delete media item needs to be implemented in the FolderDeleteFanoutWorker.

---
