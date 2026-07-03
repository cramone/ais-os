# Branching & Deployment Strategy — Media Management

_Last updated: 2026-07-03_

---

## Quick reference — branch triggers & CI flow

**Branch naming**

| Branch | Pattern | Cut from | Merges to |
|--------|---------|----------|-----------|
| Production line | `main` | — | — |
| Integration (default) | `develop` | `main` | — |
| Release | `release/x.y` | `develop` | `main` + back to `develop` |
| Feature | `feature/<user>/<ticket>-<slug>` | `develop` | `develop` (PR) |
| Bugfix | `bugfix/<user>/<ticket>-<slug>` | `develop` | `develop` (PR) |
| Hotfix | `hotfix/<user>/<ticket>-<slug>` | `main` | `main` + `develop` |
| Infra/CI | `deploy/<user>/<slug>` | `develop` | `develop` (PR) |
| Release tag | `vMAJOR.MINOR.PATCH` | on `main` | — |

**Trigger → environment** (images always push to shared ECR `738608577325`)

| Trigger (ref) | Env | Account | Status |
|---------------|-----|---------|--------|
| push `develop` | **dev** | 989143135668 | ✅ active |
| push `release/**` | **qa** | 835494934465 | ✅ active |
| push `release/**` (gated promote) | **staging** | 727517389921 | ⛔ `STAGING_ENABLED=false` |
| push tag `v*` | **prod** | 614323302920 | ⛔ `PROD_ENABLED=false` |
| `workflow_dispatch` (pick env) | any | — | prod blocked unless `PROD_ENABLED=true` |

**Flow**

```
feature/chase/123-x ─PR─▶ develop ──────────▶ [dev]   auto (989143135668)
bugfix/chase/124-y  ─PR─┘

develop ─cut─▶ release/1.4 ─────────────────▶ [qa]    auto (835494934465)
                   │
                   └─(gate, DORMANT)─────────▶ [staging] (727517389921)  ⛔
                   │
                   ├─merge─▶ main ─tag v1.4.0▶ [prod] (614323302920)     ⛔
                   └─merge back▶ develop

main ─branch─▶ hotfix/chase/125-z ─┬─merge▶ main ─tag v1.4.1▶ [prod]     ⛔
                                   └─merge▶ develop
```

---

## Overview

magiq-media uses a **GitFlow** model with four AWS environments — `dev`, `qa`,
`staging`, `prod` — deployed as container images (ECR, arm64 Lambda) via the
`build-and-push.yml` GitHub Actions workflow.

Branch protection is enforced by GitHub **environment deployment-branch policies**:
a branch can only deploy to an environment its policy allows. The workflow resolves
the target environment from the branch that triggered it.

Promotion flows **left to right** — code never skips an environment:

```
develop ──▶ dev (auto)
   │
   └─ release/x.y ──▶ qa ──▶ staging (auto on push)
            │
            └─ merge to main + tag vX.Y ──▶ prod (tag-triggered)
```

---

## Branch types

| Branch            | Purpose                                              | Cut from   | Merges to            | Deploys to |
|-------------------|------------------------------------------------------|------------|----------------------|------------|
| `main`            | Production. Every commit is a shipped release.       | —          | —                    | **prod**   |
| `develop`         | Integration line. Default branch. Always deployable. | `main`     | —                    | **dev**    |
| `release/x.y`     | Release stabilisation for a version.                 | `develop`  | `main` **and** back to `develop` | **qa → staging** |
| `feature/<user>/<ticket>-<slug>` | New functionality.                    | `develop`  | `develop` (PR)       | —          |
| `bugfix/<user>/<ticket>-<slug>`  | Non-urgent fix for unreleased work.   | `develop`  | `develop` (PR)       | —          |
| `hotfix/<user>/<ticket>-<slug>`  | Urgent production fix.                | `main`     | `main` **and** `develop` | prod (via tag) |
| `deploy/<user>/<slug>`           | Infra/CI/CDK pipeline changes.        | `develop`  | `develop` (PR)       | —          |

