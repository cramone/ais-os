# SFN substrate sweep — run guide

Purpose: sequential steps and copy-paste prompts to (A) sweep `docs/spec/**` for the Step Functions pivot, (B) re-audit the 17 substrate-dependent findings in `spec-audit-2026-09-29`, then (C, D) resume the audit loop on non-substrate work and records-domain decisions.

Guardrails throughout:

- Never `/commit` without user say-so per session — this guide names the commit moments.
- Never read `magiq-media` `src/`, `tests/`, or infra. Only `aspnetcore-platform` if a platform capability check is needed.
- Never edit spec files outside the current step's file list.
- If `docs_guard.py` fails, fix before landing — never `--no-verify`.
- Fresh Claude session between Phase A and Phase B — keeps context focused.
- Caveman mode stays on throughout. Say `stop caveman` when writing the Karen briefing (needs normal prose).

---

## Phase A — SFN spec sweep

One PR, ~18 files, four steps of edits with commits between each.

### Step 1 — new branch

Terminal:

```bash
git checkout develop
git pull
git checkout -b spec/sfn-substrate-sweep
```

### Step 2 — start fresh Claude session in repo root

New session. Wait for prompt.

### Step 3 — sweep architecture layer

Prompt:

```
Sweep docs/spec/architecture/ to align with the SFN pivot decided in docs/adrs/saga-orchestration-engine.md and docs/review/spec-audit-2026-09-29/saga-orchestration-engine-selection.md. Read both first.

Guardrail: CLAUDE.md § "Spec files state the specified system". Present tense. No history. No "migration is". No "deployed as". No code-state caveats. No ADR-0nn citations. Never mention findings, docs/review/, or audits in spec text.

Files this step:
1. docs/spec/architecture/system-architecture.md
2. docs/spec/architecture/bounded-contexts.md
3. docs/spec/shared/saga-patterns.md

Replace in these files:
- media-sagas DynamoDB table, SagaTimeoutIndex GSI, SagaOrchestrator SQS driver → four Step Functions Standard state machines: magiq-media-asset-ingestion, magiq-media-document-signing, magiq-media-collection-archive-cascade, magiq-media-folder-archive-cascade
- Coordinator vocabulary: activity workers dispatched via task tokens; SendTaskSuccess / SendTaskFailure close the wait; EventBridge rules connect integration/domain events to StartExecution and callbacks; execution name is run identity (tenant + correlation key)
- SagaOrchestrator role: Step Functions activity worker Lambda, not SQS-driven orchestrator
- Diagram nodes, queue tables, DLQ tables, alarm tables — update accordingly. media-sagas queue removed. Activity Lambdas still have DLQ on activity input queue if one exists per state machine

Do not touch docs/review/. Never read magiq-media src/tests/infra.

After edits, run: python .github/scripts/docs_guard.py

Report per-file diff summary. Stop.
```

### Step 4 — commit Step 3

After review, say:

```
Land it. Commit as: spec: SFN substrate — architecture layer
```

### Step 5 — sweep per-saga spec files

Prompt:

```
Continue SFN sweep. Same guardrails. Files this step:
1. docs/spec/contexts/Processing/sagas/assetingestionsaga.md
2. docs/spec/contexts/DocumentSigning/sagas/documentsigningsaga.md
3. docs/spec/contexts/Catalog/sagas/archive-fan-out.md

Each saga becomes a Step Functions state machine specification: named states, transitions, activity tasks with task tokens, timeouts as state Timeout fields, retry policy on Retry blocks, catch on Catch blocks, terminal states. EventBridge event pattern that triggers StartExecution. Execution name convention (tenant + correlation key). Compensation as explicit states, not implicit saga logic.

Signing saga: Releasing becomes an SFN state with its own Timeout and Retry, not a scanner-driven recovery. Envelope creation and callback wait use task tokens.

Fan-out: collection cascade + folder cascade each get their own state machine. Fan-out uses SFN Map state with per-child activity. Run identity = execution name. Continuation chain replaced by Map iteration.

Delete: any reference to media-sagas rows, SagaOrchestrator scanning, SagaTimeoutIndex, TimeoutScanner-driven saga passes.

Run docs_guard.py after. Report diffs. Stop.
```

### Step 6 — commit Step 5

```
Land it. Commit as: spec: SFN substrate — per-saga specs
```

### Step 7 — scanner split and ref sweep

Prompt:

