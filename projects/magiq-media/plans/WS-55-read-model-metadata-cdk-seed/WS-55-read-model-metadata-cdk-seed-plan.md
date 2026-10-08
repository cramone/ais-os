---
id: MM-077
type: plan
project: magiq-media
workstream: WS-55-read-model-metadata-cdk-seed
repo: cdk-magiq-media
tags: [cdk-magiq-media, infra, projections, rotation, read-model-metadata]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/projections/INDEX.md#WS-55 (no gap file; row-tracked); no separate review document.
---

# WS-55 — CDK seeds `read-model-metadata`

**Target repo:** `cdk-magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`
**Depends on:** none
**Pairs with:** MM-078 (WS-56) — the SDK stops seeding from host startup. Independent: neither has to ship first.
**Unblocks:**
- MM-067 (WS-33): `ProjectionReplay rotate` in every CDK-owned environment
- the annual recovery drill (`deploy-runbook.md` Scenario 4), whose read-model cutover runs through `rotate`

**Spec:**
- `docs/spec/architecture/system-architecture.md` § Projection Table Versioning & Rotation → **Seeding**
- `docs/spec/shared/event-store-and-messaging.md` § DynamoDB Tables, `read-model-metadata` row
- Rationale: `docs/adrs/persistence-and-eventing.md`, "The deploy seeds the pointer; hosts do not"

**Today:**
- Nothing seeds `read-model-metadata` in any deployed environment. `Platform__DynamoDB__Migrations__EnableMigrations` is hard-set to `'false'` (`lib/magiq-media-stack.ts:253`), so `ProjectionsTableMigration` never runs, and no construct writes the rows.
- Live reads therefore resolve the compiled `schemaVersion`. That's harmless while all 24 manifest tables are at v1, but a bump would serve the new, empty table on deploy.
- `rotate` cannot start, because `BeginReplayAsync` is a conditional `UpdateItem` against a row that does not exist.

## Design

- **One `AwsCustomResource` per manifest table**, in a new construct `ReadModelMetadataSeed` beside `PlatformTables`. It takes the same inputs as `ReadModelTables`: `projection-tables.manifest.json` and `retainedPreviousVersions`.
- **The call** is the same on `onCreate` and `onUpdate`. There is no `onDelete`, so a deploy never deletes a row.
  ```
  dynamodb:PutItem
    TableName:           <readModelMetadata.tableName>
    Item:                TableId (S) = tableId
                         ActiveVersion (S) = String(min(schemaVersion, ...retainedPreviousVersions[tableId]))
                         ReplayInProgress (BOOL) = false
                         LastRotatedAt (S) = <deploy time, ISO-8601>
    ConditionExpression: attribute_not_exists(TableId)
  ignoreErrorCodesMatching: ConditionalCheckFailedException
  physicalResourceId:       read-model-metadata-seed:<tableId>   (fixed — a bump updates, never replaces)
  ```
- **The row shape must match `ReadModelTableMetadataStore.InitializeAsync` exactly.**
  - `LastRotatedAt` is required, because the store's `Map` indexes it directly and throws on a row without it.
  - `ActiveVersion` is a **string**.
  - `PreviousVersion` and `PendingVersion` are absent.
- **Lowest provisioned version.** If a table's first-ever seed lands in the same deploy as a bump with the old version retained, the row pins the old version, which is the table holding data. In the normal case it is the manifest version.
- **Re-runs every deploy.** `LastRotatedAt` changes every deploy, so `onUpdate` fires each time and runs 24 conditional writes, all refused and ignored. Accepted. A refused write leaves the original `LastRotatedAt` untouched.
- **IAM:**
  - `AwsCustomResourcePolicy.fromStatements` with `dynamodb:PutItem` on `readModelMetadata.tableArn` only — no `fromSdkCalls` wildcard.
  - `dynamoDbKey.grantEncryptDecrypt(<custom resource grantPrincipal>)`, because the table uses a customer-managed key.
- **`installLatestAwsSdk: false`**, so the deploy pulls nothing from npm.
- **Ordering:**
  - Each seed resource depends on `platform.readModelMetadata`.
  - Every host function depends on the seed resources: Api, QueryApi, every `makeWorker` function and the scheduled scanner. CloudFormation then writes the rows before deployed code runs.

## Session invocation

Open a new Claude Code session and `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`. Paste:

