---
id: MM-035
type: review
project: magiq-media
workstream: event-reliability
raised-by: []
status: draft
outcome: pending
todo-id: 595f8315-407a-56cd-ac1c-2cd6a1c25f8c
created: 2026-08-27
---

> **Backfilled into the review cycle 2026-08-31 as MM-035.** Not yet planned; the work is almost entirely in `aspnetcore-platform`. Verdict: `Magiq.Platform.Messaging.Outbox` has never been run — zero adopters, zero tests, the drain is invoked by nothing and sent messages are never marked sent, so adopting it as-is would produce **unbounded duplicate publication** of every event. Read it before anyone treats 'adopt IOutbox' as the small option.

# Implementing `IOutbox` — what adopting it would actually involve

_Opened 2026-08-27, from **gate decision 6** and open question 1 of
[`event-reliability-review-2026-08-25.md`](./event-reliability-review-2026-08-25.md). Scope: **X-11.44**._

_Read entirely from source in `aspnetcore-platform`, `magiq-media` and `cdk-magiq-media`. Nothing here is
inferred from documentation._

---

## The verdict, up front

**`Magiq.Platform.Messaging.Outbox` has never been run.**

Not "is unused in magiq-media" — **unused anywhere, by anything.** Across the whole platform repo the only
reference to the outbox outside its own three projects is a string inside an exception message. There are
**no tests**. And there are **two defects that prevent the happy path from working at all**, either of which
would be found in the first hour of real use.

This matters because gate decision 6 framed option B as *"adopt `IOutbox` as it ships."* **There is no
shipping behaviour to adopt.** The correct framing is: *finish and prove the platform outbox, then adopt
it.* That is a materially bigger and differently-shaped job than the option implied, and it belongs mostly
in `aspnetcore-platform`, not here.

> **This does not reverse decision 6 — it strengthens it.** The decision was to correct ADR-005 and let
> measurement choose the remedy rather than adopt a partial one blind. Had we adopted blind, we would have
> shipped an unbounded duplicate-publish loop into the one path that carries every domain event.

---

## What exists, and what is actually good about it

The design intent is sound and the pieces are mostly there. Worth saying plainly, because the defect list
below is long and it is not a write-off.

| Component | State |
|---|---|
| `IOutbox` / `Outbox` | Enqueue only. Polly retry ×3, exponential backoff |
| `IOutboxStore` | 4 methods: `EnqueueAsync`, `DequeueNextBatchAsync`, `MarkAsProcessedAsync`, `EnqueueFailedMessagesAsync` |
| `DynamoDbOutboxStore` | Complete implementation of all four. Table `messaging-outbox`, `GSI_NextAttempt` |
| `InMemoryOutboxStore` | Complete — usable for tests and the dev in-process path |
| `OutboxMessageBus` | **Implements `IMessageBus` directly** — a genuine drop-in |
| `OutboxMessageProcessor` | The drain: dequeue → deserialize → route → mark. Retry/poison classification present |
| `OutboxOptions` | `BatchSize` 100, `MaxRetryCount` 3, `NextRetryMinutes` 60 |

**Two things are genuinely well designed:**

1. **The sparse-GSI dequeue.** `NextAttemptAt` is the GSI sort key; `MarkAsProcessedAsync` **`REMOVE`s** it
   and sets a 7-day `ExpiresAt` TTL. So "present in the index" means "still needs sending" — a clean,
   cheap work-queue over DynamoDB with no scanning and automatic cleanup.
2. **`OutboxMessageBus` is a drop-in `IMessageBus`.** This is the single most important fact for costing
   the magiq-media side: `DomainEventPublishingMiddleware` depends on `IMessageBus` and calls
   `PublishAsync`. **It would not have to change at all.** Adoption on our side is close to a DI swap plus
   a drain host — the work is overwhelmingly in the platform.

**And one correction to my own earlier reading**, recorded so the next session does not re-derive it:
`OutboxLogicalMessageFactory.Create` passes `metadata.Timestamp` as `nextAttemptAt`, so a newly enqueued
message **does** appear in the drain query immediately. I initially read that argument as `null` (which
would have made new messages invisible to a sparse GSI) and it is not. The dequeue path is fine.

