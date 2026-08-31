---
id: MM-030
type: review
project: magiq-media
workstream: event-reliability
raised-by: []
status: findings-agreed
outcome: pending
todo-id: 57f79a46-e83d-5be0-ae03-8269516a4cbc
created: 2026-08-25
---

> **Backfilled into the review cycle 2026-08-31 as MM-030.** reviews/README.md flags this row as one to read twice: findings agreed and being worked **with no plan**, which is the one shape the cycle does not model. It needs either a plan or a terminal outcome. X-11.6 and the X-11.5 core closed 2026-08-27; X-11.44 is decision-gated, not work-gated.

# Event reliability — three ways work disappears silently

_Opened 2026-08-25 from the spec-drift review (W19, W25). **Two 🟠 gate blockers.** This was the
thinnest-documented workstream and contains what is arguably the most consequential finding on the gate._

---

## The theme

Three separate defects, one symptom: **something fails, nothing is retried, nothing is recorded, and the
system reports success.** Each has a different mechanism and a different fix, but they share a shape — a
failure path that was written to be forgiving and ended up being silent.

None of them is theoretical. All three are read directly from source.

---

## X-11.6 — the saga DLQ is unreachable ☑ **fixed 2026-08-27**

> **☑ Closed 2026-08-27.** The rule is written into `docs/spec/shared/saga-patterns.md` § *Failure
> handling* (in the magiq-media repo), and applied to all five pairs. Inner handlers no longer catch at all; the outer
> catch stays and is now live rather than dead code. Eleven tests added in
> `Processing.WriteModel.Tests/Sagas/` — the `Sagas` test folder existed and was **empty**, which is why
> this survived. ⚠️ **Written without a compiler — no .NET SDK in the session. Not properly closed until
> `dotnet test` is green**, same caveat as X-11.31 and X-11.16.
>
> **The rule** (open question 2, answered): *the saga signals a handled outcome by returning, never by
> throwing.* Every outcome `AssetIngestionSaga` recognises — no active saga, already terminal, unexpected
> status, no ProcessingJob projection — is an early `return`. **No handled outcome raises an exception**,
> so an exception escaping the saga is by construction an outcome nobody decided, and there is no exception
> *type* that means "handled". That is why the fix is not a taxonomy: the inner handler catches nothing,
> and the outer catches once solely to convert to `MessageProcessStatus.Failed()`.
>
> **No infrastructure change was needed** — verified in CDK. The saga event source already has
> `reportBatchItemFailures: true`, `Function.cs` already returns the per-item batch response, `media-sagas`
> already has `maxReceiveCount: 3`, and the DLQ alarm already exists. The whole transport was correct and
> waiting; only the swallow was in the way.
>
> **Two consequences to expect.** (a) `media-sagas-dlq-depth` will fire for the first time — a poison
> message now costs three attempts over ~10 minutes before landing. Intended, not a regression. (b) **This
> does not fix X-11.5 and does not make it worse** — see the boundary note below.

**The most consequential finding on the gate, and the least visible.**

Both handler layers catch and swallow:

- The inner `IIntegrationEventHandler` catches every exception, logs, and **does not rethrow**.
- The outer `IMessageHandler`'s catch is therefore **dead code**, and it always returns
  `MessageProcessStatus.Success()`.

**So the message is acknowledged and deleted.** A DynamoDB throttle, a serialization error or a dispatch
throw is **logged once and the event is gone**. `maxReceiveCount: 3` never counts, `media-sagas-dlq` never
receives it, and the `media-sagas-dlq-depth` alarm — the only saga alarm that exists — cannot fire for this
class of failure.

**Both log lines say the message will be retried. It will not.**

Only errors *outside* the handler can DLQ — cold start, DI resolution, AWS.Messaging deserialization.

> **The same pattern is in all five handler pairs.** A saga handler should let infrastructure exceptions
> propagate and reserve catch-and-log for domain outcomes it has genuinely handled. That distinction is the
> fix.

`Processing.WriteModel/IntegrationEvents/Consuming/Handlers/*SagaHandler.cs` ·
`hosts/SagaOrchestrator/AssetIngestion/Handlers/*SagaHandler.cs`

