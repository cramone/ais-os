# Deploy Runbook — magiq-media ↔ cdk-magiq-media

_Status: 2026-07-06 — magiq-media's side is merged to `develop`
(`deploy/chase/cdk-branch-sync-deploy`). cdk-magiq-media's side (config
files, `deploy.yml` rewrite, `ORGANIZATION_ID` warning) is committed locally
on `develop`, not yet pushed. Captures the branch-mirroring + git-driven
reconciliation model worked out with Chase to close the app/infra drift gap.
See "Implementation status" below for exactly what's done vs. still open.
Supersedes the dispatch-only model described in `plans/deploy-handoff-tom.md`
and `CDK-ALIGNMENT-GAPS.md` (cdk-magiq-media), and builds on the
branch-naming conventions in `spec/architecture/branching-and-deployment.md`.

**Note on approval gating throughout this doc:** required-reviewer
protection on GitHub Environments needs GitHub Team or above for private
repos — confirmed via a 422 when we tried to set it up on this org. So
anywhere below that says a deploy "waits for reviewer approval" or is
"gated by required-reviewer," read that as: gated by `STAGING_ENABLED` /
`PROD_ENABLED` (account readiness) plus Tom's sign-off as a process
convention (confirmed before merging/tagging a release), not a
platform-enforced approval click. Revisit if the org upgrades its plan.

## Model summary

- **Mirrored branches.** cdk-magiq-media grows `develop`, `release/x.y`, and
  `main` branches matching magiq-media's, so infra promotes on the same
  left-to-right path as the app instead of always deploying off `main`.
- **Single source of truth per environment.** Each branch in cdk-magiq-media
  carries a small config file — `config/dev.json`, `config/qa.json`,
  `config/prod.json` — holding `{ "imageTag": "<sha>" }`. There is no
  `config/staging.json`: staging always deploys whatever `config/qa.json`
  currently holds, since it's validating exactly what QA already proved, not
  a separate build. That file, at the branch's HEAD, is the entire answer to
  "what's running in this environment": infra shape (the CDK code around it)
  and app version (the tag) together, in one place, with full git history.