```
Continue SFN sweep. Same guardrails. Files this step:

1. docs/spec/shared/operations.md
2. docs/spec/shared/concurrency-and-consistency.md
3. docs/spec/contexts/Processing/context-overview.md
4. docs/spec/contexts/Processing/aggregates/ProcessingJob/processingjob.write-model.md
5. docs/spec/contexts/Processing/aggregates/ProcessingJob/processingjob.api.md
6. docs/spec/contexts/Processing/aggregates/ProcessingJob/processingjob.scenarios.md
7. docs/spec/contexts/AssetManagement/aggregates/Asset/asset.write-model.md
8. docs/spec/contexts/AssetManagement/aggregates/Asset/asset.scenarios.md
9. docs/spec/contexts/AssetManagement/context-overview.md
10. docs/spec/contexts/DocumentSigning/context-overview.md
11. docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md
12. docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.read-model.md
13. docs/spec/contexts/Registration/aggregates/Registration/registration.read-model.md
14. docs/spec/glossary.md
15. docs/spec/README.md
16. docs/spec/shared/event-store-and-messaging.md
17. docs/spec/shared/api-conventions.md

Sweep for these terms, remove or restate each:
- TimeoutScanner → MaintenanceScanner where the context is a non-saga pass (upload expiry, registration-response overdue, retention reconciliation, quarantine-move retry). Saga passes removed. AssetIngestionTimeoutScanner and SagaTimeoutScanner deleted from spec — their function is now an SFN state Timeout.
- MediaItemLeaseExpiryScanner: state as its own Catalog-owned Lambda (not a MaintenanceScanner pass, not saga)
- media-sagas SQS queue and media-sagas DynamoDB table: removed
- SagaOrchestrator: Step Functions activity worker, not SQS-driven
- Any "AssetIngestionSaga correlates on X in media-sagas" → "the magiq-media-asset-ingestion state machine correlates on X via execution name"

Retention triggers, quarantine-move retry, upload expiry, registration-response overdue stay as MaintenanceScanner passes with their existing indexes.

Run docs_guard.py after. Report diffs. Stop.
```

### Step 8 — commit Step 7

```
Land it. Commit as: spec: SFN substrate — scanner split and ref sweep
```

### Step 9 — verification sweep

Prompt:

```
Verify SFN sweep is complete. Grep docs/spec/ for each term below; report every remaining hit with two lines of context and decide remove-or-restate:

  media-sagas
  SagaTimeoutIndex
  TimeoutScanner
  SagaTimeoutScanner
  AssetIngestionTimeoutScanner
  SagaOrchestrator (any context where it is described as SQS-driven, DynamoDB-state-owning, or scanner-driven)

Also grep docs/spec/ for:
  Step Functions
  state machine
  StartExecution
  task token
  activity worker
  execution name

Confirm each hit is a specified-design statement, not a code-state caveat or migration note.

Run python .github/scripts/docs_guard.py.

Report: list of remaining substrate hits (should be zero), list of new SFN mentions (should be non-trivial), docs_guard result.
```

### Step 10 — fix CLAUDE.md contradiction

Prompt:

```
CLAUDE.md § Known deferred/partial work currently claims "media-sagas and SagaTimeoutIndex are removed from the spec. No spec file names them today." After the sweep this is true — leave the sentence. Verify by grep: media-sagas and SagaTimeoutIndex should return zero hits in docs/spec/.

If any hit remains, either finish the sweep or narrow the CLAUDE.md sentence to name the file that still holds the reference and why.

Also verify these CLAUDE.md bullets still match the post-sweep spec:
- "TimeoutScanner is renamed MaintenanceScanner" — should now be accurate design in spec
- SagaOrchestrator.DocumentSigning host row — activity worker phrasing
- Step Functions state machines deferred bullet — still accurate (state machines specified, not deployed)

Report any drift. Fix if any. Then /commit as: spec: SFN substrate — reconcile CLAUDE.md
```

---

## Phase B — re-audit 17 substrate findings

New Claude session (fresh context), same branch.

### Step 11 — resolution pass

Prompt:

```
The SFN spec sweep has landed on this branch. Re-audit these 17 findings against the post-sweep spec and update each finding file + docs/review/spec-audit-2026-09-29/INDEX.md status cell:

  F007, F018, F019, F022, F023, F028, F029, F030, F031, F032, F033, F034, F042, F049, F074, F075, F076, F087

For each finding:
1. Read the finding file. Read its cited spec lines fresh.
2. Decide one of:
   - superseded — defect gone from current text.
     Set status: fixed. Append: resolution: resolved by SFN substrate sweep — <one line naming the new statement>. Append: changed: <files>.
   - narrowed — part remains.
     Keep status: open. Narrow proposal: to remainder. Add: recheck: yes. Add verification-notes line: "SFN sweep addressed <X>; remaining defect is <Y>".
   - unchanged — defect orthogonal to substrate.
     Keep status: open. Add verification-notes line: "Confirmed after SFN sweep — defect is <substrate-independent reason>".

Skip F075 and F042 — still held by 09-28 rows. Leave held.

Do not edit docs/spec/ in this pass. Only:
  docs/review/spec-audit-2026-09-29/F*.md
  docs/review/spec-audit-2026-09-29/INDEX.md § All findings status cells

Report a resolution table: id | verdict | one-line reason. Stop.
```

