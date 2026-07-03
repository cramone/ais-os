# Todos — magiq-media

## Add bulk delete media item command
_Captured: 2026-06-02T04:52:00Z_

The bulk delete media item needs to be implemented in the FolderDeleteFoanoutWorker.

---

## CI has no deploy step — images pushed but environments not rolled
_Captured: 2026-07-03_

`.github/workflows/build-and-push.yml` builds and pushes container images to ECR
(SHA-tagged, plus `-latest` on prod tag builds) but stops there — there is no step
that updates the running Lambdas/services to the new image. Need to confirm how
environments actually pick up a new image:

- CDK deploy step to add to the workflow? or
- A separate deploy pipeline already handles it? or
- Manual Lambda `update-function-code`?

Blocks the branching strategy from being truly end-to-end (push → running env).
See `spec/architecture/branching-and-deployment.md` → "CI changes required" #5 and
"Open questions".

---

## Review: enable staging deploy (Model A — dedicated AWS account)
_Captured: 2026-07-03_

Chose **Model A** (one AWS account per environment). Staging AWS account is not
provisioned yet, so the `deploy-staging` job in `.github/workflows/build-and-push.yml`
is provisioned but **dormant** — guarded by `vars.STAGING_ENABLED == 'true'` (unset =
skipped) and a placeholder step that `exit 1`s if run.

To enable when the account is ready:
1. Create staging AWS account + `GitHubOidcMagiqMediaRole` OIDC role in it.
2. (Done) Env-level `AWS_DEPLOY_ROLE_ARN` on `staging` =
   `arn:aws:iam::727517389921:role/GitHubOidcMagiqMediaRole`. Grant it cross-account pull
   on the shared ECR in `738608577325`.
3. Add required-reviewer protection rule on the `staging` environment (Model B gate).
4. Implement the real promote-to-staging deploy step (depends on the deploy-step gap above).
5. Set `STAGING_ENABLED = 'true'`.

Note: Model A implies dedicated accounts for **all** envs — dev/qa/prod still share
`738608577325` today. Prod-in-shared-account is the higher-risk piece. Worth an ADR +
decision-log entry for the full multi-account rollout.

---

## DISABLED until ready + Tom-approved: prod & staging deploys
_Captured: 2026-07-03_

ECR stays central in account `738608577325` (repo-level `AWS_ECR_ROLE_ARN`) — all envs
push images there. Per-env account bound as **env-level `AWS_DEPLOY_ROLE_ARN`** (role
`GitHubOidcMagiqMediaRole`), used by the future deploy step. Each env account's deploy
role needs cross-account pull rights on the `738608577325` ECR (repo policy + trust).

| Env     | Account name | Account ID     | Trigger status |
|---------|--------------|----------------|----------------|
| dev     | Development  | 989143135668   | **active** (push `develop`) |
| qa      | QA           | 835494934465   | **active** (push `release/**`) |
| staging | Demo         | 727517389921   | **DISABLED** (`STAGING_ENABLED=false`) |
| prod    | Prod         | 614323302920   | **DISABLED** (`PROD_ENABLED=false`) |

**prod** and **staging** deploys are OFF until: (a) their AWS accounts are ready to
accept deploys, and (b) **Tom approves**.

Re-enable checklist:
- prod: confirm account 614323302920 has `GitHubOidcMagiqMediaRole` OIDC role + ECR →
  Tom approval → set repo var `PROD_ENABLED='true'`. Add required-reviewer rule on the
  `prod` environment.
- staging: confirm account 727517389921 ready + real deploy step wired → Tom approval →
  set `STAGING_ENABLED='true'`. Add required-reviewer rule on `staging`.

Assumption to verify: OIDC role name is `GitHubOidcMagiqMediaRole` in every account.
The old repo-level default (`738608577325`) is now unused — all envs override per-account.

---
