# Spec vs Repo Alignment Report

Generated: 2026-06-11  
Scope: `D:\source\github\magiq-media\src\modules\` (excluding `.claude/worktrees/`)  
Spec root: `C:\Users\chase\OneDrive\Magiq\AIS-OS\projects\magiq-media\spec\contexts\`

---

## Summary

| Context | Mismatches | Spec-not-in-repo | Repo-not-in-spec |
|---|---|---|---|
| AssetManagement | 9 | 1 | 4 |
| Catalog | 2 | 0 | 4 |
| Processing | 3 | 0 | 1 |
| Registration | 0 | 0 | 0 |
| Metadata | 0 | 0 | 1 |
| DocumentSigning | 1 | 4 | 0 |
| ChangeRequests | 1 | 0 | 0 |

**Total findings: 31**

---

### Commands / Trigger Timing

#### MISMATCH: Processing job created on upload initiation, not upload confirmation

- **Spec says:** `CreateProcessingJobCommand` is dispatched by the handler for `AssetUploadConfirmedIntegrationEvent`.
- **Repo has:** `AssetUploadInitiatedEventHandler` (in `Processing.WriteModel`) dispatches `CreateProcessingJobCommand` immediately on receipt of `AssetUploadInitiatedIntegrationEvent` — before the S3 upload has even occurred. `AssetUploadConfirmedEventHandler` only triggers `IAssetValidationWorker.ValidateAsync` and does not create a job.
- **Which is correct:** Spec — creating a processing job before the file is confirmed uploaded means the job exists in a `Queued` state for an asset that may never complete its upload (e.g. browser closes). This is a functional bug.
- **Recommended fix:** Move `CreateProcessingJobCommand` dispatch to `AssetUploadConfirmedEventHandler`, and have `AssetUploadInitiatedEventHandler` do nothing (or be removed). Ensure `AssetValidationWorker` is invoked after job creation.

---

