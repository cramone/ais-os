# ADR-011 — Unified PUT endpoint for media item folder assignment and move

**Date:** 2026-05-25
**Status:** Accepted
**Deciders:** Chase Ramone

---

## Context

The spec defined two separate endpoints for folder-related operations on a media item:

- `PUT /v1/catalog/items/{itemId}/folder` — initial assignment (item has no folder)
- `POST /v1/catalog/items/{itemId}/move` — reassignment (item already has a folder)

The implementation instead provides a single `PUT /v1/catalog/items/{itemId}/folder` endpoint
(`AssignOrMoveMediaItemFolderEndpoint`) that handles both cases transparently. It attempts
`AssignMediaItemToFolderCommand` first; if the domain rejects it with a 422 (item already
assigned), it falls back to `MoveMediaItemCommand`.

On the domain side these remain separate commands emitting distinct events
(`MediaItemAssignedToFolder` vs `MediaItemMoved`) — the unification is purely at the HTTP layer.

---

## Decision

**Keep the single `PUT /v1/catalog/items/{itemId}/folder` endpoint. Remove `POST .../move` from the spec.**

`PUT` on a sub-resource (`/folder`) has clear idempotent semantics: "set this item's folder to
the supplied value." That contract holds for both initial assignment and reassignment — the caller
does not need to know whether the item currently has a folder. Requiring callers to track state in
order to choose the correct verb adds unnecessary coupling and increases the chance of 422 errors
at the API boundary.

`POST /move` is an RPC-style action verb. It is not idiomatic REST for this operation, and it
duplicates a capability already handled cleanly by `PUT`.

---

## Consequences

- **Spec updated:** `POST /v1/catalog/items/{itemId}/move` removed from the route table and
  traceability table in `mediaitem.api.md`.
- **No implementation change required.** `AssignOrMoveMediaItemFolderEndpoint` already implements
  this contract.
- **Domain events unchanged.** `MediaItemAssignedToFolder` and `MediaItemMoved` remain as distinct
  events with separate audit semantics — the consolidation is HTTP-layer only.
- **Breaking change for consumers of `POST .../move`:** None expected — that endpoint was never
  implemented.
