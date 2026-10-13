---
id: MM-023e
type: plan
project: magiq-media
workstream: WS-21e-outbox-metrics
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, outbox, metrics, observability]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-023e-WS-21e-outbox-metrics]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/48
merge-sha: f6d47c08
shipped: 2026-10-13
created: 2026-10-12
depends-on: MM-080a (SDK EMF bridge — shipped 2026-10-12, `9abdfb04`, PR #45)
adr: docs/adrs/metrics-export.md
split-from: WS-21 — parent split 2026-10-12
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-21e (row-tracked); no separate review document.
---

# WS-21e — Outbox instrumentation

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** MM-080a (SDK EMF bridge, shipped). **Not** blocked on MM-023d — latency and failure classification live inside `OutboxMessageProcessor.ProcessAsync`, which is already in the SDK; the relay Lambda is only the AWS trigger around it.
**Unblocks:** none directly — the host registration (MM-080c) picks up these instruments automatically once wired.

## Scope

Finish the `Magiq.Platform.Messaging.Outbox` Meter. `outbox.entry_parked` (WS-21c) is shipped and will export via the EMF bridge once hosts register (MM-080c). Add two more instruments where the data lives — inside the SDK processor — plus the failure-class taxonomy relay call-sites tag with.

### Instruments

| Instrument | Type | Call site | Tags |
|---|---|---|---|
| `outbox.entry_parked` | `Counter<long>` | **shipped WS-21c** — `OutboxMessageProcessor.MarkMessageAsFailed` on retry exhaustion | `message.type` |
| `outbox.publish_latency` | `Histogram<double>` (unit `ms`) | `OutboxMessageProcessor.ProcessAsync` around `IMessageRouter.PublishAsync` | `message.type` |
| `outbox.publish_failure_rate` | `Counter<long>` | `OutboxMessageProcessor` — every `MarkMessageAsFailed` path | `message.type`, `failure.reason` |

Standard dimensions (`tenant.id`, `environment`) are injected by the EMF listener's execution-context resolver (ADR / WS-58a). Instruments do not tag them locally.

### `outbox.depth` — deferred, option (c)

Spec names `outbox.depth` as a back-pressure signal. Resolving it inside the SDK means either
(a) a scheduled `PutMetricData` scan (ADR rejected direct AWS SDK on the hot path) or
(b) a maintained counter row updated on enqueue + dequeue (writes two rows per outbox entry, inflates DynamoDB cost per message).

**Decision — option (c):** drop the SDK-owned gauge. Operators read back-pressure from CloudWatch's native DynamoDB metrics on the outbox table:

- `ApproximateItemCount` on the outbox table / `GSI_NextAttempt` partition.
- `WriteThrottleEvents` and `ReadThrottleEvents` for pressure on the relay.

Alarms covering those live in CDK (MM-023d / MM-080b), outside this workstream. If a cheap in-process depth signal becomes necessary later, split a new workstream and attach it to a scanner rather than the hot path.

### Failure-reason taxonomy

Expose as `OutboxMetrics.FailureReason*` string constants so relay tags are frozen and alarm names stay stable:

- `serialization` — serializer or type resolver returned null, or `Deserialize` threw.
- `routing_failed` — `IMessageRouter.PublishAsync` returned a per-message result with `PublishStatus.Failed`.
- `router_exception` — `IMessageRouter.PublishAsync` threw before yielding per-message results.
- `unknown` — anything the above does not cover. Any non-zero reading in prod is a signal to extend the taxonomy; never a long-term dimension.

## Phase 0 — Scope confirmation
- [ ] MM-080a (SDK EMF bridge) merged (`9abdfb04`); `EmfMetricsListener` resolves `tenant.id` + `environment` per measurement
- [ ] Confirm `OutboxMetrics` singleton registration path (`MessagingBuilderExtensions`) + current `OutboxMessageProcessor` injection pattern
- [ ] Confirm `IMessageRouter.PublishAsync` returns a `PublishResult` per message (status `Succeeded` / `PartiallySucceeded` / `Failed`) and that `Succeeded`/`PartiallySucceeded` are the ones that mark the row sent today (so `Failed` is the per-message failure case to count)
- [ ] Record `outbox.depth` deferral in the plan session log so the next planner does not re-litigate

## Phase 1 — Instruments on `OutboxMetrics`
- [ ] Add `Histogram<double> _publishLatency` — `name = "outbox.publish_latency"`, `unit = "ms"`, description names it as the relay publish round-trip
- [ ] Add `Counter<long> _publishFailures` — `name = "outbox.publish_failure_rate"`, `unit = "{failure}"`, description names the taxonomy source
- [ ] Add public constants: `FailureReasonSerialization`, `FailureReasonRoutingFailed`, `FailureReasonRouterException`, `FailureReasonUnknown`
- [ ] Add emission methods:
  - `RecordPublishLatency(string messageTypeIdentifier, double elapsedMs)` → tag `message.type`
  - `RecordPublishFailure(string messageTypeIdentifier, string failureReason)` → tag `message.type` + `failure.reason`
- [ ] Keep `RecordParked` unchanged — call sites already compile against it

## Phase 2 — Wire emission in `OutboxMessageProcessor`
- [ ] Deserialization / type-resolver failures (`serializer is null`, `messageType is null`, deserialize throws): `RecordPublishFailure(message.MessageTypeIdentifier, FailureReasonSerialization)` before / inside `MarkMessageAsFailed`
- [ ] Wrap `messageRouter.PublishAsync(messagesToSend, cancellationToken)` with a `Stopwatch`; on each returned `PublishResult`:
  - `RecordPublishLatency(result.Message.Metadata.MessageTypeIdentifier, elapsedMs)` — record per-message so the `message.type` dimension is always valid even for mixed-type batches; the elapsed value is the batch wall-clock, which keeps p99 shape intact
  - `PublishStatus.Failed` → `RecordPublishFailure(..., FailureReasonRoutingFailed)` alongside the existing `MarkMessageAsFailed`
- [ ] Outer `catch (Exception ex)` around `PublishAsync`: for every message in the batch, `RecordPublishFailure(message.MessageTypeIdentifier, FailureReasonRouterException)` before marking failed
- [ ] Any `MarkMessageAsFailed` path that is not covered by the above (future paths) → `FailureReasonUnknown` as a fallback

## Phase 3 — Tests (`tests/Magiq.AspNetCore.Tests/EventSourcing/` or a new `tests/.../Messaging/OutboxMetricsTests.cs`)
- [ ] Serializer-null path emits one `outbox.publish_failure_rate` with `failure.reason=serialization` and `message.type=<id>`
- [ ] Deserialize throws → same, `failure.reason=serialization`
- [ ] `PublishAsync` returns `PublishStatus.Failed` → one `outbox.publish_failure_rate` with `failure.reason=routing_failed` plus one `outbox.publish_latency` measurement
- [ ] `PublishAsync` throws → one `outbox.publish_failure_rate` per message with `failure.reason=router_exception`; **no** `outbox.publish_latency` emission for the exceptional batch (Stopwatch stops but the measurement is skipped — see Phase 1 design note)
- [ ] Happy path (`PublishStatus.Succeeded`) → one `outbox.publish_latency` measurement per message, no `outbox.publish_failure_rate`
- [ ] Taxonomy constants are `public const string` — a const string ties to the alarm expression in CDK
- [ ] Attribute-less `message.type` null-safe — if the identifier is empty string, measurement still records (tag value `""`) rather than throwing

### Design note — latency on `router_exception`

A thrown `PublishAsync` has no round-trip to measure (the request never returned). Record only `outbox.publish_failure_rate` in that path; the latency histogram stays clean of outlier zero / exception-timing samples. Document this in the processor comment next to the outer `catch`.

## Phase 4 — Ship
- [ ] PR to `aspnetcore-platform/main` titled `Outbox publish latency + failure instruments (WS-21e / MM-023e)`
- [ ] No `Magiq.Platform.*` version bump — batched once the dependency-gap plans are done
- [ ] Document `outbox.depth` deferral in `src/platform/Messaging/Magiq.Platform.Messaging.Outbox/README.md` (if present) or inline on `OutboxMetrics` XML — point readers at the DynamoDB native metric

## Phase 5 — Close
- [ ] Tower MM-023e: `new` → `done`; drop `blocked-by-WS-58` tag; add shipped activity event
- [ ] Note on MM-023d (relay Lambda): instruments are already in SDK — Lambda only needs to pass through them; no new relay-side instrumentation code required
- [ ] If MM-080b (CDK dashboards + alarms) consumes these metric names, append a cross-reference to its plan

## Session log
- 2026-10-12: drafted after MM-023 split. Blocked by WS-58 mechanism decision.
- 2026-10-12: WS-58 decisions landed (ADR). Dep narrowed to **MM-080a** (SDK EMF bridge). `outbox.entry_parked` already shipped by WS-21c — remaining work is depth/latency/failure-rate instruments + wiring export.
- 2026-10-13: plan fleshed out into Phase 0-5. Scope correction — the three remaining instruments all have their natural call site inside `OutboxMessageProcessor.ProcessAsync` (SDK), so MM-023e is **not** blocked on MM-023d (relay Lambda); the Lambda is only the AWS trigger around the processor. `outbox.depth` deferred under option (c) — operators read `ApproximateItemCount` + DynamoDB throttle metrics instead of a maintained in-process gauge, so the hot path stays free of extra writes and PutMetricData calls. Failure-reason taxonomy frozen at four values (`serialization`, `routing_failed`, `router_exception`, `unknown`); any non-zero `unknown` reading signals the taxonomy needs extending.
- 2026-10-13: shipped on branch `feature/chase/MM-023e-WS-21e-outbox-metrics`.
  - `OutboxMetrics` extended with `outbox.publish_latency` (`Histogram<double>`, unit `ms`) + `outbox.publish_failure_rate` (`Counter<long>`, unit `{failure}`) + four public `const string` failure-reason tags (`FailureReasonSerialization`, `FailureReasonRoutingFailed`, `FailureReasonRouterException`, `FailureReasonUnknown`). `RecordPublishLatency(messageType, elapsedMs)` + `RecordPublishFailure(messageType, failureReason)` emission methods. `outbox.depth` deferral documented on the class XML — operators read CloudWatch's native DynamoDB metrics on the outbox table instead.
  - `OutboxMessageProcessor.MarkMessageAsFailed` signature now takes an explicit `failureReason`; every call site (`serializer is null`, `messageType is null`, deserialize threw, `PublishStatus.Failed`) passes a frozen taxonomy constant. `PublishAsync` wrapped in `Stopwatch`; `elapsedMs` recorded via `RecordPublishLatency` per message in `results`. Router-threw catch records `FailureReasonRouterException` per in-flight message (filtered by `messagesToSend` id set so already-serialization-failed rows are not double-tagged) and skips latency emission — no round-trip to measure.
  - 8 unit tests in `tests/Magiq.AspNetCore.Tests/Messaging/OutboxMetricsTests.cs`: serializer-null, type-resolver-null, deserialize-throws, PublishStatus.Failed, router throws (no latency on exception path), happy path (latency per message, no failure counter), taxonomy constants frozen at stable string values, empty `message.type` doesn't throw. 15 pass across `OutboxMetricsTests` + `OutboxParkingTests`; full non-Docker regression 215 pass.
  - No `Magiq.Platform.*` version bump — batched once the dependency-gap plans are done.
- 2026-10-13: PR #48 merged to `aspnetcore-platform/main` as `f6d47c08`. Tower MM-023e flipped `new` → `done`. MM-023d (relay Lambda) — no new relay-side instrumentation code required; Lambda invokes `OutboxMessageProcessor.ProcessAsync` and the instruments emit from there. `docs/dependency-gaps/platform-capabilities/INDEX.md` + `INTEGRATION-BACKLOG` not present in the Z:/claudia/magiq snapshot — closure recorded in Tower + this session log only. Cross-reference to MM-080b (CDK dashboards + alarms) pending — alarm expressions should bind to the four `failure.reason` tag values + the `outbox.publish_latency` percentile dimensions.
