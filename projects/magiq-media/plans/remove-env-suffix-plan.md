# Plan — Remove the Environment-Name Suffix from Resource Naming

**Created:** 2026-07-21 · **Owner:** Chase Ramone · **Scope choice:** naming only
(runtime behavior unchanged) · **Deliverable:** this plan + the ADR topic doc
`deployment-and-resource-naming.md`, for review *before* any code changes.

Goal: every deploy is named the way `prod` is named today (no `-{env}` suffix).
"Environment" = the AWS account + region it lands in; per-environment differences
reach the hosts as configuration, not as name suffixes. `Media:Environment` /
`ASPNETCORE_ENVIRONMENT` behavior is retained.

---

## Decisions to confirm before implementing

1. **API Gateway stage segment** (`api-gateway.construct.ts:54`,
   `stageName: config.env`): keep as-is (recommended — it's URL routing tied to
   `Media:Environment`, not a naming collision) or make it uniform too?
2. **`Platform__DynamoDB__TableSuffix` injection**: inject `''` explicitly
   (recommended — keeps the app/infra lockstep contract visible) or stop
   injecting it and rely on the app default? Both yield an empty suffix.
3. **Non-prod data**: OK to discard dev/qa event-store + read-model + S3 data on
   cutover and reseed/replay (recommended), or is a backfill/migration required?
4. **Vestigial `ENVIRONMENT_NAME` plumbing**: remove it once naming no longer
   depends on it, or leave it inert for now?

---

## Change inventory

Everything below flows from two facts: (a) in the CDK, ~all names route through
`resourceName()`/`bucketName()` in `lib/config.ts`; (b) in the app, naming routes
through `MediaResourceNaming`. So the functional change is small; most of the work
is tests, comments, and the destructive-cutover coordination.

### Repo A — `cdk-magiq-media`

1. **`lib/config.ts`**
   - `resourceName`: return the bare `name` unconditionally (drop the
     `env === 'prod' ? … : `${name}-${env}`` branch). Update the doc comment.
   - `bucketName`: `return `${name}-${config.account}-${config.region}`;` (drop
     the `resourceName` wrap so no env segment). Update comment + examples.
   - `isProd` stays — still used for removal policy, log retention, API throttling,
     and DynamoDB deletion protection (all behavioral, unchanged).