---

## The defects

### O-1 🔴 A sent message is never marked sent — unbounded duplicate publication

**`IOutboxStore.MarkAsProcessedAsync` and `EnqueueFailedMessagesAsync` are implemented on both stores and
called by nothing.** Verified by grep across the entire platform: the only `MarkAsProcessedAsync` call site
is on `IProcessedMessageStore` — a different interface, for inbound message idempotency, unrelated.

`OutboxMessageProcessor.ProcessAsync` routes the batch and then calls `outboxMessage.MarkAsSent(...)` or
`MarkedAsFailed(...)`. **Both mutate the in-memory `OutboxLogicalMessage` and nothing writes it back.**
`ProcessAsync` ends after the try/catch with no store call.

**Consequence, and it compounds with the otherwise-good GSI design:** `MarkAsProcessedAsync` is what
`REMOVE`s `NextAttemptAt` and takes the item out of the index. It is never called, so **every successfully
sent message stays in the drain query forever** and is re-dequeued and re-published on every subsequent
drain. Not "some duplicates" — **unbounded, growing, permanent re-publication of every event ever
enqueued.** The 7-day TTL is also never set, so nothing ages out.

For magiq-media this would mean every domain event replayed into `media-domain-events` on every drain
cycle, forever, hitting every projector.

### O-2 🔴 Nothing invokes the drain

`IOutboxMessageProcessor` has **exactly one reference in the platform** — its own DI registration in
`MessagingBuilderExtensions.cs:31`. `ProcessAsync` is a plain method: no `BackgroundService`, no
`IHostedService`, no timer, no Lambda entry point, no scheduling of any kind, in the platform or anywhere
else.

So the write half would work and the read half would never run. Messages would accumulate in DynamoDB and
**nothing would ever be published** — which, for the finding this is meant to fix, is strictly worse than
today: X-11.44 loses events only when a publish fails, whereas this loses *all* of them until a drain
exists.

Whoever adopts this must build the scheduler. That is a design decision, not a wiring task — see open
question 2.

### O-3 🟠 `Outbox.EnqueueAsync` swallows its exceptions

```csharp
try  { await _retryPolicy.ExecuteAsync(() => store.EnqueueAsync(outboxLogicalMessages, cancellationToken)); }
catch (Exception ex) { logger.LogError(ex, "An error occurred while enqueuing message '{MessageType}'."); }
```

Both overloads. After three Polly attempts it logs and **returns normally** — the caller cannot tell the
message was not enqueued.

**This is the X-11.6 pattern, inside the component proposed as the fix for X-11.44.** And it defeats the
entire point: an outbox exists so that a durable write happens or the caller knows it did not. Adopting
this as-is would replace *"the SNS publish failed and the event is lost, silently"* with *"the outbox
enqueue failed and the event is lost, silently."* **The loss and the silence both survive the fix.**

Note it would be *slightly* worse than today in one respect: `DomainEventPublishingMiddleware` currently
lets a publish failure surface on the command, so the caller can retry. Route it through `Outbox` and even
that signal disappears.

Fix is one line — rethrow — but it is a platform change and it changes behaviour for any future adopter.

### O-4 🟠 One constant partition key for every message and every tenant

`DynamoDbOutboxTableSchema.PartitionKeyValue = "OUTBOX"`. Every item: `PK = "OUTBOX"`, `SK = "MSG#{id}"`.
The GSI partitions on the same constant.

**Two separate problems.**

*Scale:* a single DynamoDB partition sustains ~1000 WCU / 3000 RCU. Every domain event from every tenant
would write to one partition key, and the drain would read it back through one GSI partition. That is a
hard ceiling with no sharding path, and it sits directly in front of the write path of the whole system.

*Convention:* magiq-media's rule is **`TENANT#{TenantId}#{EntityId}` on every table** — stated in both
`CLAUDE.md` files and honoured by every table we own. This table would be the sole exception, holding
**serialized event payloads from all tenants in one un-partitioned space**, in a compliance-grade
multi-tenant records platform for government. The `TenantId` *is* carried in `Metadata` so routing still
works — but that is a payload field, not a partition boundary. This needs a deliberate decision and
probably a sign-off, not a shrug.

