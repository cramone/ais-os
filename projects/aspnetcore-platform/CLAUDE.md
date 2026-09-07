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
| spec/ | Spec files |

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
