# Todos — magiq-media

## Where the plans live (reorganised 2026-08-24)
_Captured: 2026-08-24_
_Status: reference — not a todo_

`plans/` is now one subfolder per workstream, indexed by `plans/README.md`. Live entry points:

| Workstream | Folder | Entry point | State |
|---|---|---|---|
| Spec ↔ repo drift | `plans/spec-drift-review/` | `spec-repo-drift-review.md` | **Active** — 59 open findings; tick the ✓ column as they land |
| Architecture-review remediation | `plans/architecture-review-remediation/` | `COWORK-EXECUTION-INSTRUCTIONS.md` → `IMPLEMENTATION-PLAN.md` | Active — 169 ADO items, nothing started |
| Authz + outbox | `plans/architecture-review-remediation/` | `architecture-review-authz-and-outbox-deferred-plan.md` | **Parked** — deferred in sequencing only, both are pre-prod gates |
| Projection tables | `plans/projection-tables/` | `schema-versioned-projection-tables-plan.md` | Proposed — supersedes the hot-swap rotation plan beside it |
| Deployment naming | `plans/deployment-naming/` | `remove-env-suffix-plan.md` | **Parked** — 4 decisions open (see the todo below) |
| Design | `plans/design/` | `mediaitem-edit-session-design.html` | Active |

Each folder has its own `Archive/`; `plans/Archive/` holds finished work with no live workstream.

`reviews/` mirrors this exactly — same workstream folder names, indexed by `reviews/README.md`. Work
goes **review first, then plan**, and new plans take their review's filename so the pair stays traceable
after archiving; see `CLAUDE.md § Review → Plan`. The eleven 2026-07 architecture reviews are the one
many-to-one case: `reviews/architecture-review-remediation/` → the single plan set of the same name.

The DDD coverage review now has a plan of the same name in `plans/spec-drift-review/` — see the todo
below.

---

## Decide the six questions blocking the DDD remediation plan
_Captured: 2026-08-24_
_Status: todo — plan drafted, Phases 0–1 unblocked, Phases 2 and 4 waiting on you_

`plans/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md` §1 lists six decisions. The two that
change the most downstream work:

- **D1 — authority model.** Banner the three stale architecture docs (hours) or rewrite them (a week,
  against a spec Phase 3 is still repairing). Recommendation: banner now, rewrite only `domain-model.md`
  later, delete `bounded-context.md`'s duplicate inventories outright.
- **D3 — integration event naming.** `media.mediaitem.*` (16 uses) vs `media.item.*` (12). External SNS
  filter policies cannot be written against both. Needs a code check, then an ADR.

D2 (truncated tails), D4 (`Capability` enum), D5 (authorization-matrix scope) and D6 (who owns deleting
`MediaItemReviewSaga`) are in the plan with recommendations.

**Worth knowing before you read it:** the review said "regenerate the 15 truncated files". There is
nothing to regenerate from. It is 17 files truncated mid-token (plus 5 missing only a newline), the tails
are **not in git** — `asset.api.md` ends at the same token across all six commits while growing 13KB —
and **not in the wiki**, which cuts at the identical tokens. They have to be rewritten from the code.
Worse, it is still happening: `system-spec.md` has been re-cut at a *different* point since the
migration, so something in the authoring workflow is still truncating whole-file writes. Phase 0 is a CI
guard for exactly that.

---

**Stale reference I could not fix:** the Cowork project instructions point at
`plans\docs-migration-plan.md`; it is now `plans\Archive\docs-migration-plan.md`. Needs editing in the
project settings.

---

## Verify and ship the X-9.7 / X-9.8 fixes
_Captured: 2026-08-24_
_Status: todo — code written, never executed_

Both came out of the drift review on 2026-08-24 and are **written but not built or run** — no .NET
toolchain in the session that wrote them. Detail in `plans/spec-drift-review/spec-repo-drift-review.md`
§I.9.

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
_Status: todo_

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

See `spec/architecture/branching-and-deployment.md` → "Open questions".

---

## Add bulk delete media item command
_Captured: 2026-06-02T04:52:00Z_

The bulk delete media item needs to be implemented in the FolderDeleteFoanoutWorker.

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

## RESOLVED: metadata shape breaking-change versioning gate (api-consistency plan Stage 4)
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
  either shape: Akshay Gaikwad's current work is all OpenSearch infra provisioning, unrelated to
  MediaItem metadata endpoints. Estelle Wu's most recent related item (#33946, "Add Metadata
  Validation") is backend validation work still in Code Review — confirms the endpoint itself is
  still under active construction, not yet integrated against by any downstream consumer.
- No action needed. Re-check this if UI/integration work against `PUT/POST .../metadata` starts
  before the array shape is fully stable.

---

## Remove environment-name suffix from resource naming
_Captured: 2026-07-21_
_Status: todo — plan drafted, awaiting go-ahead_

Treat every deploy as prod-named: drop the `-{env}` suffix from all resource names so the
"environment" is just the AWS account+region it lands in, with per-env differences delivered
as host config (not name suffixes). Naming-only — `Media:Environment` / `ASPNETCORE_ENVIRONMENT`
behaviour is retained.

**Plan:** `plans/deployment-naming/remove-env-suffix-plan.md` — full change inventory across `cdk-magiq-media`
(`lib/config.ts` `resourceName`/`bucketName`, `magiq-media-stack.ts` `TableSuffix`), the
`magiq-media` app (`MediaResourceNaming`, `MediaConfigurationExtensions`, host bootstrap),
spec/docs, plus sequencing, the destructive non-prod cutover, and verification steps.

**Decision (2026-07-21):** naming-only + ADR-first. ADR is the new "Deployment & Resource
Naming" topic: `D:\source\github\magiq-media\docs\adrs\deployment-and-resource-naming.md`
(README index updated).

**Confirm 4 open decisions before coding (top of the plan):**
1. API Gateway stage segment (`stageName: config.env`) — keep env-named (recommended) or uniform?
2. Inject `Platform__DynamoDB__TableSuffix: ''` explicitly (recommended) vs stop injecting?
3. OK to discard dev/qa data on cutover + reseed/replay (recommended)?
4. Remove vestigial `ENVIRONMENT_NAME` plumbing, or leave inert?

**Key risk:** removing the suffix renames every non-prod stateful resource → CloudFormation
*replace* (data loss on dev/qa/staging; prod unaffected — already unsuffixed). Safe only while
no two environments share one AWS account+region.

---