### O-5 🟡 No lease or claim on dequeue

`DequeueNextBatchAsync` queries and returns; it does not mark, lease, or conditionally claim. Two
concurrent drains return the same batch and both publish it. Tolerable under at-least-once delivery *if*
O-1 is fixed — and unbounded if it is not. It also constrains the answer to open question 2: the drain must
be a singleton, or claiming must be added.

### O-6 ⚪ `Console.WriteLine` in the retry callback

`Outbox`'s Polly `onRetry` writes to `Console`. The platform's own `CLAUDE.md` says *"Use `ILogger<T>` —
never `Console.Write` or static loggers."* Trivial, but it is a fair signal about how much production
exposure this component has had.

### O-7 — context, not a defect

**Zero tests** anywhere for any outbox type, and **zero adopters**. Combined with O-1 and O-2 the
conclusion is not "lightly used" but "never executed".

---

## The atomicity question, settled

ADR-005 described the future outbox as writing *"in the same transaction as the event-store write"*. It
cannot, and this is structural rather than a bug:

- **`IOutboxStore.EnqueueAsync(messages, ct)` accepts no transaction handle** and no
  `List<TransactWriteItem>` to contribute to. `DynamoDbOutboxStore` issues its own `PutItem` (single) or
  `TransactWriteItems` (batch) against the outbox table.
- **`DynamoDbEventStore.SaveAsync<TAggregate>(aggregate, ct)` — the single-aggregate path, which is the
  one every command takes — is a plain `PutItemAsync`.** There is no transaction for an outbox row to join.
  Only the multi-aggregate overload uses `TransactWriteItems`, capped at 25 items.

**So even a fully-fixed platform outbox gives at-least-once with durable retry, not atomicity.** It
narrows the dual-write window from "publish to SNS across the network" to "write to a DynamoDB table in the
same region" — genuinely narrower, and genuinely not closed. Anyone approving this as "the dual-write
problem is solved" is buying a weaker guarantee than the words suggest.

Closing it properly means changing `DynamoDbEventStore.SaveAsync` to a transactional write that accepts
contributed items, and giving `IOutboxStore` an overload to contribute them. **That is option C**, and it
is an SDK change affecting every consuming application.

---

## What adoption would cost, by repo

**The split is lopsided and that is the useful finding.** Almost none of this is magiq-media work.

### `aspnetcore-platform` — the bulk

| # | Work |
|---|---|
| 1 | **O-1** — call `MarkAsProcessedAsync` / `EnqueueFailedMessagesAsync` from `ProcessAsync`. The store methods already exist and are correct |
| 2 | **O-2** — decide and build the drain execution model (open question 2) |
| 3 | **O-3** — stop swallowing in `Outbox.EnqueueAsync` |
| 4 | **O-4** — decide the partition strategy (open question 3); likely a schema change |
| 5 | **O-5** — claim-on-dequeue, or constrain the drain to a singleton |
| 6 | Tests. There are none, and O-1/O-2 are exactly what a single end-to-end test would have caught |
| 7 | *(option C only)* transaction-participating enqueue + event-store change |

### `magiq-media` — small

| # | Work |
|---|---|
| 1 | DI: register `OutboxMessageBus` as `IMessageBus` on the write host. **`DomainEventPublishingMiddleware` does not change** |
| 2 | Keep the dev/in-process path working — `InMemoryOutboxStore` exists, but dev currently projects synchronously in-request (`AddInProcessMessageBus`), and an outbox is asynchronous by nature. **This would change dev behaviour**, and dev is where the rebuild runbook and everything else is exercised. See open question 4 |
| 3 | Integration tests for the ingestion path end to end |

### `cdk-magiq-media` — small but real

| # | Work |
|---|---|
| 1 | `messaging-outbox` table + `GSI_NextAttempt`, TTL on `ExpiresAt` |
| 2 | The drain's compute + schedule, whatever question 2 decides, with IAM to the table and publish rights to both SNS topics |
| 3 | Alarms — **outbox depth and oldest-unsent age**. Note these are the first real instances of the divergence metric (gate decision 7), which is not a coincidence: an outbox makes the failure *measurable* even before it makes it *rarer* |
| 4 | Confirm the table is outside the projection-manifest/rotation machinery — it is not a projection |