### The boundary of this fix — established while making it

**A rejected command never reaches any catch, so propagation cannot surface it.** The saga dispatches via
`ICommandDispatcher.SendAsync(ICommand)` — the **non-generic** overload, which returns bare `Task` and
**discards the handler's `Result<T, DomainError>` entirely**. Traced through
`CommandDispatcher.ExecuteCommand` → `CommandHandlerInvokerFactory.CreateInvoker`: the invoker converts the
handler's return to `Task` and never inspects it. All three commands the saga dispatches
(`Fail`/`Start`/`BypassProcessingJobCommand`) inherit the non-generic `Command` base, so all three take that
path.

Two things follow, and both are good news for sequencing:

- **X-11.6 could be fixed alone.** A domain rejection does not throw, so removing the swallow was never at
  risk of turning X-11.5's rejections into a redelivery loop. The two findings are genuinely independent.
- **X-11.5 is untouched by this.** Closing X-11.6 makes *infrastructure* failures visible and leaves
  *domain-rejection* failures exactly as invisible as they were. Anyone reading "the swallowing is fixed"
  should know that is the half it covers.

---

## X-11.44 — there is no outbox 🟠

Domain events are published to SNS **after** the event store commits, inside the same request. **The
ordering is deliberate and correct** — the code says so:

> *"`next` is awaited first so the event store write commits before any downstream consumer sees the
> events."*

But if the publish then fails, **the event is committed and never reaches a projector**. The write is
durable and correct; the read model is wrong **permanently, not temporarily**. No retry exists because
nothing knows it was missed. **Only a manual rebuild fixes it** — and the rebuild path is itself incomplete
(see `reviews/projection-rebuild/`).

This is the one failure mode where *"eventually consistent"* is untrue. The accurate phrase is **eventually
consistent, or silently divergent**.

**It follows from ADR-005**, which chose inline publication over a publisher Lambda — a defensible decision
whose cost was never written down. Note the platform SDK's own guidance says the opposite: *"Never publish
to a message bus directly from a command handler. Always use `IOutbox`."*

**So the decision is: adopt the outbox, or record the deviation in ADR-005 with this consequence stated.**
What should not persist is a documented platform rule that the app silently contradicts.

`Api/Infrastructure/Middleware/DomainEventPublishingMiddleware.cs`

### ⚠ Correction 2026-08-27 — the cost *was* written down, and what it says is wrong

**The premise "this consequence was never written down" does not survive reading ADR-005.** It is written
down, at `docs/adrs/persistence-and-eventing.md:60`, under *Accepted trade-off — dual-write risk*. That
changes this from *undocumented cost* to something worse: **a documented mitigation that does not hold and
a revisit trigger that cannot fire.** Three specific defects in that paragraph:

| What ADR-005 says | Why it is wrong |
|---|---|
| the event is *"temporarily invisible to the bus"* | **Not temporary — permanent.** Nothing retries, because nothing knows it was missed. `consistency-model.md` states this correctly; the ADR contradicts it |
| *"full event store replay is always available to rebuild projections"* | **False as written.** Replay covers **6 of 10** aggregates; **seven** reference indexes cannot be rebuilt by replay at all; the two uniqueness counters cannot be rebuilt by anything; and the runbook is dev-only and has never been exercised where it would be needed |
| *"Revisit if dual-write failures are observed at a measurable frequency"* | **Nothing measures it.** No metric, no alarm, no dashboard. The escape hatch is conditioned on an observation the system cannot make — so it can never fire |

**So option B is not "write down the cost" — it is "correct three false statements".** That is a smaller
job than adopting an outbox and a strictly necessary one either way, because the ADR currently tells the
next reader that a safety net exists.

### And the platform's outbox does not do what ADR-005 assumes

ADR-005 describes the future option as *"writing the event to a `media-outbox` DynamoDB table **in the same
transaction as** the event-store write"*. **The platform SDK cannot do that today:**

- `IOutboxStore.EnqueueAsync(messages, ct)` takes **no transaction handle** and no list of
  `TransactWriteItem` to contribute to. `DynamoDbOutboxStore.EnqueueAsync` issues its **own**
  `PutItem`/`TransactWriteItems` against the outbox table.
