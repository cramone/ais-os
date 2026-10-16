---
id: MAS-013
type: plan
project: magiq-auth-serverless
workstream: WS-12-media
repo: magiq-auth-serverless
tags: [media, asset, malware-scan, s3, guardduty]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-12 — Media

`Asset` aggregate with `Scanning → Available | Infected | ScanFailed` state. Quarantine S3 bucket + GuardDuty Malware Protection (ADR-021).

Spec:
- `docs/spec/contexts/Media/README.md`
- `docs/dependency-gaps/platform-capabilities/F001-media-malware-scan.md`
- ADR-021 pre-serve malware scan

## Session invocation

> Picking up WS-12 (plan MAS-013). Asset uploads land in quarantine bucket; GuardDuty scan transitions to Available or Infected; serve path reads only from clean bucket.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name Media -Aggregate Asset -Type auth.asset`

## Phase 1 — Domain
- [ ] `Asset` non-ES per ADR-001 opt-out
- [ ] State machine: `Scanning → Available | Infected | ScanFailed`

## Phase 2 — CDK S3 + GuardDuty
- [ ] Quarantine bucket with GuardDuty Malware Protection for S3 enabled
- [ ] Clean bucket for serve path
- [ ] EventBridge rule: GuardDuty finding → `Media.Writes` transition command

## Phase 3 — Commands + handlers
- [ ] `InitiateUpload` → presigned URL to quarantine bucket
- [ ] `RecordScanResult` (triggered by EventBridge)
- [ ] `PromoteToAvailable` → copy to clean bucket; emit `AssetAvailable`
- [ ] `QuarantineInfected` → emit `AssetInfected`; retain for forensic hold

## Phase 4 — Projections
- [ ] Metadata read model in `auth-media-assets`

## Phase 5 — Erasure cascade
- [ ] `Media.ErasureCascade` — delete user-owned assets

## Phase 6 — Hosts
- [ ] `Media.Writes` — `/platform/media/**` writes
- [ ] `Media.Reads`
- [ ] `Media.Projector`
- [ ] `Media.ErasureCascade`

## Phase 7 — Tests
- [ ] EICAR fixture → upload → scan → Infected state
- [ ] Clean file → upload → scan → Available
- [ ] Serve path rejects Scanning + Infected

## Phase 8 — Deploy + validate

## Exit criteria

- EICAR test fixture quarantined on dev
- Clean file promotes to serve
- Serve path denies non-Available

## Session log

- 2026-10-15: plan drafted
