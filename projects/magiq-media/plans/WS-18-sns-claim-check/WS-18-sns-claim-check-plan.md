---
id: MM-029
type: plan
project: magiq-media
workstream: WS-18-sns-claim-check
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, outbox, sns, s3, claim-check]
consumes: []
blocked-by-external: [MM-023]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F008-sns-claim-check-and-item-offload.md and INDEX.md#WS-18; no separate review document.
---

# WS-18 — SNS claim-check envelope + item-level S3 offload + bounded relay retries

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** MM-023 (WS-21 — outbox + relay)
**Unblocks:** large events / envelopes stop being unshippable

Delivers F008. Item-level offload > 350 KB; outbox-envelope claim-check > 240 KB; bounded relay to 10 attempts then `OutboxEntryParked`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Confirm MM-023 (WS-21) shipped. Paste:

> Picking up WS-18 (plan MM-029). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-18-sns-claim-check\WS-18-sns-claim-check-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F008-sns-claim-check-and-item-offload.md`.
>
> Depends on WS-21 (MM-023). Pre-publish: event > 350 KB → S3 `event-payloads/{guid}`, body = `{"payloadRef":"s3://..."}`. Outbox entry > 240 KB → S3 `event-envelopes/{guid}`, SNS message = `{"envelopeRef":"s3://..."}`. Outbox relay 10-attempt bound; exhaustion raises `OutboxEntryParked` + dead store.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F008 § Required-shape, § Detection signals
- [ ] Confirm MM-023 shipped (outbox contract available)
- [ ] Locate SNS publisher + outbox relay

## Phase 1 — Item-level S3 offload
- [ ] Pre-publish: measure byte size
- [ ] > `ItemOffloadThreshold` (default 350 KB) → write to `event-payloads/{guid}`
- [ ] Body replaced by `{"payloadRef":"s3://..."}`
- [ ] Consumer: detect `payloadRef`, read from S3, deserialize

## Phase 2 — Outbox envelope claim-check
- [ ] Pre-publish: measure outbox entry serialized size
- [ ] > `EnvelopeClaimCheckThreshold` (default 240 KB) → write to `event-envelopes/{guid}`
- [ ] SNS message carries `{"envelopeRef":"s3://..."}`
- [ ] Consumer: detect `envelopeRef`, read from S3

## Phase 3 — Bounded relay retries
- [ ] Outbox relay (WS-21) tracks `AttemptCount` per entry
- [ ] After 10 failures → raise `OutboxEntryParked` + move to dead store
- [ ] CloudWatch metric: `OutboxEntryParkedCount`

## Phase 4 — S3 lifecycle
- [ ] `event-payloads/` + `event-envelopes/` buckets — lifecycle per spec (document in README; infra may be WS-27a scope or separate)
- [ ] IAM: writer role for `Api` / outbox relay; reader for SQS consumers

## Phase 5 — Tests
- [ ] Unit: small payload — no offload
- [ ] Unit: large payload → S3 + `payloadRef`
- [ ] Unit: consumer rehydrates offloaded payload
- [ ] Unit: outbox entry > 240 KB → envelope claim-check
- [ ] Unit: 10 failed relay attempts → `OutboxEntryParked` + dead store
- [ ] Integration: LocalStack S3 + SNS round-trip

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] F008: shipped
- [ ] platform-capabilities/INDEX.md: WS-18 → § Shipped
- [ ] Transparent to handlers — no magiq-media `-b` row

## Session log
- 2026-10-08: plan drafted (blocked on MM-023 ship)