Prefixes match existing repo convention (`feature/chase/…`, `bugfix/chase/…`,
`deploy/chase/…`). Include the ClickUp/ADO ticket number in the slug where one exists.

---

## Environment → branch policy

Enforced in GitHub (`repos/magiqsoftware/magiq-media/environments/*/deployment-branch-policies`).

| Env       | Allowed branches      | Trigger                          | Purpose                          |
|-----------|-----------------------|----------------------------------|----------------------------------|
| `dev`     | `develop`             | auto on push                     | Continuous integration sandbox   |
| `qa`      | `release/**`          | auto on push                     | QA / test verification           |
| `staging` | `release/**`          | Model B: gated promote after qa (**dormant** — account not ready)| Pre-prod, UAT, prod-like data    |
| `prod`    | `main`                | tag `v*` push (or manual dispatch)| Production                       |

### AWS account binding (Model A — account per environment)

Two distinct roles — do not conflate them:

- **ECR / build-push role** — `AWS_ECR_ROLE_ARN`, repo-level, **always the shared ECR
  account `738608577325`**. Every environment's build pushes images to this one central
  registry. Not overridden per env.
- **Deploy role** — lives in **`cdk-magiq-media`**, not here: per-env secret
  `AWS_DEPLOY_ROLE_ARN` + var `CDK_DEFAULT_ACCOUNT` on that repo's GitHub environments.
  magiq-media only builds/pushes + dispatches; the CDK repo assumes the deploy role and
  updates that account's Lambdas, pulling the image cross-account from the shared ECR.
  (magiq-media environments carry **no** env-level vars — earlier `AWS_DEPLOY_ROLE_ARN`
  vars here were redundant and removed.)

| Env     | Account name | Account ID (cdk `CDK_DEFAULT_ACCOUNT`) | Deploy trigger |
|---------|--------------|----------------|----------------|
| dev     | Development  | 989143135668   | active — push `develop` |
| qa      | QA           | 835494934465   | active — push `release/**` |
| staging | Demo         | 727517389921   | **disabled** (`STAGING_ENABLED=false`) — pending account + Tom approval |
| prod    | Prod         | 614323302920   | **disabled** (`PROD_ENABLED=false`) — pending account + Tom approval |

> **Cross-account ECR pull.** Each env account's deploy role needs pull access to the
> shared ECR in `738608577325` (ECR repository policy + role trust). Infra to set up
> before deploys work.

> **CI change required.** The current `build-and-push.yml` maps `main` → `dev` and
> has no `prod` path. To adopt this strategy the workflow must map `main`/tags → `prod`,
> and the `dev` and `prod` environment branch policies must be updated (drop `main`
> from `dev`; set `prod` policy to `main` + tag). See "CI changes" below.

---

## Everyday flow

### Feature / bugfix
1. Branch from `develop`: `feature/chase/33222-write-projectors`.
2. Open PR into `develop`. CI runs build + tests.
3. Squash-merge on green + review. `develop` auto-deploys to **dev**.

### Cutting a release
1. From `develop`: `git switch -c release/1.4`.
2. Push → auto-deploys to **qa**, then promote/verify into **staging**.
3. Only stabilisation commits (bug fixes, version bump) land on the release branch —
   no new features. Cherry-pick or PR fixes as needed.
