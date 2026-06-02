# MAGIQ Auth

## Project Overview
Central identity, tenant, onboarding, and access-management platform for all MAGIQ cloud applications and APIs.

**Current status:** Draft — scaffolded from Hermes capture. Spec not yet started.

## Stack
C# .NET 8, DynamoDB, Lambda, Openiddict, Fast-endpoints

## Modules
- TenantManagement
- UserManagement
- AuthPolicy
- TokenIssuance
- OnBoarding

## Integrations
All MAGIQ cloud applications and APIs

## ADO Board
_Not yet assigned_

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
| spec/ | Spec files |

## Decisions

All architecture and design decisions go in decisions/log.md.
Formal ADRs go in adrs/.

---

## Memory System

This folder contains MEMORY.md — your external memory for this project.

At the start of every session: Read MEMORY.md before responding. Use what you find — do not announce it.

Memory is user-triggered only. Only add entries when Chase explicitly asks using phrases like
"remember this", "make a note", "log this", "save this". Write immediately and confirm.

All memories are persistent until Chase explicitly asks to remove or change them.

Flag contradictions — never silently overwrite.