- `DynamoDbEventStore.SaveAsync<TAggregate>(aggregate, ct)` — the single-aggregate path, which is the
  common one — is a plain **`PutItemAsync`, not a transaction**. There is no transaction for an outbox row
  to join. (Only the multi-aggregate overload uses `TransactWriteItems`, capped at 25 items.)

**Consequence: adopting `IOutbox` as it ships would move the failure window, not close it.** Instead of
*"event committed, SNS publish failed"* you get *"event committed, outbox enqueue failed"* — a second
DynamoDB write that throttles for the same reasons the publish does. It buys **retry for messages that
reached the table**, which is real and worth something, but it is **not atomicity**, and anyone approving it
as "adopt the outbox, problem solved" would be buying a weaker guarantee than the words imply.

True atomicity needs the outbox row inside the same `TransactWriteItems` as the event append — a change to
`Magiq.Platform.EventSourcing.DynamoDb` / `IOutboxStore` in the **platform repo**, affecting every consuming
application, not a magiq-media-local change.

> **This is why open question 1 is not a binary.** See the three options in the table below.

---

## X-11.5 — compensation is not idempotent, despite its comment ☑ **core fixed 2026-08-27**

> **☑ The compensation defect is closed 2026-08-27. Two related gaps in the same file remain open** — see
> *Still open* at the end of this section. ⚠️ **Written without a compiler; not properly closed until
> `dotnet test` is green.**
>
> **Open question 5, answered — and neither option as posed was right.** The question was *"is
> `FailProcessingJobCommand` made genuinely idempotent, or does the caller start checking results?"* The
> answer is **a state machine**, because the two cases the old guard conflated pull in opposite directions:
>
> | Status | Outcome | Why |
> |---|---|---|
> | `Failed` | idempotent success | Already in the requested state; matches `Start`/`Bypass`. The first failure's reason and category are preserved so a duplicate cannot overwrite the real cause |
> | `Queued` · `Running` | **transition** | A job that never started can still fail. **Blanket idempotency here would have re-created the exact bug** — a `Queued` job returning "success" without transitioning is still stranded |
> | `Succeeded` · `Bypassed` | **refuse** | Terminal with a *different* outcome. Nothing should turn a succeeded job into a failed one |
>
> **A second defect surfaced while fixing it, and it was load-bearing.** `ProcessingJobFailureCategory` had
> **no `ValidationTimeout` member** — despite its own doc claiming values "match `AssetManagement.FailureCategory`
> so the string representation round-trips". So the saga's `Enum.TryParse` fell back to `ProcessingTimeout`
> … which is **the one category `ProcessingJob.Complete()` treats as reversible**. A validation timeout was
> therefore mislabelled *and* wrongly eligible for timeout recovery. Fixing `Fail()` without this would have
> quietly enabled that path. `ValidationTimeout` is now a member, appended so existing ordinals are unchanged.
>
> **The test suite was green because it asserted the defect.** Two tests —
> `ProcessingJobAggregateTests.Fail_WhenNotRunning_ReturnsError` and
> `FailProcessingJobHandlerTests.HandleAsync_QueuedJob_ReturnsDomainError` — required a `Queued` job to be
> refused. That is a sharper failure than X-11.16's *no* tests: here the tests existed, passed, and locked
> the bug in. Both replaced, plus six new cases covering each arm of the state machine.

### Original finding

`AssetIngestionSaga`'s comment: *"Safe to call on an already-terminal aggregate — `FailProcessingJobCommand`
is a no-op."*

**False.** `ProcessingJob.Fail()` guards `if (Status != Running) return DomainError.InvalidOperation(...)` —
it returns a failed `Result`, and **nothing inspects it**.

The consequence lands on the **validation-timeout** path: the scanner dispatches `FailProcessingJobCommand`
against a job still in `Queued`, it is rejected, and **the ProcessingJob stays `Queued` forever** while its
Asset shows `Failed`.

`Start()` and `Bypass()` *are* genuinely idempotent, which is probably where the assumption came from.

