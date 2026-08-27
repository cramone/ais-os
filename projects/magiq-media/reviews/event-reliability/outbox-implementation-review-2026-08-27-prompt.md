Work the outbox implementation question on magiq-media — X-11.44.

Read first:
  Z:\claudia\magiq\projects\magiq-media\reviews\event-reliability\outbox-implementation-review-2026-08-27.md
  Z:\claudia\magiq\projects\magiq-media\reviews\event-reliability\event-reliability-review-2026-08-25.md
  D:\source\github\magiq-media\docs\adrs\persistence-and-eventing.md  (ADR-005, corrected 2026-08-27)
  D:\source\github\magiq-media\docs\spec\shared\consistency-model.md

Context: gate decision 6 was answered 2026-08-27 — correct ADR-005 (done) and let
measurement choose the remedy. So do NOT start building. X-11.44 is decision-gated,
and gate decision 7 (the divergence metric, currently unowned between event-reliability
and projection-rebuild) is its critical path.

The review found the platform outbox has never been run: nothing invokes the drain,
sent messages are never marked sent (so adopting it as-is means unbounded duplicate
publication), and Outbox.EnqueueAsync swallows its own failures. Verify those three
against aspnetcore-platform source yourself before building on them — I want them
independently confirmed, not inherited.

Then work the review's open questions in order. Question 1 first and it is mine to
answer: do we own the platform defects (O-1..O-6 in aspnetcore-platform) or does that
team? Bring me the tradeoff, don't pick for me.

Questions 2 and 3 need real design answers, not preferences:
  - what runs the drain (scheduled Lambda / DynamoDB stream / poller), noting it
    interacts with O-5's missing claim-on-dequeue
  - whether the outbox table keeps PK = "OUTBOX", which is a hot-partition ceiling
    AND breaks our TENANT#{TenantId} convention on every table

Question 4 matters more than it looks: dev/qa/staging run AddInProcessMessageBus and
project synchronously in-request. An outbox is async. Decide deliberately whether
those tiers adopt it or keep bypassing it — bypassing preserves the environment
divergence that already makes X-11.19 and X-11.44 unreproducible outside prod.

Question 5 is a live option, not a formality: if measurement shows dual-write loss is
rare, keeping inline publication and spending the effort on the rebuild path may be
the honest answer. Don't treat building the outbox as the default outcome.

Constraints:
- Follow the Review → Plan convention in CLAUDE.md. If this graduates to a plan it
  goes in plans/event-reliability/ with a matching name, and plans/README.md and
  reviews/README.md both get updated.
- Spec files: edit in place, section by section, never regenerate whole. Run
  .github/scripts/check-spec-truncation.py before finishing.
- If you change platform code, that is a separate repo and a separate PR.
- Check whether a .NET SDK is available early and say so. Three sessions of changes
  are currently uncompiled; if you can run dotnet test, do that first and report it.