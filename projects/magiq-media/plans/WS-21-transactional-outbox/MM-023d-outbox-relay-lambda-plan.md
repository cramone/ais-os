---
id: MM-023d
type: plan
project: magiq-media
workstream: WS-21d-outbox-relay-lambda
repo: cdk-magiq-media
tags: [cdk-magiq-media, lambda, outbox, relay, sns]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-12
depends-on: MM-023b (pipeline wiring), MM-023c (table split)
split-from: WS-21 — parent split 2026-10-12
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-21d (row-tracked); no separate review document.
---

# WS-21d — Outbox relay Lambda

**Target repo:** `cdk-magiq-media`

## Scope

Lambda that consumes committed outbox rows and publishes to SNS. Options:

- **DynamoDB Streams trigger** — new-image event per committed row, lambda publishes + deletes on success
- **Scheduled scan** — CloudWatch rule invokes lambda every N seconds, queries `GSI_NextAttempt`, publishes batch, marks row processed

Spec (§ Transactional Outbox):
- 10 attempts with exponential backoff, then park (move to `outbox-dead`)
- Parking raises `OutboxEntryParked` metric (any non-zero reading pages)
- Delivery is at-least-once

Phases:
- Phase 0: Pick stream-vs-scan (likely streams for latency, scan as fallback for Streams-filter edge cases)
- Phase 1: CDK construct — Lambda, SQS DLQ, IAM, EventBridge/Streams source mapping
- Phase 2: Lambda handler — publish, success → delete row; failure → increment AttemptCount; at 10 → park
- Phase 3: `OutboxEntryParked` metric emission
- Phase 4: Chaos test (SNS failure → row retained, re-published after remediation)
- Phase 5: PR

## Session log
- 2026-10-12: drafted after MM-023 split.