- **One trigger, `main` excluded.** cdk-magiq-media deploys on `push` to
  `develop` / `release/**`, plus `v*` tags — not on a plain push to `main`.
  It doesn't matter whether the commit was a human's infra PR or
  magiq-media's CI bumping the `imageTag` field; both are "the branch's state
  changed," and the job always does the same thing: resolve env from branch
  name, read `imageTag` from that branch's config file, `cdk deploy --all`.
  Staging deploys automatically off the same `release/**` push that deploys
  qa — there's no separate "promote" push. There's no platform-enforced
  approval pause on it (required-reviewer rules aren't available on this
  org's GitHub plan) — the practical gate is `STAGING_ENABLED` plus Tom's
  sign-off as a process step before the release branch is cut.
- **magiq-media's role shrinks to two things:** build + push images to the
  shared ECR (738608577325), then push a one-line commit bumping the matching
  branch's config file in cdk-magiq-media. No `repository_dispatch`, no
  client-payload plumbing.
- **Prod is excluded from auto-reconciliation.** A push to `main` in
  cdk-magiq-media does not deploy prod by itself. Prod only moves on a tag
  push (which bumps `config/prod.json` in the same tagged commit) or a manual
  `workflow_dispatch` — gated in practice by `PROD_ENABLED` and Tom's sign-off
  as a process step, not a platform-enforced reviewer approval.
- **Expand/contract discipline**, independent of the above: additive infra
  (new table, new queue, new optional field) ships and merges *before* the app
  code that uses it, so it sits harmlessly unused until the app catches up.
  Destructive infra (rename, delete, drop a field) ships only *after* no
  deployed app version still depends on the old shape.
- **Tag both repos together at release time.** When `release/x.y` merges to
  `main` and gets tagged `vX.Y.0` in magiq-media, tag cdk-magiq-media's `main`
  at the same commit. Gives an unambiguous "app vX.Y ran against this exact
  infra" pairing without reconstructing it from config-file history.

| App branch | cdk branch | Deploys to | Account | Config file |
|---|---|---|---|---|
| `develop` | `develop` | dev | Development — 989143135668 | `config/dev.json` |
| `release/x.y` | `release/x.y` | qa | QA — 835494934465 | `config/qa.json` |
| `release/x.y` (same push, gated) | `release/x.y` | staging | Demo — 727517389921 | `config/qa.json` (shared with qa) |
| `main` (tag `vX.Y.Z`) | `main` (tag `vX.Y.Z`) | prod | Prod — 614323302920 | `config/prod.json` |

Region for all accounts: `ap-southeast-2`. Shared ECR lives in the DevOps
account, 738608577325, and is never overridden per environment.

`STAGING_ENABLED` and `PROD_ENABLED` now need to be set as repo variables in
**both** magiq-media (gates whether magiq-media even builds/tags for that
env) and cdk-magiq-media (gates whether the `deploy-staging` job runs at
all). Missing either one leaves the corresponding job dormant.

---

## Everyday developer flow (feature / bugfix)

1. Pick up the ticket on the Media board. Branch off `develop` in magiq-media:
   `feature/chase/<ticket>-slug` (or `bugfix/...`).
2. If the change needs new or changed infrastructure, also branch
   cdk-magiq-media off *its* `develop`, same ticket number in the name.
3. **Additive infra ships first.** Write and merge the infra PR into cdk's
   `develop` before the app PR. That merge alone redeploys dev — new
   resource, unused, no app change yet, nothing breaks.
4. Write and merge the app PR into magiq-media's `develop`. CI builds all
   hosts, pushes images tagged by commit SHA, then pushes a commit into
   cdk-magiq-media's `develop` bumping `config/dev.json`'s `imageTag`. That
   push is cdk's only trigger — dev redeploys with the new code against the
   infra that's already there.
5. **Destructive infra ships last.** If the change removes or reshapes
   something, reverse the order: ship the app change that stops depending on
   the old shape first, confirm it's deployed, then remove the old infra in a
   follow-up PR.

---

## Scenario 1 — new table: develop → Development → release cut → QA → staging/prod

**Develop → Development (989143135668)**

1. Branch cdk-magiq-media off `develop`. Add the new table construct
   (`TENANT#{TenantId}#{EntityId}` PK, CMK encryption, wired into the
   relevant `*-tables.construct.ts`), grant read/write to whichever
   Lambda(s) need it. PR, review, merge to cdk `develop`.
2. That push triggers cdk's dev deploy on its own: env resolves to dev,
   `config/dev.json` still points at the currently-running app SHA, so dev
   redeploys unchanged app code against the new table. Table exists, empty,
   unused — no behavior change.
3. Branch magiq-media off `develop`. Implement the read model / projection
   that uses the new table (`ITenantScoped`, `LastObservedAtUtc`, idempotent
   on `ProjectedVersion`, per the module conventions). PR, review, merge to
   magiq-media `develop`.
4. CI builds and pushes images for the new SHA, then bumps `config/dev.json`
   in cdk-magiq-media's `develop` to that SHA. Dev redeploys again — same
   table, new code. Feature is live in Development.

**Release cut → QA (835494934465)**

5. Cut `release/1.4` in magiq-media from `develop`, and cut a matching
   `release/1.4` in cdk-magiq-media from *its* `develop`. The table construct
   is already on cdk's `develop`, so it comes along automatically — no
   separate infra PR needed for the release.
6. Pushing `release/1.4` in magiq-media resolves env=qa, builds/pushes
   images, then bumps `config/qa.json` on cdk's `release/1.4` (not
   `develop`).
7. That push triggers cdk's qa deploy: `config/qa.json` on `release/1.4` has
   both the new table and the new imageTag together — QA gets table + code
   atomically, as one consistent release.
8. Only stabilization fixes land on `release/1.4` from here. If a fix needs
   an infra tweak, it goes into both repos' `release/1.4` branches together.

**QA → staging → prod**

9. Staging (Demo, 727517389921) reads `config/qa.json` directly — the same
   push that deployed qa in step 6 also kicks off the `deploy-staging` job
   automatically (once `STAGING_ENABLED` is set in both repos). There's no
   platform-enforced approval pause here — that needs a GitHub plan this org
   doesn't have — so the actual gate is getting Tom's sign-off before cutting
   the release branch, not a click in the GitHub UI. There's no separate
   config file and no separate promotion push either — it's the identical
   table + imageTag QA just validated.
10. On sign-off: merge `release/1.4` → `main` in **both** repos, tag
    `v1.4.0` in **both** at the same commit. The tag push in magiq-media
    resolves env=prod and bumps `config/prod.json` on cdk's `main` in that
    same tagged commit, which also triggers `cdk deploy --all` in prod
    directly — there's no reviewer-approval pause to wait behind, so the tag
    push itself needs to be the deliberate, signed-off action.
