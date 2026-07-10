# COPL Data Conversion

## Project Overview
Take a pre-defined database and import it into the MAGIQ Documents system using the web service. The database contains folders, folder metadata, documents, document metadata, and associations between them. An IXExportCore application exports the data into JSON files, which are then imported into the Documents system via the web service.

**Current status:** Draft

## Stack
TBD

## Modules
TBD

## Integrations
- IXExportCore (export to JSON)
- MAGIQ Documents web service (import)

## ADO Board
Not yet assigned

## Priority
Medium

## File Map

| File | Purpose |
|------|---------|
| brief.md | Project summary and constraints |
| notes.md | Open question resolutions and session notes |
| risks.md | Risk register |
| decisions/log.md | Architecture and design decisions (append-only) |
| adrs/ | Formal ADRs for architectural decisions |
| spec/ | Spec files |
| gitignored/ | Local-only database backups (excluded from git) |

## Decisions

All architecture and design decisions go in decisions/log.md.
Formal ADRs go in adrs/.