---

## Open questions for the session that picks this up

| # | Question |
|---|---|
| 1 | **Is the platform team going to own O-1…O-6, or are we?** This is the first fork in the road. The defects are in `aspnetcore-platform`, which is shared, and fixing a never-run component on behalf of every future consumer is a different commitment from fixing our own bug. **Answer this before writing any code** |
| 2 | **What runs the drain?** A scheduled Lambda (matches `TimeoutScanner`, simplest, adds latency equal to the schedule interval) · a DynamoDB Stream on the outbox table (near-real-time, no scheduler, but streams-on-outbox is close to just using streams on the event store and skipping the outbox) · a long-running poller (lowest latency, worst fit for our all-Lambda topology). **Interacts with O-5**: anything concurrent needs claiming first |
| 3 | **Does the outbox table stay `PK = "OUTBOX"`?** Changing it to `TENANT#{TenantId}` fixes both the hot partition and the convention breach, but makes the drain query fan out across tenants instead of one clean index read — which is exactly why it was written this way. A middle option is a fixed shard count (`OUTBOX#{0..N}`). **This is the one that needs a real design answer**, not a preference |
| 4 | **What happens to dev/qa/staging?** They run `AddInProcessMessageBus` and project synchronously in-request. An outbox is asynchronous. Either those tiers keep bypassing the outbox — **preserving the environment divergence that already makes X-11.19 and X-11.44 unreproducible outside prod** — or they adopt it and dev stops being read-your-own-writes, which changes how everyone develops and tests. Neither is obviously right |
| 5 | **Does this still get built at all, or does the metric make it unnecessary?** Decision 6 deferred the remedy until divergence is measured. If measurement shows dual-write loss is genuinely rare, the honest answer may be to keep inline publication, keep the corrected ADR, and spend the effort on the rebuild path instead — which is the *only* repair either way, and is itself incomplete (`reviews/projection-rebuild/`) |

---

## Sequencing

```
0. Gate decision 7 — the divergence metric.
   Decision 6 already made this the gate on X-11.44. This review adds a reason:
   the metric tells you whether any of the below is worth doing.
1. Open question 1 — who owns the platform defects. A conversation, not code.
2. Open questions 2 and 3 — drain model and partition strategy. Design, together.
3. O-1, O-3, O-5, O-6 + tests in aspnetcore-platform. O-1 and O-3 are small;
   the tests are the point, since their absence is why this was believed usable.
4. O-2 / O-4 per the question-2 and question-3 answers.
5. magiq-media DI swap + CDK table, drain and alarms.
6. Open question 4 — the environment split. Decide before rollout, not after.
```

**Do not start at step 5.** The magiq-media side is the small, appealing part and it is inert until the
platform half works.

---

## One thing to carry into any session on this

**The platform outbox contains the same defect class this workstream was opened to fix.** O-3 is a
catch-log-continue that reports success — X-11.6 in a different file. O-1 is a state transition that
happens in memory and is never persisted, which is the archive fan-out's shape (X-11.16) in a different
file.

That is worth more than the individual findings: **the review that produced this workstream found a
recurring failure pattern, and the proposed remedy is built out of it.** Anything adopted here should be
read for that pattern first, not last.

---

## Related

- [`event-reliability-review-2026-08-25.md`](./event-reliability-review-2026-08-25.md) — the parent review;
  X-11.44's three options and the ADR-005 correction
- `plans/prod-readiness/prod-readiness-gate.md` — decisions **6** (this) and **7** (the metric that gates it)
- `docs/adrs/persistence-and-eventing.md` — ADR-005, corrected 2026-08-27
- `docs/spec/shared/consistency-model.md` — the lag path, the no-outbox caution, environment divergence
- `docs/spec/shared/saga-patterns.md` § Failure handling — the swallow rule O-3 violates
- `reviews/projection-rebuild/` — the repair path, which stays load-bearing under every option here