2. **`lib/magiq-media-stack.ts`**
   - Line ~239: `Platform__DynamoDB__TableSuffix: ''` always (per decision #2).
     Update the adjacent comment.
   - Leave `ASPNETCORE_ENVIRONMENT` (238) and `Media__Environment` (245) exactly
     as they are.
3. **Construct doc comments** referencing the suffix (no behavior, keep honest):
   `constructs/dynamodb/platform-tables.construct.ts` (header + the
   `media-folder-locks` "always uses the env suffix / single-account" note,
   ~lines 20, 115–116), `read-models.construct.ts` / `write-indexes.construct.ts`
   headers (~lines 20–22), `api-gateway.construct.ts` (~line 13).
4. **`environment-variables.md`** (Chase-authored, 2026-07-20): update the
   `Platform__DynamoDB__TableSuffix` row (now always empty), the `Media__Environment`
   notes, and the §4a/§4b `ENVIRONMENT_NAME` derivation notes. Flag for Chase's
   own edit given ownership.
5. **`test/`**: CDK snapshot / assertion tests almost certainly assert suffixed
   physical names. Regenerate snapshots and fix expectations. `npm test` green.
6. (Decision #1) `api-gateway.construct.ts:54` stage segment — likely no change.

### Repo B — `magiq-media` (application)

7. **`src/shared/Media.Shared.Configuration/Naming/MediaResourceNaming.cs`**
   - `TableSuffix(env)` → return `string.Empty` (or remove and inline).
   - `BucketName(...)` → drop the `environmentName` segment:
     `{prefix}-{purpose}-{account}-{region}`.
   - `ComputeDefaults(...)` → no longer gate on `environmentName`; compute bucket
     names from account + region, table suffix empty. Update the XML summary (the
     `→ -{env}` examples).
8. **`src/shared/Media.Shared.Configuration/MediaConfigurationExtensions.cs`**:
   `AddMediaComputedConfiguration` no longer needs `ENVIRONMENT_NAME` for naming
   (still needs account/region for local bucket names). Simplify per decision #4;
   update comments. (In Lambda these defaults are overridden by CDK-injected
   explicit values regardless.)
9. **Host bootstrap** — `Startup.cs:90–91` builds the idempotency table name from
   `MediaResourceNaming.TableSuffixKey`; with an empty suffix it resolves to the
   bare `media-idempotency-keys`. No functional change (already `?? string.Empty`),
   but update the "env-scope it explicitly with the same suffix" comment. **Check
   the other hosts** (`QueryApi`, `Projectors.*`, `EventConsumers`,
   `ProcessingWorker`, `SagaOrchestrator`, `TimeoutScanner`) for parallel
   suffix reads / `AddMediaConfiguration` usage.
10. **Local dev** — `docker-compose*.yml` + `.env.example` set `ENVIRONMENT_NAME`
    and rely on suffixed local table/bucket names. With the suffix gone, local
    resources become bare too; ensure dynamodb-local seeding + migrations use the
    bare names consistently. Update `.env.example` notes.
11. **Tests**: unit + integration tests asserting `-dev` / a non-empty
    `TableSuffix` / `{env}` bucket names. Search and update; run `dotnet test` on
    affected projects (naming, config, and any integration fixtures that build
    table names).

### Repo C — spec / docs

12. `docs/spec` grep surfaced no substantive suffix *rule* — only incidental
    `-dev` / `-staging` in test-secret and tenant-id examples in
    `spec/shared/api-conventions.md` (not resource naming). Skim
    `spec/architecture` for any deployment/config-topology page that describes the
    suffix; update if present. Otherwise no spec change.
13. Co-locate the ADR topic doc `docs/adrs/deployment-and-resource-naming.md` (the
    companion to this plan) in the app PR, and add its row to `docs/adrs/README.md`.

---

## Sequencing & cutover

14. **Land app + CDK together.** App resource names and CDK-provisioned names must
    match at runtime. The CDK injects the explicit bucket names + empty
    `TableSuffix` onto every Lambda, so the CDK deploy is the runtime source of
    truth and ordering risk is low — but keep the app-side defaults consistent so
    local/CLI match. Build the app image with the new defaults, then deploy the
    CDK referencing that image tag.
15. **Per-non-prod-tier cutover is destructive** (see ADR Consequences). Deploy
    `dev` first, validate, reseed/replay as needed; then `qa`. `staging`/`prod`
    deploys are gated off (`STAGING_ENABLED` / `PROD_ENABLED`) — and prod naming
    is unchanged regardless. Follow the `todos.md` re-enable checklist before
    touching staging/prod deploy config.
16. **Branches** (per the app repo GitFlow table — infra/CI change ⇒ `deploy/`):
    - `cdk-magiq-media`: `deploy/chase/<ticket>-remove-env-suffix`
    - `magiq-media`: `deploy/chase/<ticket>-remove-env-suffix` (ADR + code together)
    Open both PRs; cross-link them.

---

## Verification

17. `cdk diff --context env=dev` and `--context env=prod`: confirm every physical
    name loses its suffix on dev, and **prod shows no resource-name diffs**.
18. `npm test` (CDK snapshots) and `dotnet test` (app naming/config/integration)
    both green.
19. Post-change grep of both repos for residual `-{env}` naming: `TableSuffix`
    non-empty, `ENVIRONMENT_NAME`-driven naming, and any `resourceName`/
    `MediaResourceNaming` path that could reintroduce a suffix.
20. After the `dev` deploy, hit `/healthz` (DynamoDB / SNS / S3 health checks) to
    confirm the app resolves the bare resource names end-to-end.

---

## Effort estimate

Small functional change, spread thin: ~2 core edits (CDK `config.ts`, `stack.ts`)
+ ~2 app edits (`MediaResourceNaming`, `MediaConfigurationExtensions`), then the
long tail — comment/doc updates, test-snapshot regeneration, local-dev parity, and
the coordinated non-prod destructive deploys. Bulk of the risk and time is in
tests + cutover coordination, not the code.