4. When signed off:
   - Merge `release/1.4` → `main`.
   - Tag `main`: `git tag v1.4.0 && git push origin v1.4.0` → deploys to **prod**.
   - Merge `release/1.4` back into `develop` (so fixes aren't lost).
   - Delete the release branch.

### Hotfix (prod is broken)
1. Branch from `main`: `hotfix/chase/1490-null-asset`.
2. Fix, PR into `main`, tag `v1.4.1` → **prod**.
3. Merge back into `develop` (and any active `release/*`).

---

## Versioning

- Semantic versioning `vMAJOR.MINOR.PATCH`.
- Release branches are named for the minor line: `release/1.4`.
- Production deploys are always **tag-triggered** — the tag is the immutable record
  of what shipped. Image tags in ECR use the commit SHA (`api-<sha>`); `main` builds
  additionally tag `-latest`.

---

## CI changes required to adopt this strategy

The workflow today (`.github/workflows/build-and-push.yml`) only builds and pushes
images; it resolves env as `release/* → qa`, else `dev`. To align with GitFlow
main=prod:

1. **Trigger on tags** — add `tags: ['v*']` to the `push` trigger.
2. **Resolve prod** — in `resolve-env`, map a `v*` tag (or `refs/heads/main`) to `prod`.
3. **Resolve staging** — decide staging trigger: auto on `release/**` push after qa,
   or keep it manual-dispatch only. (Recommend: auto-deploy release/** to **qa** and
   **staging** in sequence, gated by an environment approval on staging.)
4. **Drop `main` → dev** — remove `main` from the `dev` branch policy so an accidental
   push to `main` cannot hit dev.
5. **Deploy step** — _resolved_: deploy is a **cross-repo dispatch to
   `cdk-magiq-media`** (see "Deploy handoff" below), not an in-repo step. Outstanding:
   create the `CDK_DISPATCH_TOKEN` secret and grant cross-account ECR pull.

### Deploy handoff — magiq-media → cdk-magiq-media

After the ECR push, magiq-media dispatches to the CDK repo, which owns the actual deploy:

```
build-and-push (images → shared ECR 738608577325)
      │  repository_dispatch  event_type: deploy
      │  client_payload: { env, imageTag: <git sha> }
      ▼
cdk-magiq-media  deploy.yml
      environment = payload.env          (GitHub required-reviewer gate for staging/prod)
      role  = env secret AWS_DEPLOY_ROLE_ARN     (that env's own AWS account)
      cdk deploy --all --context env=… imageTag=… migrationsEnabled=true
      → pulls <prefix>-<sha> from shared ECR cross-account, updates that account's Lambdas
```

- **Contract:** `imageTag` is the git SHA — cdk resolves `<prefix>-<sha>` per host, so the
  same artifact promotes dev → qa → staging → prod (no rebuild).
- **magiq-media jobs:** `dispatch-deploy` (dev/qa/prod, env from `publish-all`) and
  `dispatch-staging` (env=staging, `STAGING_ENABLED`-gated). Both skip until repo secret
  `CDK_DISPATCH_TOKEN` (dispatch rights on cdk-magiq-media) exists.
- **cdk env config:** `CDK_DEFAULT_ACCOUNT` var + `AWS_DEPLOY_ROLE_ARN` secret per env —
  dev 989143135668, qa 835494934465, staging 727517389921, prod 614323302920.
- **Known gap:** cdk deploys 8 hosts; `saga-document-signing` is built but not yet wired
  in cdk `magiq-media-stack.ts`.

Environment **required-reviewer** protection rules are recommended on `staging` and
`prod` so promotion needs a human approval, independent of branch policy.

---

## Open questions

- **Staging:** _decided_ — Model B gated promote from `release/**` after qa, with
  required-reviewer approval. **Model A** account isolation chosen: staging gets its own
  AWS account. Job is provisioned but **dormant** (`STAGING_ENABLED` flag off) until the
  account exists — see AIS-OS `todos.md` → "Review: enable staging deploy".
- **Deploy mechanism:** _resolved_ — cross-repo dispatch to `cdk-magiq-media` (see
  "Deploy handoff"). Blocked only on the `CDK_DISPATCH_TOKEN` secret + cross-account ECR pull.
- **`main` fast-forward vs merge:** decide merge policy for `release → main` (no-ff
  merge preserves release history; recommended).
