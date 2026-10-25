---
id: MM-041
type: plan
project: magiq-media
workstream: WS-28b-domain-event-versions
repo: magiq-media
tags: [magiq-media, event-schema, upcaster, alias, registration]
consumes: []
blocked-by-external: [MM-022]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-28.
---

# WS-28b — Add `[DomainEvent(Version, Aliases)]` + upcasters for versioned events

**Target repo:** `magiq-media`
**Depends on:** MM-022 (WS-28a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

Key gating fix: `registrationsubmissionrecorded@1` alias so Registration streams reading that discriminator load correctly after the rename to `RegistrationDispatched`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-28b (plan MM-041). SDK (MM-022) ships versioned discriminators + alias + `IEventUpcaster<T>`.
>
> Update `[DomainEvent]` on events listed in `CLAUDE.md` § Known deferred/partial work "Mix of versioned and unversioned discriminators": `MediaProfilePublished@2`, `MediaProfileCreated@1`, `MediaItemCreated@2`, `MediaItemAssignedToFolder@2`, `MediaItemMoved@2`, `FolderClosed@2`, `FolderDescriptionUpdated@2`, each folder metadata `@2`, `RegistrationDispatched@2 (alias registrationsubmissionrecorded)`, `RegistrationInitiated@2`. Write upcasters per `v1→v2` migration.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-022 shipped
- [ ] Enumerate every event in CLAUDE.md "Mix of versioned and unversioned discriminators" bullet

## Phase 1 — `[DomainEvent]` annotations
- [ ] For each event: `Version`, `Aliases` where needed
- [ ] `RegistrationDispatched`: `Aliases = ["registrationsubmissionrecorded"]`
- [ ] Verify discovery via `AddDomainEventsFromAssembly`

## Phase 2 — Upcasters
- [ ] For each `v1→v2` event: `IEventUpcaster<EventV1, EventV2>` implementation
- [ ] `MediaItemCreated@1 → @2`: fill new members per spec
- [ ] `MediaProfilePublished@1 → @2`: likewise
- [ ] Folder metadata events: likewise
- [ ] `RegistrationInitiated@1 → @2`: likewise
- [ ] `MediaItemAssignedToFolder@1 → @2`: likewise
- [ ] `MediaItemMoved@1 → @2`: likewise
- [ ] `FolderClosed@1 → @2`: likewise

## Phase 3 — Discovery
- [ ] `AddDomainEventUpcastersFromAssembly` in host startup
- [ ] Startup validation: no ambiguous alias / duplicate `(type, version)`

## Phase 4 — Tests
- [ ] Unit per upcaster: v1 record → v2 record with expected fields
- [ ] Integration: stream containing `registrationsubmissionrecorded@1` + newer records loads via alias path
- [ ] Golden-file test for each upcaster against fixture

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] event-schema/INDEX.md: WS-28 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-28b → § Shipped
- [ ] Remove `Mix of versioned and unversioned discriminators` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-022 + user policy)
