# Todos — magiq-media

## Add bulk delete media item command
_Captured: 2026-06-02T04:52:00Z_

The bulk delete media item needs to be implemented in the FolderDeleteFoanoutWorker.

---

## RESOLVED: deploy mechanism = cross-repo dispatch to cdk-magiq-media
_Captured: 2026-07-03 · Resolved: 2026-07-03_

Deploy is done by **`magiqsoftware/cdk-magiq-media`** (separate CDK/TypeScript repo),
not a step in magiq-media. `.github/workflows/build-and-push.yml` builds + pushes images
to the shared ECR (738608577325), then dispatches to the CDK repo.

**Integration contract** (implemented):
- magiq-media `dispatch-deploy` / `dispatch-staging` jobs send `repository_dispatch`
  (`event_type: deploy`) to cdk-magiq-media with `client_payload = { env, imageTag: <sha> }`.
- cdk `deploy.yml` listens on that dispatch, resolves `environment` from payload, assumes
  per-env `AWS_DEPLOY_ROLE_ARN` (secret) + `CDK_DEFAULT_ACCOUNT` (var), runs
  `cdk deploy --all --context env=… imageTag=… migrationsEnabled=true`.
- cdk pulls `<prefix>-<sha>` from shared ECR → build-once/deploy-that-artifact holds.

**OUTSTANDING — required before deploys actually run:**
1. **Create repo secret `CDK_DISPATCH_TOKEN`** in magiq-media — fine-grained PAT or GitHub
   App token with `contents: write` (dispatch) on cdk-magiq-media. Until set, the dispatch
   steps are skipped (guarded on token presence) — builds stay green, no deploy fires.
2. Cross-account ECR pull: each env's deploy role needs pull rights on the 738608577325 ECR.
3. cdk deploys only **8** hosts — `SagaOrchestrator.DocumentSigning` (`saga-document-signing`)
   is built by magiq-media but has no `ecrCode(...)` in cdk `magiq-media-stack.ts`. Wire it
   when the signing host is ready to deploy.
4. (Done) The per-env `AWS_DEPLOY_ROLE_ARN` **vars** on magiq-media environments were
   redundant — deploy role lives in cdk-magiq-media (secrets). Removed; magiq-media envs
   now carry no env-level vars.

See `spec/architecture/branching-and-deployment.md` → "Open questions".

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
