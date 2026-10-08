---
id: MM-033
type: plan
project: magiq-media
workstream: WS-02b-system-actor-defence-in-depth
repo: magiq-media
tags: [magiq-media, security, auth, callback-routes]
consumes: []
blocked-by-external: [MM-025]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-02 F024; may be no-op (handler already requires actor_type == System on callback routes); keep as placeholder for defence-in-depth review.
---

# WS-02b — `System` actor-type defence-in-depth check in magiq-media

**Target repo:** `magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media`
**Depends on:** MM-025 (WS-02a — magiq-auth ships client-class gate)
**User policy gate:** no magiq-media code change until all external deps ship.

Spec signing / registration callback routes already require `actor_type == "System"`. Once magiq-auth issuance tightens (WS-02a), the exploit closes without magiq-media change. This workstream is reserved for defence-in-depth review: confirm no second route path grants `System` scope downstream of the token guard; optionally add a logged assertion.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Confirm all external deps shipped. Paste:

> Picking up WS-02b (plan MM-033). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-02b-system-actor-defence-in-depth\WS-02b-system-actor-defence-in-depth-plan.md`. Depends on MM-025 (WS-02a) shipped.
>
> Audit magiq-media for every route admitting `actor_type == System`. Confirm each is a platform-integration callback (signing, registration). Review client-id presented on these routes — if feasible, log + metric on receipt to catch any residual issue post-WS-02a. Decide: no-op close, or small defence-in-depth change.
>
> PR to `develop` if change needed; otherwise close with audit note.

## Phase 0 — Audit
- [ ] Confirm MM-025 (WS-02a) shipped
- [ ] Enumerate magiq-media routes checking `actor_type == "System"`
- [ ] For each: confirm it is a platform-integration callback
- [ ] Review `IPermissionRequirement` matrix for `System` admission

## Phase 1 — Decide (branch)
- [ ] (a) No change required — close with audit note in Session log
- [ ] (b) Add logged assertion `OriginatingClientId` on `System`-admitting routes → metric `MagiqMedia/Auth/SystemCallbackAccepted` dimensioned by client id

## Phase 2 — Ship (if branch b)
- [ ] Implement + unit test
- [ ] PR to `develop`

## Phase 3 — Close
- [ ] security/INDEX.md: WS-02 → § Shipped (both halves)
- [ ] F024: shipped
- [ ] INTEGRATION-BACKLOG: WS-02b → § Shipped
- [ ] Remove `magiq-auth emits System for any client` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-025 ship + user policy)