**Two related gaps in the same file:**

- The bypass branch **saves terminal state before dispatching** and never checks the result, so a failed
  dispatch strands the Asset in `Validating` with nothing to retry.
- `DynamoDbSagaRepository.SaveAsync` is an unconditional `PutItem` with **no optimistic concurrency** — the
  `Version` attribute is written and never read. Harmless for asset ingestion, where events are naturally
  serial; **it becomes real the moment a saga handles genuinely concurrent events**, which is exactly what
  a signing saga would do.

### Still open in this finding — deliberately not taken 2026-08-27

Both remaining gaps are **separable from the compensation defect** and were left rather than bundled:

| Gap | Why it was left |
|---|---|
| **Bypass branch saves before dispatching** | It is a genuine ordering bug, but fixing it means deciding what a *failed* dispatch should do to already-persisted terminal saga state — a compensation design question, not a one-line reorder. It deserves its own change with its own tests, and it interacts with the now-live redelivery behaviour from X-11.6 |
| **No optimistic concurrency on saga `SaveAsync`** | This is **open question 3**, and it is a real decision rather than an oversight — the `Version` attribute is already written, so the cost is reading it. Asset ingestion events are naturally serial, so nothing is broken today; it becomes real for the first saga handling genuinely concurrent events. **Worth deciding before `DocumentSigningSaga` is built, not after** |

**Note X-11.6 changed the stakes on both.** Now that failures redeliver instead of vanishing, an
uncompensated bypass strand and a last-writer-wins saga save are both reachable more often — three
deliveries where there was previously one.

---

## What makes this workstream urgent out of proportion to its size

**Nothing measures any of it.**

- **No alarm on queue age** — `ApproximateAgeOfOldestMessage` appears nowhere in the CDK.
- **No projector metric** — `PutMetricData` is called in exactly one place, and it is a timeout scanner.
- **No dashboard.**
- The only alarms in the entire infrastructure are **per-queue DLQ depth ≥ 1** and `SagasApproachingTimeout`
  — and X-11.6 means the first of those cannot fire for the failure it exists to catch.

So all three defects are **discovered, never detected**. Usually by a guard behaving oddly weeks later.

**And production is the only tier where any of it happens.** Dev, qa and staging run
`ASPNETCORE_ENVIRONMENT=Development`, which wires the in-process bus — events are dispatched synchronously
inside the HTTP request, so there is no queue, no retry, no DLQ and no lag. **None of these three findings
can be reproduced outside production.**

---

## Open questions

| # | Question |
|---|---|
| 1 | **Outbox or documented deviation?** ⚠️ **Reframed 2026-08-27 — it is not a binary.** See the three options below |
| 2 | ☑ **Answered 2026-08-27.** *The saga signals a handled outcome by returning, never by throwing* — so there is no exception type meaning "handled", the inner handler catches nothing, and the outer catches once only to convert to `Failed()`. Written into `docs/spec/shared/saga-patterns.md` § Failure handling and applied to all five pairs |
| 3 | Does `DynamoDbSagaRepository` get optimistic concurrency now, or when the first concurrent-event saga is built? The `Version` attribute is already written |
| 4 | Should a **lag / divergence metric** land in this workstream? Comparing `ProjectedVersion` to aggregate version is small, and it is what turns all three of these from invisible to detectable. Shared with `reviews/projection-rebuild/` — **decide which workstream owns it** |
| 5 | Is `FailProcessingJobCommand` made genuinely idempotent, or does the caller start checking results? The second is more honest and more work |

---

## Open question 1, reframed — three options, not two

_Opened for decision 2026-08-27, after reading ADR-005, `IOutboxStore` and `DynamoDbEventStore`._

