# aspnetcore-platform

## Project Overview
The .NET Core framework SDK that MAGIQ application code runs on top of. Provides shared platform infrastructure, conventions, and abstractions consumed by all MAGIQ services including magiq-media and other bounded contexts.

**Current status:** Active

## Stack
- .NET 8
- ASP.NET Core
- FastEndpoints
- DynamoDB (projections, event store abstractions)
- SNS / SQS (messaging abstractions)

## Modules
TBD

## Integrations
- magiq-media
- All other MAGIQ bounded context services

## ADO Board
Not yet assigned

## Priority
High

## File Map

| File | Purpose |
|------|---------|
| brief.md | Project summary and constraints |
| notes.md | Open question resolutions and session notes |
| risks.md | Risk register |
| decisions/log.md | Architecture and design decisions (append-only) |
| adrs/ | Formal ADRs for architectural decisions |
| plans/ | Project-specific implementation plans |
| reviews/ | Where work starts — review artifacts, in workstream subfolders mirroring `plans/`. Start at `reviews/README.md` |
| spec/ | Spec files |

## Review → Plan cycle

prefix: AP
we-operate: true

Adoption marker for the [[review-cycle]] and [[workstream-query]] skills. `prefix` seeds document ids
(`AP-001`, `AP-002`, …), minted per project and never reused — `MM` is magiq-media and `MA` is magiq-auth.
`we-operate: true` means we own this repo's code and may raise reviews in it directly, rather than tracking
its work as an external blocker on a consuming project's plan.

**Added 2026-09-16.** This project was already tracked here — `adrs/`, `plans/`, `spec/` and a decision log
all predate the marker — but it carried no adoption section, which made it formally out of scope for the
cycle. The omission surfaced when magiq-media's spec-baseline review (`MM-001`) found work that only this
repo can do: the `IIdempotencyStore` contract cannot express response replay, so conformance to the
idempotency standard is an SDK change rather than a consumer spec edit.

**Work goes through a review before it gets a plan.** `reviews/<workstream>/` pairs with
`plans/<workstream>/` — the folder name is the link, and it survives archiving. The convention in full is
in `projects/magiq-media/CLAUDE.md` § Review → Plan; it is not duplicated here.

**Cross-repo note.** This SDK is consumed as NuGet, not by project reference — `Directory.Packages.props`
in each consumer pins `$(MagiqPlatformVersion)`. A contract change here is therefore not done when it
merges: it is done when the packages are published and the consumer's version is bumped. Plans in this
project state the release step explicitly rather than assuming it.

## Decisions

All architecture and design decisions go in decisions/log.md.
Formal ADRs go in adrs/.

---

## Memory System

This folder contains `MEMORY.md` — external memory for this project.

At the start of every session: Read `MEMORY.md` before responding. Use what you find — do not announce it.

Memory is user-triggered only. Only add entries when the user explicitly asks using phrases like "remember this", "make a note", "log this". Write immediately and confirm.

All memories are persistent until the user asks to remove or change them.

Flag contradictions — never silently overwrite.