11. Merge `release/1.4` back into `develop` in both repos, delete both
    release branches.

---

## Scenario 2 — hotfix (prod is broken)

Hotfix branches cut from `main`, not `develop` — and critically, `main` isn't
covered by any auto-deploy branch policy today (only `develop`, `release/**`,
and tags are). That means a hotfix branch never silently deploys anywhere on
its own; validation has to be requested deliberately.

1. Branch magiq-media off `main`: `hotfix/chase/<ticket>-slug`. If the fix
   needs an infra change too, branch cdk-magiq-media off *its* `main` with
   the same name.
2. **Smoke-test before tagging prod.** Two ways to do this, manually — hotfix
   branches aren't in the automatic env→branch mapping by design, so nothing
   validates one for you unless you ask:
   - `workflow_dispatch` magiq-media's `build-and-push.yml` from the hotfix
     branch targeting `dev`. This builds a real image *and* runs
     `update-deploy-config`, which bumps `config/dev.json` on cdk's `develop`
     to the hotfix SHA — dev temporarily runs the hotfix until the next
     ordinary `develop` push overwrites it. Fine for a smoke test, just be
     aware of the side effect.
   - If the image is already built and sitting in ECR, `workflow_dispatch`
     cdk-magiq-media's `deploy.yml` directly with `env=dev` and an explicit
     `imageTag` override — deploys it without touching `config/dev.json` at
     all.
3. Once satisfied, PR the hotfix into `main` (both repos if infra was
   touched). Tag `v1.4.1` in **both** repos at the merge commit.
4. The tag push in magiq-media resolves env=prod, builds the fix, bumps
   `config/prod.json` on cdk's `main` in the same tagged commit — which
   triggers `cdk deploy --all` in prod directly, with no reviewer-approval
   pause. That makes the tag push itself the point of no return: don't tag
   until the fix is actually confirmed good.
5. Merge the hotfix back into `develop` **and** any active `release/*`
   branch, in both repos, so the fix isn't lost or overwritten by the next
   regular promotion. If it touched infra, merge the cdk-side hotfix branch
   back the same way.

---

## Scenario 3 — brand-new deploy (environment/account has nothing running yet)

Applies to standing up staging for the first time, or bootstrapping the whole
pipeline from scratch. The git-driven reconciliation model above depends on a
config file already existing with a valid `imageTag` — a new environment has
neither, so it needs a manual seeding pass before the normal flow takes over.

1. **AWS account prerequisites.** Create the account (or confirm it exists).
   In it: create `GitHubOidcMagiqMediaRole` trusting the deploying repo via
   OIDC, run `cdk bootstrap` (creates the `CDKToolkit` stack) in
   `ap-southeast-2`, and add the account to the shared ECR's cross-account
   pull policy (`ecr:GetAuthorizationToken`, `BatchGetImage`,
   `GetDownloadUrlForLayer`, `BatchCheckLayerAvailability`) in the DevOps
   account, 738608577325.
2. **GitHub environment setup.** Create the environment in cdk-magiq-media
   (dev/qa already exist; staging/prod need it) with `AWS_DEPLOY_ROLE_ARN`
   secret and `CDK_DEFAULT_ACCOUNT` var set. Required-reviewer protection
   isn't available on this org's GitHub plan (confirmed via a 422), so there's
   nothing else to add here — the environment itself is the only gate.
3. **Branch, if it doesn't exist yet.** Confirm cdk-magiq-media has the
   matching branch (`develop`, or the current `release/x.y` for a new
   staging account). For the very first bootstrap of the whole pipeline,
   this branch itself may need creating.
