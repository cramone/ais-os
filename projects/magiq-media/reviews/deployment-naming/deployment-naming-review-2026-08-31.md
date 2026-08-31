---
id: MM-005
type: review
project: magiq-media
workstream: deployment-naming
raised-by: []
status: done
outcome: plan
todo-id: fb73731b-a4e0-5fc7-a934-dd480dfadc98
created: 2026-08-31
exception: retrospective backfill — the plan it consumes (MM-004) predates the cycle, so this review was written after the work rather than before it. No paste-ready prompt file exists; no session was ever run from it.
---

# Deployment naming — environment suffix removal, verified

A **retrospective** review. It records what shipped against what MM-004 specified, so the workstream
enters the review cycle with a status that survives the next session.

Written because `plans/README.md` carried MM-004 as **Parked — "Four open decisions at the top of
the plan; ADR-first"**. Three of the four decisions were in fact taken and implemented. The fourth —
the ADR that was supposed to come *first* — is the only thing left, and it never got written.

## Scope

Verified 2026-08-31 against:

| Repo | Ref read |
|---|---|
| `magiq-media` | `feature/change-requests` (2026-08-27) |
| `cdk-magiq-media` | `feature/change-requests` (2026-08-24) |

Checked: MM-004 § *Change inventory* items 1–13 and § *Verification* items 17–20.

**Not checked:** items 17, 18 and 20 — `cdk diff`, `npm test`, `dotnet test`, and the post-deploy
`/healthz` probe. Nothing was run. Verification here is **source-level only**, and the cutover
(items 14–15) is a deploy-time question this review cannot answer.

## Findings

### DN-1 — The ADR was never written, and the repo knows it. Severity: Medium

MM-004's header names the deliverable as *"this plan **+ the ADR topic doc**
`deployment-and-resource-naming.md`, for review **before** any code changes."* The code landed; the
ADR did not.

`docs/adrs/deployment-and-resource-naming.md` does not exist on any branch. `docs/adrs/README.md:20`
carries the row with an explicit marker:

> | Deployment & Resource Naming | ⚠ **not written** — see below | Environment-agnostic resource naming (no environment-name suffix) … |

followed at line 22 by *"⚠ The Deployment & Resource Naming row above has no document behind it."*

This is the single open item in the workstream. The decision it should record is not lost — it is
reconstructable from MM-004 §§ 1, 14–15 and from the code — but it currently lives only in a
planning repo that is not code-reviewed, while the ADR index in the code repo advertises a gap.

Impact is bounded and real: the destructive-cutover consequence (CloudFormation *replaces* renamed
stateful resources, so dev/qa/staging lose data) is recorded nowhere a future engineer would look
before renaming something else.

### DN-2 — The naming change is complete in both repos. Severity: Low (record-keeping)

| MM-004 item | Evidence |
|---|---|
| 1 — cdk `resourceName` returns the bare name | `cdk-magiq-media/lib/config.ts:50-52`, doc comment updated |
| 1 — cdk `bucketName` = `{name}-{account}-{region}` | `lib/config.ts:61-62`, comment and example rewritten to `magiq-media-originals-111122223333-ap-southeast-2` |
| 2 — `Platform__DynamoDB__TableSuffix: ''` always | `lib/magiq-media-stack.js:182` |
| 3 — construct doc comments | `read-models` and `write-indexes` headers now read *"now always empty (environment-agnostic naming)"* |
| 7 — app `MediaResourceNaming` | XML summary rewritten; suffix no longer derived, defaults to empty |
| 19 — post-change grep for residual `-{env}` naming | Zero hits across tracked `.ts` sources |

`isProd` survives, as MM-004 item 1 required — still driving removal policy, log retention, API
throttling and DynamoDB deletion protection, all behavioural and all unchanged.

### DN-3 — Decision 4 resolved as "keep, repurposed" rather than "remove". Severity: Low

MM-004 § *Decisions to confirm* item 4 asked whether to remove the vestigial `ENVIRONMENT_NAME`
plumbing or leave it inert. Neither happened. It was **kept and given a different job**: selecting
the AWS Secrets Manager overlay (`magiq-media/<env>`) and, on cortex, Traefik router naming.

`src/shared/Media.Shared.Configuration/README.md:50` states the new contract exactly — *"Does **not**
drive resource naming (that's environment-agnostic)"* — and `MagiqSecretsOptions.cs:115` shows
`MAGIQ_SECRETS_ENV` taking precedence over it.

Good outcome, but it is a decision that was taken in code and documented in a component README
rather than in the ADR DN-1 is about. That is precisely the gap DN-1 describes.

### DN-4 — Stale build output contradicts the source. Severity: Low

`cdk-magiq-media/lib/constructs/compute/media-api-function.construct.js:52` still injects
`isProd(config) ? '' : \`-${config.env}\``, which reads as an unfixed site.

It is not. The file is untracked build output from 2026-05-12 — `.gitignore` excludes `*.js` and
`*.d.ts`, and the `.ts` source no longer exists. Left in the working tree it will mislead the next
grep, exactly as it did during this verification.

## Open Questions

1. **Answered:** were MM-004's four opening decisions ever taken? Three were, in code: decision 1
   (API Gateway stage segment) left as-is; decision 2 (`TableSuffix`) injected explicitly as `''`;
   decision 4 (`ENVIRONMENT_NAME`) kept and repurposed — see DN-3. Decision 3 (non-prod data
   discard) is a cutover question this review cannot verify from source.
2. **Answered:** is MM-004 done? Code, yes. The plan is not, because item 13 — the ADR — is in
   scope and unwritten. See DN-1.
3. **Answered:** does the ADR gap warrant reopening the code work? No. The code is consistent and
   verified across both repos. The gap is documentation of a decision already taken.

## Dependencies

None. MM-004 depends on no other document in this project.

## Recommended sequencing

1. **Write `docs/adrs/deployment-and-resource-naming.md`** and replace the ⚠ row in
   `docs/adrs/README.md`. Content is reconstructable from MM-004 §§ 1 and 14–15 plus DN-3. The
   consequence that must survive into the ADR: renaming a stateful resource makes CloudFormation
   *replace* it, so every non-prod tier loses data on cutover. This closes DN-1, and with it MM-004.
2. **Delete the stale `.js` / `.d.ts` build output** from `cdk-magiq-media/lib/` (DN-4), or leave it
   and accept that the next grep gets the same false positive.
3. **Run the verification MM-004 § 17–18, 20 called for** — `cdk diff --context env=dev` and
   `--context env=prod` (prod must show no resource-name diffs), `npm test`, `dotnet test`, then
   `/healthz` after a dev deploy. Converts this review from source-level to verified.

Item 1 is the whole remaining workstream. Items 2 and 3 are hygiene.

## Related

- MM-004 — the plan this review consumes, `plans/deployment-naming/remove-env-suffix-plan.md`
- `docs/adrs/README.md:20-22` — the ⚠ row and its own warning about itself
- `src/shared/Media.Shared.Configuration/README.md` — where DN-3's contract is currently recorded