| | Option | What it actually buys | Cost | Leaves open |
|---|---|---|---|---|
| **A** | **Correct ADR-005 and stop there** | Honesty. The three false statements above are fixed, so the next reader stops believing replay is a safety net | Hours. Doc-only | The divergence itself. Platform rule still contradicted — but now *knowingly*, which is the point of an ADR |
| **B** | **Adopt `IOutbox` as it ships** | **Retry for messages that reached the outbox table.** Real, but **not atomicity** — the enqueue is its own write and can fail exactly where the publish does now | Medium. New table, a drain Lambda + schedule (`OutboxMessageProcessor.ProcessAsync` is a plain method — nothing calls it on a timer), and the middleware rewritten | The dual-write window, narrowed but not closed. **Risk: it reads like a fix and is not one** |
| **C** | **Transaction-participating outbox** | **Actual atomicity** — the outbox row in the same `TransactWriteItems` as the event append | **Large, and in the platform repo.** `DynamoDbEventStore.SaveAsync` (single-aggregate) is a plain `PutItem` today; `IOutboxStore` has no transaction overload. Affects every consuming app | Nothing on this axis — but it is an SDK change with an SDK-sized blast radius |

**A is a prerequisite for B and C, not an alternative to them.** Whatever is chosen, the ADR paragraph is
wrong today and should be corrected in the same PR.

> ### ☑ Decided 2026-08-27 (Chase): **option A**
>
> **ADR-005 is corrected** — `persistence-and-eventing.md`, the *Accepted trade-off — dual-write risk*
> paragraph, plus the "exactly-once" overclaim in the Integration Events section and the second unfirable
> revisit trigger. Each carries a dated correction rather than a silent edit.
>
> **X-11.44 stays open on the gate** as a known, accepted and *unmeasured* risk. It comes off when the
> divergence metric exists and says something — which makes **decision 7 (metric ownership) the critical
> path for this finding**, not a side quest.
>
> **⚠ Option B is not what it looked like.** A follow-up review —
> [`outbox-implementation-review-2026-08-27.md`](./outbox-implementation-review-2026-08-27.md) — read the
> platform outbox properly and found it **has never been run**: no adopters and no tests anywhere in
> `aspnetcore-platform`, **nothing invokes the drain**, and **sent messages are never marked sent**, so
> adopting it as-is would re-publish every event on every drain cycle, forever. It also **swallows its own
> enqueue failures** — X-11.6's exact pattern, inside the component proposed as the fix. **Option B is
> therefore "finish and prove the platform outbox, then adopt it", not "adopt it"** — and had we taken it
> blind, we would have shipped an unbounded duplicate-publish loop onto the path carrying every domain
> event. Read that review before re-opening this decision.

**My recommendation: A now, and let measurement decide between B and C.** ADR-005's own revisit trigger is
*"dual-write failures at measurable frequency"* — the right response to an unfirable trigger is to **make it
fireable**, not to guess past it. That is open question 4's divergence metric, which turns this from a
judgement call into an observation. Doing B blind buys a partial guarantee at real cost and, worse, retires
the finding in everyone's mind while the window is still open.

**Chase's call** — this is a gate blocker and an ADR-level decision.

---

## Sequencing

```
1. X-11.6 — the handler-layer rule, applied to all five pairs   ☑ done 2026-08-27
2. Open question 1 → X-11.44                                    ← reframed; awaiting Chase
   1a. ADR-005 correction (option A) — needed under every branch
3. X-11.5 — compensation idempotency, plus the two related gaps in the same file
4. Open question 4 — the divergence metric, wherever it lands
```

**Note the promotion.** Open question 4's metric was a "should this land here?" question. After the ADR-005
reading it is closer to **load-bearing**: it is what makes option A's revisit trigger real, and without it
the choice between B and C stays a guess. Worth deciding its owner sooner than step 4 implies.

---

## Related

- `docs/spec/shared/consistency-model.md` — the full lag path, the no-outbox caution, environment divergence
- `docs/spec/contexts/Processing/sagas/assetingestionsaga.md` — the only real saga, with its DLQ and
  compensation sections
- `docs/spec/shared/saga-patterns.md` — cross-cutting saga rules
- `docs/adrs/persistence-and-eventing.md` — ADR-005, why publication is inline
- `reviews/projection-rebuild/` — the repair path X-11.44 depends on, and shares open question 4
- `plans/spec-drift-review/spec-repo-drift-review.md` — X-11.5, X-11.6, X-11.44 in full
- `plans/prod-readiness/prod-readiness-gate.md`
