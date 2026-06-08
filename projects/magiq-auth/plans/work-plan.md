# magiq-auth Work Plan

Generated: 2026-06-03

## Summary

26 items → 8 branches/PRs
**Flagged:** SQL column name missing (item 9) — confirm before that PR ships

---

## Ordered Delivery

| # | Item | Type | Risk |
|---|------|------|------|
| 1 | Add centralized package management | chore | low |
| 2 | Add version and common build props | chore | low |
| 3 | Upgrade to .NET 8 | infra | high |
| 4 | Fix apache calling process with injection | bugfix | HIGH |
| 5 | Fix security issue passing username to documents API | bugfix | HIGH |
| 6 | Fix user disabled and lockouts | bugfix | high |
| 7 | Fix encryption exception handling | bugfix | medium |
| 8 | Add SQL script for new index | infra | low |
| 9 | Add SQL script for new column `[NAME NEEDED]` | infra | low |
| 10 | Set AsNoTracking on EF queries | refactor | low |
| 11 | Remove redis lock library dependency | infra | low |
| 12 | Fix redis double round trip | bugfix | low |
| 13 | Update redis connection timeouts | chore | low |
| 14 | Normalize encryption services | refactor | medium |
| 15 | Standardize claims | refactor | medium |
| 16 | Add token refresh | feat | medium |
| 17 | Add tenant switching | feat | high |
| 18 | Add batch get customer | feat | low |
| 19 | Add batch save GenericAttributes | feat | low |
| 20 | Convert sync to async | refactor | medium |
| 21 | Fix threadblocks and race conditions | bugfix | high |
| 22 | Upgrade WebClient to HttpClient | refactor | medium |
| 23 | Fix cache TTL | bugfix | low |
| 24 | Remove redundant cache entries | refactor | low |
| 25 | Fix misuse of logging | bugfix | low |
| 26 | Code clean and standardization | refactor | low |

---

## Branch / PR Breakdown

### Branch 1 — `chore/build-infrastructure`
**PR:** [Chore] Centralized package management, build props, and .NET 8 upgrade
**Base:** main

- Add centralized package management
- Add version and common build props
- Upgrade to .NET 8

_Build foundation — all other branches depend on this compiling cleanly on .NET 8._

---

### Branch 2 — `fix/security-critical`
**PR:** [Security] Fix injection, username leak, lockouts, and encryption exceptions
**Base:** chore/build-infrastructure

- Fix apache calling process with injection
- Fix security issue passing username to documents API
- Fix user disabled and lockouts
- Fix encryption exception handling

_Highest blast-radius fixes — isolated so they can be reviewed urgently and independently._

---

### Branch 3 — `infra/data-and-cache`
**PR:** [Infra] SQL scripts, EF no-tracking, and Redis cleanup
**Base:** chore/build-infrastructure

- Add SQL script for new index
- Add SQL script for new column `[NAME NEEDED]`
- Set AsNoTracking on EF queries
- Remove redis lock library dependency
- Fix redis double round trip
- Update redis connection timeouts

_Data layer and cache infrastructure with no feature dependencies — safe to ship early._

---

### Branch 4 — `refactor/encryption-and-claims`
**PR:** [Refactor] Normalize encryption services and standardize claims
**Base:** fix/security-critical

- Normalize encryption services
- Standardize claims

_Auth foundation refactor — token refresh and tenant switching build on this shape._

---

### Branch 5 — `feat/auth-features`
**PR:** [Feat] Add token refresh and tenant switching
**Base:** refactor/encryption-and-claims

- Add token refresh
- Add tenant switching

_New auth capabilities — tenant switching is high risk, kept paired with refresh for reviewability._

---

### Branch 6 — `feat/batch-operations`
**PR:** [Feat] Batch get customer and batch save GenericAttributes
**Base:** infra/data-and-cache

- Add batch get customer
- Add batch save GenericAttributes

_Cohesive data access additions with no auth dependencies — can ship in parallel with auth work._

---

### Branch 7 — `refactor/async-and-concurrency`
**PR:** [Refactor] Convert sync to async, fix threading, upgrade WebClient
**Base:** feat/auth-features

- Convert sync to async
- Fix threadblocks and race conditions
- Upgrade WebClient to HttpClient

_Concurrency correctness is tightly coupled — async conversion and thread safety land together._

---

### Branch 8 — `refactor/cache-and-quality`
**PR:** [Refactor] Fix cache TTL, remove redundant entries, fix logging, code cleanup
**Base:** refactor/async-and-concurrency

- Fix cache TTL
- Remove redundant cache entries
- Fix misuse of logging
- Code clean and standardization

_Non-functional quality pass — lowest risk, ships last._

---

## Open Questions

- [ ] Column name for SQL script (item 9)
- [ ] ADO area path / iteration for task creation
