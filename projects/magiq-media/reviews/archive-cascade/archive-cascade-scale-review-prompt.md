Work the archive-cascade workstream on magiq-media — X-11.41, then decide on Tier 2.

Read first:
  Z:\claudia\magiq\projects\magiq-media\plans\archive-cascade\archive-cascade-review-2026-08-25.md
  Z:\claudia\magiq\projects\magiq-media\reviews\archive-cascade\archive-cascade-scale-review.md
  D:\source\github\magiq-media\docs\spec\contexts\Catalog\sagas\archive-fan-out.md

X-11.16, X-11.18 and X-11.15 closed 2026-08-27. Steps 2 onward are open.

Start with X-11.41: FolderMediaItemsIndex is add-only — its projector handles MediaItemCreated
and nothing else, so archiving a folder archives items the user has already moved out of it,
under their old parent. Open question 5 in the correctness review is the fork: add removal
handlers, or stop using the index as the traversal. Answer it before writing code.

Two things make this more urgent than its severity suggests. Since the X-11.16 fix those stale
entries produce real refusals that block ancestors, not silent warnings — so it is louder now.
And the Tier 2 design depends on it: a planner writing OutstandingChildren counts from a stale
index deadlocks rather than slows.

Then the scale review's "What to do first": add timing and item/folder counts to both cascade
paths and a queue-age metric on the collection path, so the Tier 2 decision has numbers. There
is no telemetry on either path today. Do not start building Tier 2's durable run model in this
session.

Extend the existing fixtures — FolderArchiveFanOutWorkerTests and
CollectionArchiveFanOutWorkerTests in Catalog.WriteModel.Infrastructure.Tests. Two rules the
last session paid for: never construct a ProjectionKey inside a Moq Setup expression tree, and
keep the negative assertions (_dispatched.Should().NotContain(...)) — they are what actually
test the stranding.

Check whether a .NET SDK is available before you start, and say so if not — the last two
sessions shipped uncompiled.