4. **Seed the config file.** There's no prior deploy to read an `imageTag`
   from, so create `config/<env>.json` by hand, seeded with whatever SHA is
   already built and sitting in the shared ECR for the corresponding
   magiq-media branch (or trigger one fresh `workflow_dispatch` build if
   nothing's been pushed yet). Commit it directly — this one commit is the
   only manual exception to "config changes always come from CI."
5. **First deploy will be slow and from-empty.** `cdk deploy --all` against a
   clean account creates everything from scratch — DynamoDB tables,
   OpenSearch domain (if enabled), SQS/SNS topology, Lambda functions, API
   Gateway. No existing tenants, no existing event stream. Run with
   `migrationsEnabled=true` explicitly for this first pass.
6. **Smoke test before flipping any gate.** Confirm the deploy end-to-end
   (health checks, a basic write + read round-trip) before setting
   `STAGING_ENABLED`/`PROD_ENABLED` or relying on the environment for real
   traffic. This mirrors the existing "smoke test dev first" step in
   `plans/deploy-handoff-tom.md`, generalized to any newly-bootstrapped
   environment.
7. From this point on, the environment behaves like any other — pushes to
   its matching branch (whether infra PRs or CI-driven `imageTag` bumps)
   reconcile automatically, except prod, which stays gated as described
   above.

---

## Implementation status

**Done:**

1. magiq-media's `build-and-push.yml`, `README.md`, and `CLAUDE.md` changes
   merged to `develop` (via `deploy/chase/cdk-branch-sync-deploy`):
   `dispatch-deploy`/`dispatch-staging` replaced by one `update-deploy-config`
   job — resolves the matching cdk branch (dev→develop, qa→same `release/x.y`
   name, prod→main), clones cdk-magiq-media, bumps the env's config file,
   commits, pushes. Still guarded on `CDK_DISPATCH_TOKEN` being present.
2. cdk-magiq-media: `config/dev.json`, `config/qa.json`, `config/prod.json`
   created, plus `config/README.md` explaining the model. All three seeded
   with the same placeholder (magiq-media `develop` HEAD, `489772a`) —
   replace with the real last-deployed SHA per environment before relying on
   these for an actual deploy, especially if qa/prod are behind develop.
3. cdk-magiq-media's `.github/workflows/deploy.yml` rewritten: `push` trigger
   on `develop`/`release/**`/`v*` tags (no `main`, no `repository_dispatch`),
   `resolve` job maps branch→env, `deploy` job reads `imageTag` from the
   matching config file (or a `workflow_dispatch` override), `deploy-staging`
   job reads `config/qa.json` and runs automatically off the qa push, gated
   by `STAGING_ENABLED`. **No required-reviewer protection** — confirmed via
   a 422 that this org's GitHub plan doesn't support it for private repos.
   Concurrency group added per environment.
4. `bin/magiq-media.ts`'s `ORGANIZATION_ID` fallback now logs a loud warning
   instead of silently deploying with the fake placeholder. It still
   defaults to `o-abc123test` if unset — this is a warning, not a hard
   fail, so it won't break local `cdk synth` for a dev with no `.env`.
5. `STAGING_ENABLED`/`PROD_ENABLED` repo variables confirmed present on
   magiq-media (`false`/`false`). Same variables need setting on
   cdk-magiq-media too (see below).
6. Confirmed via `gh`: all four GitHub Environments (`dev`/`qa`/`staging`/
   `prod`) exist in cdk-magiq-media with correct `AWS_DEPLOY_ROLE_ARN` +
   `CDK_DEFAULT_ACCOUNT` per environment (989143135668 / 835494934465 /
   727517389921 / 614323302920).

**Still open:**

7. cdk-magiq-media's `develop` branch, config files, `deploy.yml`, and
   `ORGANIZATION_ID` fix are committed locally on `develop` — not yet
   pushed. Pushing will fire a live `cdk deploy` against the Development
   account immediately (dev's `AWS_DEPLOY_ROLE_ARN`/`CDK_DEFAULT_ACCOUNT` are
   already configured), so push deliberately, not as a side effect.
8. Set `STAGING_ENABLED` / `PROD_ENABLED` repo variables on
   **cdk-magiq-media** — confirmed via `gh variable list` that neither
   exists there yet (new requirement — the staging gate now lives there too,
   not just in magiq-media).
9. Create the `CDK_DISPATCH_TOKEN` secret in magiq-media — confirmed via
   `gh secret list` that it doesn't exist yet. Still the standing blocker;
   needs `contents: write` for a git push rather than a dispatch event.
10. Tag cdk-magiq-media's `main` alongside magiq-media's `vX.Y.Z` tags at
    every prod release, going forward — a process step, not something to
    automate.
11. No required-reviewer gate exists or can exist on the current GitHub
    plan. If two-person approval before a staging/prod deploy actually
    matters (not just account-readiness gating), that requires either
    upgrading the org to GitHub Team+, or building an equivalent check
    outside GitHub's native environment protection (e.g., a manual approval
    step via a different tool). Worth a decision, not just a checkbox.