### Step 12 — commit Phase B

```
Land it. Commit as: audit(2026-09-29): resolve 17 substrate findings against SFN sweep
```

### Step 13 — push branch, open PR

Terminal:

```bash
git push -u origin spec/sfn-substrate-sweep
gh pr create --base develop --title "spec: Step Functions substrate sweep" --body "$(cat <<'EOF'
## Summary
- Sweeps docs/spec/** to align with SFN pivot (ADR: docs/adrs/saga-orchestration-engine.md)
- Four state machines named; media-sagas/SagaTimeoutIndex/TimeoutScanner substrate removed from spec
- Re-audits 17 spec-audit-2026-09-29 substrate findings against post-sweep spec

## Test plan
- [ ] python .github/scripts/docs_guard.py passes
- [ ] Grep docs/spec/ for media-sagas, SagaTimeoutIndex, TimeoutScanner returns zero hits
- [ ] INDEX.md § All findings reflects the re-audit outcomes
EOF
)"
```

---

## Phase C — resume 09-29 audit on non-substrate work

### Step 14 — new branch after PR merges to develop

Terminal:

```bash
git checkout develop
git pull
git checkout -b spec/if-match-coverage
```

### Step 15 — F046 / F047 If-Match decision

New Claude session:

```
/spec-audit-next F046
```

When it stops for the decision, reply with option letters. Example:

```
F046=B, F047=A, PATCH-item=leave-optional
```

Continue until the unit closes and the session reports the ITER summary.

### Step 16 — resume 09-29 top-to-bottom

Each turn:

```
/spec-audit-next 2026-09-29
```

Repeat. Feed decisions when the session stops for one. Loop until:

```
AUDIT 2026-09-29 COMPLETE
```

Commit at logical breakpoints (per unit or per wave). Ask for commits with:

```
/commit
```

Open a fresh PR per branch worth of work — do not stack the entire audit on one branch.

---

## Phase D — records-domain session (Karen / legal)

### Step 17 — prep briefing doc

New Claude session:

```
Prepare one briefing doc for the records-domain session with Karen covering these eleven decisions:

09-29 open, decision-owner records-domain:
  F004, F036, F039, F059, F088, F089, F090, F091

09-28 blocked, Wave 4:
  shared-arch/F022 — retention triggers + clock-start events enumeration
  ctx-metadata/F006 — RetentionScheduleDeprecated cascade gap
  ctx-registration/F005 — crypto-shred key store concrete name

For each: 3-line summary of what breaks today, the options with consequences, and the spec files each option touches. Output as a single markdown doc suitable to hand Karen.

Write to Z:/claudia/magiq/projects/magiq-media/reviews/records-domain-briefing-2026-09-30.md if that path exists, otherwise report the content inline.

Do not edit spec files.
```

### Step 18 — apply Karen's decisions

New branch:

```bash
git checkout develop && git pull
git checkout -b spec/records-domain-decisions
```

Per finding, new or continued session:

```
/spec-audit-next F004
```

Provide Karen's decision inline. Repeat for F036, F039, F059, F088, F089, F090, F091.

### Step 19 — close 09-28 Wave-4 blocked rows

Same branch. Per row:

```
/spec-audit-next shared-arch/F022
```

Provide the decision. Session auto-releases held 09-29 findings.

Repeat:

```
/spec-audit-next ctx-metadata/F006
/spec-audit-next ctx-registration/F005
```

### Step 20 — close remaining 09-28 blocked rows (Chase decisions)

Same branch or new one. Provide decision inline per invocation:

```
/spec-audit-next ctx-catalog/F004 <decision: dual-publish OR version-createdBy>
/spec-audit-next ctx-processing/F005 <decision: shape-line OR member-table>
/spec-audit-next ctx-catalog/F007 <decision: sync-cap-value>
/spec-audit-next ctx-catalog/F027 <decision: new-code-name>
/spec-audit-next ctx-registration/F004 <decision: remove-vs-guard>
/spec-audit-next ctx-registration/F007 <decision: align-vs-deviate>
```

---

## Exit check

### Step 21 — final verification

Terminal:

```bash
python .github/scripts/docs_guard.py
```

New Claude session:

```
Verify audit closure. Report:

1. docs/review/spec-audit-2026-09-28/WORKLIST.md — count of [ ], [!], [~], [x] rows. Only zero [ ] and zero [!] is done.

2. docs/review/spec-audit-2026-09-29/INDEX.md § All findings — count by status. Only records-domain findings (if unmet) and platform-gap entries should remain non-fixed.

3. docs_guard result.

4. git status.

If clean, print AUDIT LOOP CLOSED. Otherwise list the remaining rows and their owners.
```