> Picking up WS-55 (plan MM-077). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-55-read-model-metadata-cdk-seed\WS-55-read-model-metadata-cdk-seed-plan.md`.
>
> Add a `ReadModelMetadataSeed` construct that seeds one `read-model-metadata` row per manifest table via `AwsCustomResource` — conditional `PutItem`, `ActiveVersion` = lowest provisioned version, `ConditionalCheckFailedException` ignored, no `onDelete`, `PutItem` scoped to the table ARN plus KMS on `dynamoDbKey`. Host functions depend on it. Follow the plan's § Design exactly; the row shape must match the SDK store.
>
> Branch off `develop` as `deploy/<user>/ws-55-read-model-metadata-seed`. PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Read spec § Seeding (`system-architecture.md`) and the ADR bullet
- [ ] Confirm the row shape against `aspnetcore-platform` `ReadModelTableMetadataStore.InitializeAsync` + `Map` (attribute names and types)
- [ ] List every host function in `magiq-media-stack.ts` that must depend on the seed
- [ ] Check stack resource headroom: +24 custom resources + 1 provider (CloudFormation 500-resource limit)

## Phase 1 — Seed construct
- [ ] `lib/constructs/dynamodb/read-model-metadata-seed.ts`: one `AwsCustomResource` per manifest table, per § Design
- [ ] Seed version = `min(schemaVersion, ...retainedPreviousVersions[tableId])`
- [ ] `PutItem` scoped to the `read-model-metadata` ARN; KMS encrypt/decrypt on `dynamoDbKey`
- [ ] `installLatestAwsSdk: false`

## Phase 2 — Stack wiring
- [ ] Instantiate in `MagiqMediaStack` after `PlatformTables` and `ReadModelTables`
- [ ] Seed resources depend on `platform.readModelMetadata`
- [ ] Every host function `node.addDependency(seed)`
- [ ] Leave `QueryApi` with `grantReadData` only. It never writes `read-model-metadata`.

## Phase 3 — Stale comments
- [ ] `platform-tables.ts:32-35`: drop "Also created idempotently by `ProjectionsTableMigration`". State that the CDK provisions and seeds it, and that the migration covers local development only.
- [ ] `platform-tables.ts:143-146`: "Deployed hosts read/write it" → hosts read it, the deploy seeds it, and the replay tool writes it during a rotation

## Phase 4 — Tests (`test/magiq-media.test.ts`)
- [ ] 24 `Custom::AWS` resources, one per manifest table, each with `attribute_not_exists(TableId)` and `ConditionalCheckFailedException` ignored
- [ ] `ActiveVersion` is the manifest version; with `retainedPreviousVersions` set for a table, it is the lowest retained version
- [ ] Item carries `LastRotatedAt` and `ReplayInProgress = false`; no `PreviousVersion` / `PendingVersion`
- [ ] Custom-resource policy: `dynamodb:PutItem` on the metadata table ARN only
- [ ] No delete call is defined
- [ ] Host functions depend on the seed resources

## Phase 5 — Deploy + verify (dev)
- [ ] Deploy to dev: scan `read-model-metadata` → 24 rows, `ActiveVersion = "1"`
- [ ] Redeploy: rows unchanged (`LastRotatedAt` keeps its first value)
- [ ] `ProjectionReplay rotate --table <any>` → "already on v1; nothing to rotate". That proves `rotate` finds its row.
- [ ] Repeat on qa; staging and prod with their deploy

## Phase 6 — Ship
- [ ] PR to `develop`

## Phase 7 — Close
- [ ] `docs/dependency-gaps/projections/INDEX.md`: WS-55 → § Shipped
- [ ] `docs/dependency-gaps/INTEGRATION-BACKLOG.md`: MM-077 → § Shipped
- [ ] magiq-media repo `CLAUDE.md`: remove the **`read-model-metadata` rows are not seeded** bullet from § Known deferred/partial work

## Closing out

The plan's card moves to `done` only after Chase agrees the work is implemented and complete. The closing card comment records every branch the work was committed to.

## Session log
- 2026-10-08: plan drafted. Spec § Seeding and the ADR bullet written the same day. Origin: review of aspnetcore-platform `feature/guid-projection-rotation`, which added host-startup seeding — rejected for cold-start cost and because it needs write access on read-only hosts (see MM-078).
